#!/usr/bin/env python3
"""Rédige le texte éditorial des pages pilier « Que faire à X » / « Cosa fare a X ».

D'OÙ ÇA VIENT. Franck, 19/09/2026 : « il faut créer du contenu avec du bon SEO. il faut
que le contenu passe par la doctrine de rédaction ». Les 193 pages de gabarit plafonnaient
entre 48 et 54 en SEO Yoast parce qu'elles ne portaient QUE le shortcode d'agenda : aucun
texte, donc aucune matière à noter. Le modèle validé à la main (Chambéry, 19/09) sort à
81/90 en français, 77/90 en italien.

CE QUE FAIT CE SCRIPT, ET CE QU'IL NE FAIT PAS. Il écrit à partir d'un DOSSIER DE FAITS
construit sur NOTRE base (les lieux, catégories et villes qui apparaissent réellement dans
nos fiches publiées et encore devant nous), plus une recherche web dont chaque fait doit
arriver avec son URL. Il ne laisse passer aucun nom propre absent de ce dossier : le
contrôle `noms_propres` refuse le texte et dit lequel. C'est la leçon du 19/09 — le lien
que j'avais noté « 200 » la veille rendait 404 le lendemain, le site ayant changé
d'arborescence. Donc ici : TOUTE adresse citée est interrogée, et un 404 refuse le texte.

LE PORTILLON SE REJOUE-T-IL SUR LA MÊME MATIÈRE ? Non, et c'est la règle 3 de CLAUDE.md.
Un refus renvoie au modèle la LISTE NOMMÉE de ce qui a cloché (« phrase de 24 mots »,
« nom propre inconnu : Vicario », « lien 404 : … »). Le passage suivant reçoit donc une
matière différente, pas la même. Après `--essais` tentatives, la page est GARÉE dans
data/hubs_refuses.json avec son motif — et ce garage n'est pas un cul-de-sac : `--rejouer`
la représente, et le compteur de fin dit combien de pages y dorment.

PÉRIMÈTRE DES COMPTEURS (règle 6). « candidates » = pages de gabarit sans texte éditorial.
« respectées » = pages où quelqu'un a déjà écrit à la main, jamais écrasées. « refusées »
= le texte produit n'a pas passé les contrôles. « écrites » = recomptées sur WordPress
après écriture, pas la longueur d'une liste.

Usage :
    python -m scripts.textes_hubs                         # dry-run, tout le stock
    python -m scripts.textes_hubs --villes Chambéry Aoste # un échantillon
    python -m scripts.textes_hubs --cap 10 --apply        # écrit 10 pages
    python -m scripts.textes_hubs --rejouer               # reprend les pages garées
    python -m scripts.textes_hubs --essai-controles f.html --langue fr --cle "..."
"""
from __future__ import annotations
import argparse
import html as htmlmod
import json
import os
import re
import sqlite3
import sys
from datetime import date
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.logger import get_logger                      # noqa: E402
from scripts.publisher import _headers                   # noqa: E402
from scripts.yoast_scores import papiers, noter           # noqa: E402 — un seul moteur, pas deux

log = get_logger("textes-hubs")
DB = ROOT / "data" / "events.db"
GARAGE = ROOT / "data" / "hubs_refuses.json"

# Les bornes mécaniques. Elles viennent du modèle Chambéry MESURÉ, pas d'une intuition :
# 490 mots, 4 H2, 5 gras, 0 phrase de plus de 20 mots, clé 3 fois (densité 0,61 %).
MOTS_MIN, MOTS_MAX = 380, 560
H2_MIN, H2_MAX = 3, 4
GRAS_MIN, GRAS_MAX = 3, 5
PHRASE_MAX = 20            # Yoast français : au-delà, `textSentenceLength` vire à l'orange
CLE_MIN, CLE_MAX = 2, 5

# Mots qu'un texte peut porter en majuscule sans venir du dossier de faits : notre propre
# marque, les quatre territoires, les jours, les mois. Tout le reste doit être sourcé.
BLANCHE = {
    "Agenda", "Sabauda", "Savoie", "Savoia", "Haute-Savoie", "Piémont", "Piemonte",
    "Vallée", "Aoste", "Valle", "Aosta", "Nice", "Nizza", "Alpes", "Alpi", "Italie",
    "Italia", "France", "Francia", "Europe", "Europa", "Turin", "Torino",
    "Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche",
    "Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica",
    # LA FAIBLESSE ASSUMÉE DU CÔTÉ ITALIEN, écrite pour qu'on la connaisse : nos sources
    # locales sont des pages FRANÇAISES, donc un nom propre traduit (« Sindone » pour
    # « Saint Suaire », « Belle Arti » pour « Beaux-Arts ») n'y figure jamais et serait
    # refusé à tort. On les autorise ici, par une liste courte et VERSIONNÉE. Le contrôle
    # italien est donc plus faible que le français : il ne rattrape que ce qui sort de
    # cette liste. Le dire plutôt que de laisser croire les deux côtés équivalents.
    "Sindone", "Belle", "Arti", "Duchi", "Ducato", "Sabaudo", "Ottocento", "Novecento",
    "Settecento", "Lione", "Sindaco", "Comune",
    # Ajoutés le 20/09 : « Annibale » (Hannibal) et « Grenoble » (que la source française
    # n'écrit qu'en adjectif, « grenoblois »). Cette liste s'allonge à chaque page
    # italienne, et c'est le SIGNAL qu'elle n'est pas la bonne réponse à long terme : la
    # vraie serait une source en italien par ville, ou une table de correspondance des
    # noms propres. En attendant, elle est courte, versionnée, et on sait pourquoi.
    "Annibale", "Grenoble",
}


# --------------------------------------------------------------------------- lecture

def texte_nu(h: str) -> str:
    """Le HTML débarrassé de ses balises — ce que le lecteur lit, et ce que Yoast compte."""
    return htmlmod.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h))).strip()


def atts_hub(content: str) -> dict:
    """Ville / territoire / quand LUS DANS LE SHORTCODE de la page, pas devinés du titre.

    Le titre est réécrit par l'éditorial ; le shortcode, lui, est ce que WordPress exécute.
    C'est la seule source qui dit vraiment de quoi cette page parle."""
    m = re.search(r"\[cs_hub_(?:ville|territoire)([^\]]*)\]", content)
    if not m:
        return {}
    return {k: v for k, v in re.findall(r'(\w+)="([^"]*)"', m.group(1))}


