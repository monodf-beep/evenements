#!/usr/bin/env python3
"""RÈGLES + AGENT de vérification des images d'événements — un seul endroit.

Deux défenses complémentaires contre les visuels hors-sujet (bandeaux, pubs,
sliders, images sans rapport) :

  1. RÈGLES déterministes (gratuites, toujours actives) — looks_parasitic() :
     rejette une URL qui correspond à un motif d'habillage connu
     (config/blocked_image_patterns.txt). Rapide, extensible sans code.

  2. AGENT vision (payant, ciblé) — verify_relevance() : un LLM regarde l'image et
     dit si elle correspond VRAIMENT à l'événement. C'est le vrai garde-fou de
     pertinence — le seul capable de dire « ce ruban vert est une campagne don
     d'organes, pas une reconstitution historique ».

Utilisé par la chaîne de résolution (scripts.visuals.resolve_image) et par l'agent
web de dernier recours (scripts.images_web) — plus de logique de vérification
dupliquée.
"""
from __future__ import annotations

import base64
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_PATTERNS_FILE = ROOT / "config" / "blocked_image_patterns.txt"
_OK_MIME = ("image/jpeg", "image/png", "image/webp", "image/gif")

_patterns_cache: "list[str] | None" = None


def load_blocked_patterns() -> list[str]:
    """Motifs d'URL parasites (config/blocked_image_patterns.txt), en minuscules."""
    global _patterns_cache
    if _patterns_cache is None:
        pats: list[str] = []
        try:
            for line in _PATTERNS_FILE.read_text(encoding="utf-8").splitlines():
                s = line.strip()
                if s and not s.startswith("#"):
                    pats.append(s.lower())
        except OSError:
            pass
        _patterns_cache = pats
    return _patterns_cache


def looks_parasitic(url: str, patterns: "list[str] | None" = None) -> bool:
    """Vrai si l'URL correspond à un motif d'habillage/parasite connu (déterministe)."""
    if not url:
        return False
    low = url.lower()
    for p in (patterns if patterns is not None else load_blocked_patterns()):
        if p in low:
            return True
    return False


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"(?s)<[^>]+>", " ", text or "")).strip()


_SEASON_FR = {12: "hiver", 1: "hiver", 2: "hiver",
              3: "printemps", 4: "printemps", 5: "printemps",
              6: "été", 7: "été", 8: "été",
              9: "automne", 10: "automne", 11: "automne"}


def season_fr(date_str: str) -> str:
    """Saison FR déduite d'une date AAAA-MM-JJ — repère pour juger une photo
    EXTÉRIEURE (inutile pour un intérieur/monument, mais évite une prairie verte en
    pleine photo d'un événement de janvier, ou de la neige en pleine photo d'un
    événement de juillet). '' si date absente/illisible."""
    if not date_str or len(date_str) < 7:
        return ""
    try:
        return _SEASON_FR.get(int(date_str[5:7]), "")
    except ValueError:
        return ""


