#!/usr/bin/env python3
"""Audit visuel EN LOT : repère les photos qui ne correspondent PAS à leur événement.

Idée de Franck : plutôt qu'un agent qui juge une image À LA FOIS (coûteux, et un
jugement isolé peut rater ce qu'un coup d'œil comparatif verrait tout de suite), on
compose une « planche contact » — une grille de ~20 vignettes + titre — et on demande
à l'agent vision de repérer en UN SEUL appel les cases qui détonnent (photo sans
rapport avec son titre).

Complète les vérifications déjà faites AU MOMENT de choisir l'image
(utils.image_verify.verify_relevance, cf. scripts/visuals.py) : celle-ci ne juge
qu'UNE image isolée, avec sa propre marge d'erreur, et n'existait pas pour tous les
événements publiés avant son ajout. L'audit en lot est un filet de sécurité a
posteriori, sur TOUT le catalogue.

Usage (VPS) :
    .venv/bin/python3 -m scripts.image_audit --dry-run       # compte les lots, rien n'appelle
    .venv/bin/python3 -m scripts.image_audit                 # audit complet + digest Slack
    .venv/bin/python3 -m scripts.image_audit --limit 100      # se limiter aux 100 plus récents
"""
from __future__ import annotations
import argparse
import base64
import io
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils import completeness as comp
from utils import slack
from scripts.scraper_events import init_db

log = get_logger("image_audit")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
MODEL = os.getenv("ANTHROPIC_MODEL_VISION") or "claude-haiku-4-5"

_UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"}
# Planche contact : grille COLS colonnes, vignette carrée + 2 lignes de titre dessous.
COLS = 4
CELL_W = CELL_H = 240
LABEL_H = 44
PADDING = 12


def _select(conn: sqlite3.Connection, limit: int) -> list[dict]:
    """TOUT le catalogue retenu avec une vraie photo (pas la bannière générique — on
    sait déjà qu'elle est générique, inutile de faire juger l'agent dessus)."""
    q = ("SELECT id, title, url_image, image_source, wp_permalink_as FROM events_raw "
         "WHERE duplicate_of IS NULL AND statut IN ({}) AND COALESCE(url_image,'') <> '' "
         "AND COALESCE(image_source,'') <> 'banner' ORDER BY id DESC"
        ).format(",".join("?" * len(comp.RETAINED_STATUTS)))
    rows = [dict(r) for r in conn.execute(q, comp.RETAINED_STATUTS).fetchall()]
    return rows[:limit] if limit else rows


def _download(url: str) -> "Image.Image | None":
    try:
        r = requests.get(url, headers=_UA, timeout=15)
        if r.status_code != 200:
            return None
        return Image.open(io.BytesIO(r.content)).convert("RGB")
    except Exception:
        return None


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                 "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _wrap_title(draw, text: str, font, max_w: int) -> list[str]:
    words, lines, cur = (text or "").split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines[:2]


