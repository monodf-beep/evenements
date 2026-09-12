#!/usr/bin/env python3
"""Panel de personas sur le SITE + coordinateur — docs/PANEL_SITE_COORDINATEUR.md.

Demande de Franck (2026-08-05) : faire lire le SITE (pas seulement un article) par
le panel de personas (`docs/personas/`, déjà utilisé pour la relecture d'articles,
`scripts.enrich.reader_panel`) — avec un COORDINATEUR qui filtre les retours avant
de les transmettre, pour qu'une critique qui contredit un choix délibéré (« il
manque le prix », alors que c'est décidé qu'aucun prix ne s'affiche) ne remonte
pas comme un bug.

TROIS ÉTAGES :
  1. Chaque persona lit une page (home ou territoire) et signale ce qui lui semble
     manquer, en trop, hors-lieu, hors-saison, ou une info absente — SA sensibilité
     propre, pas un jugement uniformisé. La doctrine (config/doctrine_affichage.md)
     est dans son prompt : premier filtre, gratuit.
  2. Le coordinateur REVÉRIFIE contre la doctrine (second filet, déterministe —
     utils.doctrine.contredit_doctrine), REGROUPE les trouvailles qui se recoupent
     (plusieurs personas indépendants qui disent la même chose pèsent plus qu'un
     avis isolé), et ROUTE chaque signal survivant.
  3. Un RAPPORT, jamais une action — même doctrine que tout le reste du dépôt.

COÛT : usage LLM (pas un audit déterministe gratuit) — hebdomadaire, pas quotidien
(proposition du doc). Chaque appel est protégé par PlafondAPI (utils/api_limite.py) :
un plafond arrête le lot proprement, comme partout ailleurs dans ce dépôt.

⚠️ CE MODULE NE PEUT PAS ÊTRE TESTÉ DE BOUT EN BOUT SANS CRÉDIT API — voir
tests/test_panel_site.py, qui teste tout ce qui NE dépend PAS d'un appel LLM (la
récupération de page, la construction du prompt, la doctrine, le coordinateur) sur
des trouvailles RECONSTRUITES à la main, jamais générées par un vrai persona.

Usage :
    .venv/bin/python -m scripts.panel_site               # 5 pages, panel complet
    .venv/bin/python -m scripts.panel_site --pages home  # une seule page
    .venv/bin/python -m scripts.panel_site --guides 2422 # UN guide, à la main
    .venv/bin/python -m scripts.panel_site --guides      # les 12 guides publiés

`--guides` répond à la demande de Franck du 2026-08-17 : « que le guide puisse être lu
par le panel de personas pour vérifier si ça correspond bien à ce qu'on fait avec le
reste du site, mais c'est tout. » À la main, quand un guide vient d'être écrit — pas de
cron (voir le commentaire de GUIDES_SLUGS pour ce que cette décision a écarté).
"""
from __future__ import annotations
import argparse
import html
import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils import personas as personas_mod
from utils.doctrine import load_doctrine, doctrine_pour_prompt, contredit_doctrine
from utils.api_limite import PlafondAPI, est_plafond

log = get_logger("panel-site")

# URLs vérifiées le 2026-08-05 (navigation réelle du site, pas devinées).
PAGES = [
    {"cle": "home", "label": "Accueil", "url": "https://agendasabauda.eu/", "territoire": None},
    {"cle": "savoie", "label": "Savoie / Haute-Savoie",
     "url": "https://agendasabauda.eu/territoire/savoie/", "territoire": "Savoie"},
    {"cle": "piemont", "label": "Piémont",
     "url": "https://agendasabauda.eu/territoire/piemont/", "territoire": "Piemonte"},
    {"cle": "aoste", "label": "Vallée d'Aoste",
     "url": "https://agendasabauda.eu/territoire/vallee-d-aoste/", "territoire": "Vallee-Aoste"},
    {"cle": "nice", "label": "Comté de Nice",
     "url": "https://agendasabauda.eu/territoire/comte-de-nice/", "territoire": "Nice"},
]
SEUIL_MOTIF = int(os.getenv("PANEL_SITE_SEUIL", "2"))
FETCH_TIMEOUT = 20
_UA = {"User-Agent": "Mozilla/5.0 (compatible; AgendaSabaudaBot/1.0)"}

