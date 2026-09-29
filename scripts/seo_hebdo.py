#!/usr/bin/env python3
"""Le bilan Search Console du lundi matin, en image animée dans Slack.

D'OÙ ÇA VIENT (2026-09-28). Franck : « j'aimerais bien avoir une notification Slack tous
les lundis matin avec les derniers chiffres, clics, impressions, comparaison, moyenne de
positionnement… mais quelque chose de visuel, de graphique, motion design ».

Ça RENVERSE un arbitrage écrit dans `gsc_report._enregistre` (13/08) : « à 19 clics sur
trois mois, un rapport hebdomadaire envoyé sur Slack serait du bruit ». C'est Franck qui
le demande, et c'est UN message par semaine : il ne rouvre pas la question des sept
notifications par jour. L'archivage du dimanche (`gsc_report --enregistrer`) reste tel
quel ; ce script-ci ne lit que l'API, il n'écrit rien en base.

CE QUE LE MESSAGE COMPARE, écrit ici parce que c'est le piège (journal SEO du 10/09,
faute 1 : une fenêtre de trafic sans date prise pour l'actuelle) :
  - « la semaine » = les 7 DERNIERS JOURS PUBLIÉS par Google, pas la semaine civile. La
    Search Console a deux à trois jours de retard ; un lundi, le dernier jour complet est
    en général le jeudi ou le vendredi. Le script ne DEVINE pas ce retard : il demande
    tout jusqu'à hier et prend la dernière date que l'API renvoie vraiment ;
  - comparée aux 7 jours qui la précèdent ;
  - la position moyenne est pondérée par les impressions, comme dans `gsc_report --tendance`
    (une moyenne simple des jours donnerait le même poids à un jour à 3 impressions) ;
  - les dates réelles sont écrites SUR l'image et dans le texte.

POURQUOI UN GIF, ET POURQUOI HÉBERGÉ PAR LE BACKOFFICE. Slack reçoit nos messages par un
webhook entrant (`utils/slack.notify`), qui ne sait pas téléverser de fichier : une image
n'y entre que par son ADRESSE. Le GIF est donc écrit dans `data/rapports_publics/` et servi
par la route publique `/embed/rapports/<fichier>` du backoffice (même famille que
`/embed/events.json`, déjà publique). Le nom porte une empreinte : Slack met les images en
cache par adresse, et une adresse réutilisée montrerait le bilan de la semaine d'avant.
Slack anime les GIF dans les messages, c'est la seule animation que le webhook permet.

AVANT D'ENVOYER, le script vérifie que l'adresse répond 200 depuis l'extérieur. Si elle ne
répond pas (backoffice pas encore redéployé, disque plein…), le message part SANS image et
le dit — plutôt qu'un bloc image que Slack refuserait, ce qui ferait tomber tout le message.

Usage :
    .venv/bin/python -m scripts.seo_hebdo                 # simulation : GIF + texte, rien envoyé
    .venv/bin/python -m scripts.seo_hebdo --apply         # envoie sur Slack
    .venv/bin/python -m scripts.seo_hebdo --demo          # données inventées, sans Google
"""
from __future__ import annotations

import argparse
import hashlib
import io
import math
import os
import random
import sys
from datetime import date, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger  # noqa: E402

log = get_logger("seo_hebdo")

# Lu aussi par la route /embed/rapports de app/app.py : un seul endroit pour le chemin.
DOSSIER_PUBLIC = ROOT / "data" / "rapports_publics"
PREFIXE = "seo-hebdo-"
NB_SEMAINES = 8           # l'histogramme : huit blocs de 7 jours
GARDER = 12               # GIF conservés sur disque (trois mois de lundis)

MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.",
        "oct.", "nov.", "déc."]

# Charte du site (mêmes valeurs que les mu-plugins : fond crème, encre, rouge brique).
CREME, ENCRE, BRIQUE, GRIS = "#F7F1E8", "#1D1D1B", "#DC5D45", "#6F6B62"
CARTE, TRAIT = "#FBF7F0", "#E3DCCE"
VERT, ROUGE = "#2E7D4F", "#B3261E"


