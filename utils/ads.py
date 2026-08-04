#!/usr/bin/env python3
"""Régie pub « hors flux » (skin + gouttières) pilotée depuis le back-office.

Sert /api/active-ads à agendasabauda.eu (lu par les mu-plugins WordPress
cs-regie-serve.php et cs-regie.php) et /go/<id> pour le clic sortant compté.

Le slot "3" (bandeau bas sticky) existait déjà en production AVANT ce module —
servi par du code ajouté directement sur le VPS, jamais commité (voir
docs/REGIE_MISE_EN_PLACE_SOCLE.md, conflit #2). On ne l'a pas vu tourner : ce
module le RECONSTRUIT à partir du seul contrat observable (la réponse JSON de
/api/active-ads le 2026-08-04), avec le même id=2 pour ne pas casser le lien
/go/2 déjà diffusé. À vérifier en prod après déploiement — si le code non
versionné faisait autre chose (ex. rotation, quota), ce n'est PAS reproduit ici.

Slots gérés : "3" (bandeau bas, déjà en Ad Inserter — restera piloté par ce
module si le Bloc 3 est repassé en mu-plugin), "skin" (habillage desktop),
"left" (gouttière gauche 160×600), "right" (gouttière droite 300×600). Les
formats display purs (leaderboard, pavés) restent hors de ce module : ce sont
des unités AdSense, pas des créatives maison.
"""
from __future__ import annotations
import os
import sqlite3
from datetime import datetime, timezone

# Slots connus, dans l'ordre d'affichage de la page d'admin. "format" est un
# libellé humain (taille attendue) ; il ne contraint rien techniquement.
SLOTS = {
    "3":     {"label": "Bandeau bas (sticky)",   "format": "970×90 · vignette mobile"},
    "skin":  {"label": "Habillage / Skin",       "format": "1920×1080 · bandes latérales, desktop ≥1840px"},
    "left":  {"label": "Gouttière gauche",       "format": "160×600 · desktop ≥1440px"},
    "right": {"label": "Gouttière droite",       "format": "300×600 · desktop ≥1440px"},
}

# Seed de démarrage : reproduit l'état observé du slot "3" en prod (id=2, pour
# préserver le lien /go/2 déjà en circulation). Les autres slots démarrent OFF,
# sans créative — comportement identique à cs-regie.php (scaffold jamais
# déployé, tout à 0 par défaut).
_SEED_SLOT_3 = {
    "id": 2,
    "image": "https://agendasabauda.eu/wp-content/uploads/2026/08/970x9028129.png",
    # Destination réelle inconnue (seule la version /go/2 a été observée) —
    # place-holder neutre, à corriger depuis /ads dès qu'on a le vrai lien annonceur.
    "dest_url": "https://agendasabauda.eu/",
}


def init_ads_db(conn: sqlite3.Connection) -> None:
    conn.execute("""
    CREATE TABLE IF NOT EXISTS ad_slots (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        slot        TEXT NOT NULL UNIQUE,
        active      INTEGER NOT NULL DEFAULT 0,
        image       TEXT,
        dest_url    TEXT,
        clicks      INTEGER NOT NULL DEFAULT 0,
        updated_at  TEXT
    )
    """)
    conn.commit()
    existing = {r["slot"] for r in conn.execute("SELECT slot FROM ad_slots")}
    if "3" not in existing:
        conn.execute(
            "INSERT INTO ad_slots (id, slot, active, image, dest_url, updated_at) "
            "VALUES (?, '3', 1, ?, ?, datetime('now'))",
            (_SEED_SLOT_3["id"], _SEED_SLOT_3["image"], _SEED_SLOT_3["dest_url"]),
        )
    for slot in SLOTS:
        if slot != "3" and slot not in existing:
            conn.execute(
                "INSERT INTO ad_slots (slot, active, image, dest_url, updated_at) "
                "VALUES (?, 0, '', '', datetime('now'))", (slot,))
    conn.commit()


def backoffice_base() -> str:
    return (os.getenv("BACKOFFICE_BASE_URL", "https://backoffice.agendasabauda.eu") or "").rstrip("/")


def get_active_ads_payload(conn: sqlite3.Connection) -> dict:
    """Forme exacte attendue par cs-regie-serve.php / cs-regie.php côté WP :
    {"ads": {"<slot>": {"id":.., "format":.., "image":.., "link": ".../go/<id>"}}}."""
    base = backoffice_base()
    ads = {}
    rows = conn.execute(
        "SELECT * FROM ad_slots WHERE active=1 AND image != '' AND dest_url != ''"
    ).fetchall()
    for row in rows:
        meta = SLOTS.get(row["slot"], {})
        ads[row["slot"]] = {
            "id": row["id"],
            "format": meta.get("format", ""),
            "image": row["image"],
            "link": f"{base}/go/{row['id']}",
        }
    return {"ads": ads}


def get_all_slots(conn: sqlite3.Connection) -> list[dict]:
    rows = {r["slot"]: dict(r) for r in conn.execute("SELECT * FROM ad_slots")}
    out = []
    for slot, meta in SLOTS.items():
        row = rows.get(slot, {})
        out.append({
            "slot": slot,
            "label": meta["label"],
            "format": meta["format"],
            "active": bool(row.get("active")),
            "image": row.get("image") or "",
            "dest_url": row.get("dest_url") or "",
            "clicks": row.get("clicks") or 0,
            "updated_at": row.get("updated_at") or "",
        })
    return out


def set_slot(conn: sqlite3.Connection, slot: str, active: bool, image: str, dest_url: str) -> None:
    if slot not in SLOTS:
        raise ValueError(f"slot inconnu : {slot}")
    conn.execute(
        "UPDATE ad_slots SET active=?, image=?, dest_url=?, updated_at=? WHERE slot=?",
        (1 if active else 0, image.strip(), dest_url.strip(),
         datetime.now(timezone.utc).isoformat(timespec="seconds"), slot),
    )
    conn.commit()


def resolve_click(conn: sqlite3.Connection, ad_id: int) -> str | None:
    """Incrémente le compteur et renvoie l'URL de destination, ou None si id inconnu/inactif."""
    row = conn.execute("SELECT dest_url, active FROM ad_slots WHERE id=?", (ad_id,)).fetchone()
    if not row or not row["active"] or not row["dest_url"]:
        return None
    conn.execute("UPDATE ad_slots SET clicks = clicks + 1 WHERE id=?", (ad_id,))
    conn.commit()
    return row["dest_url"]