# ══ LES GUIDES, À LA DEMANDE ET SANS CRON ═══════════════════════════════════════════
#
# Franck, 2026-08-17 : « les guides, ça doit être rédigé une fois et c'est tout. Il n'y a
# pas d'autre chose. La seule chose que je demande, c'est que le guide puisse être lu par
# le panel de personas pour vérifier si ça correspond bien à ce qu'on fait avec le reste
# du site, mais c'est tout. »
#
# D'où DEUX décisions, et la seconde est la plus importante :
#   • le panel sait lire un guide comme il lit une page — même trois étages, même
#     coordinateur, même doctrine. Rien de neuf, juste une source de plus ;
#   • AUCUN CRON. Un guide se relit quand on vient de l'écrire, pas tous les jours. Un
#     audit quotidien de la péremption des guides existait (Code Snippets #138, écrit le
#     matin même) : il est abandonné sur cette décision, et le motif est écrit dans
#     deploy/wordpress/code-snippets/README.md pour qu'une prochaine session ne le
#     ressuscite pas en croyant combler un trou.
#
# L'OBJECTION QUI A ÉTÉ ÉCARTÉE, notée ici parce qu'elle reste vraie : un guide « écrit
# une fois » vieillit quand même — « Festivals de l'été en Savoie 2026 » annonce des dates
# passées, et il est servi en premier sur l'accueil pour la Savoie. Ce n'est pas un défaut
# technique mais un choix éditorial, et il appartient à Franck. Si un jour la question se
# repose, elle se posera sur la FRAÎCHEUR, pas sur ce panel-ci.
#
# Le panel n'est PAS gratuit (un appel par persona et par guide) : il ne tourne donc que
# sur demande explicite, `--guides`, jamais par défaut.
# Slugs VÉRIFIÉS sur le site le 2026-08-17, pas devinés : la catégorie française est
# `guides` (id 445, 6 articles), l'italienne `guide-it` (id 447, 6 articles) — Polylang
# suffixe le slug de la traduction quand il entrerait en collision. Chercher `guide` ne
# rendait RIEN, et la liste s'arrêtait donc aux six guides français sans le dire.
GUIDES_SLUGS = ("guides", "guide", "guide-it", "guide-fr")
LANGUES = ("fr", "it")


def guides_publies(base: str = "https://agendasabauda.eu") -> list[dict]:
    """Les guides publiés, au format de PAGES. Lecture PUBLIQUE : aucun crédit, aucun secret.

    Le filtre passe par la CATÉGORIE, pas par « tous les articles » : au 2026-08-17 les
    douze articles publiés sont tous des guides, mais le jour où un autre article paraîtra,
    « tous les articles » le ferait relire par huit personas sans que personne l'ait demandé.
    Si la catégorie ne peut pas être résolue, on le DIT et on ne devine pas (règle 6 : un
    zéro doit dire d'où il vient).
    """
    # `requests` est importé au plus près de l'usage dans ce module (voir
    # fetch_page_text) : on garde la même convention plutôt que d'ajouter un import
    # global qui changerait le coût de chargement du script pour tous les autres.
    import requests
    # UNE PASSE PAR LANGUE, catégories COMPRISES — et c'est un correctif, pas une
    # précaution. Le premier essai résolvait les catégories en une fois, sans `lang`, et
    # rendait SIX guides sur douze : Polylang filtre les collections REST (articles ET
    # catégories) sur la langue courante, sans le dire. Le compteur « 6 guide(s) » avait
    # l'air parfaitement juste. Trouvé en LISANT la sortie, pas en relisant le code — c'est
    # la faute n° 4 de docs/ERREURS_2026-08-17.md, prise en flagrant délit le jour même.
    # Si Polylang disparaît, `lang` est ignoré, les deux passes rendent la même chose, et
    # la déduplication par identifiant garde le résultat correct.
    posts, vus, langues_vides = [], set(), []
    for langue in LANGUES:
        try:
            cats = requests.get(f"{base}/wp-json/wp/v2/categories",
                                params={"slug": ",".join(GUIDES_SLUGS), "per_page": 20,
                                        "lang": langue},
                                timeout=FETCH_TIMEOUT, headers=_UA)
            cats.raise_for_status()
            ids = [c["id"] for c in cats.json() or []]
        except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
            log.warning("Catégories « guides » non résolues en %s (%s) — liste INCOMPLÈTE.",
                        langue, exc)
            continue
        if not ids:
            langues_vides.append(langue)
            continue
        try:
            r = requests.get(f"{base}/wp-json/wp/v2/posts",
                             params={"categories": ",".join(map(str, ids)), "per_page": 100,
                                     "status": "publish", "lang": langue,
                                     "_fields": "id,link,title"},
                             timeout=FETCH_TIMEOUT, headers=_UA)
            r.raise_for_status()
            for p in r.json() or []:
                if p.get("id") not in vus:
                    vus.add(p.get("id"))
                    posts.append(p)
        except (requests.RequestException, ValueError) as exc:
            log.warning("Guides non récupérés en %s (%s) — la liste est INCOMPLÈTE.",
                        langue, exc)
    if langues_vides:
        # Ne JAMAIS laisser une langue muette passer pour une langue sans guides : c'est
        # exactement ce qui a caché la moitié de la liste au premier essai.
        log.warning("Aucune catégorie de guides trouvée en %s (slugs cherchés : %s) — "
                    "renommée ? La liste est peut-être incomplète.",
                    "/".join(langues_vides), ", ".join(GUIDES_SLUGS))
    if not posts:
        log.warning("Aucun guide publié listé — ce n'est PAS la preuve qu'il n'y en a pas.")

    return guides_depuis_payload(posts)


