#!/usr/bin/env python3
"""SEO / GEO / AEO d'un événement — pour les événements PHARES, à la demande.

Deux volets (cf. docs/AGENT_SEO_DASHBOARD_SPEC.md) :
  • DÉTERMINISTE, gratuit : le JSON-LD schema.org/Event, construit depuis la base
    (aucun appel LLM). C'est la donnée structurée réutilisable pour l'export
    WordPress (Cultura Sabauda aujourd'hui, Agenda Sabauda demain).
  • LLM, à la demande : title/méta/réponse directe (AEO)/FAQ — la langue et le
    jugement. Réservé aux phares (coût maîtrisé).

Règle maison LLM_OU_CODE : le schema = code ; la langue = LLM.
"""
from __future__ import annotations
import json
import re

# Territoire → (region lisible, code pays ISO) pour PostalAddress.
_TERRITORY_GEO = {
    "Savoie": ("Savoie / Haute-Savoie", "FR"),
    "Piemonte": ("Piemonte", "IT"),
    "Vallee-Aoste": ("Vallée d'Aoste", "IT"),
    "Nice": ("Alpes-Maritimes", "FR"),
}


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


# Suffixe de marque imposé par le prompt SEO_PROMPT ci-dessous et par la convention du
# site (docs/REGLES_SEO_GEO_AEO_AGENDA_SABAUDO.md §1.1 : toute page — hub, catégorie,
# fiche — se termine par « — Agenda Sabauda »). Budget visé : 50-60 caractères, suffixe
# INCLUS. Le LLM le respecte la plupart du temps, mais rien ne le garantissait : un titre
# qui dépasse partait tronqué à 70 caractères pile, sans égard pour un mot coupé en deux
# ni pour le suffixe lui-même amputé (« — Agenda Sabau »). Corrigé le 2026-08-06 : sous
# tension de place, on laisse tomber le suffixe de MARQUE en premier — un site encore
# inconnu ne gagne rien à l'afficher, contrairement au nom de l'événement, qui est ce
# que la recherche cible réellement (cf. discussion avec Franck sur la préconisation SEO).
_SUFFIXE_MARQUE = " — Agenda Sabauda"
_TITRE_SEO_CIBLE = 60

# Yoast affiche « La méta description fait plus de 156 caractères » (constaté le
# 2026-09-08 sur les fiches WP#7490 et WP#7518, captures d'écran de Franck). Le prompt
# ci-dessous vise 150-160 — DÉJÀ au-delà de 156 dans sa propre consigne — et
# `optimize_seo` ne faisait que tronquer sec à 180, ce qui peut couper un mot en deux
# ET laisse passer tout ce qui est entre 157 et 180. `_ajuste_meta_seo` applique la
# même discipline que `_ajuste_titre_seo` : jamais de mot coupé, jamais au-delà du
# budget réel de Yoast.
#
# ET 156 N'ÉTAIT PAS LE BUDGET RÉEL — trouvé le 2026-09-16 en lisant le code de Yoast
# sur le serveur (src/editors/framework/seo/posts/description-data-provider.php) :
# la longueur mesurée est `description + date + 3`, la date au format « Sep 6, 2026 »
# (« Juil 21, 2026 » au plus long : 13), ajoutée SANS CONDITION pour tout contenu daté.
# Le plafond utile est donc 156 − 16 = 140. Mesuré ce jour-là sur le site : 202 des 276
# fiches événements avec description dépassaient (108 encore devant nous), 58 pages,
# 12 articles — toutes écrites « dans le budget » de 156.
#
# Et la coupe préfère la fin d'une PHRASE à la fin d'un mot : « …du 17 juin au 28
# septembre 2026. Peinture et haute » est un mot entier, mais une description tronquée
# en plein élan se lit comme une faute. On ne recule à la phrase que si elle garde au
# moins _META_SEO_PLANCHER caractères — sinon la coupe au mot, comme avant.
_META_SEO_CIBLE = 140
_META_SEO_PLANCHER = 100


