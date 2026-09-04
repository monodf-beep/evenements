#!/usr/bin/env python3
"""Complète les VISUELS des événements d'une période (bouton « Compléter les visuels »).

Quand le flux RSS ne fournit pas d'image, on va chercher une photo — chaîne en 4
étages, du meilleur au repli (aucune carte n'est jamais vide) :

    1. image du flux RSS ......................... (déjà en base, on ne touche pas)
    2. og:image de la page officielle ............ déterministe (institutionnel)
    3. photo licenciable Wikimedia Commons ....... le LLM rédige la requête, le
       code cherche/filtre (JPEG/PNG, taille, pas de logo) + crédit ; JAMAIS une
       image de presse (charte : source licenciable uniquement)
    4. bannière de marque du territoire .......... repli garanti (Observatoire)

Léger et idempotent : ne traite QUE les événements retenus de la période SANS
image. Rejouable sans surcoût (une fois l'image posée, l'événement est ignoré).

LLM ? OUI pour la seule requête visuelle (jugement : « quoi photographier »).
La recherche, le filtrage et le repli restent déterministes. Voir docs/LLM_OU_CODE.md.

Usage :
    python scripts/visuals.py                       # 7 prochains jours
    python scripts/visuals.py --from 2026-07-01 --to 2026-07-31
    python scripts/visuals.py 12 15 18              # ces id précis
"""
from __future__ import annotations
import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils.images import (commons_search, europeana_search, fetch_og_image,
                          fetch_content_image, remote_dims, looks_like_banner_shape,
                          MIN_DIM)
from utils.sources import (is_blocked_image, is_logo_image, load_blocked_image_domains,
                           load_territory_category_images, pick_banner_image)
from utils import image_verify
from utils.api_limite import PlafondAPI, est_plafond
from scripts.scraper_events import init_db

log = get_logger("visuals")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
# Modèle de la requête visuelle : tâche simple → économique par défaut.
MODEL = os.getenv("ANTHROPIC_MODEL_VISUALS") or os.getenv("ANTHROPIC_MODEL_EXTRACT", "claude-haiku-4-5-20251001")
# Plafond d'événements traités par lancement (garde-fou coût/temps).
CAP = int(os.getenv("VISUALS_CAP", "80"))
STATUTS = ("evaluated", "published_cs", "published_sub")


def _is_radar(ev: dict) -> bool:
    return ev.get("source_type") == "radar" or "(radar)" in (ev.get("source_name") or "")


def _final_text(message) -> str:
    return "".join(getattr(b, "text", "") for b in message.content
                   if getattr(b, "type", None) == "text").strip()


