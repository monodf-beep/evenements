#!/usr/bin/env python3
"""Évaluation LLM des événements pending.

SDK anthropic DIRECT — même pattern que synthesize.py de l'Observatoire.
PAS de LiteLLM.
Cron : 0 9 * * * (quotidien 9h, après le scraping de 8h)
"""
from __future__ import annotations
import anthropic
import argparse
import json
import os
import re
import sqlite3
import sys
from datetime import date
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils import usage
from utils.eventness import non_event_reason
from utils.sources import is_excluded_event, load_excluded_events_filter
from scripts.perimetre import ville_hors_perimetre
from scripts.scraper_events import init_db

log = get_logger("evaluator")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
# (Le modèle n'est PAS fixé ici : il vient de settings.model() / ANTHROPIC_MODEL
#  dans main() ; l'ancien DEFAULT_MODEL était du code mort, retiré.)
BATCH_SIZE = 100

# Seuil de rétention « mise en avant » : score >= RETAIN_MIN_SCORE → à valider
# (home) ; en dessous → catalogue. Source unique, défaut 7 (compat ENRICH_MIN_SCORE).
RETAIN_MIN_SCORE = int(os.getenv("RETAIN_MIN_SCORE", os.getenv("ENRICH_MIN_SCORE", "7")))

# Sentinel : échec d'APPEL API (réseau / statut). L'événement reste 'pending'
# et sera réévalué au prochain run — jamais rejeté à tort pour une panne API.
API_ERROR = object()

CATEGORIES = ("Expositions & Patrimoine", "Concerts & Musique",
              "Spectacle vivant", "Festivals", "Gastronomie & Sagre",
              "Marchés & Foires", "Sport", "Cinéma", "Jeune public & Famille",
              "Conférences & Rencontres", "Fêtes & Traditions populaires")

# Territoires couverts, valeurs canoniques (mêmes libellés que config/sources.txt).
# L'évaluateur peut CORRIGER le territoire d'une source large mal étiquetée.
TERRITOIRES = ("Savoie", "Piemonte", "Vallee-Aoste", "Nice")


def is_past_event(ev: dict, today: str) -> bool:
    """Vrai si l'événement est TERMINÉ (sa date de fin — ou de début à défaut —
    est antérieure à aujourd'hui). On informe de ce qui VA se passer, pas du passé.
    Sans date connue → False (indécidable, on laisse la suite juger)."""
    end = (ev.get("date_event_end") or ev.get("date_event_start") or "").strip()[:10]
    return bool(end) and end < today

