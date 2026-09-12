#!/usr/bin/env python3
"""La signature d'un article n'est PAS l'organisateur de l'événement.

Incident du 2026-08-11, trouvé en vérifiant moi-même les 28 doutes restants de la file
« À vérifier » (Franck : « c'est à toi de vérifier »). CINQ des vingt-huit posaient la
même question, sur cinq fiches sans rapport :

  fiche  473  « Organisateur réel de la foire (Arabella Pezza semble être une
               journaliste, pas l'organisatrice) »
  fiche 3995  « Stefania Marchiano : autrice de l'article ou organisatrice ? »
  fiche 4381  « Rôle exact d'Amelio Ambrosi : organisateur ou contact presse ? »
  fiche 4127  « Fonction exacte de Denis Falconieri (organisateur, association,
               commune ?) »
  fiche 3545  « Nom exact de l'organisateur (Emilie DUPONT confirmé ?) »

Vérification faite : la Foire de Saint-Ours est organisée par la Région autonome Vallée
d'Aoste, le Marché au Fort par l'Assessorat de l'agriculture avec la Commune de Bard, la
Chambre valdôtaine et le Forte di Bard, le Percorso in Rosso par la Pro Loco de
Saint-Rhémy-en-Bosses, La Farandole par la Ville de Nice avec le Collectif des Arts
Traditionnels – Lou Cat. Aucune des cinq personnes citées n'organise quoi que ce soit.
« Emilie DUPONT » n'est même pas quelqu'un : c'est le nom-bouchon des formulaires.

CE N'ÉTAIT PAS UN DOUTE, C'ÉTAIT UNE LIGNE DE CODE. `scripts/scraper_events.py` écrivait
`entry.get("author")` dans la colonne `organisateur`. Dans un flux RSS, `author` /
`dc:creator` est l'auteur de l'ARTICLE — le journaliste sur un flux de presse, le compte
WordPress qui a publié sur un flux d'institution. Jamais l'organisateur. Le modèle
recopiait ensuite ce nom dans l'article, le contrôleur s'en méfiait à juste titre, et
posait une tâche que personne ne pouvait résoudre en cliquant : la matière ne contenait
pas la réponse. Cinq clics impossibles par récolte, tous les jours.

CE QUE FAIT CE MODULE. Il tranche, sans modèle : ce nom d'organisateur est-il une
signature ou un vrai organisateur ? Deux tests, dans cet ordre.

  1. EST-CE UN NOM DE PERSONNE ? « Ville de Nice », « Pro Loco », « Forte di Bard »
     portent un mot d'organisme — on garde sans discuter. « Arabella Pezza » n'en porte
     aucun et a la forme Prénom Nom : suspect.
  2. LA MATIÈRE LE DIT-ELLE ORGANISATEUR ? Un petit organisateur PEUT s'appeler Denis
     Falconieri. Alors on cherche la preuve dans le texte : « organisé par X »,
     « a cura di X », « promosso da X »… Trouvée, on garde ; absente, on vide.

POURQUOI VIDER PLUTÔT QUE SIGNALER. Parce que la colonne vide donne un MEILLEUR résultat :
`scripts/enrich.py` retombe déjà sur `source_name` (« Organisateur : Ville de Nice »
plutôt que « Organisateur : Emilie Dupont »). Un doute de moins et un fait juste, au lieu
d'un fait faux et d'une tâche.

CE QU'IL NE FAIT JAMAIS : deviner un organisateur. Il ne sait qu'écarter ce qui n'en est
sûrement pas un.
"""
from __future__ import annotations

import re
import unicodedata

