#!/usr/bin/env python3
"""LA DESCRIPTION PARLE-T-ELLE DE CETTE FICHE ? — contrôle déterministe, zéro appel LLM.

POURQUOI CE MODULE EXISTE. Arbitrage de Franck, 2026-08-04 : « je veux qu'il puisse juger
la description, et ce, partout. On ne doit pas faire des choses automatiques pour faire
des choses automatiques sans réfléchir. »

Il répondait à une proposition de ma part qui était mauvaise : j'avais présenté la
relecture humaine quotidienne de deux permaliens comme « la seule protection » contre une
description polluée. C'était faire compenser à un humain un contrôle qu'on pouvait écrire —
exactement ce que `docs/ETATS_TERMINAUX.md` interdit ailleurs (« un humain qui tape une
commande n'est pas une réponse »).

CE QUI REND LE CONTRÔLE POSSIBLE, et qu'on n'avait pas vu pendant trois jours : la
contradiction de WP#6798 était visible SANS INTELLIGENCE ARTIFICIELLE. La fiche disait
« Une semaine pas plus · La Comédie des Alpes · Chambéry » et sa description disait
« Fête du lac 2026 : les spectateurs qui n'habitent pas Annecy paieront plus cher ». Aucun
mot commun, et une autre commune nommée. Il n'y avait rien à comprendre — seulement à
comparer.

LES DEUX SIGNAUX, et pourquoi ceux-là :

  ① AUCUN MOT COMMUN entre la description et l'identité propre de la fiche (titre + lieu +
    ville). Universel : il ne dépend d'aucune liste, marche dans les deux langues et sur
    les quatre territoires. C'est le signal qui attrape WP#6798.

  ② UNE AUTRE COMMUNE NOMMÉE, et pas la sienne. Décisif quand il tombe, mais il ne couvre
    que la Savoie/Haute-Savoie et le Comté de Nice — seuls territoires dont on possède la
    liste des communes. Il complète ①, il ne le remplace pas.

CE QU'IL NE FAIT PAS, ET C'EST VOULU. Il ne juge pas la QUALITÉ d'une description, ni sa
véracité : seulement si elle parle de la même chose que le reste de la fiche. Une
description médiocre mais cohérente passe — ce module n'est pas un critique littéraire,
et lui demander de l'être en ferait un générateur de faux positifs.

Il ne BLOQUE rien non plus par lui-même : il rend un motif ou None, et chaque appelant
décide. Poser un blocage uniforme sans mesurer d'abord combien de fiches il attrape, ce
serait précisément « faire de l'automatique sans réfléchir » — et fabriquer un état
terminal de plus.
"""
from __future__ import annotations
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Longueur minimale du texte VISIBLE pour que le SIGNAL ① seul puisse conclure. Une
# description de deux lignes peut légitimement ne reprendre aucun mot du titre ; c'est sur
# un texte fourni que l'absence totale de recoupement devient anormale. Le signal ① est
# une absence — et une absence ne prouve quelque chose que s'il y avait la place d'être
# présent.
#
# ⚠️ CORRECTIF DU 2026-08-04, ET LA LEÇON VAUT PLUS QUE LE CORRECTIF. Ce seuil gardait
# d'abord l'entrée des DEUX signaux. Conséquence, mesurée sur une sauvegarde d'avant
# réparation : le contrôle ne signalait NI 2153 NI 4495 — les deux fiches de l'incident
# pour lequel il a été écrit. Leurs descriptions faisaient 126 et 138 caractères visibles,
# donc elles étaient écartées avant qu'aucune règle ne s'applique.
#
# La cause est une erreur de raisonnement, pas une faute de frappe : un fil Google News
# est COURT PAR NATURE (son volume est dans l'URL encodée, pas dans le texte). La classe de
# pollution visée passait donc systématiquement sous le seuil censé la protéger des faux
# positifs. Et mon test sur fixture ne l'a pas vu parce que j'y avais écrit une longue
# description polluée — j'avais vérifié le code contre ma propre hypothèse, jamais contre
# la donnée réelle.
#
# Le signal ② n'a, lui, aucun besoin de longueur : nommer Annecy quand la fiche dit
# Chambéry est décisif en dix mots comme en mille. Le seuil ne garde donc plus que ①.
MIN_TEXTE_VISIBLE = 200