def cible(atts: dict) -> dict:
    """Ce dont la page parle, dans les TROIS formes réellement en ligne.

    Mesuré sur WordPress le 19/09/2026, sur les 192 pages de gabarit, parce que mon
    premier dry-run rendait « 0 paire » pour Aoste et que je n'ai pas voulu le deviner :

      • 84 pages portent villes="Chambéry" — une seule ville ;
      • 36 portent une LISTE : villes="Torino,Turin", villes="Aoste,Aosta". Les comparer
        à une ville ne matche jamais, et interroger la base sur « Aoste,Aosta » ne rend
        aucune fiche ;
      • 72 n'ont PAS d'attribut villes du tout : ce sont les pages de TERRITOIRE, qui
        portent ville_label="Savoie" / "Savoia" / "Piémont". Ma première version repliait
        sur territoire="vda" et serait allée chercher des fiches dont la ville vaut
        « vda » — c'est-à-dire aucune.

    Soit 108 pages sur 192 qui auraient reçu un dossier de faits VIDE. Le script n'aurait
    pas planté : il aurait écrit du creux, ou tout refusé, sans dire pourquoi.

    Le libellé change de langue (« Savoie » / « Savoia ») mais pas la cible : le
    regroupement des jumelles se fait donc sur les villes ou le territoire, jamais sur le
    libellé."""
    villes = [v.strip() for v in (atts.get("villes") or "").split(",") if v.strip()]
    territoire = (atts.get("territoire") or "").strip()
    label = (atts.get("ville_label") or "").strip() or (villes[0] if villes else territoire)
    return {"villes": villes, "territoire": territoire, "label": label,
            "est_territoire": not villes,
            # clé de regroupement des deux jumelles, insensible à la langue
            "groupe": ("V", tuple(sorted(villes))) if villes else ("T", territoire)}


def texte_editorial(content: str) -> str:
    """Le contenu moins les shortcodes : vide = page de gabarit, non vide = quelqu'un a écrit."""
    return re.sub(r"\[[^\]]+\]", "", content or "").strip()


def langue_de(cle: str) -> str:
    if cle.startswith("Que faire"):
        return "fr"
    if cle.startswith("Cosa fare"):
        return "it"
    return ""


# --------------------------------------------------------------------- dossier de faits

def dossier(conn: sqlite3.Connection, cib: dict) -> dict:
    """Ce que NOTRE base sait de cette cible, et rien d'autre.

    Règle 5 : seuls comptent les événements à venir ou EN COURS — c'est `date_event_end`
    qui décide, jamais `date_event_start` seule — et une fiche sans date n'est pas
    « passée », c'est une donnée manquante, donc on la garde.

    Deux périmètres, parce qu'il y a deux sortes de pages : une page de ville interroge
    ses villes (elles peuvent être plusieurs, « Torino,Turin » étant le même lieu écrit
    des deux côtés), une page de territoire interroge tout le territoire."""
    aujourdhui = date.today().isoformat()
    devant = ("(date_event_end >= ? OR (date_event_end IS NULL AND "
              "(date_event_start IS NULL OR date_event_start >= ?)))")

    if cib["est_territoire"]:
        ou, args = "territoire = ?", (cib["territoire"],)
    else:
        trous = ",".join("?" * len(cib["villes"]))
        ou, args = f"ville IN ({trous})", tuple(cib["villes"])
    base = f"FROM events_raw WHERE wp_post_id_as IS NOT NULL AND {ou} AND {devant}"
    args = args + (aujourdhui, aujourdhui)

    nb = conn.execute(f"SELECT COUNT(*) {base}", args).fetchone()[0]
    lieux = [r[0] for r in conn.execute(
        f"SELECT lieu, COUNT(*) c {base} AND lieu IS NOT NULL AND TRIM(lieu) <> '' "
        f"GROUP BY lieu ORDER BY c DESC LIMIT 8", args).fetchall()]
    cats = [r[0] for r in conn.execute(
        f"SELECT llm_categorie, COUNT(*) c {base} AND llm_categorie IS NOT NULL "
        f"GROUP BY llm_categorie ORDER BY c DESC LIMIT 6", args).fetchall()]

    if cib["est_territoire"]:
        # Sur une page de territoire, « les voisines » sont les villes du territoire.
        voisines = [r[0] for r in conn.execute(
            f"SELECT ville, COUNT(*) c {base} AND ville IS NOT NULL AND TRIM(ville) <> '' "
            f"GROUP BY ville ORDER BY c DESC LIMIT 8", args).fetchall()]
    else:
        trous = ",".join("?" * len(cib["villes"]))
        voisines = [r[0] for r in conn.execute(
            "SELECT ville, COUNT(*) c FROM events_raw WHERE wp_post_id_as IS NOT NULL "
            f"AND territoire = ? AND ville NOT IN ({trous}) AND {devant} "
            "AND ville IS NOT NULL AND TRIM(ville) <> '' "
            "GROUP BY ville ORDER BY c DESC LIMIT 6",
            (cib["territoire"],) + tuple(cib["villes"]) + (aujourdhui, aujourdhui)).fetchall()]

    return {"ville": cib["label"], "villes": cib["villes"], "territoire": cib["territoire"],
            "page_de_territoire": cib["est_territoire"],
            "fiches_en_ligne": nb, "lieux": lieux, "categories": cats,
            "villes_voisines": voisines}


def _fetch(url: str, timeout: int = 30) -> tuple[int, str]:
    """Appelle une adresse et rend (code, texte nu).

    Une adresse qu'on n'a pas appelée n'est pas une adresse vérifiée — leçon du
    19/09/2026, où un lien noté « 200 » la veille rendait 404 le lendemain, le site ayant
    changé d'arborescence.

    UN TIMEOUT N'EST PAS UN LIEN MORT, et cette distinction a coûté un faux refus le
    20/09 : deux de nos propres adresses italiennes ont dépassé les 20 secondes, le
    contrôle les a déclarées injoignables, et un re-test immédiat a rendu 200 quatre fois
    de suite. Notre WordPress est sur un mutualisé OVH : il a des minutes lentes.

    Pourquoi ça compte au-delà d'une seconde perdue : ce refus-là se rejouerait à
    l'identique au passage suivant, sur la même matière, et brûlerait deux appels API
    chaque jour sans que rien ne change. C'est le portillon que CLAUDE.md décrit à la
    règle 3. D'où une SECONDE tentative, plus patiente : seule une panne qui se répète
    condamne l'adresse, et le motif dit alors qu'on a essayé deux fois."""
    dernier = ""
    for essai, patience in enumerate((timeout, timeout * 2), start=1):
        try:
            r = requests.get(url, timeout=patience, allow_redirects=True,
                             headers={"User-Agent": "Mozilla/5.0 (compatible; AgendaSabauda)"})
        except requests.RequestException as exc:
            dernier = type(exc).__name__
            continue
        corps = re.sub(r"<script.*?</script>|<style.*?</style>", " ", r.text, flags=re.S)
        return r.status_code, texte_nu(corps)
    return 0, f"injoignable après 2 tentatives ({dernier})"


