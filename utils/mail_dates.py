#!/usr/bin/env python3
"""La date d'un événement dans une newsletter : celle qui est À CÔTÉ de son titre.

Franck, 2026-08-11 : « on a toujours trop de tâches ». Après trois vagues de correctifs,
la file « À compléter » gardait seize fiches venues d'un mail — six ateliers des musées de
Chambéry, quatre annonces du Département 06, Courmayeur, MITO, Turismo Torino. Toutes
sans date, et aucune n'avait de page à ouvrir : leur `url_source` est « gmail:… ».

LA CAUSE. `scripts/gmail_collect.py` demande au modèle d'extraire une date, puis range en
`description` un RÉSUMÉ RÉÉCRIT de une à deux phrases. Le corps du mail n'est gardé nulle
part. Si l'extraction rate la date, elle est perdue pour de bon : pas de page à relire,
pas de texte à reparser. C'est le même défaut que partout ailleurs dans ce dépôt — un
rétrécissement sans personne pour le rouvrir (règle 3), en version « donnée » plutôt
qu'« état ».

CE QUE FAIT CE MODULE. Il relit le corps du mail, qui contient forcément « le jeudi
21 août à 18h » quelque part. Mais une newsletter annonce DIX événements et porte VINGT
dates : la date de parution, celles des autres annonces, les horaires d'ouverture. Prendre
« la première date du mail » les collerait toutes sur la mauvaise fiche.

Alors on ne cherche pas une date, on cherche **la date qui est près du TITRE de cette
fiche-là**. Le titre est l'ancre, comme la fin connue l'était pour `debut_depuis_page` et
comme « organisé par » l'était pour `utils.bylines.corrobore` : troisième fois aujourd'hui
que le même principe résout le même genre de problème, et ce n'est pas un hasard — sur un
document écrit pour des humains, on ne peut pas EXTRAIRE, on ne peut que CONFIRMER à
partir de quelque chose qu'on sait déjà.

CE QU'IL NE FAIT JAMAIS
  • si le titre est introuvable dans le corps, il ne rend rien (plutôt que de se rabattre
    sur la première date venue) ;
  • si deux fenêtres autour du titre donnent des dates DIFFÉRENTES, il ne rend rien :
    l'ambiguïté n'est pas départageable ici, et une fiche mal datée trompe le visiteur
    sans que personne s'en aperçoive, là où une fiche sans date reste réparable.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date

# Fenêtre APRÈS le titre, et seulement après. Une newsletter s'écrit comme une liste :
# l'intitulé fait office de titre, la date le suit sur la ligne d'en dessous. Une fenêtre
# centrée sur le titre semblait plus prudente — elle est en fait systématiquement FAUSSE :
# vérifié sur la lettre des musées de Chambéry, elle attrapait la date de l'annonce
# PRÉCÉDENTE, parce que le lecteur de dates s'arrête au premier motif rencontré. Les cinq
# fiches recevaient chacune la date de sa voisine du dessus, décalées d'un cran, et rien
# dans le résultat ne l'aurait laissé voir.
#
# Une newsletter qui écrirait « Jeudi 21 août — Sieste musicale » ne rendra donc rien :
# c'est l'échec qu'on préfère, puisqu'il laisse la fiche réparable.
_FENETRE = 220
# En dessous, un « titre » ne discrimine plus rien dans un mail de 6000 caractères.
_TITRE_MIN = 12


def _norm(s: str) -> str:
    n = unicodedata.normalize("NFKD", (s or "").lower())
    n = "".join(c for c in n if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", n).strip()


def _positions(corps_norm: str, titre_norm: str) -> list[int]:
    """Où le titre apparaît dans le corps. À défaut du titre entier, une suite de mots
    significatifs assez longue pour ne désigner que lui."""
    if len(titre_norm) >= _TITRE_MIN and titre_norm in corps_norm:
        return [m.start() for m in re.finditer(re.escape(titre_norm), corps_norm)]
    # Repli : les mots longs du titre, dans l'ordre, en commençant par la suite la plus
    # longue. « Sieste musicale aux Charmettes - OudéBach » → « sieste musicale ».
    mots = [m for m in titre_norm.split() if len(m) > 3]
    for n in range(min(4, len(mots)), 1, -1):
        bout = " ".join(mots[:n])
        if len(bout) >= _TITRE_MIN and bout in corps_norm:
            return [m.start() for m in re.finditer(re.escape(bout), corps_norm)]
    return []


def _autour_de_la_date(zone: str) -> str:
    """La portion de texte qui porte le premier motif de date de la zone.

    Sert uniquement à MONTRER sur quoi la lecture s'est faite (dry-run). Si aucun motif
    n'est repérable, on rend le début de la zone : c'est alors le signe que la date vient
    d'ailleurs, et c'est précisément ce qu'il faut voir."""
    m = re.search(r"\d{1,2}\s+[a-z]{3,10}|\d{1,2}[/.]\d{1,2}[/.]\d{4}|\d{4} \d{2} \d{2}",
                  zone)
    if not m:
        return zone[:130].strip()
    debut = max(0, m.start() - 45)
    return zone[debut:m.end() + 70].strip()