def visual_query(ev: dict, client, model: str) -> str:
    """Le LLM propose une requête de photo Wikimedia Commons. '' si rien de visuel.

    RÈGLE CARDINALE (incident « Yerai Cortés » de juillet 2026) : la requête doit
    porter sur le SUJET de l'événement (artiste, groupe, œuvre, conférencier), pas
    sur le nom du LIEU. Une recherche « Fondation Maeght » ramène l'architecture et
    l'HISTOIRE du lieu — dont un portrait de son architecte (Josep Lluís Sert) —,
    jamais le concert de flamenco qui s'y tient. Le lieu seul n'est un bon sujet
    QUE s'il est lui-même le sujet (visite d'un monument) et jamais au prix d'un
    portrait d'une personne associée au lieu."""
    from utils.image_verify import season_fr
    season = season_fr(ev.get("date_event_start", ""))
    prompt = (
        "Tu aides à illustrer un événement culturel par une PHOTO réutilisable "
        "(Wikimedia Commons). Donne une requête de recherche COURTE (2 à 5 mots), "
        "visant une vraie photographie du SUJET de l'événement.\n"
        "PRIORITÉ ABSOLUE — cible le SUJET, pas le lieu :\n"
        "  • Si l'événement porte sur une PERSONNE, un GROUPE, une ŒUVRE ou un "
        "ENSEMBLE nommés (concert d'un artiste, exposition d'un peintre, conférence "
        "d'un intervenant, pièce, film…), la requête doit viser CE sujet précis "
        "— ex. « Yerai Cortés » pour un concert de Yerai Cortés, PAS « Fondation "
        "Maeght » (le lieu). Le nom de l'artiste/de l'œuvre est le meilleur sujet.\n"
        "  • Le nom du LIEU seul (« Fondation Maeght », « Auditorium de Lyon ») ramène "
        "l'architecture, l'histoire du site et les personnalités qui lui sont "
        "associées (son architecte, son fondateur) — HORS-SUJET pour l'événement. Ne "
        "l'utilise comme requête QUE si le lieu est LUI-MÊME le sujet (visite/"
        "découverte d'un monument, patrimoine) et qu'aucune personne/œuvre nommée "
        "n'est identifiable ; vise alors le BÂTIMENT (« château de Montrottier »), "
        "jamais une personne liée au lieu.\n"
        "Si aucun sujet nommé n'est identifiable (marché, fête populaire, animation), "
        "cible le lieu PRÉCIS + le TYPE d'activité — une requête comme « Aoste Vallée "
        "d'Aoste » est trop vague si l'événement se passe au Borgo di Sant'Orso : "
        "cherche « Sant'Orso Aoste marché artisanat », qui cible mieux qu'un simple "
        "nom de lieu (lequel ramène n'importe quelle photo touristique générique).\n"
        "Si la SAISON est connue et pertinente pour une photo extérieure (pas un "
        "intérieur/monument), ajoute-la à la requête (« marché de Noël hiver Aoste » "
        "plutôt qu'une photo d'été du même lieu).\n"
        "Si l'événement n'a LUI-MÊME aucun rapport avec la nature/montagne, ÉVITE une "
        "requête qui ramènerait un paysage naturel générique (lac, sommet, vallée) sous "
        "prétexte que le territoire est alpin.\n"
        "Évite les affiches, les logos, le texte. N'inclus JAMAIS le nom d'une personne "
        "qui n'est PAS le sujet de l'événement (architecte/fondateur du lieu…).\n\n"
        f"Titre : {ev.get('title','')}\n"
        f"Lieu précis : {ev.get('lieu','')}\n"
        f"Ville : {ev.get('ville','')}\n"
        f"Territoire : {ev.get('territoire','')}\n"
        f"Dates : {ev.get('date_event_start','')} → {ev.get('date_event_end','')}"
        + (f" (saison : {season})" if season else "") + "\n"
        f"Catégorie : {ev.get('llm_categorie','')}\n"
        f"Description : {(ev.get('description') or '')[:400]}\n\n"
        'Réponds en JSON strict : {"query": "…", "ok": true} '
        '(ok=false si aucune photo générique ne conviendrait).'
    )
    try:
        msg = client.messages.create(
            model=model, max_tokens=200,
            messages=[{"role": "user", "content": prompt}])
    except Exception as exc:  # jamais bloquant : on retombera sur la bannière
        if est_plafond(exc):  # …sauf plafond : la bannière serait DÉFINITIVE, cf. main()
            raise PlafondAPI(str(exc)) from exc
        log.warning("[%s] requête visuelle LLM échouée : %s", ev.get("id"), exc)
        return ""
    raw = _final_text(msg)
    # MESURÉ (2026-08-11) : ce poste n'était pas compté du tout. Franck, 2026-08-10 :
    # « je consomme beaucoup trop de token API pour le résultat médiocre » — on ne peut
    # ni le lui confirmer ni le lui infirmer tant que la moitié des appels sont
    # invisibles. Voir scripts/audit_couts.py pour la répartition par poste.
    from utils import usage
    usage.record_message(model, msg, label="requete_visuelle")
    m = raw[raw.find("{"):raw.rfind("}") + 1] if "{" in raw else ""
    try:
        data = json.loads(m or raw)
    except (ValueError, TypeError):
        return ""
    return (data.get("query") or "").strip() if data.get("ok") else ""


def _acceptable(url: str, blocked: set[str], patterns: list) -> bool:
    """RÈGLES déterministes : ni domaine proscrit, ni logo, ni motif parasite connu
    (bandeau/pub/slider, voir config/blocked_image_patterns.txt)."""
    return bool(url) and not is_blocked_image(url, blocked) \
        and not is_logo_image(url) and not image_verify.looks_parasitic(url, patterns)