# ─────────────────────────── calcul ───────────────────────────

def _bloc(lignes: list[dict], debut: date, fin: date) -> dict:
    """Totaux d'une fenêtre [debut, fin] à partir des lignes quotidiennes de l'API."""
    c = i = pp = 0.0
    jours = 0
    for l in lignes:
        d = date.fromisoformat(l["keys"][0])
        if debut <= d <= fin:
            c += l.get("clicks", 0)
            i += l.get("impressions", 0)
            pp += l.get("position", 0) * l.get("impressions", 0)
            jours += 1
    return {"debut": debut, "fin": fin, "jours": jours, "clics": c, "impressions": i,
            "ctr": (c / i if i else 0.0), "position": (pp / i if i else None)}


def synthese(lignes_date: list[dict]) -> dict | None:
    """Semaine, semaine précédente et huit semaines d'historique. None si l'API n'a rien
    renvoyé — un zéro ne doit pas se lire comme « aucune visite »."""
    if not lignes_date:
        return None
    dernier = max(date.fromisoformat(l["keys"][0]) for l in lignes_date)
    semaines = []
    for k in range(NB_SEMAINES - 1, -1, -1):
        fin = dernier - timedelta(days=7 * k)
        semaines.append(_bloc(lignes_date, fin - timedelta(days=6), fin))
    return {"dernier": dernier, "semaine": semaines[-1], "precedente": semaines[-2],
            "historique": semaines, "lignes": len(lignes_date)}


def _variation(a: float, b: float) -> float | None:
    return None if not b else (a - b) / b * 100


def _fr(n: float, dec: int = 0) -> str:
    s = f"{n:,.{dec}f}".replace(",", " ").replace(".", ",")
    return s.replace(" ", " ")


def _periode(d1: date, d2: date) -> str:
    if d1.month == d2.month:
        return f"du {d1.day} au {d2.day} {MOIS[d2.month - 1]}"
    return f"du {d1.day} {MOIS[d1.month - 1]} au {d2.day} {MOIS[d2.month - 1]}"


def _fleche(v: float | None, inverse: bool = False) -> tuple[str, str]:
    """(texte, couleur). `inverse` : pour la position, BAISSER est un progrès."""
    if v is None:
        return "nouveau", GRIS
    if abs(v) < 0.5:
        return "stable", GRIS
    bon = (v < 0) if inverse else (v > 0)
    return (("▲ " if v > 0 else "▼ ") + ("+" if v > 0 else "−") + _fr(abs(v)) + " %",
            VERT if bon else ROUGE)


def _delta_position(s: dict, p: dict) -> tuple[str, str]:
    if s["position"] is None or p["position"] is None:
        return "—", GRIS
    d = s["position"] - p["position"]
    if abs(d) < 0.05:
        return "stable", GRIS
    # Une position qui DIMINUE remonte dans Google : on écrit le gain en places.
    return ((f"▲ gagne {_fr(-d, 1)} place" if d < 0 else f"▼ perd {_fr(d, 1)} place")
            + ("s" if abs(d) >= 2 else ""), VERT if d < 0 else ROUGE)


# ─────────────────────────── image ───────────────────────────

_POLICES = {
    "bold": ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
             "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"],
    "reg": ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"],
}


def _police(kind: str, taille: int):
    for chemin in _POLICES[kind]:
        try:
            return ImageFont.truetype(chemin, taille)
        except OSError:
            continue
    return ImageFont.load_default()


def _ease(t: float) -> float:
    """Sortie douce (cubique) : le compteur file puis se pose."""
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def _texte_centre(dr, x, y, w, texte, police, couleur):
    tw = dr.textlength(texte, font=police)
    dr.text((x + (w - tw) / 2, y), texte, font=police, fill=couleur)


W, H = 960, 720