# LES OUVREURS DE PHRASE, liste FERMÉE et versionnée.
#
# Pourquoi elle existe : en tête de phrase toute majuscule est ambiguë. On tranche d'abord
# par le vocabulaire des pages citées, mais leur lexique est court (quelques centaines de
# mots) et il laisse passer des ordinaires — le témoin du 19/09 a été refusé sur
# « Quatre », qui n'était sur aucune des cinq sources.
#
# Le coût des deux erreurs n'est pas le même, et la liste penche donc vers la complétude :
#   • un FAUX REFUS coûte un essai. Le motif est nommé, le modèle reçoit une matière
#     différente au passage suivant, donc le refus ne se rejoue pas à l'identique (règle 3) ;
#   • un FAUX PASSAGE met un nom inventé sur une page publique, et personne ne le voit.
#
# Faiblesse assumée, écrite pour qu'on la connaisse : un nom propre dont la forme minuscule
# est un mot courant (« Carré », « Soute ») passe en tête de phrase. Il doit alors venir du
# dossier de faits pour passer ailleurs dans le texte, ce qui limite la portée du trou.
OUVREURS = set("""
un une le la les des de du au aux ce cet cette ces son sa ses leur leurs notre nos votre
mon ma mes ton ta tes il elle ils elles on nous vous je tu y en lui
zero un deux trois quatre cinq six sept huit neuf dix onze douze quinze vingt cent mille
premier premiere deuxieme troisieme dernier derniere
dans sur sous avec sans pour par entre vers chez depuis pendant avant apres selon malgre
contre parmi jusqu jusque hors outre voici voila
et ou mais donc or ni car puis ensuite enfin aussi ainsi alors quand lorsque comme si que
qui quoi dont ou pourquoi combien
cela ceci autre autres meme memes tout toute tous toutes chaque plusieurs quelques certains
beaucoup peu rien personne aucun aucune nul
est sont etait etaient sera seront a ont avait avaient aura auront fait font faisait
reste restent vient viennent passe passent trouve trouvent porte portent tient tiennent
loin pres ici la-bas deja encore toujours jamais souvent parfois bientot hier demain
uno una il lo la gli le dei degli delle del della nel nella sul sulla
questo questa questi queste quel quella suo sua suoi sue loro nostro vostro mio
due tre quattro cinque sei sette otto nove dieci undici dodici quindici venti cento mille
primo prima secondo terzo ultimo ultima
in su sotto con senza per tra fra da presso durante prima dopo secondo nonostante
e ed o oppure ma dunque quindi perche come se che chi cui dove quando mentre anche pure
inoltre invece infatti allora poi ancora sempre mai spesso talvolta oggi domani ieri
cio altro altri altra altre stesso stessa tutto tutta tutti tutte ogni alcuni alcune
molto poco nulla nessuno nessuna
essere sono era erano sara saranno ha hanno aveva avevano avra avranno fa fanno
resta restano viene vengono passa passano trova trovano porta portano tiene tengono
lontano vicino qui li qua
accanto basta cambia cambiano molti molte piccolo piccola piccoli piccole grande grandi
proteggono protegge indicano indica guidava guidano credono crede ricordi ricorda
attraversa attraversano trasforma trasformano susseguono conviene occorre bisogna
""".split())

_MAJ = re.compile(r"[A-ZÀ-ÖØ-Þ][\w'’\-]*")
_MOT = re.compile(r"[\wÀ-ÿ'’\-]+")


def _sans_accents(m: str) -> str:
    """La liste des ouvreurs est écrite sans accents : « apres » y couvre « après »."""
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", m)
                   if unicodedata.category(c) != "Mn")


def noms_autorises(dos: dict, pages_citees: dict, cle: str, ancres: list[str]) -> tuple[set, set]:
    """Rend (noms propres autorisés, mots courants connus).

    Le premier jeu vient du dossier tiré de notre base, du TEXTE des pages citées qu'on
    vient de lire, de notre expression clé et des ancres de nos liens internes. Une source
    qu'on n'a pas lue n'autorise rien.

    Le second jeu est la trouvaille du 19/09 : les mots que les pages citées emploient en
    MINUSCULE. Il sert au début de phrase, où toute majuscule est ambiguë — « Dans »,
    « Colonnes », « Ses » y sont des mots courants, « Zanetti » un nom inventé. La position
    ne les distingue pas ; le vocabulaire, si."""
    maj = set(BLANCHE)
    mins: set = set()
    maj |= set(_MAJ.findall(str(dos.get("ville") or ""))) | set(_MAJ.findall(str(dos.get("territoire") or "")))
    for v in dos.get("villes") or []:
        maj |= set(_MAJ.findall(str(v)))
    for liste in ("lieux", "villes_voisines", "categories"):
        for v in dos.get(liste) or []:
            maj |= set(_MAJ.findall(str(v)))
    for corps in pages_citees.values():
        maj |= set(_MAJ.findall(corps))
        mins |= {m.lower() for m in _MOT.findall(corps) if m[:1].islower()}
    maj |= set(_MAJ.findall(cle))
    for a in ancres:
        maj |= set(_MAJ.findall(a))
    return maj, mins


# Un siècle en chiffres romains est une majuscule légitime, pas un nom propre : XIXe, XXᵉ.
_SIECLE = re.compile(r"^[IVXLC]+(e|ᵉ|er|ème)?$")
# « L'office », « Nell'antica », « Un'aria » : la majuscule porte sur l'article élidé, pas
# sur le nom. L'italien en élide plusieurs lettres (nell', dell', sull', quest'), d'où le
# {1,5} — la version à une seule lettre refusait « Nell'antica » et « Un'aria ».
_ELISION = re.compile(r"^[A-Za-zÀ-ÿ]{1,5}['’]")