# Mots qui désignent un ORGANISME. Leur seule présence suffit à garder la valeur : aucune
# personne physique ne s'appelle « Théâtre de la Ville ». Liste FR/IT/EN — le dépôt lit
# les deux langues, et quelques flux anglophones.
_MOTS_ORGANISME = {
    "ville", "citta", "city", "commune", "comune", "mairie", "municipalite", "municipio",
    "region", "regione", "departement", "provincia", "province", "metropole", "metropoli",
    "assessorat", "assessorato", "prefecture", "syndicat", "communaute", "comunita",
    "association", "associazione", "associacio", "asso", "aps", "odv", "ets", "asbl",
    "fondation", "fondazione", "foundation", "fonds", "fondo",
    "societe", "societa", "cooperative", "cooperativa", "consortium", "consorzio",
    "srl", "spa", "sas", "sarl", "sca", "scop",
    "theatre", "teatro", "opera", "auditorium", "salle", "sala", "scene", "scena",
    "musee", "museo", "musei", "museum", "galerie", "galleria", "gallery", "pinacoteca",
    "chateau", "castello", "castel", "fort", "forte", "citadelle", "cittadella",
    "abbaye", "abbazia", "prieure", "paroisse", "parrocchia", "diocese", "cathedrale",
    "bibliotheque", "biblioteca", "mediatheque", "archives", "archivio",
    "conservatoire", "conservatorio", "academie", "accademia", "institut", "istituto",
    "ecole", "scuola", "universite", "universita", "college", "lycee", "mjc",
    "festival", "biennale", "rencontres", "rassegna", "salon", "foire", "fiera",
    "office", "ufficio", "tourisme", "turismo", "syndicat d'initiative", "pro loco",
    "proloco", "comite", "comitato", "collectif", "collettivo", "club", "cercle",
    "centre", "centro", "maison", "casa", "espace", "spazio", "atelier", "laboratorio",
    "parc", "parco", "jardin", "giardino", "domaine", "tenuta",
    "orchestre", "orchestra", "ensemble", "chorale", "coro", "harmonie", "banda",
    "filarmonica", "philharmonique", "compagnie", "compagnia", "troupe", "cie",
    "federation", "federazione", "union", "unione", "amis", "amici", "groupe", "gruppo",
    "chambre", "camera", "cci", "confartigianato", "coldiretti",
    "cinema", "cineclub", "librairie", "libreria", "bar", "cave", "cantina",
    "hotel", "auberge", "refuge", "rifugio", "camping",
    "ministere", "ministero", "prefettura", "onu", "unesco",
    # PROGRAMMES ET DISPOSITIFS. Ajoutés le 2026-08-11 le soir même, après que la purge
    # a vidé « Interreg ALCOTRA » sur trois fiches (2126, 4304, 4370) : c'est le programme
    # de coopération transfrontalière France-Italie, et il organise bel et bien ses
    # webinaires et son Sommet des Terres Monviso. Deux mots capitalisés, aucun mot
    # d'organisme dans ma liste — il avait exactement la forme d'un prénom et d'un nom.
    # Trois faux positifs sur 187 : le filet a tenu (la valeur était en mémoire), mais
    # c'est bien le genre de nom qu'aucune règle de FORME ne saura jamais reconnaître.
    "interreg", "alcotra", "leader", "erasmus", "europe", "european", "europeen",
    "programme", "programma", "projet", "progetto", "dispositif", "reseau", "rete",
    "agence", "agenzia", "atl", "adt", "epci", "gal", "gect",
}

# Signatures de flux : ni personne ni organisme, juste la mécanique du CMS.
_AUTEURS_DE_FLUX = {
    "redazione", "redaction", "la redaction", "la redazione", "admin", "administrator",
    "amministratore", "webmaster", "staff", "editor", "editore", "author", "autore",
    "ufficio stampa", "service communication", "communication", "comunicazione",
    "comunicati", "press", "presse", "rp", "wordpress", "site", "web", "internet",
    "anonyme", "anonimo", "n/a", "na", "-", "--", "nc",
}

# Particules : « de », « di », « van »… ne comptent pas comme un mot du nom.
_PARTICULES = {"de", "du", "des", "d", "la", "le", "les", "di", "da", "del", "della",
               "dei", "degli", "van", "von", "der", "den", "el", "al", "y", "e"}

# Preuves qu'un nom est bien l'organisateur, telles qu'elles s'écrivent dans la matière.
# Cherchées JUSTE AVANT le nom (fenêtre courte) : « organisé par Denis Falconieri ».
_PREUVES = (
    r"organi[sz][a-z]*\s+(?:par|da|dal|dalla|dai|by)",
    r"a cura di", r"curat[oa] da", r"ideat[oa] da", r"promoss[oa] da",
    r"presentat[oa] da", r"realizzat[oa] da", r"in collaborazione con",
    r"a l'initiative de", r"su iniziativa di", r"port[ée]e? par",
    r"sous l'egide de", r"con il patrocinio di",
    r"president[e]? (?:de|di|du|dell)", r"presidente", r"organisateur", r"organizzatore",
    r"organisatrice", r"organizzatrice",
)
_FENETRE_PREUVE = 90


def _norm(s: str) -> str:
    """Minuscules sans accents — pour comparer, jamais pour restituer."""
    n = unicodedata.normalize("NFKD", (s or "").strip().lower())
    n = "".join(c for c in n if not unicodedata.combining(c))
    return " ".join(n.replace("'", "'").split())


def _mots(nom: str) -> list[str]:
    return [m for m in re.split(r"[\s\-]+", _norm(nom)) if m and m not in _PARTICULES]