def _verified(url: str, ev: dict, verify_client, verify_model: str,
             subject: str = "") -> tuple[bool, float, float]:
    """AGENT vision (optionnel) : si un client est fourni, l'image doit correspondre à
    l'événement — et on récupère au passage le POINT FOCAL suggéré (visage / texte en
    bas à protéger d'un recadrage 4:3, cf. utils.image_verify). Sans client, on fait
    confiance aux règles déterministes (focal centré par défaut)."""
    if verify_client is None:
        return True, 0.5, 0.5
    from utils.images import _PAGE_UA, _MAX_CHECK_BYTES  # réutilise le téléchargement borné
    import requests
    try:
        r = requests.get(url, headers=_PAGE_UA, timeout=15, stream=True)
        if r.status_code != 200:
            return True, 0.5, 0.5  # injoignable pour la vérif : ne bloque pas (le push refera sa chaîne)
        mime = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        buf = b""
        for chunk in r.iter_content(65536):
            buf += chunk
            if len(buf) > _MAX_CHECK_BYTES:
                break
    except requests.RequestException:
        return True, 0.5, 0.5
    return image_verify.verify_relevance(buf, mime, ev, verify_client, verify_model, subject)


def resolve_image(ev: dict, client, blocked: set[str],
                  verify_client=None,
                  verify_model: str = "claude-haiku-4-5",
                  cat_banners: dict | None = None,
                  *, keep_existing: bool = True) -> tuple[str, str, str, float, float]:
    """Renvoie (url, credit, source, focal_x, focal_y) selon la chaîne 4 étages. url=''
    seulement si aucune bannière n'est configurée pour le territoire. focal_x/y ∈ [0,1] :
    point focal suggéré par l'agent vision (visage / texte en bas à protéger d'un
    recadrage 4:3 « cover » — sans effet sur une affiche portrait, jamais recadrée).
    (0.5, 0.5) si pas d'agent vision ou rien de particulier à protéger.

    RÈGLES (toujours) : chaque candidat passe _acceptable (domaine/logo/parasite).
    AGENT (si verify_client) : og / page / Commons sont vérifiés par vision — une image
    qui ne correspond pas à l'événement est refusée et on descend d'un étage.

    keep_existing (défaut True) : NE JAMAIS DÉGRADER une image déjà valide. Si
    l'événement porte DÉJÀ une vraie photo (image_source ∈ {og, page}) qui passe les
    défenses, on la conserve telle quelle — on ne la remplace pas par un résultat de
    moindre confiance (Commons/bannière). Passe keep_existing=False seulement quand le
    but EST de remplacer l'image actuelle (mode --lowres : troquer une petite photo
    valide contre une plus grande du même sujet)."""
    patterns = image_verify.load_blocked_patterns()
    # ── Fix 1 : ne JAMAIS dégrader une image DÉJÀ valide ─────────────────────────
    # Si l'événement a déjà une vraie photo (og:image / photo de page) qui passe les
    # DEUX défenses (règles déterministes + agent vision quand il est disponible), on
    # la CONSERVE : pas question de la troquer contre un résultat Commons de moindre
    # confiance (incident « Yerai Cortés » : la bonne og de la Fondation Maeght écrasée
    # par une photo hors-sujet trouvée par recherche Commons sur le nom du lieu). Les
    # modes qui distrust l'image existante la vident en amont (--bad-url/--unverified :
    # ev['url_image']='') ou passent keep_existing=False (--lowres).
    if keep_existing:
        existing = (ev.get("url_image") or "").strip()
        existing_src = (ev.get("image_source") or "").strip()
        if existing and existing_src in ("og", "page") and _acceptable(existing, blocked, patterns):
            ok, fx, fy = _verified(existing, ev, verify_client, verify_model)
            if ok:
                return existing, ev.get("image_credit") or "", existing_src, fx, fy
    # Repli 'page' tenu en réserve : accepté seulement si assez grand pour le rendu
    # social, OU si Commons n'est pas disponible pour faire mieux (voir plus bas) —
    # jamais rejeté d'office (la leçon DON D'ORGANES reste valable : une petite photo
    # PERTINENTE vaut mieux qu'une grande PARASITE). Ici on ne fait que lui laisser une
    # chance d'être doublée par une photo Commons plus grande du MÊME sujet, pas
    # "aller chercher plus grand sur la page" (ce qui causait l'incident).
    content_fallback = None  # (url, credit, source, fx, fy) si trouvé mais petit
    # Étage 2 — og:image de la page officielle (jamais pour un radar : image de presse).
    if not _is_radar(ev):
        og = fetch_og_image(ev.get("url_source", ""))
        # Forme (déterministe, TOUJOURS active — pas besoin de l'agent vision) : un
        # og:image très plat ou très étroit est un bandeau d'habillage (souvent la même
        # image sert de bannière de partage ET de header visuel du site), pas une photo.
        if _acceptable(og, blocked, patterns) and not looks_like_banner_shape(*remote_dims(og)):
            ok, fx, fy = _verified(og, ev, verify_client, verify_model)
            if ok:
                return og, "", "og", fx, fy
        # Étage 2b — repli : 1re vraie photo de CONTENU (pages sans og:image, ex.
        # offices de tourisme). L'info est sur la page, on la prend au lieu d'abandonner.
        content = fetch_content_image(ev.get("url_source", ""))
        if _acceptable(content, blocked, patterns):
            content_w, content_h = remote_dims(content)
            if not looks_like_banner_shape(content_w, content_h):
                ok, fx, fy = _verified(content, ev, verify_client, verify_model)
                if ok:
                    # Assez grande, ou pas de recherche Commons possible → on la prend
                    # tout de suite (comportement historique, inchangé).
                    if client is None or min(content_w, content_h) >= MIN_DIM:
                        return content, "", "page", fx, fy
                    # Trop petite pour le rendu social (floue une fois étirée à 1080px+,
                    # déclenche le fond abstrait) : on la garde en réserve et on tente
                    # Commons — qui cherche PRÉCISÉMENT une photo du même sujet, donc pas
                    # le risque « grande image sans rapport » de l'incident DON D'ORGANES.
                    content_fallback = (content, "", "page", fx, fy)
    # Étage 2c — AGENT WEB : la VRAIE image D'ABORD (affiche officielle, photo de la page
    # de l'événement / du lieu / de l'artiste), AVANT de se rabattre sur une photo Commons
    # GÉNÉRIQUE (ex. un portrait quelconque de la personnalité au lieu de l'affiche de CET
    # événement — cf. « Dialoghi con George Clooney »). L'agent privilégie déjà l'officiel
    # et évite les photos d'agence/presse (posture de droits, charte §8), et un second agent
    # vision vérifie la pertinence. Gaté par env (coût : 1 recherche web + vision / event) —
    # VISUALS_WEB_IMAGE=0 pour désactiver (ex. gros rattrapage à moindre coût).
    if client is not None and os.getenv("VISUALS_WEB_IMAGE", "1") == "1":
        try:
            from scripts.images_web import find_verified_image
            w_url, w_credit, wfx, wfy = find_verified_image(ev, client, blocked)
        except PlafondAPI:
            raise
        except Exception as exc:  # jamais bloquant : on continue vers Commons
            if est_plafond(exc):
                raise PlafondAPI(str(exc)) from exc
            log.warning("[%s] agent image web indisponible : %s", ev.get("id"), exc)
            w_url = ""
        if w_url:
            log.info("[%s] Web (officiel/affiche) → %s", ev["id"], w_url[:70])
            return w_url, w_credit, "web", wfx, wfy
    # Étage 3 — photo licenciable Wikimedia Commons (LLM = requête, code = fetch).
    if client is not None:
        q = visual_query(ev, client, MODEL)
        if q:
            url, credit, commons_title = commons_search(q)
            if _acceptable(url, blocked, patterns):
                # Le nom du fichier Commons (ex. « Marché Saint-Ours Aoste.jpg ») est un
                # indice textuel de plus pour l'agent : utile quand l'image seule est
                # ambiguë mais que le nom confirme (ou dément) le sujet exact.
                subject = f"{q} (fichier Commons : « {commons_title} »)" if commons_title else q
                ok, fx, fy = _verified(url, ev, verify_client, verify_model, subject)
                if ok:
                    log.info("[%s] Commons « %s » → %s", ev["id"], q, url[:70])
                    return url, credit, "commons", fx, fy
            # Étage 3b — Europeana (musées/bibliothèques du territoire), même requête.
            # Inactif sans EUROPEANA_API_KEY → europeana_search renvoie '' (no-op).
            eu_url, eu_credit, eu_title = europeana_search(q)
            if _acceptable(eu_url, blocked, patterns):
                eu_subject = f"{q} (Europeana : « {eu_title} »)" if eu_title else q
                ok, fx, fy = _verified(eu_url, ev, verify_client, verify_model, eu_subject)
                if ok:
                    log.info("[%s] Europeana « %s » → %s", ev["id"], q, eu_url[:70])
                    return eu_url, eu_credit, "europeana", fx, fy
    # Commons n'a rien donné de mieux : on ressort la photo de page, petite mais
    # pertinente — toujours préférable à la bannière générique.
    if content_fallback:
        return content_fallback
    # Étage 4 — bannière territoire × catégorie (repli garanti, jamais parasite).
    banner = pick_banner_image(ev.get("territoire", ""), ev.get("llm_categorie", ""),
                               str(ev["id"]), cat_banners or {})
    if banner:
        return banner, "", "banner", 0.5, 0.5
    return "", "", "", 0.5, 0.5