def noms_inconnus(raw: str, autorises: set, courants: set) -> tuple[list[str], list[str]]:
    """Rend (refus, avertissements) — deux sévérités, parce que les deux positions ne se
    valent pas.

    REFUS, au MILIEU d'une phrase : c'est là que vivent les noms propres factuels (« la
    cathédrale Saint-François-de-Sales », « part pour Turin », « chez Casimir Vicario »).
    Une majuscule qu'aucune source citée ni le dossier ne portent y est un fait inventé, et
    le texte est refusé.

    AVERTISSEMENT, en TÊTE de phrase : toute majuscule y est ambiguë et on ne peut trancher
    qu'avec un dictionnaire. Ce conteneur n'en a pas, et `pip install` demande l'accord de
    Franck. On tranche donc avec ce qu'on a — la liste OUVREURS et le vocabulaire des pages
    citées — et ce qui reste est SIGNALÉ, pas refusé.

    Pourquoi pas un refus là aussi : essayé le 19/09, le témoin italien sortait rouge sur
    neuf mots parfaitement ordinaires (« Colonne », « Diventa », « Facciate »), parce que
    nos sources locales sont françaises et n'emploient aucun mot italien en minuscule. Un
    portillon qui refuse neuf fois sur dix à tort ne protège rien : il fait tourner la
    boucle à vide et coûte des appels API. Le trou qui reste est étroit et nommé — un nom
    inventé, placé en ouverture de phrase, et nulle part ailleurs dans le texte. Un
    dictionnaire français/italien le fermerait ; c'est une demande à faire, pas un oubli.
    """
    nu_texte = texte_nu(raw)
    courants = courants | {m.lower() for m in _MOT.findall(nu_texte) if m[:1].islower()}
    refus, ouvertures = [], []
    blocs = re.findall(r"<(?:p|h2)>(.*?)</(?:p|h2)>", raw, re.S) or [raw]
    for bloc in blocs:
        for phrase in re.split(r"(?<=[.!?:])\s+", texte_nu(bloc)):
            for i, mot in enumerate(phrase.split()):
                propre = mot.strip("«»\"'()[],;.:!?…")
                if not propre or not propre[0].isupper():
                    continue
                if _SIECLE.match(propre) or _ELISION.match(propre) or propre in autorises:
                    continue
                if i == 0:
                    if (propre.lower() not in courants
                            and _sans_accents(propre.lower()) not in OUVREURS):
                        ouvertures.append(propre)
                else:
                    refus.append(propre)
    return sorted(set(refus)), sorted(set(ouvertures))


def anti_patterns() -> list[str]:
    """Les expressions que la voix nomme comme anti-patterns, LUES DANS LA VOIX.

    AUCUNE COPIE DANS CE DÉPÔT. La section « ## Anti-patterns clés » de la note Obsidian
    est la seule source, comme pour le vocabulaire interdit : si Franck y ajoute un
    superlatif, le contrôle le connaît au passage suivant sans qu'on touche au code. C'est
    la leçon de `config/vocabulaire_interdit.json`, dont le miroir avait divergé dans les
    deux sens avant d'être supprimé le 05/09/2026.

    Même arbitrage qu'`utils.vocabulaire` pour la panne : Obsidian injoignable rend une
    liste vide et le pipeline continue, plutôt que de bloquer."""
    try:
        from utils import voix
        texte = voix.load_voix()
    except Exception:                                   # noqa: BLE001 — jamais bloquant
        return []
    m = re.search(r"##\s*Anti-patterns[^\n]*\n(.*?)(?=\n#|\Z)", texte, re.S)
    if not m:
        return []
    return [x.strip() for x in re.findall(r"«\s*([^»]+?)\s*»", m.group(1)) if x.strip()]


# ------------------------------------------------------------------------- contrôles

def lire_adresses(raw: str, sources: list[str]) -> tuple[list[str], dict]:
    """Appelle UNE FOIS chaque adresse du texte et chaque source déclarée.

    Rend (adresses mortes, {url: texte de la page}). Deux contrôles s'en servent — le
    404 et les noms propres — et ils lisent donc la MÊME lecture : pas deux détecteurs
    pour la même chose, dont un seul serait juste (docs/ERREURS_2026-09-08.md)."""
    morts, corps = [], {}
    urls = sorted(set(re.findall(r'href="([^"]+)"', raw)) | set(sources))
    for url in urls:
        code, txt = _fetch(url)
        if code == 0 or code >= 400:
            morts.append(f"{url} → {txt if code == 0 else code}")
        elif "agendasabauda.eu" not in url:
            # NOS PROPRES pages n'autorisent AUCUN nom propre. Elles listent les
            # événements du jour : leurs titres y changent tous les matins, donc s'en
            # servir reviendrait à tout autoriser et à croire le portillon fermé alors
            # qu'il est ouvert. Ce qui vient de chez nous passe par le dossier de faits
            # (lieux, villes voisines), qui est lu en base et pas sur une page web.
            corps[url] = txt
    return morts, corps