def verify_relevance(img_bytes: bytes, mime: str, event: dict, client, model: str,
                     subject: str = "") -> tuple[bool, float, float]:
    """AGENT VISION : l'image correspond-elle vraiment à l'événement ? Et si elle est
    RECADRÉE en 4:3 « cover » (photo paysage), quel point focal (x,y ∈ [0,1]) évite de
    couper un visage ou une zone de texte informatif en bas de l'image ? (Sans effet sur
    une affiche portrait : celle-ci part en letterbox, jamais recadrée — voir
    utils/card_image.py.)

    Renvoie (ok, focal_x, focal_y). Refuse explicitement (ok=False) les bandeaux/pubs/
    logos/captures/affiches-tout-texte et les images sans rapport. Tolérant en cas
    d'échec technique (renvoie (True, 0.5, 0.5)) SEULEMENT si l'appel plante — l'appelant
    décide alors ; ici on préfère ne pas bloquer sur une panne réseau. Un refus DE CONTENU
    (l'image ne colle pas) renvoie bien ok=False."""
    if not img_bytes or mime not in _OK_MIME or client is None:
        return True, 0.5, 0.5  # rien à vérifier / pas de client → laisse passer, cadrage centré
    b64 = base64.standard_b64encode(img_bytes).decode("ascii")
    season = season_fr(event.get("date_event_start", ""))
    dates = event.get("date_event_start", "")
    if event.get("date_event_end") and event["date_event_end"] != dates:
        dates += f" → {event['date_event_end']}"
    prompt = (
        "Voici une image candidate pour illustrer un ÉVÉNEMENT CULTUREL sur un média "
        "public. Dis si elle est PERTINENTE et publiable pour CET événement précis.\n"
        f"Titre : {_clean(event.get('article_title') or event.get('title'))}\n"
        f"Lieu précis : {_clean(event.get('lieu'))}\n"
        f"Ville : {_clean(event.get('ville'))}\n"
        f"Dates : {dates}" + (f" (saison : {season})" if season else "") + "\n"
        f"Catégorie : {event.get('llm_categorie') or ''}\n"
        + (f"Sujet attendu : {subject}\n" if subject else "")
        + "\nREFUSE (ok=false) si l'image est : un bandeau ou une bannière de campagne "
        "(don d'organes, sécurité routière, climat…), une publicité, un logo, une "
        "capture d'écran, une affiche pleine de texte illisible, un visuel d'habillage "
        "de site (slider, en-tête), une image de très mauvaise qualité, ou tout "
        "simplement SANS RAPPORT avec l'événement.\n"
        "REFUSE AUSSI (même si le sujet général semble correct) :\n"
        "  • une SAISON incompatible et visible (verdure/soleil éclatant pour un "
        "événement d'hiver, neige pour un événement d'été…) — sauf photo d'intérieur "
        "ou de monument où la saison ne se voit pas ;\n"
        "  • un PAYSAGE NATUREL générique (montagne, lac, sommet, vallée) si "
        "l'événement se déroule dans un cadre urbain/bâti précis (centre historique, "
        "place, salle, musée…) et n'a lui-même aucun rapport avec la nature — même si "
        "le territoire environnant est montagneux, ce n'est pas le sujet de CET "
        "événement.\n"
        "ACCEPTE (ok=true) une vraie photo du lieu précis, de l'artiste, du thème, ou "
        "une affiche propre et lisible de l'événement.\n\n"
        "POINT FOCAL (utile seulement si l'image est au format PAYSAGE et sera "
        "RECADRÉE en 4:3 — une affiche PORTRAIT n'est jamais recadrée, ignore cette "
        "partie pour elle) : identifie l'ÉLÉMENT LE PLUS IMPORTANT de l'image — un "
        "visage, un TITRE ou logo incrusté dans le visuel (ex. le nom de "
        "l'événement composé graphiquement sur une affiche/illustration), ou une "
        "zone de texte informatif (horaires, prix, adresse) — OÙ QU'IL SE TROUVE "
        "dans l'image (haut, bas, gauche, droite, pas seulement en bas). Donne "
        "focal_x, focal_y ∈ [0,1] pour que le recadrage 4:3 NE LE COUPE JAMAIS.\n"
        "  • focal_x, focal_y = position de CET élément dans l'image entière "
        "(0=bord gauche/haut, 1=bord droit/bas, 0.5=centré). Exemple : un titre "
        "composé sur le tiers GAUCHE de l'image → focal_x proche de 0 (le "
        "recadrage doit garder la gauche, pas juste centrer).\n"
        "  • Si rien de particulier à protéger (photo sans texte ni visage "
        "identifiable) : focal_x=0.5, focal_y=0.5.\n"
        'Réponds en JSON STRICT : {"ok": true|false, "raison": "…", '
        '"focal_x": 0.5, "focal_y": 0.5}'
    )
    try:
        msg = client.messages.create(
            model=model, max_tokens=200,
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": mime, "data": b64}},
                {"type": "text", "text": prompt}]}])
    except Exception:
        return True, 0.5, 0.5  # panne technique : ne bloque pas (les règles déterministes ont déjà filtré)
    try:
        from utils import usage
        usage.record_message(model, msg, label="image_verify")
    except Exception:
        pass
    raw = "".join(getattr(b, "text", "") for b in msg.content
                  if getattr(b, "type", None) == "text").strip()
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return True, 0.5, 0.5
    try:
        data = json.loads(m.group())
    except (ValueError, TypeError):
        return True, 0.5, 0.5

    def _c(v, d=0.5):
        try:
            return min(max(float(v), 0.0), 1.0)
        except (TypeError, ValueError):
            return d

    return bool(data.get("ok")), _c(data.get("focal_x")), _c(data.get("focal_y"))
