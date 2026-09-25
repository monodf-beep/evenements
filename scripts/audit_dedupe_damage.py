#!/usr/bin/env python3
"""Audit RÉTROSPECTIF des fusions de doublons déjà enregistrées par scripts/dedupe.py.

POURQUOI : deux défauts de la déduplication ont été corrigés le 2026-08-02 (commit 40de3bf),
mais un correctif n'agit que sur les fusions À VENIR — les dégâts déjà inscrits en base y
restent, invisibles, et continuent d'alimenter la rédaction (enrich.py agrège la matière des
doublons) puis la traduction. Deux familles de dégâts :

  1. APPARIEMENT À TORT — `cross_lang_same` appariait deux titres sur des mots-outils :
     « Une semaine pas plus » (théâtre, Chambéry) a été fusionné avec « Fête du lac 2026 :
     les spectateurs qui n'habitent PAS Annecy paieront PLUS cher » (Google News), sur les
     seuls tokens {pas, plus}. Le contenu d'un événement étranger s'est retrouvé dans un
     vrai événement (fiche IT publiée sous « Festa del Lago 2026 » sur un spectacle).
  2. DESCRIPTION VOLÉE — `merge_group` gardait la description la PLUS LONGUE en brut : un
     item Google News RSS (un `<a href>` dont l'URL encodée pèse des centaines de caractères
     pour zéro mot de contenu) écrasait systématiquement la vraie description du gagnant,
     y compris lors de fusions PARFAITEMENT CORRECTES.

Ce script relit chaque paire (perdant `statut='merged'` + `duplicate_of` → gagnant) et la
re-teste avec le code CORRIGÉ, importé et non recopié (`same_story`, `cross_lang_same`,
`_text_len`) : une paire que le code d'aujourd'hui n'apparierait plus est, par construction,
un dégât de l'ancienne logique. S'y ajoutent les contradictions factuelles (villes, lieux,
dates) et la mesure de substance des descriptions.

LECTURE SEULE ABSOLUE : aucun UPDATE / INSERT / DELETE, aucune option --apply, aucun appel
LLM (100 % déterministe). Le script ne fait que lire et classer par gravité ; la réparation
se décide à la main, cas par cas, à partir de cette liste.

Usage (VPS) :
    .venv/bin/python -m scripts.audit_dedupe_damage                  # tout
    .venv/bin/python -m scripts.audit_dedupe_damage --limit 20       # 20 cas par gravité
    .venv/bin/python -m scripts.audit_dedupe_damage --published-only # gagnants sur l'agenda
"""
from __future__ import annotations
import argparse
import os
import re
import sqlite3
import sys
import unicodedata
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils.sources import same_story
# Version CORRIGÉE des heuristiques : importée, jamais recopiée — l'audit doit rester
# aligné sur le code de production, y compris ses futures corrections.
from scripts.dedupe import cross_lang_same, _sig_tokens, _text_len, _years_incompatible

log = get_logger("audit-dedupe-damage")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

# --- Seuils ---------------------------------------------------------------
ECART_JOURS = 30            # au-delà : dates de début « éloignées »
ECART_JOURS_GRAVE = 180     # au-delà : deux éditions/événements distincts, sans discussion
DESC_BLOB_TEXTE_MAX = 80    # texte visible d'un blob : quasi nul
DESC_BLOB_RATIO = 2.5       # brut / texte visible : un blob est surtout des balises + URL
DESC_PAUVRE_MIN = 100       # écart de texte visible en deçà duquel on ne dit rien

GRAVITES = ("certain", "probable", "a_verifier")
LIBELLES = {
    "certain": "CERTAIN — dégât matériel constaté ou double contradiction",
    "probable": "PROBABLE — un signal fort, à corriger sauf preuve du contraire",
    "a_verifier": "À VÉRIFIER — un seul signal faible, jugement humain requis",
}