def guides_depuis_payload(posts: list[dict]) -> list[dict]:
    """Transforme la réponse de l'API en entrées au format de PAGES. Fonction PURE :
    c'est elle que la fixture éprouve (tests/test_panel_guides.py), sans réseau."""
    guides, vus = [], set()
    for p in posts:
        if p.get("id") in vus:
            continue
        vus.add(p.get("id"))
        brut = ((p.get("title") or {}).get("rendered") or "")
        # Les titres de l'API arrivent en HTML : `l&rsquo;été` doit devenir `l’été` avant
        # d'entrer dans un prompt de persona, sinon on lui fait lire du balisage.
        titre = html.unescape(re.sub(r"<[^>]+>", "", brut)).strip()
        guides.append({
            "cle": f"guide-{p.get('id')}",
            "label": f"Guide : {titre or p.get('id')}",
            "url": p.get("link") or "",
            # TERRITOIRE VOLONTAIREMENT NON RENSEIGNÉ, donc TOUT le panel lit le guide.
            # Deux raisons, et la première a failli me faire écrire une fausse mécanique :
            # la taxonomie du site rend des IDENTIFIANTS de termes, que `personas_for()`
            # ne reconnaît pas — il se rabattrait sur le panel complet en donnant
            # l'illusion d'un ciblage. Et surtout, la demande est de vérifier « si ça
            # correspond bien à ce qu'on fait avec le RESTE du site » : c'est un contrôle
            # de cohérence d'ensemble, où le regard d'un persona d'un autre territoire
            # vaut autant que celui du local.
            "territoire": None,
        })
    return [g for g in guides if g["url"]]


# --------------------------------------------------------------------------- #
# ÉTAGE 0 — récupération déterministe de la page. Testable SANS API : le site
# est public, aucun crédit nécessaire.
# --------------------------------------------------------------------------- #
def fetch_page_text(url: str, max_chars: int = 6000) -> str:
    """Texte visible d'une page publique, tronqué. '' si inaccessible."""
    import requests
    try:
        r = requests.get(url, timeout=FETCH_TIMEOUT, headers=_UA)
        if r.status_code != 200 or not r.text:
            return ""
    except requests.RequestException as exc:
        log.warning("Page injoignable (%s) : %s", url, exc)
        return ""
    doc = re.sub(r"(?is)<(script|style|noscript|svg|form)\b[^>]*>.*?</\1>", " ", r.text)
    doc = re.sub(r"(?s)<[^>]+>", " ", doc)
    doc = re.sub(r"&nbsp;|&amp;|&#\d+;", " ", doc)
    doc = re.sub(r"\s+", " ", doc).strip()
    return doc[:max_chars]


