#!/usr/bin/env python3
"""L'IMAGE d'une annonce dans le HTML d'une newsletter — celle de SON bloc, jamais la première.

POURQUOI PAS « LA PREMIÈRE <img> ». `scripts/gmail_collect.py` a renoncé aux images de mail
après un incident réel : le même en-tête Mailinblue collé sur 40 fiches sans rapport, parce
qu'on prenait la première image du HTML. Une newsletter annonce dix événements et porte
vingt images : l'en-tête, les icônes de réseaux, le pixel d'ouverture, et une photo par
annonce. Prendre « une image du mail » est faux neuf fois sur dix ; il faut prendre l'image
DE L'ANNONCE.

COMMENT ON RETROUVE LE BLOC DE L'ANNONCE. Un mail HTML est un emboîtement de tableaux, et
chaque annonce vit dans sa propre cellule : image, titre, texte, bouton. On ne lit donc pas
le HTML comme du texte, on le lit comme un ARBRE (html.parser, rien d'autre) : chaque
morceau de texte et chaque <img> connaît la suite de ses ancêtres. Le titre de la fiche est
localisé dans le texte — par `utils.mail_dates._positions`, le même localisateur que pour la
date et le lieu — puis on remonte ses ancêtres jusqu'au plus petit qui contient au moins une
image SANS contenir le titre d'une autre annonce du même mail. C'est le bloc de l'annonce ;
ses images sont les candidates.

Ce qui rend la chose déterministe, c'est que la question a une réponse fausse REPÉRABLE :

  • si le plus petit ancêtre porteur d'image contient aussi un titre voisin, les deux
    annonces partagent leur bloc — on ne sait pas à qui est l'image, on ne rend RIEN ;
  • si le bloc trouvé porte plus de 60 % du texte du mail, ce n'est pas un bloc d'annonce,
    c'est la lettre entière (mise en page à plat) — on ne rend RIEN non plus, sauf si
    l'attribut `alt` d'une image reprend le titre, ce qui est une attribution écrite par
    l'expéditeur lui-même ;
  • le titre introuvable dans le mail → RIEN.

CE QUE CE MODULE NE FAIT PAS : filtrer les images. Pixels de suivi, logos, icônes, bannières,
dimensions — c'est l'affaire de l'appelant (`scripts/completer_depuis_mail.py`), qui
réutilise les détecteurs existants (`utils.sources.is_logo_image`, `utils.images._is_chrome`,
`utils.images.remote_dims`, `scripts.moisson_officielle._est_traqueur`) au lieu d'en écrire
un second — racine des fautes du 08/09 : « deux détecteurs pour la même chose, un seul juste ».
Ici on ne fait qu'une chose : dire QUELLES images appartiennent à QUELLE annonce.
"""
from __future__ import annotations

from html.parser import HTMLParser

from utils.mail_dates import _TITRE_MIN, _norm, _positions
from utils.mail_lieux import carte_norm

# Éléments sans contenu : ils ne s'empilent pas.
_VIDES = frozenset(("img", "br", "hr", "meta", "link", "input", "area", "base", "col",
                    "embed", "source", "track", "wbr", "param"))
# Éléments de bloc : un espace de part et d'autre, pour que « <td>Nice</td><td>18h</td> »
# ne devienne pas « Nice18h ».
_BLOCS = frozenset(("p", "div", "tr", "td", "th", "table", "tbody", "thead", "li", "ul",
                    "ol", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article",
                    "header", "footer", "blockquote", "center", "br", "hr", "figure",
                    "figcaption", "pre", "dd", "dt"))
_MUETS = frozenset(("script", "style", "head", "title", "noscript"))
# Au-delà de cette part du texte du mail, un « bloc » n'est plus une annonce.
PART_MAX_BLOC = 0.6


class _Lecteur(HTMLParser):
    """Aplatit le HTML en une liste de nœuds (texte | img), chacun avec le chemin de ses
    ancêtres — un identifiant unique par élément ouvert, pour que deux <td> frères ne se
    confondent pas."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.pile: list[tuple[str, int]] = []
        self.noeuds: list[dict] = []
        self._muet = 0
        self._compteur = 0

    def _texte(self, t: str) -> None:
        if self._muet or not t:
            return
        self.noeuds.append({"type": "texte", "texte": t, "chemin": tuple(self.pile)})

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "img":
            self.noeuds.append({
                "type": "img",
                "src": (a.get("src") or a.get("data-src") or "").strip(),
                "alt": (a.get("alt") or a.get("title") or "").strip(),
                "largeur": (a.get("width") or "").strip(),
                "hauteur": (a.get("height") or "").strip(),
                "chemin": tuple(self.pile),
            })
            return
        if tag in _BLOCS:
            self._texte(" ")
        if tag in _VIDES:
            return
        if tag in _MUETS:
            self._muet += 1
        self._compteur += 1
        self.pile.append((tag, self._compteur))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag.lower() not in _VIDES:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in _BLOCS:
            self._texte(" ")
        if tag in _VIDES:
            return
        # HTML de newsletter : des balises se ferment sans avoir été ouvertes, d'autres
        # jamais. On dépile jusqu'à la balise nommée si elle est dans la pile, sinon on
        # ignore la fermeture — l'arbre reste cohérent avec ce qui a été ouvert.
        for i in range(len(self.pile) - 1, -1, -1):
            if self.pile[i][0] == tag:
                del self.pile[i:]
                break
        if tag in _MUETS:
            self._muet = max(0, self._muet - 1)

    def handle_data(self, data):
        self._texte(data)


def analyser(html: str) -> list[dict]:
    """Les nœuds (texte | img) du document, dans l'ordre, avec leur chemin d'ancêtres."""
    p = _Lecteur()
    try:
        p.feed(html or "")
        p.close()
    except Exception:  # noqa: BLE001 — un HTML cassé ne doit rien faire planter
        pass
    return p.noeuds


def texte_du(noeuds: list[dict]) -> str:
    """Le texte lisible du document (les seuls nœuds texte, concaténés)."""
    return "".join(n["texte"] for n in noeuds if n["type"] == "texte")


def _index_par_position(noeuds: list[dict]) -> tuple[str, list[int]]:
    """(texte complet, index du nœud pour chaque caractère du texte complet)."""
    morceaux: list[str] = []
    par_char: list[int] = []
    for i, n in enumerate(noeuds):
        if n["type"] != "texte":
            continue
        morceaux.append(n["texte"])
        par_char.extend([i] * len(n["texte"]))
    return "".join(morceaux), par_char


def _dans(chemin: tuple, bloc: tuple) -> bool:
    return chemin[:len(bloc)] == bloc


def _alt_reprend_titre(alt: str, titre_norm: str) -> bool:
    """L'`alt` désigne-t-il ce titre ? Le titre entier, ou au moins deux mots longs
    communs — « alt="Visite méditative" » pour « Visite méditative au Musée des Arts
    Asiatiques ». Un `alt` d'un seul mot ne prouve rien."""
    a = _norm(alt)
    if not a or len(a) < 6:
        return False
    if titre_norm in a or (len(a) >= _TITRE_MIN and a in titre_norm):
        return True
    mots_t = {m for m in titre_norm.split() if len(m) > 3}
    mots_a = {m for m in a.split() if len(m) > 3}
    return len(mots_t & mots_a) >= 2