def controles(raw: str, lang: str, cle: str, dos: dict, sources: list[str],
              verifier_liens: bool = True, corps: dict | None = None,
              avertissements: list | None = None,
              antipatterns: list | None = None) -> list[str]:
    """Retourne la liste NOMMÉE de ce qui cloche. Vide = le texte passe.

    Chaque motif est écrit pour être relu par le modèle au passage suivant : il doit
    pouvoir corriger sans deviner. « trop long » ne suffit pas, « phrase de 24 mots : … »
    oui."""
    from utils import vocabulaire
    ennuis: list[str] = []
    nu = texte_nu(raw)
    mots = re.findall(r"[\w’'\-]+", nu)

    for expr, phrase in vocabulaire.trouver(nu):
        ennuis.append(f"vocabulaire interdit « {expr} » dans : {phrase[:120]}")

    # LES ANTI-PATTERNS DE LA VOIX, avec DEUX sévérités, et la raison est mesurable.
    #
    # La liste mêle deux natures. « en conclusion » et « force est de constater » sont des
    # formules : elles n'ont aucun usage innocent dans notre prose, donc elles refusent.
    # « historique » en a un, et il est constant : « le centre historique », « les places
    # historiques ». Mon propre texte sur Chambéry l'emploie ainsi. Un refus aveugle
    # rejetterait donc un texte juste à chaque passage, et brûlerait deux appels API par
    # page pour rien — c'est exactement le portillon faux du 06/08 que CLAUDE.md décrit.
    #
    # Le partage retenu : une expression de PLUSIEURS mots refuse, un mot seul avertit.
    # Grossier, mais vérifiable, et il penche du bon côté : un faux refus coûte un essai,
    # un superlatif qui passe se lit sur le site. La limite est écrite ici plutôt que
    # promise, et un humain tranche les avertissements en deux secondes.
    for expr in (anti_patterns() if antipatterns is None else antipatterns):
        for m in re.finditer(re.escape(expr), nu, re.I):
            bout = nu[max(0, m.start() - 60):m.end() + 60]
            if " " in expr.strip():
                ennuis.append(f"anti-pattern de la voix « {expr} » dans : …{bout}…")
            elif avertissements is not None:
                avertissements.append(f"[{lang}] superlatif « {expr} » à relire : …{bout}…")

    if not MOTS_MIN <= len(mots) <= MOTS_MAX:
        ennuis.append(f"longueur : {len(mots)} mots, il en faut entre {MOTS_MIN} et {MOTS_MAX}")
    if nu.count("—"):
        ennuis.append(f"{nu.count(chr(8212))} tiret(s) cadratin — la charte les interdit")
    # LES LISTES NE SONT PAS INTERDITES SUR L'AGENDA, et mon premier motif de refus
    # affirmait le contraire. Surcharge explicite de la charte Agenda Sabauda, relue le
    # 19/09/2026 : « Contrairement à la voix commune Enrico (qui proscrit les listes à
    # puces), l'Agenda AUTORISE et RECOMMANDE les listes pour les faits structurés :
    # programmation, line-up, concerts du jour, horaires, tarifs. »
    #
    # Si on les refuse ICI, c'est pour une raison propre à CE gabarit, pas au nom de la
    # charte : les faits structurés de ces pages sont déjà rendus par le shortcode
    # [cs_hub_ville] juste en dessous, avec leurs horaires et leurs lieux. Une liste dans
    # le texte de tête les redirait, en moins bien et sans se mettre à jour. Le texte de
    # tête est un cadre, la liste est la machine.
    if re.search(r"<(ul|ol|li)\b", raw):
        ennuis.append("liste à puces dans le texte de tête : les faits structurés sont déjà "
                      "rendus par le shortcode juste en dessous, et eux se mettent à jour. "
                      "(Les listes restent autorisées ailleurs sur l'Agenda.)")
    if re.search(r"<h[13-6]\b", raw):
        ennuis.append("seuls les H2 sont admis (ni H1 ni H3)")

    h2 = [texte_nu(x) for x in re.findall(r"<h2>(.*?)</h2>", raw, re.S)]
    if not H2_MIN <= len(h2) <= H2_MAX:
        ennuis.append(f"{len(h2)} H2, il en faut entre {H2_MIN} et {H2_MAX}")

    gras = [texte_nu(g) for g in re.findall(r"<strong>(.*?)</strong>", raw, re.S)]
    if not GRAS_MIN <= len(gras) <= GRAS_MAX:
        ennuis.append(f"{len(gras)} passage(s) en gras, il en faut entre {GRAS_MIN} et {GRAS_MAX}")
    for g in gras:
        if re.search(r"\d", g) or any(m[:1].isupper() for m in g.split()[1:]):
            ennuis.append(f"gras sur un nom propre, une date ou un chiffre : « {g} »")

    for bloc in re.findall(r"<p>(.*?)</p>", raw, re.S) + h2:
        for ph in re.split(r"(?<=[.!?:])\s+", texte_nu(bloc)):
            n = len(re.findall(r"[\w’'\-]+", ph))
            if n > PHRASE_MAX:
                ennuis.append(f"phrase de {n} mots (maximum {PHRASE_MAX}) : « {ph[:110]} »")

    occ = len(re.findall(re.escape(cle), nu, re.I))
    if not CLE_MIN <= occ <= CLE_MAX:
        ennuis.append(f"l'expression clé « {cle} » apparaît {occ} fois, il en faut "
                      f"entre {CLE_MIN} et {CLE_MAX}")
    premier = texte_nu(raw.split("</p>")[0])
    if cle.lower() not in premier.lower():
        ennuis.append(f"l'expression clé « {cle} » manque dans le premier paragraphe")
    if not any(cle.lower() in x.lower() for x in h2):
        ennuis.append(f"l'expression clé « {cle} » manque dans les sous-titres")

    liens = re.findall(r'href="([^"]+)"', raw)
    internes = [l for l in liens if "agendasabauda.eu" in l]
    externes = [l for l in liens if "agendasabauda.eu" not in l]
    if len(internes) < 2:
        ennuis.append(f"{len(internes)} lien(s) interne(s), il en faut au moins 2")
    if not externes:
        ennuis.append("aucun lien externe : il en faut au moins un, vers la source citée")

    # Les adresses sont lues UNE fois : leur code sert au contrôle 404, leur texte sert
    # à savoir quels noms propres le texte a le droit de porter.
    # `corps` déjà fourni = la fixture a préchargé le texte des pages sources : le test
    # tourne alors hors ligne et donne le MÊME verdict qu'en production, sans dépendre
    # d'un site tiers qui peut changer d'arborescence du jour au lendemain.
    morts, corps = (lire_adresses(raw, sources) if verifier_liens else ([], corps or {}))
    for m in morts:
        ennuis.append(f"lien mort : {m}")

    ancres = [texte_nu(a) for a in re.findall(r"<a [^>]*>(.*?)</a>", raw, re.S)]
    inconnus, ouvertures = noms_inconnus(raw, *noms_autorises(dos, corps, cle, ancres))
    if inconnus:
        ennuis.append("nom(s) propre(s) qu'aucune source citée ni le dossier de faits ne "
                      "portent, donc invérifiables : " + ", ".join(inconnus))
    if ouvertures and avertissements is not None:
        avertissements.append(f"[{lang}] majuscule(s) en tête de phrase que je n'ai pas su "
                              f"classer (à lire, pas forcément fautives) : "
                              + ", ".join(ouvertures))
    return ennuis


# --------------------------------------------------------------------------- rédaction

PROMPT = """Tu écris le texte éditorial d'une page pilier d'Agenda Sabauda, l'agenda
culturel bilingue FR/IT des territoires sabauds. La page liste déjà les événements par
un shortcode ; ton texte vient AU-DESSUS et explique la ville à quelqu'un qui arrive
dessus par une recherche.

RÈGLE ABSOLUE SUR LES FAITS. Tu ne peux écrire un nom propre, une date ou un chiffre que
s'il vient (a) du dossier de faits ci-dessous, ou (b) d'une page web que tu as réellement
ouverte avec l'outil de recherche et dont tu rends l'adresse dans `sources`. Pas de
souvenir, pas de « on sait que ». Un fait sans adresse est un fait qui ne part pas. Les
adresses seront toutes appelées après toi : une qui rend 404 fait refuser le texte entier.

DOSSIER DE FAITS (notre base, fiches publiées encore à venir ou en cours) :
{dossier}

LE MODÈLE. Voici une page de la même famille, validée et notée 81/100 en SEO et 90/100 en
lisibilité. Reprends sa STRUCTURE et son SOUFFLE, jamais son contenu :

--- modèle français ---
{modele_fr}
--- modèle italien ---
{modele_it}

CONTRAINTES MÉCANIQUES, toutes vérifiées après toi :
- de {mots_min} à {mots_max} mots par langue ;
- {h2_min} à {h2_max} sous-titres <h2>, aucun <h1>, aucun <h3> ;
- pas de liste à puces DANS CE TEXTE : les horaires et les lieux sont déjà rendus par le
  shortcode juste en dessous, et eux se mettent à jour tous les jours. Ce texte-ci est un
  cadre en prose. (Les listes restent autorisées ailleurs sur l'Agenda.) ;
- aucune phrase de plus de {phrase_max} mots. C'est la contrainte qui casse le plus
  souvent : compte-les ;
- des connecteurs (aussi, d'ailleurs, en revanche, également, par ailleurs, ensuite,
  quant à lui) : Yoast les compte et le texte se lit mieux ;
- pas de voix passive, présent ou futur, le passé seulement pour un rappel historique ;
- {gras_min} à {gras_max} passages en <strong>, sur des EXPRESSIONS, jamais sur un nom
  propre, un lieu, une date ni un chiffre ;
- aucun tiret cadratin ;
- ne commence JAMAIS une phrase par un nom propre. En ouverture, une majuscule est
  ambiguë et le contrôle ne peut pas la vérifier : place les noms dans la phrase ;
- l'expression clé de {cle_min} à {cle_max} fois, dont une dans le premier paragraphe et
  une dans un <h2> ;
- au moins deux liens internes agendasabauda.eu parmi ceux-ci, et un lien externe vers
  la source que tu cites en passant :
{liens_internes}

CLÉ FRANÇAISE : {cle_fr}
CLÉ ITALIENNE : {cle_it}

Les deux textes sont JUMEAUX : même structure, mêmes faits, mêmes sous-titres. L'italien
n'est pas une traduction mot à mot mais il ne dit rien que le français ne dise. Ajoute
côté italien une courte parenthèse quand un terme français n'a pas d'équivalent.

Réponds UNIQUEMENT par ce JSON, sans un mot autour :
{{"fr": "<p>…</p>", "it": "<p>…</p>", "sources": ["https://…", "…"]}}
"""