# --------------------------------------------------------------------------- #
# ÉTAGE 1 — un persona lit une page. Construction du prompt : déterministe et
# testable. L'appel lui-même exige l'API.
# --------------------------------------------------------------------------- #
def _prompt_persona(persona: dict, page_label: str, page_text: str, doctrine_txt: str) -> str:
    who = (persona or {}).get("text") or "Tu es un lecteur exigeant de l'agenda culturel."
    pname = (persona or {}).get("title") or "Lecteur"
    return (
        "Tu incarnes CE persona lecteur de l'agenda culturel Agenda Sabauda :\n"
        f"\"\"\"\n{who}\n\"\"\"\n\n"
        f"Voici le contenu de la page « {page_label} » telle qu'elle se présente "
        "AUJOURD'HUI à un visiteur. Dis, avec TA sensibilité propre, ce qui te "
        "manque, ce qu'il y a en trop, ce qui n'a rien à faire là (trop loin, hors "
        "saison — un événement de Noël en plein été), ou une information absente "
        "(le lieu, par exemple).\n\n"
        + (doctrine_txt + "\n\n" if doctrine_txt else "")
        + f"PAGE « {page_label} » :\n{page_text}\n\n"
        'Réponds en JSON STRICT : {"trouvailles": [{"type": '
        '"manque"|"exces"|"hors_lieu"|"hors_saison"|"info_manquante", '
        '"texte": "<ta remarque, une phrase>"}], "rien_a_signaler": true|false}. '
        "Liste UNIQUEMENT ce qui te frappe vraiment — pas une trouvaille pour "
        "chaque catégorie si tu n'as rien à en dire."
    )


def persona_lit_page(persona: dict, page_label: str, page_text: str, client, model: str,
                     doctrine: list[dict] | None = None) -> list[dict]:
    """Fait lire une page à UN persona. Renvoie ses trouvailles brutes (non
    filtrées — c'est le rôle du coordinateur). [] si rien à signaler ou si
    l'appel échoue pour une raison DE FICHE (jamais un plafond, qui remonte)."""
    if not page_text or client is None:
        return []
    prompt = _prompt_persona(persona, page_label, page_text, doctrine_pour_prompt(doctrine))
    try:
        msg = client.messages.create(model=model, max_tokens=500,
                                     messages=[{"role": "user", "content": prompt}])
    except Exception as exc:
        if est_plafond(exc):
            raise PlafondAPI(str(exc)) from exc
        log.warning("[%s / %s] lecture échouée : %s", persona.get("title"), page_label, exc)
        return []
    raw = "".join(getattr(b, "text", "") for b in msg.content
                  if getattr(b, "type", None) == "text")
    # MESURÉ (2026-08-11) : ce poste n'était pas compté du tout. Franck, 2026-08-10 :
    # « je consomme beaucoup trop de token API pour le résultat médiocre » — on ne peut
    # ni le lui confirmer ni le lui infirmer tant que la moitié des appels sont
    # invisibles. Voir scripts/audit_couts.py pour la répartition par poste.
    from utils import usage
    usage.record_message(model, msg, label="panel_site")
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return []
    try:
        data = json.loads(m.group())
    except (ValueError, TypeError):
        return []
    out = []
    for t in (data.get("trouvailles") or []):
        if isinstance(t, dict) and t.get("texte"):
            out.append({"type": t.get("type", "?"), "texte": t["texte"],
                        "persona": persona.get("title", "?"), "page": page_label})
    return out


# --------------------------------------------------------------------------- #
# ÉTAGE 2 — LE COORDINATEUR. Entièrement déterministe, testable sans API sur
# des trouvailles RECONSTRUITES (réelles ou fixture).
# --------------------------------------------------------------------------- #
def coordonner(trouvailles: list[dict], doctrine: list[dict] | None = None,
               seuil: int = SEUIL_MOTIF) -> dict:
    """Reconcilie les trouvailles brutes du panel.

    Renvoie {"rejetees": [...], "isolees": [...], "motifs": [...]} :
      • rejetees  — contredisent la doctrine (utils.doctrine.contredit_doctrine) ;
      • isolees   — un seul persona les a vues, sous le seuil de convergence ;
      • motifs    — au moins `seuil` personas DIFFÉRENTS, même page × même type :
                    le signal qui compte, prêt pour un rapport."""
    doctrine = doctrine if doctrine is not None else load_doctrine()
    rejetees, survivantes = [], []
    for t in trouvailles:
        contredite = contredit_doctrine(t.get("texte", ""), doctrine)
        if contredite:
            rejetees.append({**t, "doctrine_contredite": contredite["titre"]})
        else:
            survivantes.append(t)

    groupes: dict[tuple[str, str], list[dict]] = {}
    for t in survivantes:
        cle = (t.get("page", "?"), t.get("type", "?"))
        groupes.setdefault(cle, []).append(t)

    motifs, isolees = [], []
    for (page, type_), items in groupes.items():
        personas_distincts = {i.get("persona") for i in items}
        if len(personas_distincts) >= seuil:
            motifs.append({"page": page, "type": type_, "n_personas": len(personas_distincts),
                           "exemples": [i["texte"] for i in items[:3]]})
        else:
            isolees.extend(items)

    return {"rejetees": rejetees, "isolees": isolees, "motifs": motifs}