def date_pres_du_titre(corps: str, titre: str, ref: date | None = None,
                       autres_titres: list | None = None,
                       _extraits: list | None = None) -> tuple[str, str]:
    """(début, fin) lus AUTOUR du titre dans le corps du mail. ('','') si rien de sûr.

    Le parsing est délégué à `scripts.dates.parse_dates`, le même lecteur que celui qui
    lit « du 11 au 29 août » dans un titre d'article : rien de neuf, seulement appliqué à
    la bonne portion de texte.

    `_extraits` (optionnel) : reçoit le texte SUR LEQUEL la date a été lue. Ajouté le
    2026-08-11 au premier run réel, qui a rendu trois dates toutes situées dans le passé
    (25 juillet, 6 et 8 août) — ce qui est la signature exacte d'une erreur possible :
    le lecteur aurait pu attraper la date d'ENVOI de la newsletter. Impossible de
    trancher sans voir la phrase. Un script qui pose une date sans montrer d'où elle
    vient demande qu'on le croie ; celui-ci montre, comme utils/infos_pratiques.py rend
    la phrase autour du tarif plutôt que le montant seul."""
    from scripts.dates import parse_dates  # import tardif : évite un cycle au chargement

    corps_norm, titre_norm = _norm(corps), _norm(titre)
    if not corps_norm or not titre_norm:
        return ("", "")
    # LES TITRES VOISINS BORNENT LA FENÊTRE, et c'est le vrai garde-fou (2026-08-11, au
    # deuxième run réel). Une fenêtre de longueur fixe suffisait tant que la description
    # était courte ; sur la lettre des musées de Chambéry, elle déborde. Vérifié sur la
    # sortie : la date rendue pour « La visite-atelier des 4-6 ans » venait d'un texte où
    # ne figurait AUCUNE date — elle avait été prise APRÈS le paragraphe de description,
    # donc dans l'annonce suivante.
    #
    # Or on connaît les autres annonces : ce sont les autres fiches issues du même mail.
    # Le texte d'un événement s'arrête où commence le titre du suivant. Ce n'est plus une
    # distance devinée, c'est une borne lue dans le document.
    bornes = [_norm(t) for t in (autres_titres or [])]
    bornes = [b for b in bornes if len(b) >= _TITRE_MIN and b != titre_norm]
    trouves = set()
    for pos in _positions(corps_norm, titre_norm):
        apres = pos + len(titre_norm)
        fin_fenetre = apres + _FENETRE
        for b in bornes:                      # première annonce voisine rencontrée
            suivant = corps_norm.find(b, apres)
            if suivant != -1:
                fin_fenetre = min(fin_fenetre, suivant)
        zone = corps_norm[apres:fin_fenetre]
        s, e, src = parse_dates(zone, ref)
        if src == "parsed" and s:
            trouves.add((s, e or s))
            if _extraits is not None:
                # L'EXTRAIT MONTRE L'ENDROIT DE LA DATE, pas le début de la zone. La
                # première version affichait les 140 premiers caractères : sur deux des
                # trois dates du premier run, ils ne contenaient aucune date, donc la
                # preuve affichée ne prouvait rien. Une preuve qui ne montre pas le fait
                # qu'elle établit est pire qu'une absence de preuve — elle rassure.
                _extraits.append(_autour_de_la_date(zone))
    # Une seule réponse, ou rien. Deux dates différentes autour du même titre veulent dire
    # que la fenêtre a mordu sur l'annonce voisine — et on ne devine pas laquelle est
    # la bonne.
    return trouves.pop() if len(trouves) == 1 else ("", "")


def message_id_de(url_source: str) -> str:
    """« gmail:19fa305b67f95221#3 » → « 19fa305b67f95221 ».

    C'est ce qui rend le rattrapage possible : l'identifiant du mail a été conservé dans
    l'adresse de la fiche, donc le message est retrouvable dans Gmail même trois mois
    après, alors que son corps, lui, n'a jamais été enregistré."""
    u = (url_source or "").strip()
    if not u.startswith("gmail:"):
        return ""
    return u[len("gmail:"):].split("#", 1)[0].strip()