def images_du_titre(html: str, titre: str,
                    autres_titres: list[str] | None = None) -> tuple[list[dict], str]:
    """(candidates, motif). Les images qui appartiennent à l'annonce `titre`, chacune
    {src, alt, largeur, hauteur, pourquoi} — celles dont l'`alt` reprend le titre d'abord,
    puis celles du bloc de l'annonce, dans l'ordre du document. `motif` explique une liste
    vide (« titre introuvable », « bloc partagé avec une autre annonce »…) : c'est la
    ligne qu'on montre en dry-run, pour qu'un zéro dise d'où il vient."""
    noeuds = analyser(html)
    if not any(n["type"] == "img" for n in noeuds):
        return [], "le mail ne contient aucune image"
    texte, par_char = _index_par_position(noeuds)
    norm, carte = carte_norm(texte)
    titre_norm = _norm(titre)
    if not norm or not titre_norm:
        return [], "mail sans texte ou titre vide"
    positions = _positions(norm, titre_norm)
    if not positions:
        return [], "titre introuvable dans le mail"
    noeuds_titre = {par_char[carte[p]] for p in positions}

    voisins: set[int] = set()
    for t in autres_titres or []:
        tn = _norm(t)
        if len(tn) < _TITRE_MIN or tn == titre_norm:
            continue
        for p in _positions(norm, tn):
            voisins.add(par_char[carte[p]])
    voisins -= noeuds_titre

    total_texte = sum(len(n["texte"]) for n in noeuds if n["type"] == "texte") or 1
    candidats: list[dict] = []
    vus: set[str] = set()

    def _ajouter(n: dict, pourquoi: str) -> None:
        src = n["src"]
        if src and src not in vus:
            vus.add(src)
            candidats.append({"src": src, "alt": n["alt"], "largeur": n["largeur"],
                              "hauteur": n["hauteur"], "pourquoi": pourquoi})

    # ① L'expéditeur a lui-même écrit à qui est l'image : l'alt reprend le titre.
    for n in noeuds:
        if n["type"] == "img" and _alt_reprend_titre(n["alt"], titre_norm):
            _ajouter(n, "l'attribut alt reprend le titre")

    # ② Le bloc de l'annonce.
    motif = ""
    for it in sorted(noeuds_titre):
        chemin = noeuds[it]["chemin"]
        bloc = None
        for k in range(len(chemin), 0, -1):
            e = chemin[:k]
            contenu = [i for i, n in enumerate(noeuds) if _dans(n["chemin"], e)]
            if not any(noeuds[i]["type"] == "img" for i in contenu):
                continue
            if any(i in voisins for i in contenu):
                # Le bloc propre de l'annonce (sa cellule) n'avait pas d'image ; le premier
                # ancêtre qui en porte est aussi celui d'une autre annonce. Attribuer une
                # de ses images serait tirer au sort.
                motif = ("aucune image propre à l'annonce : le premier bloc qui en contient "
                         "est partagé avec une autre annonce du même mail")
                break
            bloc = e
            break
        if bloc is None:
            motif = motif or "aucune image dans le bloc de ce titre"
            continue
        contenu = [i for i, n in enumerate(noeuds) if _dans(n["chemin"], bloc)]
        part = sum(len(noeuds[i]["texte"]) for i in contenu
                   if noeuds[i]["type"] == "texte") / total_texte
        if part > PART_MAX_BLOC:
            motif = (f"le bloc du titre porte {part:.0%} du texte du mail : c'est la lettre "
                     f"entière, pas une annonce")
            continue
        for i in contenu:
            if noeuds[i]["type"] == "img":
                _ajouter(noeuds[i], "dans le bloc de l'annonce")

    if not candidats:
        return [], motif or "aucune image attribuable à ce titre"
    return candidats, ""