# --------------------------------------------------------------------------- #
# ORCHESTRATION
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="Panel de personas sur le site + coordinateur.")
    parser.add_argument("--pages", nargs="+", choices=[p["cle"] for p in PAGES], default=None,
                        help="Sous-ensemble de pages (défaut : toutes, sauf si --guides).")
    parser.add_argument("--guides", nargs="*", default=None, metavar="ID",
                        help="Fait lire les GUIDES par le panel : sans argument, tous les "
                             "guides publiés ; avec des identifiants (2422 3648), ceux-là "
                             "seulement. Demande de Franck du 2026-08-17 — à la main, "
                             "quand un guide vient d'être écrit, JAMAIS en cron.")
    args = parser.parse_args(argv)

    # --guides seul ne lit QUE les guides : demander la relecture d'un guide qu'on vient
    # d'écrire ne doit pas facturer au passage les cinq pages du site.
    pages = [] if (args.guides is not None and args.pages is None) else \
        [p for p in PAGES if not args.pages or p["cle"] in args.pages]
    if args.guides is not None:
        guides = guides_publies()
        if args.guides:
            voulus = {str(i).strip() for i in args.guides}
            guides = [g for g in guides if g["cle"].split("-")[-1] in voulus]
            manquants = voulus - {g["cle"].split("-")[-1] for g in guides}
            if manquants:
                log.warning("Identifiant(s) sans guide publié correspondant : %s — "
                            "vérifier qu'ils sont publiés et en catégorie « Guides ».",
                            ", ".join(sorted(manquants)))
        log.info("%d guide(s) à faire lire par le panel.", len(guides))
        pages = pages + guides
    doctrine = load_doctrine()
    log.info("%d page(s) à lire, %d entrée(s) de doctrine chargée(s).", len(pages), len(doctrine))

    client = None
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key, timeout=60.0)
    else:
        log.warning("ANTHROPIC_API_KEY absente : les pages seront récupérées, mais "
                    "aucun persona ne pourra les lire (0 trouvaille possible).")
    model = os.getenv("ANTHROPIC_MODEL_PERSONAS") or os.getenv("ANTHROPIC_MODEL_EXTRACT",
                                                                "claude-haiku-4-5")

    trouvailles: list[dict] = []
    plafonne = False
    for page in pages:
        texte = fetch_page_text(page["url"])
        if not texte:
            log.warning("[%s] page vide ou inaccessible, ignorée.", page["label"])
            continue
        panel = (personas_mod.personas_for(page["territoire"]) if page["territoire"]
                 else personas_mod.load_personas())
        log.info("[%s] %d caractère(s) récupérés, %d persona(s) au panel.",
                 page["label"], len(texte), len(panel))
        for persona in panel:
            try:
                trouvailles += persona_lit_page(persona, page["label"], texte, client,
                                                model, doctrine)
            except PlafondAPI as exc:
                log.error("PLAFOND API — lot arrêté à [%s / %s] : %s",
                         persona.get("title"), page["label"], exc)
                plafonne = True
                break
        if plafonne:
            break

    resultat = coordonner(trouvailles, doctrine)
    log.info("=== %d trouvaille(s) brute(s) — %d rejetée(s) (doctrine), %d isolée(s), "
             "%d motif(s) (≥%d personas) ===",
             len(trouvailles), len(resultat["rejetees"]), len(resultat["isolees"]),
             len(resultat["motifs"]), SEUIL_MOTIF)
    for m in resultat["motifs"]:
        log.info("  MOTIF [%s] %s (%d personas) : %s", m["page"], m["type"],
                 m["n_personas"], m["exemples"][0][:100])
    for r in resultat["rejetees"]:
        log.info("  REJETÉ (doctrine « %s ») : %s", r["doctrine_contredite"], r["texte"][:80])

    if plafonne:
        log.error("Le lot s'est arrêté sur un plafond API. Relever le plafond ou "
                  "recharger le crédit (console Anthropic), puis relancer.")
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
