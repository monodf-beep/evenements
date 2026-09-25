#!/usr/bin/env python3
"""La doctrine rédactionnelle en UN seul texte, servable à un agent qui écrit ailleurs.

D'OÙ ÇA VIENT. Franck, 06/09/2026 : « c'est pénible quand je demande de la rédaction ici
sur Claude, je dois systématiquement expliquer que c'est via Obsidian, le ton, la
doctrine, le vocabulaire etc. » Le pipeline, lui, n'a jamais ce problème : `utils/voix.py`
et `utils/vocabulaire.py` lisent les notes Obsidian du VPS à CHAQUE exécution. Le trou
était ailleurs — une session de chat (Claude Chrome, Cowork, Claude Code sur le web) ne
tourne pas sur le VPS et n'a donc, elle, aucun moyen d'aller lire ces notes. La consigne
écrite jusqu'ici était « demander à Franck de coller la sortie de deux commandes » :
c'est-à-dire lui faire refaire à la main, à chaque texte, exactement ce dont il se
plaignait. Ce module existe pour que plus personne n'ait à coller quoi que ce soit.

CE QU'IL FAIT, ET CE QU'IL NE FAIT PAS. Il ASSEMBLE, il ne stocke rien : chaque appel
relit les notes. Aucun cache, aucune copie dans le dépôt. La règle du 05/09 (« tout doit
être dans Obsidian, les règles ne doivent pas vivre dans GitHub ») tient donc toujours —
ce texte est une VUE, périmée une seconde après avoir été rendue, et il le dit lui-même
en tête. Le jour où quelqu'un colle sa sortie dans un fichier versionné, la divergence
recommence (cf. `docs/VOCABULAIRE_OBSIDIAN.md`, qui raconte la précédente).

TROIS BLOCS, DEUX MONDES :
  1. la VOIX éditoriale        — Obsidian (filet : `docs/voix/VOIX.md`, dans le dépôt) ;
  2. le VOCABULAIRE interdit   — Obsidian, sans filet (choix de Franck le 05/09) ;
  3. la CHARTE éditoriale      — `docs/CHARTE_EDITORIALE.md`, dans le dépôt.

ET IL CRIE QUAND UN BLOC MANQUE. C'est la seule différence assumée avec le pipeline :
`utils/vocabulaire.interdits()` renvoie `()` en silence quand la note est injoignable, et
c'est voulu — « continuer sans filtre, silencieusement » plutôt que bloquer une
publication. Ici le lecteur est un rédacteur : un silence lui ferait croire qu'il a la
doctrine alors qu'il n'a rien, et il écrirait sans filtre en pensant le contraire. Un zéro
doit dire s'il vient d'un échec ou d'une absence de règles (CLAUDE.md, journal du 11/08) :
chaque bloc porte donc sa provenance, sa taille, et son alerte le cas échéant — en TÊTE
du texte servi, pas dans un log que personne ne lit.

NOM ET VOISINAGE. Ce module s'appelle `doctrine_redaction` et non `doctrine` : il existe
déjà un `utils/doctrine.py` dans ce dépôt, et il parle d'autre chose — la doctrine
d'AFFICHAGE (`config/doctrine_affichage.md`, les choix délibérés que le site ne montre
pas, lue par `scripts/panel_site.py`). Deux « doctrines » pour deux objets : ici ce qu'on
écrit, là-bas ce qu'on montre. Le 21/09, en créant ce fichier, j'ai commencé par écraser
l'autre — le nom seul m'avait suffi pour croire la place libre.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CHARTE = ROOT / "docs" / "CHARTE_EDITORIALE.md"


def _sous_le_depot(chemin: str) -> bool:
    """True si ce chemin vit DANS ce dépôt — donc si c'est le filet versionné qui
    répond, et pas Obsidian. Distinction invisible autrement : les deux rendent un
    texte de voix parfaitement plausible."""
    try:
        Path(chemin).resolve().relative_to(ROOT)
        return True
    except (ValueError, OSError):
        return False


def _bloc_voix() -> dict:
    from utils import voix as voixmod
    st = voixmod.voix_status()
    texte = voixmod.voix_integrale()
    chemins = [{"chemin": s["path"], "existe": s["exists"], "chars": s["chars"],
                "notes": [f["title"] or f["name"] for f in s["files"]]}
               for s in st["sources"]]
    alerte = ""
    if not texte:
        alerte = ("AUCUNE voix chargée — ni Obsidian ni le filet du dépôt n'ont répondu. "
                  "Écrire sans elle donnerait un texte au ton générique.")
    elif chemins and all(_sous_le_depot(c["chemin"]) for c in chemins):
        alerte = ("la voix servie vient du FILET VERSIONNÉ du dépôt "
                  f"({', '.join(Path(c['chemin']).name for c in chemins)}), pas d'Obsidian : "
                  "les retouches faites dans le vault ne sont PAS dans ce texte. "
                  "Vérifier VOIX_DIR / OBSIDIAN_VOIX_PATH dans le .env du VPS.")
    plafond = voixmod.max_chars()
    return {"cle": "voix", "titre": "VOIX ÉDITORIALE", "texte": texte,
            "origine": "Obsidian (VPS)" if not alerte else "dépôt (filet)",
            "chemins": chemins, "alerte": alerte, "chars": len(texte),
            "note_de_pied": (
                f"Le pipeline, lui, n'en injecte que {plafond} caractères "
                f"(VOIX_MAX_CHARS) : il voit donc {len(texte) - plafond} caractères de "
                "MOINS que toi, coupés en fin de note."
                if len(texte) > plafond else "")}


def _bloc_vocabulaire() -> dict:
    from utils import vocabulaire as vocab
    regles = vocab.interdits()
    chemin = vocab.note_path()
    morceaux = []
    fr = vocab.consigne_prompt("fr")
    if fr:
        morceaux.append("Quand tu écris en FRANÇAIS :\n" + fr)
    if any(r.get("remplacement_it") for r in regles):
        morceaux.append("Quand tu écris en ITALIEN :\n" + vocab.consigne_prompt("it"))
    if regles:
        morceaux.append(
            "On ne remplace JAMAIS automatiquement : une expression interdite peut être "
            "le titre officiel d'une exposition ou une citation (« Il Regno di Sardegna » "
            "sur l'affiche d'un musée n'est pas notre prose). Ces règles valent pour TA "
            "prose, pas pour ce que tu cites.")
    alerte = ""
    if not regles:
        alerte = ("AUCUNE règle de vocabulaire chargée" + (
            f" — la note « {chemin} » est introuvable ou vide."
            if chemin else " — OBSIDIAN_VOCAB_PATH n'est pas réglé dans le .env du VPS.")
            + " Le pipeline, lui, continue sans filtre en silence (choix du 05/09) ; "
              "toi, tu écrirais sans savoir que tu n'as pas la liste.")
    return {"cle": "vocabulaire", "titre": "VOCABULAIRE INTERDIT",
            "texte": "\n\n".join(morceaux), "origine": "Obsidian (VPS)",
            "chemins": [{"chemin": chemin or "(non réglé)", "existe": bool(regles),
                         "chars": 0, "notes": []}],
            "alerte": alerte, "chars": sum(len(m) for m in morceaux),
            "note_de_pied": f"{len(regles)} règle(s) lue(s) dans la note." if regles else ""}


def _bloc_charte() -> dict:
    try:
        texte = CHARTE.read_text(encoding="utf-8")
    except OSError:
        texte = ""
    return {"cle": "charte", "titre": "CHARTE ÉDITORIALE",
            "texte": texte, "origine": "dépôt (versionné)",
            "chemins": [{"chemin": str(CHARTE), "existe": CHARTE.exists(),
                         "chars": len(texte), "notes": []}],
            "alerte": "" if texte else "docs/CHARTE_EDITORIALE.md est illisible.",
            "chars": len(texte),
            "note_de_pied": "Structure, temps des verbes, casse, bilinguisme (§ 6/6 bis), "
                            "dark patterns proscrits (§ 7)."}


def blocs() -> list[dict]:
    """Les trois blocs, relus À L'INSTANT. Aucun cache : une note éditée dans Obsidian
    doit se voir au rafraîchissement suivant, sans redémarrer quoi que ce soit."""
    return [_bloc_voix(), _bloc_vocabulaire(), _bloc_charte()]


def statut() -> dict:
    """Ce qu'il y a, d'où ça vient, et ce qui manque. `ok` est faux dès qu'UN bloc
    manque — pas seulement quand tout manque : écrire avec deux tiers de la doctrine
    est précisément l'erreur qu'on ne verrait pas."""
    bs = blocs()
    alertes = [f"{b['titre']} : {b['alerte']}" for b in bs if b["alerte"]]
    # `vide` ne regarde QUE la voix et le vocabulaire — pas la charte. La charte est
    # versionnée : elle répond toujours, donc un « tout est vide » qui l'inclurait ne
    # serait jamais vrai, et le 503 de /doctrine.txt serait un témoin qui n'a jamais été
    # rouge (journal du 14/09 : « un témoin ne prouve rien s'il n'a jamais été rouge »).
    # La panne réelle qu'on veut crier, c'est le vault Obsidian démonté sur le VPS.
    vivants = [b for b in bs if b["cle"] in ("voix", "vocabulaire")]
    return {"blocs": bs, "alertes": alertes, "ok": not alertes,
            "vide": not any(b["texte"] for b in vivants),
            "chars": sum(b["chars"] for b in bs),
            "lu_le": datetime.now().strftime("%Y-%m-%d %H:%M")}


def doctrine_texte(st: dict | None = None) -> str:
    """Le texte complet, prêt à être servi à un agent rédacteur.

    L'en-tête n'est pas décoratif : il dit QUAND la lecture a eu lieu, D'OÙ vient chaque
    bloc et COMBIEN il pèse. Un compteur doit dire ce qu'il compte (CLAUDE.md, règle 6),
    et un texte de doctrine sans sa date se fait recopier dans un fichier trois semaines
    plus tard sans que personne puisse dire de quand il date."""
    st = st or statut()
    out = [
        "DOCTRINE RÉDACTIONNELLE — Agenda Sabauda / Cultura Sabauda",
        f"Lue en direct le {st['lu_le']} sur le VPS de production.",
        "",
        "Ceci est une VUE, pas un document : la voix et le vocabulaire vivent dans "
        "Obsidian et changent quand Franck les édite. Ne recopie ce texte nulle part — "
        "rappelle cette adresse à la place. Une copie diverge, c'est déjà arrivé deux "
        "fois dans ce projet.",
        "",
        "CE QUE TU AS SOUS LES YEUX",
    ]
    for b in st["blocs"]:
        chemins = ", ".join(c["chemin"] for c in b["chemins"]) or "(aucun)"
        out.append(f"  · {b['titre']} — {b['chars']} caractères, {b['origine']} : {chemins}")
        if b["note_de_pied"]:
            out.append(f"      {b['note_de_pied']}")
    if st["alertes"]:
        out += ["", "⚠️  CE QUI MANQUE — à dire à Franck avant d'écrire :"]
        out += [f"  · {a}" for a in st["alertes"]]
    out += [
        "",
        "CE QUE CE TEXTE NE CONTIENT PAS : le périmètre éditorial (quatre territoires, "
        "public visé), les personas lecteurs, et la checklist d'auto-évaluation — ils "
        "vivent dans le dépôt (CLAUDE.md, docs/personas/, "
        ".claude/skills/redaction-agenda-sabauda/). Une session qui a le dépôt sous la "
        "main les lit là ; une session qui ne l'a pas doit le dire plutôt que de deviner.",
        "",
    ]
    for i, b in enumerate(st["blocs"], 1):
        out += ["", "=" * 78, f"{i}. {b['titre']}", "=" * 78, ""]
        out.append(b["texte"] or f"(vide — {b['alerte'] or 'raison inconnue'})")
    return "\n".join(out).strip() + "\n"