def select_events(conn: sqlite3.Connection, ids, dfrom, dto) -> list[dict]:
    # ⚠️ UNE BANNIÈRE N'EST PAS UNE IMAGE TROUVÉE (2026-08-11). La sélection exigeait
    # `url_image = ''`, donc une fiche à qui la chaîne avait posé une BANNIÈRE de
    # territoire — le dernier étage, générique, choisi faute de mieux — n'était plus
    # jamais reprise : le champ n'était plus vide. C'est le cul-de-sac de la règle 3, et
    # il s'est produit en grand le soir même : un run --sans-llm a « complété » 57 fiches
    # dont QUARANTE avec une bannière. Sans ce correctif, ces quarante gardaient une
    # image générique pour toujours, alors que leur page officielle porte peut-être une
    # affiche — simplement inatteignable ce soir-là, plafond API oblige.
    #
    # Les vraies photos (image_source ∈ {og, page, commons, europeana}) ne sont PAS
    # reprises : resolve_image les conserve de toute façon (keep_existing), et les
    # reprendre gonflerait chaque run pour rien.
    #
    # L'ORDRE protège le cap : les fiches SANS aucune image passent d'abord, les
    # bannières ensuite. Une fiche sans image n'a rien à montrer ; une fiche à bannière
    # montre déjà quelque chose, même d'imparfait.
    base = (f"SELECT * FROM events_raw WHERE statut IN ({','.join('?' * len(STATUTS))}) "
            "AND duplicate_of IS NULL "
            "AND (COALESCE(url_image,'') = '' OR COALESCE(image_source,'') = 'banner') ")
    params = list(STATUTS)
    if ids:
        base += f"AND id IN ({','.join('?' * len(ids))}) "
        params += list(ids)
    elif dfrom and dto:
        base += "AND COALESCE(date_event_start,'') <= ? AND COALESCE(date_event_end,'') >= ? "
        params += [dto, dfrom]
    base += ("ORDER BY CASE WHEN COALESCE(url_image,'') = '' THEN 0 ELSE 1 END, "
             "llm_score DESC LIMIT ?")
    params.append(CAP)
    return [dict(r) for r in conn.execute(base, params).fetchall()]