def _ajuste_meta_seo(meta: str) -> str:
    """Fait rentrer `meta` dans le budget Yoast (140 car., la date comptée), sans jamais
    couper un mot — et à la fin d'une phrase quand c'est possible."""
    meta = _clean(meta)
    if len(meta) <= _META_SEO_CIBLE:
        return meta
    tete = meta[:_META_SEO_CIBLE]
    fin_phrase = max(tete.rfind(". "), tete.rfind("! "), tete.rfind("? "))
    if fin_phrase + 1 >= _META_SEO_PLANCHER:
        return tete[:fin_phrase + 1]
    coupe = tete.rsplit(" ", 1)[0].rstrip(" ,.;:—-")
    return coupe or tete


def _ajuste_titre_seo(titre: str) -> str:
    """Fait rentrer `titre` dans le budget visé, SANS jamais couper un mot en deux.

    Ordre des replis, du moins au plus coûteux pour la clarté du titre :
      1. déjà dans le budget → inchangé ;
      2. porte le suffixe de marque ET dépasse → suffixe retiré d'abord (c'est lui qui
         coûte le plus cher, ~18 caractères, pour l'apport le plus faible sur un site
         sans notoriété) ;
      3. toujours trop long (nom d'événement déjà long à lui seul) → coupé au dernier
         mot ENTIER sous la limite, jamais en plein milieu d'un mot.
    """
    titre = _clean(titre)
    if len(titre) <= _TITRE_SEO_CIBLE:
        return titre
    if titre.endswith(_SUFFIXE_MARQUE):
        sans_suffixe = titre[: -len(_SUFFIXE_MARQUE)].rstrip()
        if sans_suffixe and len(sans_suffixe) <= _TITRE_SEO_CIBLE:
            return sans_suffixe
        titre = sans_suffixe or titre
    if len(titre) <= _TITRE_SEO_CIBLE:
        return titre
    coupe = titre[:_TITRE_SEO_CIBLE].rsplit(" ", 1)[0].rstrip(" ,.;:—-")
    return coupe or titre[:_TITRE_SEO_CIBLE]