def est_signature_de_flux(nom: str) -> bool:
    """« Redazione », « admin », « Ufficio stampa » : le CMS, pas un organisateur."""
    return _norm(nom) in _AUTEURS_DE_FLUX


def porte_un_mot_d_organisme(nom: str) -> bool:
    """Un seul mot d'organisme suffit — on ne cherche pas à qualifier, juste à disculper."""
    plat = _norm(nom)
    if any(exp in plat for exp in ("pro loco", "syndicat d'initiative", "ufficio stampa")):
        return True
    return any(m in _MOTS_ORGANISME for m in re.split(r"[\s\-']+", plat) if m)


def est_nom_de_personne(nom: str) -> bool:
    """Forme « Prénom Nom » (2 ou 3 mots, initiales capitales, aucun mot d'organisme).

    Volontairement étroit : on ne cherche pas à reconnaître tous les noms du monde, mais
    à ne se tromper QUE dans le sens sûr. Un organisme pris pour une personne coûterait
    un vrai organisateur ; une personne prise pour un organisme ne coûte rien de plus
    que ce qui existe déjà aujourd'hui."""
    brut = (nom or "").strip()
    if not brut or len(brut) > 60:
        return False
    if re.search(r"[\d@/|;\n]|https?:", brut):
        return False
    mots = _mots(brut)
    if not 2 <= len(mots) <= 3:
        return False
    if porte_un_mot_d_organisme(brut):
        return False
    # Chaque mot significatif doit commencer par une capitale dans la forme d'ORIGINE
    # (« Emilie DUPONT » oui, « comité des fêtes » non).
    bruts = [m for m in re.split(r"[\s\-]+", brut) if _norm(m) not in _PARTICULES and m]
    return all(m[:1].isupper() for m in bruts)


def corrobore(nom: str, materiau: str) -> bool:
    """La matière dit-elle, en toutes lettres, que cette personne organise ?

    On regarde ce qui PRÉCÈDE chaque occurrence du nom, dans la MÊME PHRASE : « organisé
    par Denis Falconieri » corrobore, « Denis Falconieri a assisté à la fête » non. Le
    sens de lecture compte — c'est ce qui distingue l'organisateur du figurant.

    La coupure à la phrase n'est pas un détail de confort : sans elle, « Fête organisée
    par la Pro Loco. Denis Falconieri était présent. » corroborait Falconieri avec la
    preuve qui désignait quelqu'un d'autre. C'est la façon la plus naturelle dont un
    article de presse cite un témoin — donc exactement le cas qu'on veut écarter."""
    cible, texte = _norm(nom), _norm(materiau)
    if not cible or not texte:
        return False
    preuve = re.compile("|".join(_PREUVES))
    for m in re.finditer(re.escape(cible), texte):
        avant = texte[max(0, m.start() - _FENETRE_PREUVE):m.start()]
        coupure = max(avant.rfind("."), avant.rfind(";"), avant.rfind("!"),
                      avant.rfind("?"), avant.rfind("·"))
        if preuve.search(avant[coupure + 1:]):
            return True
    return False


def verdict(organisateur: str, materiau: str = "") -> tuple[str, str]:
    """('garder'|'vider', raison lisible). Ne propose JAMAIS de remplacement.

    `materiau` : titre + description de l'événement. Absent, la corroboration ne peut
    pas jouer — un nom de personne est alors vidé, ce qui est le bon défaut : sans
    preuve, on ne publie pas le nom de quelqu'un comme organisateur."""
    valeur = (organisateur or "").strip()
    if not valeur:
        return "garder", "déjà vide"
    if est_signature_de_flux(valeur):
        return "vider", "signature de flux (compte du CMS, pas un organisateur)"
    if not est_nom_de_personne(valeur):
        return "garder", "porte un mot d'organisme ou n'a pas la forme d'un nom de personne"
    if corrobore(valeur, materiau):
        return "garder", "la matière dit explicitement que cette personne organise"
    return "vider", "nom de personne sans preuve d'organisation dans la matière (signature)"


def organisateur_depuis_flux(auteur_rss: str, materiau: str = "") -> str:
    """Ce qu'on accepte d'écrire dans `organisateur` au moment de la collecte.

    Rendu vide, `scripts/enrich.py` retombe sur `source_name`, c'est-à-dire l'institution
    qui publie le flux — presque toujours le vrai organisateur, et jamais un journaliste."""
    valeur = (auteur_rss or "").strip()[:200]
    return "" if verdict(valeur, materiau)[0] == "vider" else valeur