def _image(syn: dict, t: float, propriete: str, demo: bool = False) -> Image.Image:
    """Une image de l'animation. t va de 0 (vide) à 1 (état final)."""
    s, p, hist = syn["semaine"], syn["precedente"], syn["historique"]
    im = Image.new("RGB", (W, H), CREME)
    dr = ImageDraw.Draw(im)
    f_kick, f_titre = _police("bold", 15), _police("bold", 34)
    f_sous, f_lab = _police("reg", 17), _police("bold", 14)
    f_val, f_delta, f_pied = _police("bold", 44), _police("bold", 17), _police("reg", 13)

    # En-tête : entre par la gauche pendant le premier cinquième.
    dx = int((1 - _ease(t / 0.2)) * -60)
    dr.text((40 + dx, 30), "AGENDA SABAUDA  ·  SEARCH CONSOLE", font=f_kick, fill=BRIQUE)
    dr.text((40 + dx, 54), f"Semaine {_periode(s['debut'], s['fin'])}", font=f_titre, fill=ENCRE)
    sous = f"comparée aux 7 jours {_periode(p['debut'], p['fin'])}"
    if s["jours"] < 7:
        sous += f"  ·  SEMAINE INCOMPLÈTE : {s['jours']} jour(s) de données"
    dr.text((40 + dx, 100), sous, font=f_sous, fill=BRIQUE if s["jours"] < 7 else GRIS)
    if demo:
        dr.text((W - 330, 30), "DONNÉES INVENTÉES — DÉMO", font=f_kick, fill=ROUGE)
    dr.line((40, 136, W - 40, 136), fill=ENCRE, width=2)

    tuiles = [
        ("CLICS", s["clics"], 0, _fleche(_variation(s["clics"], p["clics"]))),
        ("IMPRESSIONS", s["impressions"], 0,
         _fleche(_variation(s["impressions"], p["impressions"]))),
        ("TAUX DE CLIC", s["ctr"] * 100, 1,
         _fleche(_variation(s["ctr"], p["ctr"]))),
        ("POSITION MOYENNE", s["position"] or 0, 1, _delta_position(s, p)),
    ]
    tw, th, gx, y0 = (W - 80 - 3 * 16) / 4, 150, 16, 160
    for k, (lab, val, dec, (dtxt, dcol)) in enumerate(tuiles):
        # Chaque tuile démarre un peu après la précédente : l'œil suit l'ordre de lecture.
        tk = _ease((t - 0.08 - 0.06 * k) / 0.45)
        x = 40 + k * (tw + gx)
        y = y0 + int((1 - tk) * 30)
        dr.rounded_rectangle((x, y, x + tw, y + th), radius=6, fill=CARTE,
                             outline=TRAIT, width=1)
        dr.rectangle((x, y, x + tw, y + 4), fill=BRIQUE if k == 0 else ENCRE)
        _texte_centre(dr, x, y + 20, tw, lab, f_lab, GRIS)
        if lab == "POSITION MOYENNE" and s["position"] is None:
            chiffre = "—"
        elif lab == "POSITION MOYENNE" and p["position"] is not None:
            # Pas de compteur depuis 0 : à mi-course il afficherait « 3,7 », qu'on lirait
            # comme une excellente position. Elle GLISSE de la semaine d'avant à celle-ci,
            # et c'est ce glissement qui est l'information.
            chiffre = _fr(p["position"] + (s["position"] - p["position"]) * tk, 1)
        else:
            chiffre = _fr(val * tk, dec) + (" %" if lab == "TAUX DE CLIC" else "")
        _texte_centre(dr, x, y + 48, tw, chiffre, f_val, ENCRE)
        if t > 0.62 + 0.03 * k:        # la variation arrive quand le compteur s'est posé
            _texte_centre(dr, x, y + 110, tw, dtxt, f_delta, dcol)

    # Histogramme : clics par bloc de 7 jours, barres qui montent l'une après l'autre.
    gx0, gy0, gx1, gy1 = 60, 380, W - 40, 640
    dr.text((40, 344), f"CLICS PAR BLOC DE 7 JOURS  ·  {NB_SEMAINES} DERNIERS BLOCS",
            font=f_lab, fill=GRIS)
    maxi = max((b["clics"] for b in hist), default=0) or 1
    n = len(hist)
    larg = (gx1 - gx0) / n
    dr.line((gx0, gy1, gx1, gy1), fill=ENCRE, width=1)
    for k, b in enumerate(hist):
        tk = _ease((t - 0.3 - 0.045 * k) / 0.35)
        h = (gy1 - gy0 - 40) * (b["clics"] / maxi) * tk
        bx = gx0 + k * larg + larg * 0.18
        bw = larg * 0.64
        col = BRIQUE if k == n - 1 else ("#C9BFAD" if k < n - 2 else "#9E9486")
        if h > 0:
            dr.rectangle((bx, gy1 - h, bx + bw, gy1), fill=col)
        if tk > 0.95:
            _texte_centre(dr, bx, gy1 - h - 22, bw, _fr(b["clics"]), f_lab, ENCRE)
        lab = f"{b['fin'].day} {MOIS[b['fin'].month - 1]}"
        _texte_centre(dr, bx - 10, gy1 + 8, bw + 20, lab, f_pied, GRIS)

    pied = (f"Source : {propriete}  ·  dernier jour publié par Google : "
            f"{syn['dernier'].day} {MOIS[syn['dernier'].month - 1]}  ·  position pondérée "
            f"par les impressions")
    dr.text((40, H - 34), pied, font=f_pied, fill=GRIS)
    return im