def build_grid(batch: list[dict]) -> bytes:
    """Compose la planche contact numérotée (JPEG) — vignette carrée + titre pour
    chaque événement du lot, prête pour UN SEUL appel vision."""
    n = len(batch)
    rows = (n + COLS - 1) // COLS
    cell_total_h = CELL_H + LABEL_H
    W = COLS * CELL_W + (COLS + 1) * PADDING
    H = rows * cell_total_h + (rows + 1) * PADDING
    canvas = Image.new("RGB", (W, H), (245, 245, 245))
    draw = ImageDraw.Draw(canvas)
    fnum, ftitle = _font(22), _font(16)
    for i, ev in enumerate(batch):
        col, row = i % COLS, i // COLS
        x = PADDING + col * (CELL_W + PADDING)
        y = PADDING + row * (cell_total_h + PADDING)
        img = _download(ev["url_image"])
        if img is not None:
            scale = max(CELL_W / img.width, CELL_H / img.height)
            rw, rh = round(img.width * scale), round(img.height * scale)
            thumb = img.resize((rw, rh), Image.LANCZOS)
            left, top = (rw - CELL_W) // 2, (rh - CELL_H) // 2
            thumb = thumb.crop((left, top, left + CELL_W, top + CELL_H))
            canvas.paste(thumb, (x, y))
        else:
            draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=(200, 60, 60))
            draw.text((x + 10, y + 10), "image injoignable", font=ftitle, fill=(255, 255, 255))
        draw.rectangle([x, y, x + 38, y + 30], fill=(20, 20, 20))
        draw.text((x + 9, y + 4), str(i + 1), font=fnum, fill=(255, 255, 255))
        title = re.sub(r"\s+", " ", (ev.get("title") or "")).strip()
        ty = y + CELL_H + 4
        for ln in _wrap_title(draw, title, ftitle, CELL_W):
            draw.text((x, ty), ln, font=ftitle, fill=(20, 20, 20))
            ty += 20
    buf = io.BytesIO()
    canvas.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def judge_grid(batch: list[dict], grid_bytes: bytes, client) -> list[dict]:
    """UN appel vision sur toute la planche : renvoie les cases jugées hors-sujet."""
    legend = "\n".join(f"{i + 1}. {(ev.get('title') or '')[:80]}" for i, ev in enumerate(batch))
    prompt = (
        "Voici une PLANCHE CONTACT de photos d'événements culturels, numérotées de "
        f"1 à {len(batch)} (numéro visible en haut à gauche de chaque case), chacune "
        f"avec son titre affiché en dessous ET rappelé ici :\n{legend}\n\n"
        "Repère les cases où la PHOTO n'a clairement AUCUN rapport avec son titre "
        "(mauvais événement, image parasite récupérée par erreur sur la page source, "
        "logo, capture d'écran, bandeau publicitaire…). Ne signale PAS une photo "
        "simplement générique ou de qualité moyenne si elle reste plausible pour le "
        "sujet — seulement les cas OUTRAGEUSEMENT hors-sujet, ceux qu'un humain "
        "repérerait immédiatement d'un coup d'œil.\n"
        'Réponds en JSON strict : {"flagged": [{"n": 3, "raison": "…"}, ...]} '
        '(liste vide si tout va bien).'
    )
    try:
        msg = client.messages.create(
            model=MODEL, max_tokens=800,
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                             "data": base64.standard_b64encode(grid_bytes).decode("ascii")}},
                {"type": "text", "text": prompt}]}])
    except Exception as exc:
        log.warning("Audit lot échoué : %s", exc)
        return []
    try:
        from utils import usage
        usage.record_message(MODEL, msg, label="image_audit")
    except Exception:
        pass
    raw = "".join(getattr(b, "text", "") for b in msg.content
                  if getattr(b, "type", None) == "text").strip()
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return []
    try:
        data = json.loads(m.group())
    except (ValueError, TypeError):
        return []
    out = []
    for item in data.get("flagged") or []:
        n = item.get("n")
        if isinstance(n, int) and 1 <= n <= len(batch):
            ev = batch[n - 1]
            out.append({"id": ev["id"], "title": ev.get("title"), "url_image": ev["url_image"],
                       "wp_permalink_as": ev.get("wp_permalink_as"), "raison": item.get("raison", "")})
    return out


def main(argv=None) -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="Audit visuel en lot (planches contact + agent vision).")
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--limit", type=int, default=0,
                        help="Limite le nombre total d'événements audités (0 = tout le catalogue).")
    parser.add_argument("--dry-run", action="store_true", help="Compte les lots sans appeler l'agent.")
    parser.add_argument("--no-slack", action="store_true", help="Ne pas envoyer le digest Slack.")
    args = parser.parse_args(argv)

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    conn.row_factory = sqlite3.Row
    rows = _select(conn, args.limit)
    log.info("%d événement(s) à auditer (lots de %d).", len(rows), args.batch_size)
    if not rows:
        conn.close()
        return 0
    batches = [rows[i:i + args.batch_size] for i in range(0, len(rows), args.batch_size)]
    if args.dry_run:
        log.info("%d planche(s) SERAIENT générées (dry-run — aucun appel agent).", len(batches))
        conn.close()
        return 0

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        log.error("ANTHROPIC_API_KEY absente — audit impossible.")
        conn.close()
        return 1
    import anthropic
    client = anthropic.Anthropic(api_key=api_key, timeout=90.0)

    flagged_all = []
    for i, batch in enumerate(batches, 1):
        log.info("Planche %d/%d (%d événements)…", i, len(batches), len(batch))
        grid = build_grid(batch)
        flagged = judge_grid(batch, grid, client)
        flagged_all.extend(flagged)
        for f in flagged:
            log.warning("[%s] SUSPECT : %s — %s", f["id"], (f["title"] or "")[:60], f["raison"])

    log.info("=== Audit visuel : %d suspect(s) sur %d audité(s) (%d planches) ===",
             len(flagged_all), len(rows), len(batches))

    if flagged_all and not args.no_slack:
        base = (os.getenv("BACKOFFICE_BASE_URL") or "").rstrip("/")
        lines = [f"🖼️ *Audit visuel* — {len(flagged_all)} photo(s) suspecte(s) sur {len(rows)} auditées :"]
        for f in flagged_all[:15]:
            title = (f["title"] or "?")[:70]
            lien = f"{base}/preview/{f['id']}" if base else ""
            lines.append(f"• <{lien}|{title}> — {f['raison']}" if lien else f"• {title} — {f['raison']}")
        if len(flagged_all) > 15:
            lines.append(f"… et {len(flagged_all) - 15} de plus (voir les logs).")
        slack.notify("\n".join(lines))

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