def slugify(text: str) -> str:
    """Slug SEO : minuscules, accents retirés, mots séparés par des tirets."""
    import unicodedata
    t = unicodedata.normalize("NFD", (text or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return t[:70]


# ══ UNE URL NE PORTE JAMAIS DE DATE ══════════════════════════════════════════════════
#
# DÉCISION DE FRANCK, 2026-09-21, en voyant une adresse d'événement annuel : « ne mets
# jamais les dates, mets dans la doctrine qu'il ne faut jamais mettre les dates ». Elle
# prolonge sa décision des 08-09/09 (docs/EDITIONS_ANNUELLES.md) : un événement annuel
# garde UNE adresse, mise à jour d'édition en édition, pour capitaliser les backlinks.
# Une URL millésimée rend ça impossible — l'édition suivante ne peut que créer une
# nouvelle adresse, qui repart de zéro.
#
# CE QUI PRODUISAIT LA DATE, mesuré le 21/09 et pas deviné : `publisher_as` n'envoyait
# AUCUN slug pour une fiche originale (seules les traductions en avaient un, pour rester
# appariables à l'œil). Sans slug, WordPress dérive le permalien du TITRE — et un titre
# dit « Marché au Fort 2026 : … » ou « Du 24 au 27 septembre, Terra Madre … ». Relevé le
# même jour sur le site : 27 des 188 fiches en ligne et non terminées portent une année
# ou un mois dans leur adresse.
#
# CE QU'ON NE CHANGE PAS : le TITRE. Le lecteur et Yoast ont besoin du millésime ; c'est
# l'ADRESSE qui doit survivre à l'édition. Et les fiches DÉJÀ publiées gardent la leur :
# cs-publish.php ne pose `post_name` qu'à la création (`empty($b['wp_post_id'])`), donc
# une republication ne renomme rien. Les 27 adresses existantes se corrigent à la main,
# une par une, en renommant le slug dans WordPress — qui pose la 301 tout seul (mesuré
# le 15/09 sur Vicoforte).

_MOIS_SLUG = frozenset({
    "janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet", "aout", "septembre",
    "octobre", "novembre", "decembre",
    "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto",
    "settembre", "ottobre", "dicembre",
})
# Les mots qui INTRODUISENT une date et n'ont plus rien à dire une fois qu'elle est
# partie : « du 24 au 27 septembre », « dès le 25 septembre », « jusqu'en juin 2027 »,
# « dal 3 al 6 dicembre ». On ne les retire QUE s'ils touchent la date retirée.
_AMORCES_DATE = frozenset({
    "du", "dal", "dall", "au", "al", "le", "la", "les", "il", "des", "dei", "delle",
    "en", "in", "a", "entre", "tra", "jusqu", "jusquen", "fino", "dopo", "apres",
    "depuis", "da", "il", "lo", "der", "on", "from", "to",
    # « samedi ET dimanche », « sabato E domenica » : la conjonction part avec ses jours.
    # Et le démonstratif d'un repère relatif : « CE samedi », « QUESTO sabato ».
    "et", "e", "ou", "o", "ce", "cet", "cette", "questo", "questa",
})
# Les JOURS DE LA SEMAINE (ajouté le 23/09). Le filtre du 21/09 ne connaissait que les
# années, les mois et les quantièmes : WP#10428, créée le 22/09 avec le filtre en place,
# est sortie « …-actes-anciens-a-decouvrir-samedi ». Un « samedi » dans une adresse est
# pire qu'un millésime — il est faux dès le dimanche. Au SINGULIER seulement : « les
# samedis du jazz » dit une habitude, pas une date. (« lunedì » → « lunedi » après NFD.)
_JOURS_SLUG = frozenset({
    "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche",
    "lunedi", "martedi", "mercoledi", "giovedi", "venerdi", "sabato", "domenica",
})
# Un jour garde sa place derrière ces mots : « chaque samedi », « ogni domenica », « un
# mercoledì su due » (WP#9766, lu dans l'inventaire du 23/09), « ouvert le samedi »,
# « il sabato mattina » disent une récurrence, qui ne se périme pas. Sauf si un
# quantième suit : « le samedi 26 » est une date.
_AVANT_JOUR_DURABLE = frozenset({"chaque", "ogni", "tous", "tutti", "tutte",
                                 "un", "une", "uno", "le", "il", "la"})
# … et devant ceux-là, c'est un NOM PROPRE : « Il Sabato del villaggio » (Leopardi).
_APRES_JOUR_NOM = frozenset({"de", "des", "du", "di", "del", "della", "dei", "delle"})
# Les repères RELATIFS au jour de publication, en entier seulement : « ce soir » part,
# « en soirée » reste ; « cette semaine » part, « une semaine d'ateliers » reste. Et
# rien de nu comme « demain » ou « oggi » : mesuré le 23/09 sur les 348 fiches à venir,
# « Piante ieri, oggi e domani » est un TITRE, pas un repère.
_RELATIFS_SLUG = (
    ("ce", "soir"), ("ce", "week", "end"), ("ce", "weekend"), ("cette", "semaine"),
    ("stasera",), ("questa", "sera"), ("questo", "weekend"), ("questo", "week", "end"),
    ("questo", "fine", "settimana"), ("questa", "settimana"),
)


def _slug_entier(texte: str) -> str:
    """Comme `slugify`, mais SANS le plafond de 70 caractères — pour pouvoir filtrer la
    date avant de couper."""
    import unicodedata
    t = unicodedata.normalize("NFD", (texte or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def _coupe_slug(slug: str, maxi: int = 70) -> str:
    """Coupe à `maxi` caractères SUR UN TIRET : une adresse ne se termine ni au milieu
    d'un mot ni par un tiret orphelin."""
    if len(slug) > maxi:
        slug = slug[:maxi].rsplit("-", 1)[0] or slug[:maxi]
    # Une adresse ne se termine pas sur un mot-outil laissé en l'air par la coupe
    # (« …-ouvre-sa-saison-au »). Lu dans le dry-run du 21/09.
    mots = slug.strip("-").split("-")
    while len(mots) > 1 and mots[-1] in _AMORCES_DATE:
        mots.pop()
    return "-".join(mots)


def slug_sans_date(texte: str) -> str:
    """Le slug du titre, débarrassé de tout millésime et de toute date.

    « marche-au-fort-2026-les-saveurs-du-val-daoste-envahissent-bard »
      → « marche-au-fort-les-saveurs-du-val-daoste-envahissent-bard »
    « du-24-au-27-septembre-terra-madre-salone-del-gusto-apporte-la-biodiversite »
      → « terra-madre-salone-del-gusto-apporte-la-biodiversite »

    Retire : les années (19xx / 20xx), les noms de mois FR et IT, les jours de la semaine
    au singulier (« …-a-decouvrir-samedi », 23/09), les repères relatifs entiers (« ce
    soir », « ce week-end »), les quantièmes (1-31) qui touchent un mois ou un jour
    retiré, et les mots qui introduisaient la date. Si tout part —
    un titre qui n'était QUE sa date — on rend le slug entier plutôt qu'une adresse vide.

    LIMITE CONNUE : un titre dont le mois EST le sujet perd son mot (« Mai 68 » → « 68 »).
    Rare, et le coût d'une URL un peu pauvre est moindre que celui d'une URL périmée."""
    # Les apostrophes disparaissent au lieu de devenir des tirets : c'est ce que fait
    # `sanitize_title` de WordPress, et donc ce à quoi ressemblent toutes les adresses
    # déjà en ligne (« …-du-val-daoste-… »). Une adresse qui détonne se repère.
    sans_apostrophe = re.sub(r"['’]", "", texte or "")
    # On filtre AVANT de couper : `slugify` plafonne à 70 caractères, et couper d'abord
    # laissait « …-biodiver » et des tirets orphelins en fin d'adresse. Lu dans le
    # dry-run du 21/09, sur les titres réels — pas deviné.
    base = _slug_entier(sans_apostrophe)
    if not base:
        return base
    mots = base.split("-")
    garde = [True] * len(mots)

    def _est_annee(m):
        return len(m) == 4 and m.isdigit() and m[:2] in ("19", "20")

    def _est_quantieme(m):
        return m.isdigit() and 1 <= len(m) <= 2 and 1 <= int(m) <= 31

    for i, m in enumerate(mots):
        if _est_annee(m) or m in _MOIS_SLUG:
            garde[i] = False
    jours = set()
    for i, m in enumerate(mots):
        suivi_dun_quantieme = i + 1 < len(mots) and _est_quantieme(mots[i + 1])
        if (m in _JOURS_SLUG
                and not (i and mots[i - 1] in _AVANT_JOUR_DURABLE and not suivi_dun_quantieme)
                and not (i + 1 < len(mots) and mots[i + 1] in _APRES_JOUR_NOM)):
            garde[i] = False
            jours.add(i)
    for seq in _RELATIFS_SLUG:
        n = len(seq)
        for i in range(len(mots) - n + 1):
            if tuple(mots[i:i + n]) == seq:
                for k in range(i, i + n):
                    garde[k] = False
    # Un quantième ne se retire que s'il TOUCHE un mois ou un jour retiré :
    # « 1-000-places » n'est pas une date, et « 65e Fête de la Châtaigne » non plus.
    # « samedi 26 » en est une, même sans son mois.
    reperes = {i for i, m in enumerate(mots) if m in _MOIS_SLUG} | jours
    for i, m in enumerate(mots):
        if garde[i] and _est_quantieme(m) and ({i - 1, i + 1} & reperes):
            garde[i] = False
    # Puis on remonte vers la gauche tant que le mot précédent n'est qu'une amorce de
    # date ou un autre quantième : « du 24 au 27 septembre » part en entier.
    for i in range(len(mots) - 1, -1, -1):
        if garde[i] or i == 0:
            continue
        j = i - 1
        while j >= 0 and garde[j] and (mots[j] in _AMORCES_DATE or _est_quantieme(mots[j])):
            garde[j] = False
            j -= 1
    reste = [m for m, k in zip(mots, garde) if k]
    return _coupe_slug("-".join(reste) if len(reste) >= 2 else base)


def build_event_jsonld(ev: dict) -> dict | None:
    """Construit le JSON-LD schema.org/Event depuis les champs de la base.
    Déterministe, sans LLM. Renvoie None si l'événement n'a pas le minimum
    requis par Google (nom + date de début)."""
    name = _clean(ev.get("title"))
    start = (ev.get("date_event_start") or "").strip()
    if not name or not start:
        return None  # name + startDate sont requis (règle Google)

    region, country = _TERRITORY_GEO.get(ev.get("territoire") or "", ("", "FR"))
    # location : Place + PostalAddress (adresse rue/géo non stockées → on met ce
    # qu'on a : nom du lieu, ville, région, pays).
    address = {"@type": "PostalAddress"}
    if ev.get("ville"):
        address["addressLocality"] = _clean(ev["ville"])
    if region:
        address["addressRegion"] = region
    address["addressCountry"] = country
    place = {"@type": "Place", "address": address}
    if ev.get("lieu"):
        place["name"] = _clean(ev["lieu"])
    elif ev.get("ville"):
        place["name"] = _clean(ev["ville"])

    data = {
        "@context": "https://schema.org",
        "@type": "Event",
        "name": name,
        "startDate": start,
        "eventStatus": "https://schema.org/EventScheduled",
        "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        "location": place,
        "inLanguage": "fr",
        "publisher": {
            "@type": "Organization", "name": "Agenda Sabauda",
            "parentOrganization": {"@type": "Organization", "name": "Cultura Sabauda"},
        },
    }
    end = (ev.get("date_event_end") or "").strip()
    if end and end != start:
        data["endDate"] = end
    desc = _clean(ev.get("description"))
    if desc:
        data["description"] = desc[:300]
    if ev.get("url_image"):
        data["image"] = [ev["url_image"]]
    if ev.get("organisateur"):
        data["organizer"] = {"@type": "Organization", "name": _clean(ev["organisateur"])}
    return data


def event_jsonld_str(ev: dict) -> str:
    """JSON-LD prêt à coller dans un <script type="application/ld+json">."""
    data = build_event_jsonld(ev)
    if data is None:
        return ""
    return json.dumps(data, ensure_ascii=False, indent=2)


# Langue de rédaction du SEO. Jusqu'au 2026-09-09 le prompt disait « Produis, en
# français » en dur, et seo_batch EXCLUAIT les traductions depuis le 02/08 pour ne pas
# pousser une méta française sur une fiche italienne (son commentaire : « on exclut
# d'abord, on rédigera en italien ensuite »). Cinq semaines plus tard, « ensuite » n'était
# pas arrivé : les 34 fiches italiennes devant nous n'avaient AUCUNE expression clé, d'où
# les points GRIS de la colonne Yoast (Franck, capture du 09/09). Le prompt reçoit donc
# la langue, et seo_batch vérifie la langue de ce qui revient avant d'écrire.
_LANGUE_NOM = {"fr": "français", "it": "italien"}

SEO_PROMPT = """Tu optimises le référencement (Yoast) d'un événement culturel pour un agenda
en ligne bilingue (Savoie, Piémont, Vallée d'Aoste, Nice). Style sobre, factuel, jamais racoleur
(pas de « incontournable », « magique »). Géographie nommée (ville, territoire).
LANGUE : tout ce que tu produis (expression clé, titre, slug, méta, réponse, FAQ) est en
{langue_nom} — c'est la langue de la fiche publiée, le lecteur et Google la lisent dans
cette langue. Le suffixe de marque « — Agenda Sabauda » reste tel quel.

Événement :
Titre : {title}
Catégorie : {categorie}
Lieu : {lieu}, {ville} ({territoire})
Dates : {dates}
Description : {description}

Choisis d'abord UNE expression clé principale (« focus keyphrase ») : 2 à 4 mots, le cœur
cherché de l'événement (ex. nom propre + lieu). IMPÉRATIF : choisis des mots qui apparaissent
TELS QUELS dans la description/l'article ci-dessus (sinon Yoast signale « clé absente du
texte »). Puis rédige TOUT autour d'elle, en respectant Yoast :
- le titre SEO COMMENCE par l'expression clé ;
- la méta description CONTIENT l'expression clé ;
- la réponse directe et l'intro CONTIENNENT l'expression clé ;
- le slug CONTIENT l'expression clé (minuscules, tirets).

Produis, en {langue_nom}, en JSON strict :
{{"seo_keyphrase": "<expression clé principale, 2-4 mots>",
  "seo_title": "<titre SEO 50-60 caractères, COMMENÇANT par l'expression clé ; suffixe ' — Agenda Sabauda'>",
  "seo_slug": "<slug court contenant l'expression clé, minuscules-et-tirets, JAMAIS d'année ni de date>",
  "seo_meta": "<meta description 115-140 caractères (Yoast y ajoute la date), factuelle (quoi, où, quand) et CONTENANT l'expression clé>",
  "seo_answer": "<réponse directe de 40-60 mots (AEO), CONTENANT l'expression clé, réutilisable en chapô>",
  "seo_tags": ["<3 à 6 étiquettes : lieu, ville, artistes/thème, catégorie>"],
  "seo_faq": [
    {{"q": "<question naturelle, ex. Quand a lieu … ?>", "a": "<réponse courte et factuelle>"}},
    {{"q": "<Où se déroule … ?>", "a": "<…>"}},
    {{"q": "<Est-ce gratuit ? / Faut-il réserver ?>", "a": "<…>"}}
  ]}}
Réponds UNIQUEMENT le JSON, sans texte avant/après."""


def langue_seo(ev: dict) -> str:
    """Langue dans laquelle le SEO de cette fiche doit être rédigé : 'fr' ou 'it'.
    `translated_lang` fait foi pour une traduction ; sinon la langue de l'ARTICLE publié
    (`utils.lang.effective_lang`), la même source de vérité que la publication et la
    traduction depuis le 2026-09-07."""
    forced = str(ev.get("translated_lang") or "").strip().lower()
    if forced in _LANGUE_NOM:
        return forced
    from utils.lang import effective_lang
    return effective_lang(ev)


def optimize_seo(ev: dict, client, model: str, lang: str | None = None) -> dict | None:
    """Passe LLM : title/méta/réponse directe/FAQ. Renvoie un dict validé ou None.
    Les exceptions API (crédit, réseau) remontent à l'appelant (la route les gère).
    `lang` : 'fr' ou 'it' ; à défaut, déduite de la fiche (`langue_seo`). Le dict rendu
    porte la langue demandée sous `seo_lang`, pour que l'appelant puisse la contrôler."""
    lang = lang if lang in _LANGUE_NOM else langue_seo(ev)

    def _dates(ev):
        s = (ev.get("date_event_start") or "").strip()
        e = (ev.get("date_event_end") or "").strip()
        if s and e and e != s:
            return f"du {s} au {e}"
        return s or "date à confirmer"

    # Matière pour choisir la clé : l'ARTICLE rédigé s'il existe (c'est LUI qui
    # sera publié → la clé doit y figurer), sinon la description brute.
    material = _clean(ev.get("article_md") or ev.get("description"))
    from utils.voix import voix_block
    prompt = voix_block() + SEO_PROMPT.format(
        title=_clean(ev.get("title")),
        categorie=ev.get("llm_categorie") or "",
        lieu=ev.get("lieu") or "",
        ville=ev.get("ville") or "",
        territoire=ev.get("territoire") or "",
        dates=_dates(ev),
        description=material[:900],
        langue_nom=_LANGUE_NOM[lang],
    )
    message = client.messages.create(
        model=model, max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    try:
        from utils import usage
        usage.record_message(model, message, label="seo")
    except Exception:
        pass  # le suivi de coût ne doit jamais bloquer la génération
    raw = "".join(getattr(b, "text", "") for b in message.content
                  if getattr(b, "type", None) == "text").strip()
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        return None
    try:
        data = json.loads(match.group())
    except json.JSONDecodeError:
        return None
    # Validation légère : on garde ce qui est exploitable.
    faq = data.get("seo_faq") or []
    faq = [{"q": _clean(x.get("q")), "a": _clean(x.get("a"))}
           for x in faq if isinstance(x, dict) and x.get("q") and x.get("a")]
    tags = data.get("seo_tags") or []
    tags = [_clean(t) for t in tags if isinstance(t, str) and _clean(t)][:6]
    # Clé recalée sur la matière RÉELLEMENT publiée : une préposition d'écart et Yoast
    # compte zéro occurrence (voir `recale_keyphrase`). Déterministe, aucun appel de plus.
    keyphrase = recale_keyphrase(_clean(data.get("seo_keyphrase")), material)
    slug = slugify(data.get("seo_slug") or keyphrase or _clean(data.get("seo_title")))
    return {
        "seo_keyphrase": keyphrase[:60],
        "seo_title": _ajuste_titre_seo(data.get("seo_title"))[:70],
        "seo_slug": slug,
        "seo_meta": _ajuste_meta_seo(data.get("seo_meta")),
        "seo_answer": _clean(data.get("seo_answer")),
        "seo_tags": tags,
        "seo_faq": faq,
        "seo_lang": lang,
    }


# ── Recalage de l'expression clé sur le texte réellement publié ─────────────────────
#
# D'OÙ ÇA VIENT — 2026-09-10, capture de Franck : « on a peu de vert pour le SEO des
# événements ». Mesuré le jour même sur deux fiches, une VERTE et une ROUGE, toutes deux
# passées par `seo_batch` :
#
#   WP#772  « La Foire de Saint-Ours 2027 »      250 mots, 1 sous-titre  → vert
#   WP#2283 « La Fiera del Bue Grasso di Carrù » 243 mots, 0 sous-titre  → rouge
#
# Et sur la rouge, la clé rendue par le LLM était « Fiera del Bue Grasso Carrù » quand le
# corps écrit — le corps est rédigé AVANT le choix de la clé — dit « Fiera del Bue Grasso
# DI Carrù ». Un seul mot de liaison d'écart, et Yoast compte zéro occurrence : clé absente
# de l'introduction, densité nulle, clé absente des sous-titres. Trois points rouges pour
# une préposition.
#
# Le prompt exigeait déjà « des mots qui apparaissent TELS QUELS » (règle 3 : un portillon
# qui se rejoue sur la même entrée n'est pas un rouvreur — ici on ne refuse RIEN, on
# recale, donc pas de boucle et pas d'appel API supplémentaire). Le contrôle est
# DÉTERMINISTE : on ne fait jamais confiance au LLM pour une comparaison de chaînes.
_MOTS_LIAISON = {
    "de", "du", "des", "d", "la", "le", "les", "l", "a", "au", "aux", "et", "en",
    "di", "del", "della", "dei", "degli", "delle", "il", "lo", "i", "gli", "e",
    "al", "alla", "ai", "dell", "da", "dal", "in", "of", "the",
}


def _mots_replies(texte: str) -> list[tuple[str, str]]:
    """(mot d'origine, mot replié) — minuscules, accents retirés, ponctuation ignorée."""
    import unicodedata
    sortie = []
    for mot in re.findall(r"[^\W_]+", texte or "", flags=re.UNICODE):
        plie = unicodedata.normalize("NFD", mot.lower())
        plie = "".join(c for c in plie if unicodedata.category(c) != "Mn")
        sortie.append((mot, plie))
    return sortie


def cle_dans_texte(cle: str, texte: str) -> bool:
    """La clé apparaît-elle TELLE QUELLE (aux accents et à la casse près) dans le texte ?
    C'est la question que Yoast pose pour l'introduction, la densité et les sous-titres."""
    mots_cle = [p for _, p in _mots_replies(cle)]
    mots_txt = [p for _, p in _mots_replies(texte)]
    if not mots_cle or len(mots_cle) > len(mots_txt):
        return False
    n = len(mots_cle)
    return any(mots_txt[i:i + n] == mots_cle for i in range(len(mots_txt) - n + 1))


def recale_keyphrase(cle: str, texte: str, tolerance: int = 2) -> str:
    """Rend la clé telle qu'elle est ÉCRITE dans le texte, quand seuls des mots de liaison
    l'en séparent. Sinon rend la clé inchangée : on ne fabrique jamais une clé absente.

    « Fiera del Bue Grasso Carrù » + un corps qui dit « Fiera del Bue Grasso di Carrù »
    → « Fiera del Bue Grasso di Carrù ». Deux mots de liaison intercalés au plus, et
    AUCUN mot porteur de sens : sauter un mot plein changerait le sens de la clé.
    """
    cle = _clean(cle)
    if not cle or not texte or cle_dans_texte(cle, texte):
        return cle
    mots_cle = [p for _, p in _mots_replies(cle)]
    tokens = _mots_replies(texte)
    if not mots_cle:
        return cle
    for depart in range(len(tokens)):
        if tokens[depart][1] != mots_cle[0]:
            continue
        i, k, sautes = depart + 1, 1, 0
        while i < len(tokens) and k < len(mots_cle):
            if tokens[i][1] == mots_cle[k]:
                i += 1
                k += 1
            elif tokens[i][1] in _MOTS_LIAISON and sautes < tolerance:
                sautes += 1
                i += 1
            else:
                break
        if k == len(mots_cle):
            return " ".join(orig for orig, _ in tokens[depart:i])
    return cle


def faq_jsonld_str(faq: list[dict]) -> str:
    """JSON-LD FAQPage depuis la FAQ générée."""
    if not faq:
        return ""
    data = {
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": x["q"],
             "acceptedAnswer": {"@type": "Answer", "text": x["a"]}}
            for x in faq
        ],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)