def rendre_gif(syn: dict, propriete: str, n_images: int = 42, demo: bool = False) -> bytes:
    images = [_image(syn, k / (n_images - 1), propriete, demo) for k in range(n_images)]
    # Palette commune : couleurs stables d'une image à l'autre, fichier léger.
    pal = images[-1].quantize(colors=64, method=Image.Quantize.MEDIANCUT)
    images = [i.quantize(palette=pal, dither=Image.Dither.NONE) for i in images]
    durees = [45] * (n_images - 1) + [6000]   # l'état final reste six secondes à l'écran
    buf = io.BytesIO()
    images[0].save(buf, format="GIF", save_all=True, append_images=images[1:],
                   duration=durees, loop=0, optimize=True, disposal=1)
    return buf.getvalue()


def publier_gif(donnees: bytes, dernier: date) -> Path:
    DOSSIER_PUBLIC.mkdir(parents=True, exist_ok=True)
    nom = f"{PREFIXE}{dernier.isoformat()}-{hashlib.sha1(donnees).hexdigest()[:8]}.gif"
    chemin = DOSSIER_PUBLIC / nom
    chemin.write_bytes(donnees)
    anciens = sorted(DOSSIER_PUBLIC.glob(f"{PREFIXE}*.gif"), key=lambda f: f.stat().st_mtime)
    for f in anciens[:-GARDER]:
        f.unlink()   # fichiers régénérables, produits par ce seul script
    return chemin


# ─────────────────────────── message ───────────────────────────

def _court(url: str, base: str) -> str:
    u = url.replace(base, "") or "/"
    return u if len(u) <= 60 else u[:57] + "…"