EVAL_PROMPT = """Tu es l'assistant éditorial de Cultura Sabauda, agenda culturel bilingue
FR/IT couvrant Savoie/Haute-Savoie, Piémont, Vallée d'Aoste et Nice. On couvre LARGE, à la
manière de GuidaTorino : expositions, concerts, spectacles, festivals, sagre et gastronomie,
marchés (fleurs, antiquaires, brocante, artisanat), sport, cinéma, fêtes populaires…

ÉTAPE 0 — PÉRIMÈTRE (localisation). Où se déroule VRAIMENT l'événement ? Nos 4 territoires :
  • Savoie / Haute-Savoie (73/74) : Chambéry, Annecy, Aix-les-Bains, Albertville, Annemasse,
    Thonon, Chamonix, Tarentaise, Maurienne, Chablais, autour des lacs du Bourget et d'Annecy…
  • Piémont (Piemonte) : Turin, Cuneo, Alba, Asti, Alessandria, Biella, Novara, Langhe, Monferrato…
  • Vallée d'Aoste (Vallee-Aoste) : Aoste, Courmayeur, Cervinia, Cogne, Saint-Vincent…
  • Comté de Nice = ARRONDISSEMENT DE NICE uniquement (territoire "Nice") : Nice, Menton,
    Villefranche-sur-Mer, Beaulieu-sur-Mer, Saint-Jean-Cap-Ferrat, Roquebrune-Cap-Martin,
    Cap-d'Ail, Sospel, la Roya (Breil, Saorge, Tende), la Vésubie (Saint-Martin-Vésubie,
    Roquebillière), la Tinée (Saint-Étienne-de-Tinée, Isola), Levens, Contes, Puget-Théniers…
    ⚠️ Comté de Nice ≠ Alpes-Maritimes. L'ARRONDISSEMENT DE GRASSE est HORS PÉRIMÈTRE :
    Cannes, Antibes (et Juan-les-Pins), Grasse, Cagnes-sur-Mer, Vence, Saint-Paul-de-Vence,
    Mougins, Valbonne (et Sophia Antipolis), Le Cannet, Vallauris, Mandelieu-la-Napoule,
    Mouans-Sartoux, Villeneuve-Loubet, Saint-Laurent-du-Var, Carros, Biot, Théoule-sur-Mer…
    → "hors_perimetre": true, score 0, MÊME si la source est étiquetée « Nice », « 06 »,
    « Alpes-Maritimes » ou « Côte d'Azur ». La frontière est le fleuve Var : à l'ouest et
    au sud-ouest du Var (Cannes, Antibes, Grasse) = hors ; Nice et l'arrière-pays niçois,
    la vallée du Var côté est, Menton et les vallées = dans le périmètre.
Une source régionale/presse déborde souvent (Lyon, Grenoble, Valence, Avignon, Marseille, Gap,
Milan hors Piémont, Gênes, Turin OK mais Bologne non…). Si le lieu réel est HORS de ces 4
territoires → "hors_perimetre": true, "est_evenement": false, score 0. Un simple lieu cité en
passant (tournée, comparaison) ne suffit PAS : c'est le lieu de l'événement qui compte.
Sinon → "hors_perimetre": false, et renseigne "territoire" avec le bon parmi
Savoie · Piemonte · Vallee-Aoste · Nice (corrige si la source l'a mal étiqueté).

ÉTAPE 1 — GATE. Est-ce un ÉVÉNEMENT auquel le public peut ASSISTER, à une date à venir ou
en cours, dans un lieu ? Si NON (actualité institutionnelle, réunion/convention/subvention/
nomination, inauguration ou remise de prix DÉJÀ passée, travaux/voirie/mobilité, consultation
publique) → "est_evenement": false et score 0. Sinon → true, continue.
  ⚠️ PIÈGE PRESSE : un ARTICLE *au sujet d'*un événement n'est PAS l'événement. Rejette
  (est_evenement=false, score 0) tout ce qui est angle journalistique — logistique/pratique
  (« où circuler / se garer / stationner », « les meilleurs spots pour assister », plan de
  circulation, horaires de bus), portrait/coulisses (« ces X qui… », « la caravane
  publicitaire », interview), compte-rendu ou bilan (« s'est réuni », « retour sur »,
  « ce qu'il faut retenir »), même si un GROS événement (Tour de France, festival connu)
  est cité. Ne garde que l'ANNONCE d'une sortie datée + lieu à laquelle on peut assister.
  🎬 PIÈGE CINÉMA : une SÉANCE de cinéma ordinaire (projection d'un film dans la
  programmation courante d'une salle, ciné-club récurrent, séance unique de film sans
  dimension événementielle) n'a PAS sa place dans l'agenda → "est_evenement": true mais
  "score": 0. On GARDE en revanche, scorés normalement, les vrais ÉVÉNEMENTS cinéma :
  FESTIVALS de cinéma, rétrospectives thématiques dédiées, avant-premières
  événementielles, projections en plein air à programmation spéciale, hommages et
  rencontres avec un cinéaste. Le critère : est-ce un simple passage à l'affiche (exclu)
  ou un rendez-vous cinéma à part entière (gardé) ?

ÉTAPE 1 bis — PUBLIC VISÉ (pas seulement public ADMIS). Agenda Sabauda s'adresse à des
HABITANTS et à des VISITEURS, pas à des CONGRESSISTES. Le fait qu'une inscription soit
ouverte à tous ne suffit pas : beaucoup de congrès acceptent le public et n'intéressent
personne hors du métier concerné.
LA QUESTION À TE POSER, et la seule : « à supposer que je n'exerce PAS ce métier et que
je ne sois PAS chercheur dans ce domaine, est-ce que j'ai une raison d'y aller ? »
  → Si la réponse est NON, c'est une manifestation PROFESSIONNELLE :
    "public_vise": "professionnel", "est_evenement": false, score 0.
    Relèvent de ce cas : congrès et colloques scientifiques ou universitaires, salons
    B2B et rencontres d'affaires, conventions et séminaires d'entreprise, journées
    d'étude ou assises d'une filière, symposiums, workshops de spécialistes, remises de
    prix internes à une profession — MÊME ouverts sur inscription, même gratuits, même
    dans un lieu prestigieux. Cas réels écartés par Franck le 2026-08-02 : « IASP World
    Conference », « Colloque International Villes et Santé Mentale », « EVO 2026 ».
    Indices convergents : public désigné comme « professionnels », « experts »,
    « chercheurs », « acteurs de la filière », « décideurs » ; programme en sessions
    parallèles avec appel à communications ; tarif « exposant » / « délégué » ; langue
    de travail anglaise pour un public de spécialistes ; organisateur = société savante,
    fédération professionnelle, laboratoire, chambre consulaire.
  → Sinon "public_vise": "grand_public", et tu CONTINUES l'évaluation normalement.

  ⚠️ PIÈGE CENTRAL, à ne pas rater : NE JUGE PAS SUR LE MOT DU TITRE. « Congrès »,
  « colloque », « salon », « summit », « forum », « rencontre », « conférence » ne
  décident RIEN par eux-mêmes — un filtre sur ces mots viderait une catégorie entière
  du site. Restent PLEINEMENT dans le périmètre, et se scorent normalement :
    • Salon du livre, salon des vins, salon des antiquaires, salon du mariage grand public ;
    • foire artisanale, foire commerciale ouverte au public, marché de créateurs ;
    • rencontre / dédicace avec un auteur, un illustrateur, un cinéaste ;
    • conférence grand public d'un musée, d'une bibliothèque, d'une société d'histoire
      locale, d'une université populaire ; cycle de conférences tout public ;
    • café philo, café géo, veillée, conférence-débat citoyenne, café des sciences ;
    • congrès d'une association de passionnés qui ouvre des animations au public
      (philatélie, minéraux, généalogie, modélisme) — la partie publique compte.
  La catégorie « Conférences & Rencontres » est l'une de nos onze catégories et doit
  rester active : un événement de savoir destiné à tous est exactement ce qu'on cherche.
  Le partage se fait sur À QUI ÇA S'ADRESSE, jamais sur le format ni sur le titre.
  En cas de doute réel sur le public, considère que c'est du grand public (on préfère
  un catalogue un peu large à une catégorie vidée).

ÉTAPE 2 — SCORE D'IMPORTANCE (0-10). PAS de profondeur culturelle exigée : on mesure si
l'événement est IMPORTANT (va réunir du monde, compte dans le territoire). Note chaque critère :

- notoriete_lieu (0-3) : lieu emblématique et très cité (grand stade, opéra, grand musée,
  place centrale) = 3 ; lieu reconnu = 2 ; lieu local modeste = 1 ; confidentiel/inconnu = 0.
  Pondère par la taille de la commune (dans un petit village, le lieu local principal compte).
- organisateur_moyens (0-2) : institution / gros opérateur / grand festival = 2 ;
  ville ou association structurée = 1 ; petit organisateur informel = 0.
- edition_tradition (0-2) : rendez-vous historique / édition élevée (Xe) / anniversaire = 2 ;
  récurrent établi = 1 ; première ou ponctuel = 0.
- rayonnement (0-2) : international ou transfrontalier FR-IT = 2 ; régional = 1 ; local = 0.
- specificite_territoriale (0-1) : identitaire, propre au territoire = 1 ; générique/franchise
  qu'on trouve partout = 0.

score = somme des points (0-10). N'EXCLUS PAS le grand public, le sport, la gastronomie ni les
marchés. Écarte seulement (score bas) le TRÈS confidentiel et le PUREMENT commercial (déstockage,
vente privée, showroom de marque). ⚠️ « Purement commercial » ne vise PAS les salons et foires
grand public à dimension culturelle ou de terroir (salon du livre, salon des vins, foire
artisanale, marché de créateurs) : ceux-là se scorent normalement, comme n'importe quel autre
événement. Le méga-concert de tournée est admis mais sans bonus « territoire ».

CATÉGORIE : choisis-en UNE parmi : {categories}.

Réponds UNIQUEMENT en JSON valide, sans texte avant/après :
{{"hors_perimetre": <true|false>,
  "territoire": "<Savoie|Piemonte|Vallee-Aoste|Nice ou "" si hors périmètre>",
  "public_vise": "<grand_public|professionnel>",
  "est_evenement": <true|false>,
  "categorie": "<une catégorie de la liste>",
  "criteres": {{
    "notoriete_lieu": {{"points": <0-3>, "note": "<courte raison>"}},
    "organisateur_moyens": {{"points": <0-2>, "note": "<courte raison>"}},
    "edition_tradition": {{"points": <0-2>, "note": "<courte raison>"}},
    "rayonnement": {{"points": <0-2>, "note": "<courte raison>"}},
    "specificite_territoriale": {{"points": <0-1>, "note": "<courte raison>"}}
  }},
  "score": <0-10>,
  "justification": "<une phrase de synthèse>"}}"""