# Villes ÉQUIVALENTES d'une langue à l'autre : sur un territoire transfrontalier, le même
# lieu s'écrit différemment selon la source (FR/IT). Sans cette table, toute fusion
# inter-langue légitime serait signalée « villes différentes » — faux positif garanti.
_VILLES_EQUIV = [
    {"turin", "torino"}, {"aoste", "aosta"}, {"nice", "nizza"}, {"milan", "milano"},
    {"ivree", "ivrea"}, {"suse", "susa"}, {"coni", "cuneo"}, {"genes", "genova"},
    {"chambery", "ciamberi"}, {"courmayeur", "cormaiore"}, {"pignerol", "pinerolo"},
    {"saluces", "saluzzo"},
]


def _norm(s: str) -> str:
    """minuscule, sans accents, ponctuation réduite — pour comparer des libellés."""
    s = unicodedata.normalize("NFD", (s or "").strip().lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def _mots(s: str) -> set[str]:
    """Mots significatifs (3+ lettres) d'un libellé normalisé."""
    return {m for m in _norm(s).split() if len(m) >= 3}


def _villes_differentes(a: str, b: str) -> bool:
    """True si les deux villes sont renseignées ET manifestement distinctes.

    Conservateur : on ne signale que si AUCUN mot commun, si aucune ne contient l'autre
    (« Chambéry » vs « Chambéry (73) ») et si elles ne sont pas deux graphies FR/IT de la
    même ville. Un doute = pas de signalement."""
    na, nb = _norm(a), _norm(b)
    if not na or not nb or na == nb:
        return False
    if na in nb or nb in na:
        return False
    ma, mb = _mots(a), _mots(b)
    if ma & mb:
        return False
    for equiv in _VILLES_EQUIV:
        if (ma & equiv) and (mb & equiv):
            return False
    return True


# Mots de LIEU purement génériques : ils changent de langue et de rédacteur sans que le
# lieu change (« Piazza Roma » / « Place Roma », « Salle des fêtes » / « Sala »). Les
# retirer évite de crier « lieux différents » sur une fusion inter-langue légitime.
_LIEU_GENERIQUE = {
    "place", "piazza", "piazzale", "salle", "sala", "espace", "spazio", "centre",
    "centro", "theatre", "teatro", "musee", "museo", "eglise", "chiesa", "chateau",
    "castello", "palais", "palazzo", "parc", "parco", "jardin", "giardino", "rue",
    "via", "viale", "corso", "avenue", "boulevard", "cour", "cortile", "auditorium",
    "mediatheque", "biblioteca", "bibliotheque", "des", "les", "aux", "del", "della",
    "delle", "dei", "degli", "ville", "citta", "comune", "commune", "maison", "casa",
}


def _lieux_differents(a: str, b: str) -> bool:
    """True si les deux lieux sont renseignés et ne partagent AUCUN mot DISTINCTIF.

    Signal volontairement faible (jamais suffisant à lui seul dans `_classer`) : un même
    lieu s'écrit de vingt façons (« Théâtre Charles Dullin » / « Charles Dullin ») et
    change de langue d'une source à l'autre."""
    ma, mb = _mots(a) - _LIEU_GENERIQUE, _mots(b) - _LIEU_GENERIQUE
    if not ma or not mb:
        return False
    return not (ma & mb)


def _date_iso(row: dict) -> str | None:
    """Date de début la plus fiable d'une fiche, en ISO.

    `date_event_start` (extraite du texte par scripts/dates.py) prime sur `date_start`
    (brut de collecte, parfois du texte libre) — on n'accepte qu'un AAAA-MM-JJ reconnaissable."""
    for champ in ("date_event_start", "date_start"):
        m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", str(row.get(champ) or ""))
        if m:
            try:
                return date(int(m[1]), int(m[2]), int(m[3])).isoformat()
            except ValueError:
                continue
    return None


def _ecart_jours(a: dict, b: dict) -> int | None:
    """Écart en jours entre les deux dates de début, ou None si l'une manque."""
    da, db = _date_iso(a), _date_iso(b)
    if not da or not db:
        return None
    return abs((date.fromisoformat(da) - date.fromisoformat(db)).days)


def _est_blob(desc: str | None) -> bool:
    """La description est-elle un BLOB sans contenu (item Google News RSS ou équivalent) ?

    Signature : presque pas de texte visible, mais un volume brut disproportionné (balises
    + URL encodée). C'est exactement ce que l'ancien `merge_group` privilégiait."""
    brut = desc or ""
    texte = _text_len(brut)
    if texte > DESC_BLOB_TEXTE_MAX:
        return False
    if "news.google.com" in brut:
        return True
    return bool(brut) and len(brut) >= DESC_BLOB_RATIO * max(texte, 1)


def _apparie_aujourdhui(ta: str, tb: str) -> bool:
    """Le code CORRIGÉ apparierait-il encore ces deux titres ?

    Même expression que `dedupe._groups` : same_story (avec la garde années) OU
    cross_lang_same. On teste les DEUX voies sans savoir laquelle a produit la fusion :
    si aucune ne matche aujourd'hui, la fusion ne serait plus faite, point.

    Une exception AVANT tout calcul : deux titres IDENTIQUES (ou l'un contenu dans l'autre,
    à condition que le plus court porte au moins 2 tokens significatifs) décrivent le même
    événement, quoi qu'en disent les heuristiques. `same_story` exige 3 mots significatifs
    ou un nom propre à majuscule interne : « Fête de la musique 2026 » ne s'apparie même
    pas avec lui-même. Sans cette exception, l'audit signalerait des fusions évidemment
    justes — un faux positif qui décrédibiliserait tout le rapport."""
    na, nb = _norm(ta), _norm(tb)
    if na and nb and (na == nb
                      or ((na in nb or nb in na)
                          and len(_sig_tokens(ta if len(na) <= len(nb) else tb)) >= 2)):
        return True
    return (same_story(ta, tb) and not _years_incompatible(ta, tb)) or cross_lang_same(ta, tb)


def _titre_pauvre(titre: str) -> bool:
    """Titre trop pauvre pour apparier quoi que ce soit : moins de 2 tokens significatifs
    une fois la liste _STOP corrigée appliquée. C'est le profil exact de « Une semaine pas
    plus » — un titre bref fait de mots-outils, qui s'appariait avec presque n'importe quoi."""
    return len(_sig_tokens(titre)) < 2


def _analyser_paire(gagnant: dict, perdant: dict) -> dict:
    """Signaux + gravité d'une fusion déjà enregistrée. Pure, sans I/O."""
    tg, tp = gagnant.get("title") or "", perdant.get("title") or ""
    sig: dict[str, bool] = dict.fromkeys(
        ("appariement_perdu", "titre_pauvre", "villes_differentes", "lieux_differents",
         "dates_eloignees", "dates_tres_eloignees", "desc_volee_blob", "desc_appauvrie",
         "gagnant_fusionne", "gagnant_absent"), False)
    motifs: list[str] = []

    # 0) Gagnant introuvable : rien à comparer, tout signal calculé contre une fiche
    # fantôme serait du bruit. On sort immédiatement.
    if perdant.get("_gagnant_absent"):
        sig["gagnant_absent"] = True
        motifs.append(f"duplicate_of pointe sur un id introuvable ({perdant['duplicate_of']}) "
                      "— le perdant est orphelin, sa matière n'a rejoint aucune fiche")
        return {"gagnant": gagnant, "perdant": perdant, "signaux": sig, "motifs": motifs,
                "ecart_jours": None, "gravite": _classer(sig)}

    # 1) Appariement : le code corrigé referait-il cette fusion ?
    sig["appariement_perdu"] = not _apparie_aujourdhui(tg, tp)
    if sig["appariement_perdu"]:
        motifs.append("les titres ne s'apparient PLUS avec la version corrigée "
                      "(same_story + cross_lang_same) — fusion issue de l'ancienne logique")
    sig["titre_pauvre"] = _titre_pauvre(tg) or _titre_pauvre(tp)
    if sig["appariement_perdu"] and sig["titre_pauvre"]:
        motifs.append("un des deux titres a moins de 2 tokens significatifs : il pouvait "
                      "s'apparier à presque n'importe quoi via les mots-outils")

    # 2) Contradictions factuelles
    sig["villes_differentes"] = _villes_differentes(gagnant.get("ville"), perdant.get("ville"))
    if sig["villes_differentes"]:
        motifs.append(f"villes différentes : « {gagnant.get('ville')} » ≠ "
                      f"« {perdant.get('ville')} »")
    sig["lieux_differents"] = _lieux_differents(gagnant.get("lieu"), perdant.get("lieu"))
    if sig["lieux_differents"]:
        motifs.append(f"lieux sans un mot commun : « {gagnant.get('lieu')} » ≠ "
                      f"« {perdant.get('lieu')} »")

    ecart = _ecart_jours(gagnant, perdant)
    sig["dates_eloignees"] = ecart is not None and ecart > ECART_JOURS
    sig["dates_tres_eloignees"] = ecart is not None and ecart > ECART_JOURS_GRAVE
    if sig["dates_eloignees"]:
        motifs.append(f"dates de début éloignées de {ecart} jours "
                      f"({_date_iso(gagnant)} vs {_date_iso(perdant)})")

    # 3) Substance des descriptions (le gagnant a-t-il hérité d'un blob ?)
    tg_len, tp_len = _text_len(gagnant.get("description")), _text_len(perdant.get("description"))
    sig["desc_volee_blob"] = (_est_blob(gagnant.get("description"))
                              and tp_len >= max(DESC_PAUVRE_MIN, 3 * max(tg_len, 1)))
    sig["desc_appauvrie"] = (not sig["desc_volee_blob"]
                             and tp_len - tg_len >= DESC_PAUVRE_MIN
                             and tp_len >= 2 * max(tg_len, 1))
    if sig["desc_volee_blob"]:
        motifs.append(f"description du gagnant = BLOB sans contenu ({tg_len} car. de texte "
                      f"visible pour {len(gagnant.get('description') or '')} bruts) alors que "
                      f"le perdant en a {tp_len} — la vraie description a été écrasée")
    elif sig["desc_appauvrie"]:
        motifs.append(f"description du gagnant nettement plus pauvre que celle du perdant "
                      f"({tg_len} vs {tp_len} car. de texte visible) — matière perdue")

    # 4) Anomalie de structure : le gagnant est lui-même un perdant (chaîne de fusions),
    # ce que dedupe ne produit pas — la matière a transité par un intermédiaire.
    sig["gagnant_fusionne"] = bool(perdant.get("_gagnant_fusionne"))
    if sig["gagnant_fusionne"]:
        motifs.append("le gagnant est lui-même marqué 'merged' — chaîne de fusions")

    return {"gagnant": gagnant, "perdant": perdant, "signaux": sig, "motifs": motifs,
            "ecart_jours": ecart, "gravite": _classer(sig)}


def _classer(sig: dict[str, bool]) -> str | None:
    """Gravité d'une fusion, du plus dur au plus douteux. None = rien à signaler.

    - CERTAIN : soit le dégât est MATÉRIEL et lisible dans la donnée (le gagnant porte un
      blob à la place de sa description) — aucune inférence ; soit DEUX signaux
      indépendants se contredisent (le code corrigé n'apparierait plus ces titres ET les
      faits divergent : ville ou date). Deux erreurs ne se compensent pas par hasard.
    - PROBABLE : un signal fort seul (villes différentes, dates à plus de six mois), ou
      l'appariement perdu confirmé par un signal secondaire.
    - À VÉRIFIER : un seul signal faible, qui a une explication innocente plausible.

    Le désaccord de LIEU n'est JAMAIS suffisant seul : deux sources nomment le même lieu
    de deux façons (et pas dans la même langue), le taux de faux positifs serait trop haut.
    """
    if sig["gagnant_absent"]:
        return "certain"
    if sig["desc_volee_blob"]:
        return "certain"
    if sig["appariement_perdu"] and (sig["villes_differentes"] or sig["dates_tres_eloignees"]):
        return "certain"
    if sig["villes_differentes"] or sig["dates_tres_eloignees"]:
        return "probable"
    if sig["appariement_perdu"] and (sig["titre_pauvre"] or sig["desc_appauvrie"]
                                     or sig["lieux_differents"] or sig["dates_eloignees"]):
        return "probable"
    if (sig["appariement_perdu"] or sig["desc_appauvrie"] or sig["dates_eloignees"]
            or sig["gagnant_fusionne"]):
        return "a_verifier"
    return None


def analyser_fusions(rows: list[dict]) -> list[dict]:
    """Toutes les fusions suspectes d'un jeu de lignes events_raw. Pure, sans I/O — pour
    être appelée telle quelle par un orchestrateur (scripts/weekly_audits.py)."""
    par_id = {r["id"]: r for r in rows}
    suspects = []
    for perdant in rows:
        if (perdant.get("statut") or "") != "merged" or not perdant.get("duplicate_of"):
            continue
        gagnant = par_id.get(perdant["duplicate_of"])
        perdant = dict(perdant)
        if gagnant is None:
            # Gagnant introuvable : la fusion a détruit le rattachement (fiche purgée ?).
            perdant["_gagnant_absent"] = True
            gagnant = {"id": perdant["duplicate_of"], "title": "(introuvable)"}
        else:
            perdant["_gagnant_fusionne"] = (gagnant.get("statut") or "") == "merged"
        cas = _analyser_paire(gagnant, perdant)
        if cas["gravite"]:
            suspects.append(cas)
    return suspects


def _afficher(cas: dict) -> None:
    g, p = cas["gagnant"], cas["perdant"]
    pub = f"WP#{g['wp_post_id_as']}" if g.get("wp_post_id_as") else "NON publié"
    print(f"\n  gagnant  [{g['id']}] ({pub}) « {(g.get('title') or '')[:70]} »")
    print(f"  perdant  [{p['id']}] « {(p.get('title') or '')[:70]} »")
    for m in cas["motifs"]:
        print(f"     → {m}")


def main(argv=None) -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(
        description="Audit RÉTROSPECTIF (lecture seule) des fusions de doublons déjà "
                    "enregistrées : re-teste chaque paire avec le code corrigé.")
    parser.add_argument("--limit", type=int, default=0,
                        help="Nombre de cas AFFICHÉS par gravité (0 = tous). Les comptes "
                             "restent toujours calculés sur la totalité.")
    parser.add_argument("--published-only", action="store_true",
                        help="Ne garder que les fusions dont le GAGNANT est publié sur "
                             "l'agenda (wp_post_id_as) — les dégâts déjà visibles en ligne.")
    parser.add_argument("--tout", action="store_true",
                        help="Inclure les fusions dont l'événement est DÉJÀ PASSÉ. Par "
                             "défaut elles sont comptées à part et non détaillées : les "
                             "réparer ne sert personne (voir plus bas).")
    args = parser.parse_args(argv)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(
        "SELECT id, title, description, date_start, date_event_start, date_event_end, "
        "lieu, ville, territoire, url_source, source_type, statut, duplicate_of, "
        "wp_post_id_as "
        "FROM events_raw").fetchall()]
    conn.close()

    fusions = sum(1 for r in rows
                  if (r.get("statut") or "") == "merged" and r.get("duplicate_of"))
    suspects = analyser_fusions(rows)
    if args.published_only:
        suspects = [c for c in suspects if (c["gagnant"].get("wp_post_id_as") or 0) > 0]

    # ⚠️ PARTAGE À VENIR / PASSÉ, ajouté le 2026-08-03 sur une remarque de Franck :
    # « on peut peut-être arrêter de travailler sur les choses qui sont déjà passées ».
    # Elle est juste, et le rapport la contredisait : il présentait 94 cas comme s'ils
    # comptaient tous, alors que la fiche qui en concentre le tiers — [1789] « Torino
    # crocevia di sonorità », qui a absorbé Vermeer, Hokusai et un communiqué sur le
    # PNRR — était datée du 10 juillet, soit passée depuis trois semaines. Réparer une
    # fiche dont l'événement a eu lieu ne sert personne : elle ne sera pas republiée et
    # plus aucun visiteur ne la cherche. Un audit qui mélange les deux fabrique du
    # travail au lieu d'en désigner.
    #
    # LIMITE ASSUMÉE, et elle compte : la date lue est celle de la BASE, or c'est
    # précisément ce qu'une mauvaise fusion peut avoir corrompu (WP#6798 portait la date
    # d'un autre événement). Une fiche classée « passée » ici peut donc être à venir en
    # réalité. C'est pourquoi les passées sont COMPTÉES et non supprimées du rapport :
    # --tout les redétaille quand on veut aller les regarder.
    aujourdhui = date.today().isoformat()

    def _a_venir(cas) -> bool:
        g = cas["gagnant"]
        d = (g.get("date_event_end") or g.get("date_event_start") or "").strip()[:10]
        return (not d) or d >= aujourdhui      # sans date : on ne classe pas en « passé »

    passees = [c for c in suspects if not _a_venir(c)]
    if not args.tout:
        suspects = [c for c in suspects if _a_venir(c)]

    print(f"\n{fusions} fusion(s) enregistrée(s) en base · {len(suspects)} suspecte(s)"
          f"{' (gagnant publié)' if args.published_only else ''}"
          f"{' — À VENIR uniquement' if (passees and not args.tout) else ''}\n")
    if passees and not args.tout:
        print(f"  ({len(passees)} autre(s) cas écarté(s) : l'événement du gagnant est DÉJÀ")
        print(f"   PASSÉ, les réparer ne sert personne. --tout pour les voir.")
        print(f"   ⚠ la date vient de la BASE — une fusion fautive a pu la corrompre.)\n")

    comptes: dict[str, int] = {}
    for gravite in GRAVITES:
        lot = [c for c in suspects if c["gravite"] == gravite]
        comptes[gravite] = len(lot)
        if not lot:
            continue
        # Les cas les plus « chargés » (plusieurs motifs) d'abord : ce sont les plus nets.
        lot.sort(key=lambda c: (-len(c["motifs"]), c["gagnant"]["id"]))
        montres = lot[:args.limit] if args.limit else lot
        print(f"\n=== {LIBELLES[gravite]} — {len(lot)} cas ===")
        for cas in montres:
            _afficher(cas)
        if len(montres) < len(lot):
            print(f"\n  … {len(lot) - len(montres)} autre(s) cas non affiché(s) (--limit "
                  f"{args.limit}).")

    print("\n--- Récapitulatif ---")
    for gravite in GRAVITES:
        print(f"  {gravite:<12} : {comptes[gravite]}")
    publies = sum(1 for c in suspects if (c["gagnant"].get("wp_post_id_as") or 0) > 0)
    print(f"  {'TOTAL':<12} : {len(suspects)} sur {fusions} fusion(s) "
          f"— dont {publies} avec un gagnant DÉJÀ publié sur l'agenda")
    if passees and not args.tout:
        print(f"  {'passées':<12} : {len(passees)} écartée(s) — événement déjà eu lieu")
    print("\n(lecture seule : rien n'a été modifié. Chaque cas se répare à la main — "
          "défusionner, ou republier la fiche après avoir rendu sa description.)\n")

    log.info("Audit dédup : %d fusion(s) scannée(s), %d suspecte(s) "
             "(certain=%d, probable=%d, à vérifier=%d)", fusions, len(suspects),
             comptes["certain"], comptes["probable"], comptes["a_verifier"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