def texte_et_blocs(syn: dict, tops_pages: list[dict], tops_req: list[dict],
                   base: str, url_image: str | None, raison_sans_image: str = "") -> tuple[str, list]:
    s, p = syn["semaine"], syn["precedente"]
    var_c = _variation(s["clics"], p["clics"])
    resume = (f"SEO {_periode(s['debut'], s['fin'])} : {_fr(s['clics'])} clics "
              f"({_fleche(var_c)[0]}), {_fr(s['impressions'])} impressions, position "
              + ("—" if s["position"] is None else _fr(s["position"], 1)))
    blocs: list = [{"type": "header", "text": {"type": "plain_text",
                    "text": f"📈 Search Console — semaine {_periode(s['debut'], s['fin'])}"}}]
    if url_image:
        blocs.append({"type": "image", "image_url": url_image, "alt_text": resume})
    lignes = [
        f"*Clics* {_fr(s['clics'])} (avant : {_fr(p['clics'])}) · "
        f"*Impressions* {_fr(s['impressions'])} (avant : {_fr(p['impressions'])})",
        f"*Taux de clic* {_fr(s['ctr'] * 100, 1)} % · *Position moyenne* "
        + ("—" if s["position"] is None else _fr(s["position"], 1))
        + ("" if p["position"] is None else f" (avant : {_fr(p['position'], 1)})"),
    ]
    blocs.append({"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(lignes)}})

    def _liste(titre, rows, cle_url):
        if not rows:
            return f"*{titre}* — aucune ligne renvoyée"
        out = [f"*{titre}*"]
        for r in rows:
            k = r["keys"][0]
            nom = f"<{k}|{_court(k, base)}>" if cle_url else f"« {k} »"
            out.append(f"• {nom} — {_fr(r['clicks'])} clic(s), {_fr(r['impressions'])} impr., "
                       f"pos. {_fr(r['position'], 1)}")
        return "\n".join(out)

    blocs.append({"type": "section", "text": {"type": "mrkdwn", "text":
                  _liste("Pages qui ont amené le plus de clics", tops_pages, True)}})
    blocs.append({"type": "section", "text": {"type": "mrkdwn", "text":
                  _liste("Requêtes qui ont amené le plus de clics", tops_req, False)}})
    contexte = (f"Les 7 derniers jours publiés par Google (retard habituel de 2-3 jours), "
                f"comparés aux 7 précédents. {syn['lignes']} jour(s) de données reçus"
                + (f" — SEMAINE INCOMPLÈTE, {s['jours']} jour(s) sur 7." if s["jours"] < 7
                   else "."))
    if raison_sans_image:
        contexte += f" Image absente : {raison_sans_image}."
    blocs.append({"type": "context", "elements": [{"type": "mrkdwn", "text": contexte}]})
    return resume, blocs


def _image_joignable(url: str) -> str:
    """"" si l'adresse sert bien un GIF, sinon la raison — écrite dans le message."""
    try:
        r = requests.get(url, timeout=20, stream=True)
        ctype = r.headers.get("Content-Type", "")
        r.close()
        if r.status_code != 200:
            return f"l'adresse publique répond {r.status_code}"
        if "image/gif" not in ctype:
            return f"l'adresse publique sert « {ctype or 'rien'} » au lieu d'un GIF"
        return ""
    except requests.RequestException as exc:
        return f"adresse publique injoignable ({type(exc).__name__})"


# ─────────────────────────── données de démonstration ───────────────────────────

def _demo() -> tuple[list[dict], list[dict], list[dict]]:
    """Données INVENTÉES, pour voir l'image sans identifiants Google. Jamais envoyées :
    `--demo` et `--apply` sont refusés ensemble."""
    rnd = random.Random(7)
    fin = date.today() - timedelta(days=3)
    lignes = []
    for k in range(7 * NB_SEMAINES):
        d = fin - timedelta(days=k)
        tendance = 1 + (7 * NB_SEMAINES - k) / 40
        impr = rnd.randint(180, 320) * tendance
        lignes.append({"keys": [d.isoformat()], "clicks": round(impr * rnd.uniform(0.015, 0.04)),
                       "impressions": round(impr), "position": rnd.uniform(14, 24) / tendance})
    base = "https://agendasabauda.eu"
    pages = [{"keys": [f"{base}/ce-week-end/"], "clicks": 21, "impressions": 640, "position": 8.2},
             {"keys": [f"{base}/evenement/foire-de-savoie/"], "clicks": 14, "impressions": 410,
              "position": 6.9}]
    req = [{"keys": ["que faire ce week-end savoie"], "clicks": 9, "impressions": 220,
            "position": 7.4}]
    return lignes, pages, req


# ─────────────────────────── main ───────────────────────────

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--apply", action="store_true", help="Envoie réellement sur Slack.")
    ap.add_argument("--demo", action="store_true", help="Données inventées, sans Google.")
    args = ap.parse_args(argv)
    if args.demo and args.apply:
        log.error("--demo fabrique des chiffres : il ne s'envoie jamais (--apply refusé).")
        return 2

    load_dotenv(ROOT / ".env")
    base = (os.getenv("WP_AS_URL") or "https://agendasabauda.eu").rstrip("/")
    propriete = os.getenv("GSC_PROPERTY") or f"sc-domain:{base.split('//')[-1]}"
    backoffice = os.getenv("BACKOFFICE_BASE_URL",
                           "https://backoffice.agendasabauda.eu").rstrip("/")

    print("1/4 Lecture de la Search Console…", flush=True)
    if args.demo:
        lignes, tops_pages, tops_req = _demo()
        print("    DONNÉES INVENTÉES (--demo)")
    else:
        from scripts.gsc_report import _interroge, _service
        service = _service()
        if service is None:
            return 2
        hier = date.today() - timedelta(days=1)
        debut = hier - timedelta(days=7 * NB_SEMAINES + 7)
        try:
            lignes = _interroge(service, propriete, debut.isoformat(), hier.isoformat(),
                                ["date"], 1000)
        except Exception as exc:  # noqa: BLE001 — le message brut de l'API
            log.error("requête Search Console refusée : %s", exc)
            return 2
    syn = synthese(lignes)
    if syn is None:
        msg = (f"Search Console : l'API n'a renvoyé AUCUNE ligne pour {propriete} "
               f"({debut} → {hier}). Ce n'est pas « zéro visite » : lancer "
               f"`.venv/bin/python -m scripts.gsc_report --check`.")
        print(msg)
        if args.apply:
            from utils import slack
            slack.notify(msg, urgent=True)
        return 1
    s = syn["semaine"]
    print(f"    {syn['lignes']} jour(s) reçus, dernier jour publié : {syn['dernier']}")
    print(f"    semaine {s['debut']} → {s['fin']} ({s['jours']} j) : {s['clics']:.0f} clics, "
          f"{s['impressions']:.0f} impressions")
    if not args.demo:
        d1, d2 = s["debut"].isoformat(), s["fin"].isoformat()
        tops_pages = _interroge(service, propriete, d1, d2, ["page"], 3)
        tops_req = _interroge(service, propriete, d1, d2, ["query"], 3)

    print("2/4 Fabrication de l'animation…", flush=True)
    gif = rendre_gif(syn, propriete, demo=args.demo)
    if args.demo:
        # Jamais dans le dossier PUBLIC : des chiffres inventés n'ont pas à être servis.
        chemin = ROOT / "data" / "seo-hebdo-demo.gif"
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_bytes(gif)
    else:
        chemin = publier_gif(gif, syn["dernier"])
    print(f"    {chemin} ({len(gif) // 1024} Ko)")
    url = f"{backoffice}/embed/rapports/{chemin.name}"

    print("3/4 Vérification de l'adresse publique de l'image…", flush=True)
    raison = "" if args.demo else _image_joignable(url)
    print(f"    {url} → " + ("non vérifiée (--demo : rien ne sera envoyé)" if args.demo
                               else ("OK" if not raison else raison)))

    resume, blocs = texte_et_blocs(syn, tops_pages, tops_req, base,
                                   None if (raison or args.demo) else url, raison)
    print("4/4 Message :", flush=True)
    print("    " + resume)
    for b in blocs:
        if b["type"] == "section":
            print("    " + b["text"]["text"].replace("\n", "\n    "))
    if not args.apply:
        print("\nSimulation (défaut) : rien n'a été envoyé. Relancer avec --apply.")
        return 0
    from utils import slack
    # urgent=True : la boîte du jour (SLACK_DIGEST) ne garde que le TEXTE, l'image serait
    # perdue au vidage de 11h45. Franck a demandé CE message-là, le lundi matin, en image.
    ok = slack.notify(resume, blocks=blocs, urgent=True)
    print("Envoyé." if ok else "ÉCHEC de l'envoi Slack (voir logs).")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