def main(argv=None) -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="Complète les visuels d'une période.")
    parser.add_argument("ids", nargs="*", type=int)
    parser.add_argument("--from", dest="dfrom", default="")
    parser.add_argument("--to", dest="dto", default="")
    parser.add_argument("--verify", action="store_true",
                        help="Active l'AGENT vision (vérifie que chaque image correspond à "
                             "l'événement). Par défaut : règles déterministes seulement (gratuit) "
                             "— la vérification vision se fait surtout au moment de publier.")
    parser.add_argument("--sans-llm", action="store_true",
                        help="N'appelle AUCUN modèle : og:image, photo de page et "
                             "bannière seulement. À utiliser quand le plafond API est "
                             "atteint — une bonne part des images se trouve sans LLM.")
    args = parser.parse_args(argv)

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    conn.row_factory = sqlite3.Row
    rows = select_events(conn, args.ids, args.dfrom, args.dto)
    scope = (f"ids {args.ids}" if args.ids
             else f"{args.dfrom or '…'} → {args.dto or '…'}")
    log.info("%d événement(s) sans image (%s)", len(rows), scope)
    if not rows:
        log.info("Rien à compléter — tous les événements retenus ont déjà un visuel.")
        return 0

    # Le LLM (étage 3) est optionnel : sans clé, on fait og:image + bannière.
    client = None
    api_key = "" if args.sans_llm else os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key, timeout=60.0)
    elif args.sans_llm:
        # --sans-llm EXISTE parce que « pas de clé » et « clé plafonnée » ne se
        # ressemblent pas : avec une clé plafonnée, la chaîne tente l'étage 3, prend une
        # erreur et le garde-fou PlafondAPI interrompt tout le lot — donc og:image et la
        # bannière, qui ne coûtent RIEN, ne sont jamais atteints pour les fiches
        # suivantes. Ce drapeau saute directement aux étages gratuits.
        log.info("--sans-llm : og:image, photo de page et bannière seulement, "
                 "aucun appel modèle.")
    else:
        log.warning("ANTHROPIC_API_KEY absente : pas de recherche Commons, og:image + bannière seulement.")

    cat_banners = load_territory_category_images()
    blocked = load_blocked_image_domains()
    verify_client = client if args.verify else None
    verify_model = os.getenv("ANTHROPIC_MODEL_VISION") or "claude-haiku-4-5"
    counts = {"og": 0, "page": 0, "commons": 0, "europeana": 0, "banner": 0, "none": 0}
    plafonne = False
    for ev in rows:
        try:
            url, credit, source, fx, fy = resolve_image(
                ev, client, blocked, verify_client=verify_client,
                verify_model=verify_model, cat_banners=cat_banners)
        except PlafondAPI as exc:
            # ON N'ÉCRIT RIEN — ni pour cette fiche, ni pour les suivantes. Un plafond
            # ferait retomber toute la chaîne sur la bannière territoire, et
            # select_events ne reprend jamais une fiche qui a déjà une image : la
            # bannière posée un jour de plafond ne serait JAMAIS remplacée. Les fiches
            # non tentées n'ont rien fait, leur tour reviendra (utils/api_limite.py).
            log.error("PLAFOND API atteint — lot arrêté à la fiche %s. %d fiche(s) "
                      "restent SANS VISUEL (dont celle-ci) et RIEN n'a été écrit pour "
                      "elles : elles se représenteront au prochain run. %s",
                      ev.get("id"), len(rows) - sum(counts.values()), exc)
            plafonne = True
            break
        if not url:
            counts["none"] += 1
            log.warning("[%s] aucun visuel (pas de bannière pour %s)", ev["id"], ev.get("territoire"))
            continue
        # card_focal_x/y : seulement si jamais réglé (NULL) — ne JAMAIS écraser un
        # cadrage choisi à la main au back-office (éditeur de point focal).
        conn.execute(
            "UPDATE events_raw SET url_image=?, image_credit=?, image_source=?, "
            "card_focal_x=COALESCE(card_focal_x, ?), card_focal_y=COALESCE(card_focal_y, ?) "
            "WHERE id=?",
            (url, credit, source, fx, fy, ev["id"]))
        conn.commit()
        counts[source] += 1
    log.info("Visuels posés — og:image=%d · page=%d · Commons=%d · Europeana=%d · bannière=%d · échec=%d",
             counts["og"], counts["page"], counts["commons"], counts["europeana"],
             counts["banner"], counts["none"])
    conn.close()
    if plafonne:
        # Code retour NON NUL : c'est ce que lit le chien de garde. Un plafond qui
        # ressort « 0 » se confond avec une nuit sans travail à faire.
        log.error("Le lot s'est arrêté sur un plafond API. Relever le plafond ou "
                  "recharger le crédit (console Anthropic), puis relancer.")
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