# Le bloc événement (variable) est le SEUL contenu qui change d'un appel à l'autre :
# il part en message user, tandis que les instructions (constantes) vont en SYSTÈME mis
# en CACHE → l'énorme prompt d'instructions n'est plus refacturé à chaque événement.
EVAL_USER = """Événement à évaluer :
Titre : {title}
Description : {description}
Lieu : {lieu}, {territoire}
Source : {source_name}"""


def evaluate_event(event: dict, client: anthropic.Anthropic, model: str,
                   calibration: str = "") -> dict | None:
    # Système = instructions constantes (+ calibrage, stable sur un run) → CACHÉ.
    system_text = EVAL_PROMPT.format(categories=" · ".join(CATEGORIES)) + (calibration or "")
    user_text = EVAL_USER.format(
        title=event.get("title", ""),
        description=(event.get("description") or "")[:800],
        lieu=event.get("lieu") or event.get("ville") or "",
        territoire=event.get("territoire", ""),
        source_name=event.get("source_name", ""),
    )
    try:
        message = client.messages.create(
            model=model,
            max_tokens=1536,
            system=[{"type": "text", "text": system_text,
                     "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user_text}],
        )
        usage.record_message(model, message, label="évaluation")
        # Récupère le bloc TEXTE (le modèle peut émettre un bloc de raisonnement en 1er).
        raw = "".join(getattr(b, "text", "") for b in message.content
                      if getattr(b, "type", None) == "text").strip()
        match = re.search(r"\{.*\}", raw, re.S)
        if not match:
            return None
        return json.loads(match.group())
    except (anthropic.APIStatusError, anthropic.APIConnectionError) as exc:
        usage.note_api_error(exc)
        log.error("Erreur API Anthropic : %s", exc)
        return API_ERROR
    except (json.JSONDecodeError, IndexError) as exc:
        log.warning("JSON invalide pour '%s' : %s", event.get("title", "")[:50], exc)
        return None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Évaluation LLM des événements pending.")
    parser.add_argument("--from", dest="dfrom", default="",
                        help="Ne traiter que les événements chevauchant [from, to] (AAAA-MM-JJ).")
    parser.add_argument("--to", dest="dto", default="")
    args = parser.parse_args(argv)

    load_dotenv(ROOT / ".env")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        log.error("ANTHROPIC_API_KEY non définie")
        return 1
    # Modèle : réglage back-office (profil éco = Haiku / qualité = Sonnet) ; l'env
    # ANTHROPIC_MODEL, si posé, reste prioritaire (échappatoire power-user).
    from utils import settings as pipeline_settings
    model = os.getenv("ANTHROPIC_MODEL") or pipeline_settings.model()
    client = anthropic.Anthropic(api_key=api_key)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db(conn)  # garantit les colonnes de date même sur une base ancienne

    where, qparams = ["statut = 'pending'"], []
    scope = ""
    if args.dfrom and args.dto:
        # Circonscrit à une période de travail : n'évalue (donc ne paie) que les
        # événements qui CHEVAUCHENT la fenêtre. Voir app : « statut pilote le coût ».
        where.append("COALESCE(date_event_start,'') <= ? AND COALESCE(date_event_end,'') >= ?")
        qparams += [args.dto, args.dfrom]
        scope = f" [période {args.dfrom}→{args.dto}]"
    pending = conn.execute(
        f"SELECT * FROM events_raw WHERE {' AND '.join(where)} LIMIT ?",
        (*qparams, BATCH_SIZE)
    ).fetchall()
    log.info("%d événements à évaluer%s (modèle : %s)", len(pending), scope, model)

    today = date.today().isoformat()
    # Mémoire d'apprentissage : les ajustements de score de Franck, injectés comme
    # calibrage dans le prompt → l'évaluateur s'aligne peu à peu sur son goût.
    from utils import score_memory
    calibration = score_memory.calibration_block()
    if calibration:
        log.info("Calibrage : corrections de Franck injectées dans le prompt.")
    excluded_re = load_excluded_events_filter()
    for event in pending:
        ev = dict(event)
        # Pré-filtre GRATUIT ter : règle éditoriale explicite (config/
        # excluded_event_keywords.txt) — ex. « jamais le 27e/23e BCA ». Rejet avant
        # tout appel LLM, quel que soit le score qu'il aurait donné.
        if is_excluded_event(ev.get("title", ""), ev.get("description", ""), excluded_re):
            conn.execute("UPDATE events_raw SET statut='rejected', llm_score=0, "
                         "llm_justification='Exclu par règle éditoriale (config/excluded_event_keywords.txt).' "
                         "WHERE id=?", (ev["id"],))
            log.info("[%d] exclu (règle éditoriale) → rejeté | %s", ev["id"], ev.get("title", "")[:50])
            continue
        # Pré-filtre GRATUIT quater : PÉRIMÈTRE GÉOGRAPHIQUE sur le champ `ville`
        # (charte §2). Le « Comté de Nice » est l'arrondissement de NICE : une fiche
        # de l'arrondissement de GRASSE (Cannes, Antibes, Grasse, Cagnes-sur-Mer,
        # Vence…) n'a pas sa place au catalogue. Décision déterministe et exacte,
        # avant tout appel LLM. Si `ville` est vide (venues.py n'a rien trouvé),
        # on ne tranche pas ici : l'ÉTAPE 0 du prompt reprend la main.
        #
        # POURQUOI ICI et pas à la collecte : `ville` est vide au scraping (cron 8h00,
        # scripts/scraper_events.py n'insère pas cette colonne) et n'est renseignée
        # qu'à 8h50 par scripts/venues.py. Un filtre posé dans le scraper ne verrait
        # que des chaînes vides et ne rejetterait jamais rien. L'évaluateur (9h00) est
        # le premier point du pipeline où la donnée existe, et c'est l'entonnoir
        # unique : toute fiche y passe en 'pending' avant catalogue ou home.
        # Le rattrapage des fiches dont la `ville` arrive APRÈS 9h (venues.py plafonné,
        # page injoignable, autocomplete.py lancé du back-office) est dans
        # scripts/purge_out_of_zone.py, qui repasse sur une file plus large.
        if ville_hors_perimetre(ev.get("ville", "")):
            conn.execute(
                "UPDATE events_raw SET statut='rejected', llm_score=0, "
                "llm_justification=? WHERE id=?",
                ("Hors périmètre — %s est dans l'arrondissement de Grasse ; le Comté "
                 "de Nice couvre l'arrondissement de Nice (charte §2)."
                 % (ev.get("ville") or "").strip(), ev["id"]))
            log.info("[%d] arrondissement de Grasse (%s) → rejeté | %s", ev["id"],
                     (ev.get("ville") or "").strip(), ev.get("title", "")[:50])
            continue
        # Pré-filtre GRATUIT : un événement déjà passé est rejeté sans appeler le
        # LLM (on ne paie pas, et on ne publie que du à-venir / en cours).
        if is_past_event(ev, today):
            conn.execute("UPDATE events_raw SET statut='rejected', llm_score=0, "
                         "llm_justification='Événement passé (déjà terminé).' WHERE id=?",
                         (ev["id"],))
            log.info("[%d] passé → rejeté | %s", ev["id"], ev.get("title", "")[:50])
            continue
        # Pré-filtre GRATUIT bis : un ARTICLE de presse (logistique « où se garer »,
        # compte-rendu « le conseil s'est réuni », portrait « caravane publicitaire »)
        # n'est pas une sortie. Le LLM s'accroche au gros mot-clé et le note haut → on
        # coupe avant l'appel, haute précision (aucun vrai événement attrapé).
        news = non_event_reason(ev.get("title", ""), ev.get("description", ""))
        if news:
            conn.execute("UPDATE events_raw SET statut='rejected', llm_score=0, "
                         "llm_justification=? WHERE id=?",
                         ("Article de presse, pas un événement : %s." % news, ev["id"]))
            log.info("[%d] non-événement (%s) → rejeté | %s", ev["id"], news,
                     ev.get("title", "")[:50])
            continue
        result = evaluate_event(ev, client, model, calibration)
        if result is API_ERROR:
            # Panne API : on ne touche pas au statut (reste 'pending', réévalué
            # au prochain run). On stoppe le batch : l'API est probablement KO.
            log.warning("[%d] erreur API — laissé en pending, arrêt du batch", ev["id"])
            break
        if result is None:
            conn.execute(
                "UPDATE events_raw SET statut='rejected', llm_score=0 WHERE id=?",
                (ev["id"],)
            )
            continue
        est = result.get("est_evenement", True)
        hors = bool(result.get("hors_perimetre", False))
        # PUBLIC VISÉ (charte §3) : un congrès/colloque/salon B2B s'adresse à des
        # congressistes, pas à nos lecteurs — rejet même si l'inscription est ouverte.
        # Défaut PERMISSIF : champ absent ou valeur inattendue → grand public. Un
        # modèle qui oublierait la clé ne doit pas vider « Conférences & Rencontres ».
        pro = (result.get("public_vise") or "").strip().lower() == "professionnel"
        score = int(result.get("score", 0) or 0)
        # ÉTAPE 0 : hors des 4 territoires → rejet (2e garde après le filtre
        # déterministe du scraper : rattrape le lieu cité en passant que le
        # match de mots-clés laisse passer). Sinon, gate est_evenement + importance.
        # Un vrai événement n'est JAMAIS rejeté d'office : score >= RETAIN_MIN_SCORE
        # → à valider (mise en avant home) ; sinon → catalogue (site dédié).
        if hors or not est or pro:
            new_statut, score = "rejected", 0
        elif score >= RETAIN_MIN_SCORE:
            new_statut = "evaluated"
        else:
            new_statut = "published_sub"
        # Correction du territoire : l'évaluateur peut rectifier une source large
        # mal étiquetée (ex. Le Dauphiné « Savoie » pour un événement d'Annecy).
        terr = (result.get("territoire") or "").strip()
        new_terr = terr if terr in TERRITOIRES and not hors else ev.get("territoire")
        justif = result.get("justification", "")
        if hors:
            justif = "Hors périmètre — " + justif if justif else "Hors périmètre."
        elif pro:
            prefixe = ("Public professionnel (congrès/colloque/salon B2B), pas le grand "
                       "public — charte §3")
            justif = f"{prefixe} — {justif}" if justif else prefixe + "."
        detail = json.dumps(result.get("criteres") or {}, ensure_ascii=False)
        conn.execute("""
        UPDATE events_raw SET
            llm_score=?, llm_categorie=?, llm_justification=?, llm_score_detail=?,
            llm_model=?, llm_evaluated_at=datetime('now'), statut=?, territoire=?
        WHERE id=?
        """, (
            score,
            result.get("categorie", ""),
            justif,
            detail,
            model,
            new_statut,
            new_terr,
            ev["id"],
        ))
        if new_terr != ev.get("territoire"):
            log.info("[%d] territoire corrigé : %s → %s", ev["id"],
                     ev.get("territoire"), new_terr)
        log.info("[%d] event=%s hors=%s pro=%s score=%d statut=%s cat=%s | %s", ev["id"],
                 est, hors, pro, score, new_statut, result.get("categorie", "")[:20],
                 ev.get("title", "")[:50])

    conn.commit()
    conn.close()
    log.info("=== Évaluation terminée ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