REPRISE = """Ton texte précédent a été refusé par les contrôles. Voici, nommé, ce qui
cloche. Corrige EXACTEMENT ces points et ne touche pas au reste :

{ennuis}

Renvoie le même JSON."""


def modele() -> dict:
    return json.loads((ROOT / "config" / "modele_hub_chambery.json").read_text(encoding="utf-8"))


def prompt_initial(dos: dict, cle_fr: str, cle_it: str, liens: list[str]) -> str:
    m = modele()
    return PROMPT.format(
        dossier=json.dumps(dos, ensure_ascii=False, indent=2),
        modele_fr=m["html"]["fr"], modele_it=m["html"]["it"],
        mots_min=MOTS_MIN, mots_max=MOTS_MAX, h2_min=H2_MIN, h2_max=H2_MAX,
        gras_min=GRAS_MIN, gras_max=GRAS_MAX, phrase_max=PHRASE_MAX,
        cle_min=CLE_MIN, cle_max=CLE_MAX, cle_fr=cle_fr, cle_it=cle_it,
        liens_internes="\n".join(f"  - {l}" for l in liens))


def _json_de(txt: str) -> dict:
    """Le modèle ajoute parfois une phrase autour du JSON. On prend le premier objet."""
    m = re.search(r"\{.*\}", txt, re.S)
    if not m:
        raise ValueError(f"pas de JSON dans la réponse : {txt[:200]}")
    return json.loads(m.group(0))


def rediger(client, model: str, dos: dict, cles: dict, liens: list[str], essais: int,
            verifier_liens: bool = True) -> tuple[dict, list[str], list[str]]:
    """Écrit les deux jumelles, contrôle, et REPRÉSENTE la matière corrigée si ça coince.

    Retourne ({fr, it, sources}, motifs, avertissements). Motifs vide = le texte passe ;
    les avertissements ne bloquent pas mais remontent dans le rapport, parce qu'un signal
    qui n'apparaît nulle part ne sert à personne. Le dernier jeu de motifs est celui qui
    part au garage : il doit rester lisible par un humain."""
    import anthropic
    from utils import voix

    messages = [{"role": "user", "content": voix.voix_block() + "\n\n"
                 + prompt_initial(dos, cles["fr"], cles["it"], liens)}]
    derniers: list[str] = []
    for tentative in range(1, essais + 1):
        try:
            msg = client.messages.create(
                model=model, max_tokens=4000, messages=messages,
                tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 6}])
        except Exception as exc:                        # noqa: BLE001
            if _est_panne_generale(exc):
                raise PanneGenerale(str(exc)) from exc
            raise
        txt = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        try:
            rep = _json_de(txt)
        except (ValueError, json.JSONDecodeError) as exc:
            derniers, avert = [f"réponse illisible : {exc}"], []
            messages += [{"role": "assistant", "content": txt},
                         {"role": "user", "content": REPRISE.format(ennuis=derniers[0])}]
            continue

        sources = [str(s) for s in (rep.get("sources") or [])]
        derniers, avert = [], []
        for lang in ("fr", "it"):
            for e in controles(rep.get(lang) or "", lang, cles[lang], dos, sources,
                               verifier_liens=verifier_liens, avertissements=avert):
                derniers.append(f"[{lang.upper()}] {e}")
        if not derniers:
            log.info("  %s : passé au %de essai", dos["ville"], tentative)
            return rep, [], avert
        log.info("  %s : essai %d refusé (%d motif(s))", dos["ville"], tentative, len(derniers))
        messages += [{"role": "assistant", "content": txt},
                     {"role": "user", "content": REPRISE.format(
                         ennuis="\n".join(f"  - {e}" for e in derniers))}]
    return {}, derniers, []


# ----------------------------------------------------------------------------- garage

class PanneGenerale(Exception):
    """Une panne qui ne dépend PAS de la page en cours : crédit épuisé, clé refusée,
    quota. La réessayer ville après ville ne produit rien et coûte un appel à chaque fois.

    Mesuré le 19/09/2026 : le premier dry-run a brûlé DEUX appels pour la même erreur
    « credit balance is too low », et il en aurait brûlé un par paire sans le --cap 2."""


_PANNES_GENERALES = (
    "credit balance is too low",     # crédit épuisé
    "invalid x-api-key",             # clé fausse
    "authentication_error",
    "permission_error",
)


def _est_panne_generale(exc: Exception) -> bool:
    m = str(exc).lower()
    return any(motif in m for motif in _PANNES_GENERALES)