def _sans_accents(s: str) -> str:
    s = unicodedata.normalize("NFD", (s or "").lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def _texte_visible(html: str | None) -> str:
    """Texte débarrassé des balises et des URLs — mêmes précautions que dedupe._text_len.

    Les URLs sont retirées AVANT tout comptage : un item Google News n'est qu'un lien dont
    l'adresse encodée pèse des centaines de caractères, et c'est ce volume creux qui a
    fabriqué WP#6798 en gagnant un arbitrage de longueur."""
    s = re.sub(r"<[^>]+>", " ", html or "")
    s = re.sub(r"https?://\S+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _forme_commune(s: str) -> str:
    """Forme de comparaison des noms de lieux : minuscules, sans accents, traits d'union
    dépliés en espaces, apostrophes typographiques ramenées à l'apostrophe droite.

    ⚠️ CORRECTIF DU 2026-08-04 (revue), MÊME FAMILLE QUE CELUI DE MIN_TEXTE_VISIBLE. Cette
    normalisation n'était appliquée QU'À L'INDEX des communes (`"aix-les-bains"` rangé
    « aix les bains ») et jamais au TEXTE de la description, qui écrit « Aix-les-Bains »
    avec ses traits d'union. Les deux côtés de la comparaison n'avaient donc pas la même
    forme, et le signal ② se trompait DANS LES DEUX SENS :

      • FAUX POSITIF — une fiche d'Aix-les-Bains dont la description nomme Aix-les-Bains
        était accusée de « ne jamais nommer sa ville », parce que « aix les bains » ne se
        trouve pas dans un texte qui écrit « Aix-les-Bains » ;
      • ANGLE MORT — une description qui nomme Saint-Jorioz ou Saint-Martin-Vésubie ne
        déclenchait rien, ces communes étant introuvables sous leur forme dépliée.

    Ça ne portait pas sur un cas rare : **319 des 711 communes indexées (45 %) s'écrivent
    en plusieurs mots**. Le contrôle était donc muet sur près de la moitié du périmètre, et
    hostile à l'autre. Les fixtures de l'auteur ne l'ont pas vu parce qu'elles n'employaient
    que des communes en UN SEUL mot — Chambéry, Annecy, Ugine, Aoste, Rivoli : une fixture
    qui ne pouvait pas contredire le code."""
    s = _sans_accents(s).replace("’", "'").replace("‘", "'")
    s = re.sub(r"[-_/‐-―]+", " ", s)   # tirets ASCII, typographiques, tirets bas
    return re.sub(r"\s+", " ", s).strip()


def _forme_casse(s: str) -> str:
    """Comme `_forme_commune`, mais SANS passer en minuscules.

    Sert à vérifier qu'un nom de commune trouvé dans un texte y figure bien avec une
    MAJUSCULE — voir `_communes_nommees`. Les deux fonctions doivent appliquer les mêmes
    transformations à part la casse : si elles divergent, la position d'un mot dans l'une
    ne correspond plus à celle dans l'autre, et on retombe sur le défaut du 2026-08-04
    (deux mesures différentes des deux côtés d'une comparaison)."""
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.replace("’", "'").replace("‘", "'")
    s = re.sub(r"[-_/‐-―]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# NOMS DE COMMUNES QUI SONT AUSSI DES MOTS ORDINAIRES — français ou italien.
#
# TROUVÉ LE 2026-08-13, une heure après avoir fait du signal ② le SEUL juge habilité à
# refuser une traduction. En listant l'index pour comprendre pourquoi [4576] restait
# bloquée, 711 communes défilent — et parmi elles : « vers », « bonne », « école »,
# « contes », « cordon », « menton », « grasse », « caille », « sales », « marin »,
# « publier », et « isola » / « tende », qui sont des mots italiens courants.
#
# Une description d'agenda culturel qui écrit « vers 21h », « une bonne soirée »,
# « contes et légendes », « l'école de musique » ou « l'isola » se faisait donc accuser
# de nommer une autre commune. Sur un site bilingue FR/IT, « isola » et « tende » sont
# quasi garantis d'apparaître.
#
# Deux gardes, pas une (cf. `_communes_nommees`) : la MAJUSCULE écarte l'immense majorité
# des cas — un lieu est un nom propre —, et cette liste couvre ce que la majuscule laisse
# passer, c'est-à-dire le début de phrase et les titres (« Contes et légendes », « École
# buissonnière »). Aucune des deux ne suffit seule.
#
# Ce qu'on perd, et c'est assumé : une vraie fiche d'Ugine dont la description nommerait
# « Grasse » ne sera plus signalée. Le coût d'un faux refus est une fiche jamais traduite
# (neuf jours mesurés, et personne ne l'a vu) ; celui d'un faux passage est une alerte de
# moins dans un rapport que Franck relit. L'asymétrie penche du même côté qu'ailleurs
# dans ce fichier.
_MOTS_COURANTS = {
    "vers", "bonne", "ecole", "contes", "cordon", "menton", "grasse", "caille",
    "sales", "sale", "marin", "marie", "mures", "clans", "drap", "gars", "novel",
    "publier", "presle", "isola", "tende", "nice", "cannes", "chatel", "corbel",
    "le mas", "la tour", "villard", "mercury", "orelle", "landry",
}


def _communes_nommees(texte: str, sauf: str = "") -> set[str]:
    """Communes NOMMÉES dans un texte — au sens d'un nom propre, pas d'un mot ordinaire.

    Trois conditions cumulatives, chacune née d'un faux positif réel :

      1. le nom apparaît comme un MOT ENTIER (« Nice » ne se déclenche pas sur
         « Nicermes », ni « Bex » sur « annexe ») ;
      2. il porte une MAJUSCULE dans le texte d'origine — un lieu est un nom propre, et
         « vers 21h » n'en est pas un ;
      3. il n'est pas dans `_MOTS_COURANTS`, qui couvre ce que la majuscule laisse passer
         en début de phrase ou dans un titre.

    `sauf` : la commune de la fiche, sous forme normalisée. Les communes EMBOÎTÉES sont
    écartées avec elle — une fiche d'Annecy-le-Vieux dont la description dit « Annecy »
    parle bien de chez elle.
    """
    texte_n, texte_c = _forme_commune(texte), _forme_casse(texte)
    trouvees = set()
    for c in _communes():
        if c == sauf or c in _MOTS_COURANTS or c not in texte_n:
            continue
        if sauf and (c in sauf or sauf in c):
            continue
        m = re.search(rf"\b{re.escape(c)}\b", texte_c, re.I)
        if m and m.group(0)[:1].isupper():
            trouvees.add(c)
    return trouvees


def _mots(s: str, mini: int = 4) -> set[str]:
    """Mots significatifs. Seuil à 4 lettres et non 3 : « lac », « art », « ville »
    reviennent partout et créeraient de faux recoupements rassurants."""
    return {t for t in re.findall(r"[a-z0-9]+", _sans_accents(s)) if len(t) >= mini}


def _charger_communes() -> dict[str, str]:
    """Commune normalisée → territoire. Deux territoires seulement : ce sont les seuls dont
    on possède la liste (`config/communes_*.json`). Le Piémont et la Vallée d'Aoste n'en
    ont pas — le signal ② est donc muet pour eux, et c'est dit plutôt que masqué."""
    out: dict[str, str] = {}
    try:
        d = json.loads((ROOT / "config" / "communes_savoie_dept.json").read_text())
        for c in d:
            if not str(c).startswith("_"):
                out[_forme_commune(str(c))] = "Savoie"
    except (OSError, ValueError):
        pass
    try:
        d = json.loads((ROOT / "config" / "communes_comte_de_nice.json").read_text())
        for cle in ("arrondissement_de_nice", "arrondissement_de_grasse"):
            for c in d.get(cle) or []:
                out.setdefault(_forme_commune(str(c)), "Nice")
    except (OSError, ValueError):
        pass
    return out


_COMMUNES: dict[str, str] | None = None


def _communes() -> dict[str, str]:
    global _COMMUNES
    if _COMMUNES is None:
        _COMMUNES = _charger_communes()
    return _COMMUNES


def incoherence_description(event: dict, bloquant: bool = False) -> str | None:
    """Motif si la description ne parle manifestement pas de cette fiche, sinon None.

    None ≠ « description correcte » : ça veut dire « rien de contradictoire détecté ». La
    nuance compte, c'est elle qui empêche de prendre ce contrôle pour une garantie.

    `bloquant=True` exige les DEUX signaux À LA FOIS. À réserver aux endroits où le
    verdict REFUSE quelque chose. Chacun pris seul s'est révélé faux sur la donnée réelle
    du 2026-08-13 ; leur conjonction décrit la seule forme qu'on ait jamais vérifiée —
    un texte qui parle d'ailleurs ET qui n'a rien à voir avec cette fiche-ci.

    POURQUOI CETTE DISTINCTION, ET CE QU'ELLE A COÛTÉ D'APPRENDRE (2026-08-13).
    Le signal ① — « aucun mot commun entre la description et l'identité de la fiche » —
    bloquait la traduction. Passé sur les trois fiches qu'il retenait depuis neuf jours,
    il s'est révélé faux DEUX FOIS SUR TROIS, et pour deux raisons qui sont l'ordinaire
    de ce site :

      • [4420] « Fiera Nazionale del Peperone di Carmagnola » — titre italien,
        description française (« la plus grande manifestation italienne dédiée aux
        poivrons, dix jours de saveurs… »). Excellente description. Aucun mot commun,
        parce que le site est BILINGUE ;
      • [3739] « EVO France 2026 » — description « deuxième édition européenne du plus
        grand tournoi de jeux de combat au monde ». Excellente aussi. Aucun mot commun,
        parce qu'une bonne description PARAPHRASE au lieu de répéter le titre.

    Bilan après neuf jours de production : signal ① = zéro vrai positif, deux faux.

    J'ai alors cru que le signal ② suffisait — il porte le vrai positif historique
    (WP#6798, description d'une soirée d'Annecy sur une fiche de Chambéry). Passé sur la
    base une heure plus tard, il a signalé CINQ fiches dont quatre fausses, pour trois
    causes qui sont l'ordinaire d'un agenda de montagne : situer un lieu par sa ville
    voisine, une tournée qui énumère ses étapes, et l'homonymie d'un nom propre —
    « Dullin » est une commune de Savoie ET le théâtre Charles-Dullin de Chambéry, ce qui
    est mot pour mot le piège de la fiche 3588 que CLAUDE.md raconte.

    Aucun des deux ne tient donc SEUL. Leur conjonction, si : les cinq faux positifs
    partagent tous du vocabulaire avec leur propre titre, puisqu'ils décrivent bien leur
    propre événement. C'est la leçon du dépôt appliquée à un détecteur — sur un texte
    écrit pour des humains, on ne peut pas EXTRAIRE, seulement CONFIRMER à partir d'un
    fait qu'on connaît déjà — et il en faut ici DEUX, dont aucun ne suffit.

    Les deux signaux continuent de parler séparément dans les RAPPORTS que Franck lit et
    juge (`audit_coherence`, sans `--bloquant`). Ils n'ont plus le droit de refuser seuls.
    """
    texte = _texte_visible(event.get("description"))
    if not texte:
        return None

    ville = (event.get("ville") or "").strip()
    ancrage = " ".join(str(event.get(k) or "") for k in ("title", "lieu", "ville"))
    mots_ancrage, mots_texte = _mots(ancrage), _mots(texte)

    # ② D'ABORD : il est plus précis, donc son motif est plus utile quand les deux tombent.
    # Le texte et l'index passent par LA MÊME normalisation (cf. _forme_commune) : sans
    # ça, « Aix-les-Bains » écrit dans la description ne rencontrait jamais « aix les
    # bains » rangé dans l'index, et le signal se trompait sur 45 % des communes.
    texte_n = _forme_commune(texte)
    mienne = _forme_commune(ville)
    # `_communes_nommees` porte les trois gardes — mot entier, MAJUSCULE, et hors des
    # noms qui sont aussi des mots courants. Les deux dernières ont été ajoutées le
    # 2026-08-13 : voir `_MOTS_COURANTS`. Sans elles, « vers 21h », « une bonne soirée »,
    # « contes et légendes » ou « l'isola » suffisaient à faire refuser une fiche, et ce
    # signal venait précisément d'être promu SEUL juge habilité à bloquer.
    autres = _communes_nommees(texte, sauf=mienne) if mienne else set()
    # Sa propre ville est-elle nommée ? En mot entier et sur le texte normalisé, exactement
    # comme les autres : deux mesures différentes sur les deux côtés d'une comparaison,
    # c'est précisément ce qui produisait le faux positif.
    sienne_nommee = bool(mienne and re.search(rf"\b{re.escape(mienne)}\b", texte_n))
    signal2 = ((f"la description nomme {', '.join(sorted(autres)[:3])} et jamais "
                f"« {ville} », qui est la ville de la fiche")
               if (autres and ville and not sienne_nommee) else None)
    # « Étranger à la fiche » : aucun mot significatif partagé avec titre + lieu + ville.
    etranger = bool(mots_ancrage) and not (mots_ancrage & mots_texte)

    # ══ CE QUI BLOQUE : LES DEUX SIGNAUX ENSEMBLE, JAMAIS UN SEUL ═════════════════════
    #
    # Passés sur la base réelle le 2026-08-13 — le geste que CLAUDE.md réclame et que
    # j'avais sauté deux fois dans la même heure —, les deux signaux se sont révélés
    # bruyants CHACUN DE SON CÔTÉ :
    #
    #   ① seul (« aucun mot commun ») : faux sur le bilinguisme (titre italien,
    #     description française) et sur la paraphrase (une bonne description ne répète
    #     pas son titre). Deux faux sur trois en neuf jours.
    #
    #   ② seul (« nomme une autre commune ») : cinq fiches signalées, quatre fausses, et
    #     pour trois causes qui sont l'ordinaire d'un agenda de montagne —
    #       · SITUER LE LIEU : « le château de Montrottier, à quinze minutes d'Annecy ».
    #         Nommer la ville voisine est le service rendu au lecteur, pas une erreur ;
    #       · ÉVÉNEMENT ITINÉRANT : une tournée qui énumère ses étapes (Fessy,
    #         Saint-Paul-en-Chablais, Yvoire) ;
    #       · HOMONYMIE DE NOM PROPRE : « Dullin » est une commune de Savoie ET le nom du
    #         théâtre Charles-Dullin de Chambéry. C'est, à la lettre, le piège de la fiche
    #         3588 que CLAUDE.md décrit — le marqueur venait du NOM PROPRE.
    #
    # Leur CONJONCTION, elle, décrit exactement la forme du seul vrai positif connu
    # (WP#6798, la description d'une soirée d'Annecy sur une fiche de Chambéry) : un texte
    # qui parle d'AILLEURS **et** qui n'a RIEN à voir avec cette fiche-ci. Aucun des cinq
    # faux positifs ci-dessus n'a cette forme — tous partagent du vocabulaire avec leur
    # propre titre, puisqu'ils décrivent bien leur propre événement.
    #
    # Le seuil de longueur ne s'applique PAS ici : il existait pour empêcher ① de conclure
    # sur un texte trop court, or ② fournit la preuve positive qui manquait. C'est
    # d'ailleurs indispensable — le blob Google News de WP#6798 était court par nature.
    if bloquant:
        if signal2 and etranger:
            return (signal2 + ", et elle ne partage aucun mot avec le titre, le lieu ou "
                    "la ville — les deux signaux ensemble, jamais un seul")
        return None

    # ── HORS MODE BLOQUANT : le rapport que Franck lit et juge ────────────────────────
    # Les deux signaux parlent séparément. C'est voulu : un rapport a le droit d'être
    # bavard, personne ne se fait refuser sur sa foi. Le seuil de longueur reste sur ①,
    # parce que sur un texte court l'absence de recoupement ne prouve rien.
    if signal2:
        return signal2
    if len(texte) < MIN_TEXTE_VISIBLE:
        return None
    if etranger:
        return ("aucun mot commun entre la description et l'identité de la fiche "
                "(titre, lieu, ville)")
    return None