def garage_lire() -> dict:
    if GARAGE.exists():
        try:
            return json.loads(GARAGE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def garage_ecrire(d: dict) -> None:
    GARAGE.parent.mkdir(parents=True, exist_ok=True)
    GARAGE.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


# -------------------------------------------------------------------------- écriture

def ecrire_page(wp_url: str, auth, page_id: int, html: str, shortcode: str) -> None:
    """Le texte VIENT AVANT le shortcode : le lecteur lit, puis voit l'agenda.

    WordPress garde une révision de l'ancien contenu, donc ce geste se défait — c'est
    pour ça qu'il est du côté « réversible » de la frontière d'autonomie."""
    r = requests.post(f"{wp_url}/?rest_route=/wp/v2/pages/{page_id}",
                      json={"content": html.strip() + "\n\n" + shortcode},
                      auth=auth, headers=_headers(auth), timeout=120)
    r.raise_for_status()
    requests.post(f"{wp_url}/?rest_route=/wp/v2/pages/{page_id}",
                  json={"meta": {"cs_texte_hub": "1"}},
                  auth=auth, headers=_headers(auth), timeout=60)


# ------------------------------------------------------------------------------ main

def inventaire(wp_url: str, auth) -> tuple[list[dict], dict]:
    """Les pages de gabarit, LUES SUR WORDPRESS. Un identifiant en base ne prouve rien sur
    le site (règle 1) : c'est WordPress qui dit ce que chaque page contient aujourd'hui."""
    rep = papiers(wp_url, auth, ["page"], 500, [], True)
    pages, ecartees = [], {"sans_shortcode": 0, "sans_cle": 0, "sans_langue": 0, "deja_ecrites": 0}
    for p in rep.get("papers") or []:
        atts = atts_hub(p.get("content") or "")
        if not atts:
            ecartees["sans_shortcode"] += 1
            continue
        cle = (p.get("keyword") or "").strip()
        if not cle:
            ecartees["sans_cle"] += 1
            continue
        lang = langue_de(cle)
        if not lang:
            ecartees["sans_langue"] += 1
            continue
        p["_atts"] = atts
        p["_lang"] = lang
        p["_cible"] = cible(atts)
        p["_ville"] = p["_cible"]["label"]
        p["_quand"] = atts.get("quand") or ""
        p["_deja"] = bool(texte_editorial(p.get("content") or ""))
        if p["_deja"]:
            ecartees["deja_ecrites"] += 1
        pages.append(p)
    return pages, ecartees


def main(argv=None) -> int:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--apply", action="store_true", help="Écrit sur WordPress (sinon simulation).")
    p.add_argument("--villes", nargs="*", default=[], help="Limite à ces villes.")
    p.add_argument("--ids", nargs="*", type=int, default=[], help="Limite à ces pages.")
    p.add_argument("--cap", type=int, default=5, help="Paires de pages par run.")
    p.add_argument("--essais", type=int, default=3, help="Tentatives avant de garer la page.")
    p.add_argument("--rejouer", action="store_true", help="Reprend les pages garées.")
    p.add_argument("--refaire", action="store_true",
                   help="Réécrit AUSSI les pages qui portent déjà un texte. À la main seulement.")
    p.add_argument("--modele-llm", default="", help="Sinon le modèle qualité du profil.")
    p.add_argument("--essai-controles", default="",
                   help="Passe les contrôles sur un fichier HTML et sort. Aucun appel API.")
    p.add_argument("--langue", default="fr")
    p.add_argument("--cle", default="")
    args = p.parse_args(argv)

    # Mode banc d'essai : éprouver le portillon sur du texte réel sans dépenser un appel.
    # CLAUDE.md : « avant de livrer un portillon, le passer sur des données réelles et
    # LIRE ce qu'il refuse ».
    if args.essai_controles:
        raw = Path(args.essai_controles).read_text(encoding="utf-8")
        dos = {"ville": "Chambéry", "territoire": "savoie", "lieux": [], "categories": [],
               "villes_voisines": []}
        ennuis = controles(raw, args.langue, args.cle, dos, [], verifier_liens=True)
        print(f"{len(ennuis)} motif(s) de refus" if ennuis else "aucun motif : le texte passe")
        for e in ennuis:
            print(f"  - {e}")
        return 0

    wp_url = os.getenv("WP_AS_URL", "").rstrip("/")
    auth = (os.getenv("WP_AS_USER", ""), os.getenv("WP_AS_APP_PASSWORD", ""))
    if not all([wp_url, auth[0], auth[1]]):
        log.error("WP_AS_URL / WP_AS_USER / WP_AS_APP_PASSWORD manquants dans .env")
        return 2
    if not os.getenv("ANTHROPIC_API_KEY"):
        log.error("ANTHROPIC_API_KEY manquante — sans elle ce script ne peut rien écrire, "
                  "et un « 0 page » voudrait dire « pas de clé », pas « rien à faire ».")
        return 2

    pages, ecartees = inventaire(wp_url, auth)
    # Regroupement sur la CIBLE, pas sur le libellé : « Savoie » et « Savoia » sont la
    # même page dans deux langues, et les regrouper par libellé les séparerait — chaque
    # jumelle resterait seule, et le script n'écrirait jamais la moitié d'une paire.
    paires: dict[tuple, dict] = {}
    for pg in pages:
        paires.setdefault((pg["_cible"]["groupe"], pg["_quand"]), {})[pg["_lang"]] = pg

    garees = garage_lire()
    candidates, orphelines = [], 0
    for (groupe, quand), duo in sorted(paires.items(), key=lambda kv: str(kv[0])):
        if len(duo) < 2:
            orphelines += 1
            continue                                   # une jumelle manque : on n'écrit pas la moitié
        cib = duo["fr"]["_cible"]
        ville = cib["label"]
        if args.ids and not any(d["id"] in args.ids for d in duo.values()):
            continue
        if args.villes:
            # --villes Aoste doit attraper villes="Aoste,Aosta" ET ville_label="Savoie".
            noms = {n.lower() for n in cib["villes"]} | {d["_ville"].lower() for d in duo.values()}
            if not any(v.lower() in noms for v in args.villes):
                continue
        deja = any(d["_deja"] for d in duo.values())
        if deja and not args.refaire:
            continue
        cle_garage = f"{groupe}|{quand}"
        if cle_garage in garees and not args.rejouer:
            continue
        candidates.append((ville, quand, duo))  # ville = le libellé français, pour l'affichage

    # Le périmètre à côté du nombre (règle 6) : d'où vient ce chiffre, et ce qu'il exclut.
    log.info("%d paire(s) candidate(s) sur %d page(s) de gabarit — %d déjà écrites à la main "
             "(jamais écrasées), %d garées après refus, %d pages hors gabarit",
             len(candidates), len(pages), ecartees["deja_ecrites"], len(garees),
             ecartees["sans_shortcode"] + ecartees["sans_cle"] + ecartees["sans_langue"])
    if orphelines:
        # Une jumelle sans l'autre ne doit pas disparaître en silence : c'est une page qui
        # ne sera JAMAIS écrite tant que personne ne crée sa traduction.
        log.warning("%d page(s) sans jumelle dans l'autre langue : jamais écrites tant que "
                    "leur traduction n'existe pas", orphelines)
    if not candidates:
        print("Rien à écrire. Ce zéro vient d'une absence de cas, pas d'un échec : "
              f"{len(pages)} pages inspectées, {ecartees['deja_ecrites']} déjà pourvues, "
              f"{len(garees)} garées (les reprendre avec --rejouer).")
        return 0
    candidates = candidates[:args.cap]

    import anthropic
    from utils import settings
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"), timeout=300.0)
    model = args.modele_llm or settings.model_qualite()
    conn = sqlite3.connect(DB)

    faits, refus, erreurs, avertis = [], [], [], []
    for ville, quand, duo in candidates:
        log.info("— %s (%s) : pages %s", ville, quand, [d["id"] for d in duo.values()])
        dos = dossier(conn, duo["fr"]["_cible"])
        if not dos["fiches_en_ligne"]:
            # Un dossier vide n'est pas une matière pauvre : c'est l'absence de matière.
            # Écrire dessus produirait du creux, et le LLM comblerait le vide en inventant.
            motif = [f"dossier de faits VIDE : aucune fiche publiée encore à venir pour "
                     f"{dos['villes'] or dos['territoire']}. Rien à écrire de vérifiable."]
            refus.append((ville, quand, motif))
            garees[f"{duo['fr']['_cible']['groupe']}|{quand}"] = {
                "quand": quand, "motifs": motif, "le": date.today().isoformat()}
            log.info("  %s : dossier vide, page laissée telle quelle", ville)
            continue
        cles = {l: duo[l]["keyword"] for l in ("fr", "it")}
        liens = [d["permalink"] for d in duo.values()]
        try:
            rep, motifs, avert = rediger(client, model, dos, cles, liens, args.essais)
        except PanneGenerale as exc:
            # Le périmètre à côté du nombre (règle 6) : ce qui reste n'a pas été refusé,
            # il n'a pas été TENTÉ. Confondre les deux ferait croire à 96 pages fautives.
            non_tentees = len(candidates) - len(faits) - len(refus) - 1
            erreurs.append(f"panne générale, run interrompu après {ville} ({quand}) : {exc}")
            log.error("Panne qui vaut pour toutes les pages, on s'arrête ici plutôt que de "
                      "la rejouer %d fois : %s", non_tentees + 1, exc)
            break
        except Exception as exc:                        # noqa: BLE001
            erreurs.append(f"{ville} ({quand}) : {type(exc).__name__} — {exc}")
            log.error("  %s : %s", ville, exc)
            continue
        if motifs:
            refus.append((ville, quand, motifs))
            garees[f"{ville}|{quand}"] = {"quand": quand, "motifs": motifs,
                                          "le": date.today().isoformat()}
            continue
        garees.pop(f"{ville}|{quand}", None)
        for a in avert:
            avertis.append(f"{ville} ({quand}) {a}")
        faits.append((ville, quand, duo, rep, dos))

    conn.close()

    # LE RAPPORT SEO : le score AVANT et APRÈS, calculé par le même moteur que la colonne
    # du site. Demandé par Franck le 19/09 — « est-ce que tu mets un rapport SEO ».
    avant, apres = [], []
    for _, _, duo, rep, _ in faits:
        for lang in ("fr", "it"):
            avant.append(dict(duo[lang]))
            apres.append({**duo[lang], "content": rep[lang].strip() + "\n\n"
                          + re.search(r"\[cs_hub_[^\]]+\]", duo[lang]["content"]).group(0)})
    notes_avant = {n["id"]: n for n in noter(avant)} if avant else {}
    notes_apres = {n["id"]: n for n in noter(apres)} if apres else {}

    print(f"\n{'page':>7}  {'ville':<22} {'lg':<3} {'SEO avant':>9} {'→':^3} {'après':>5}"
          f"   {'lisib. avant':>12} {'→':^3} {'après':>5}")
    for _, _, duo, _, _ in faits:
        for lang in ("fr", "it"):
            i = duo[lang]["id"]
            a, b = notes_avant.get(i, {}), notes_apres.get(i, {})
            print(f"{i:>7}  {duo[lang]['_ville'][:22]:<22} {lang:<3} "
                  f"{str(a.get('seo', '—')):>9} {'→':^3} {str(b.get('seo', '—')):>5}"
                  f"   {str(a.get('lisibilite', '—')):>12} {'→':^3} {str(b.get('lisibilite', '—')):>5}")
    if notes_apres:
        moy = lambda d, k: round(sum(v[k] or 0 for v in d.values()) / len(d), 1)  # noqa: E731
        print(f"\nMoyenne SEO : {moy(notes_avant, 'seo')} → {moy(notes_apres, 'seo')} · "
              f"lisibilité : {moy(notes_avant, 'lisibilite')} → {moy(notes_apres, 'lisibilite')}")
        print("Rappel mesuré le 19/09 : les points `images` et `imageKeyphrase` restent rouges "
              "tant que ces pages n'ont pas de vignette à la une. Elle vaut 7 points.")

    if refus:
        print(f"\n{len(refus)} page(s) refusée(s) par les contrôles et garées dans "
              f"{GARAGE.relative_to(ROOT)} — `--rejouer` les représente :")
        for ville, quand, motifs in refus:
            print(f"  {ville} ({quand}) : " + " · ".join(motifs[:3])
                  + (f" … et {len(motifs) - 3} autre(s)" if len(motifs) > 3 else ""))
    if avertis:
        # Un signal qui n'apparaît nulle part ne sert à personne. Ces lignes ne bloquent
        # rien : ce sont les majuscules en tête de phrase que le contrôle n'a pas su
        # classer, à parcourir des yeux une fois.
        print(f"\n{len(avertis)} avertissement(s), sans conséquence sur l'écriture :")
        for a in avertis:
            print(f"  {a}")
    for e in erreurs:
        print(f"  ⚠️  {e}")
    garage_ecrire(garees)

    non_tentees = len(candidates) - len(faits) - len(refus)
    if non_tentees > 0:
        print(f"\n{non_tentees} paire(s) NON TENTÉE(S) — le run s'est arrêté avant elles. "
              f"Ce n'est pas un refus : rien ne dit encore si leur texte passerait.")
    if not args.apply:
        print(f"\nDRY-RUN — {len(faits)} paire(s) prête(s), rien d'écrit sur le site. "
              f"Relancer avec --apply.")
        return 0 if not erreurs else 1

    ecrites = 0
    for _, _, duo, rep, _ in faits:
        for lang in ("fr", "it"):
            sc = re.search(r"\[cs_hub_[^\]]+\]", duo[lang]["content"]).group(0)
            try:
                ecrire_page(wp_url, auth, duo[lang]["id"], rep[lang], sc)
                ecrites += 1
            except Exception as exc:                    # noqa: BLE001
                erreurs.append(f"page {duo[lang]['id']} : {exc}")

    # RECOMPTE sur WordPress après écriture, jamais la longueur d'une liste (règle 6).
    apres_pages, apres_ec = inventaire(wp_url, auth)
    pourvues = sum(1 for x in apres_pages if x["_deja"])
    resume = (f"✍️ *Textes des pages pilier* — {ecrites} page(s) écrite(s), "
              f"{len(refus)} refusée(s) par les contrôles, {len(erreurs)} erreur(s). "
              f"Recompté sur le site : {pourvues}/{len(apres_pages)} pages de gabarit "
              f"portent un texte.")
    log.info(resume)
    print("\n" + resume)
    from utils import pipeline_status, slack
    slack.notify(resume)
    pipeline_status.record_run("textes_hubs", ok=ecrites, warn=len(refus),
                               error=len(erreurs), summary=resume[:1500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
