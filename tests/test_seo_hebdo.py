#!/usr/bin/env python3
"""Fixture : le bilan SEO du lundi dit la bonne période, le bon sens, et ne ment pas à zéro.

⚠️ Aucun réseau, aucune base, aucun Slack. Le dossier public est redirigé vers un dossier
jetable.

D'OÙ ÇA VIENT (2026-09-28) : demande de Franck, un bilan Search Console animé chaque lundi
dans Slack (`scripts/seo_hebdo.py`). Les pièges surveillés sont ceux déjà payés dans ce
dépôt, pas des hypothèses :
  1. LA FENÊTRE. Le journal SEO du 10/09 (faute 1) : une fenêtre sans date prise pour
     l'actuelle. La « semaine » doit finir au DERNIER jour que l'API a vraiment renvoyé,
     pas à « aujourd'hui − 3 » deviné ;
  2. LE SENS DE LA POSITION. Une position qui DIMINUE est un progrès. Le cas qui doit
     PASSER près de la frontière : un écart de 0,04 place est « stable », pas un recul ;
  3. LE ZÉRO. Une API muette doit donner « pas de données », jamais un graphique à zéro ;
  4. LA SEMAINE TROUÉE est signalée, la semaine complète ne l'est pas (cas qui doit passer) ;
  5. LA ROUTE PUBLIQUE ne sert que les GIF du bilan : ni `..`, ni un autre nom ;
  6. `--demo` (chiffres inventés) ne peut pas partir avec `--apply`.

Lancer : .venv/bin/python -m tests.test_seo_hebdo
"""
import io
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402

from scripts import seo_hebdo as sh  # noqa: E402

echecs = 0


def _check(nom, ok, detail=""):
    global echecs
    print(("  ✓ " if ok else "  ✗ ") + nom + ("" if ok else f"\n      → {detail}"))
    if not ok:
        echecs += 1


def _jours(fin: date, n: int, clics=10, impr=100, pos=10.0, trous=()):
    out = []
    for k in range(n):
        d = fin - timedelta(days=k)
        if d in trous:
            continue
        out.append({"keys": [d.isoformat()], "clicks": clics, "impressions": impr,
                    "position": pos})
    return out


print("1. La fenêtre finit au dernier jour RENVOYÉ par l'API")
fin = date(2026, 9, 25)
syn = sh.synthese(_jours(fin, 70))
_check("dernier jour = 25/09 (lu dans les données, pas deviné)", syn["dernier"] == fin,
       syn["dernier"])
_check("semaine = 19 → 25/09", (syn["semaine"]["debut"], syn["semaine"]["fin"])
       == (date(2026, 9, 19), fin), syn["semaine"])
_check("précédente = 12 → 18/09", (syn["precedente"]["debut"], syn["precedente"]["fin"])
       == (date(2026, 9, 12), date(2026, 9, 18)), syn["precedente"])
_check("huit blocs d'historique, le dernier = la semaine", len(syn["historique"]) == 8
       and syn["historique"][-1] is syn["semaine"], len(syn["historique"]))
_check("semaine complète : 7 jours, 70 clics", syn["semaine"]["jours"] == 7
       and syn["semaine"]["clics"] == 70, syn["semaine"])

print("\n2. Position pondérée par les impressions, et son sens")
lignes = [{"keys": ["2026-09-25"], "clicks": 1, "impressions": 900, "position": 5.0},
          {"keys": ["2026-09-24"], "clicks": 0, "impressions": 100, "position": 45.0}]
p = sh.synthese(lignes)["semaine"]["position"]
_check("(900×5 + 100×45) / 1000 = 9,0 — pas la moyenne simple 25", abs(p - 9.0) < 1e-9, p)
s = {"position": 8.3}
_check("8,3 contre 9,5 : gain, en vert", sh._delta_position(s, {"position": 9.5})
       == ("▲ gagne 1,2 place", sh.VERT), sh._delta_position(s, {"position": 9.5}))
_check("8,3 contre 6,0 : recul, en rouge", sh._delta_position(s, {"position": 6.0})[1]
       == sh.ROUGE, sh._delta_position(s, {"position": 6.0}))
_check("⚠️ 8,30 contre 8,26 : « stable » (le cas qui doit passer)",
       sh._delta_position(s, {"position": 8.26})[0] == "stable",
       sh._delta_position(s, {"position": 8.26}))
_check("clics 0 → 5 : « nouveau », pas une division par zéro",
       sh._fleche(sh._variation(5, 0))[0] == "nouveau", sh._fleche(sh._variation(5, 0)))

print("\n3. Une API muette n'est pas « zéro visite »")
_check("aucune ligne → None", sh.synthese([]) is None)

print("\n4. Semaine trouée signalée, semaine complète non")
troue = sh.synthese(_jours(fin, 70, trous={date(2026, 9, 22), date(2026, 9, 23)}))
_, blocs = sh.texte_et_blocs(troue, [], [], "https://x", None)
ctx = blocs[-1]["elements"][0]["text"]
_check("5 jours sur 7 → « SEMAINE INCOMPLÈTE » dans le message", "INCOMPLÈTE" in ctx, ctx)
_, blocs = sh.texte_et_blocs(syn, [], [], "https://x", None)
ctx = blocs[-1]["elements"][0]["text"]
_check("7 jours sur 7 → pas d'avertissement (le cas qui doit passer)",
       "INCOMPLÈTE" not in ctx, ctx)
_check("sans adresse d'image → aucun bloc image (Slack refuserait tout le message)",
       all(b["type"] != "image" for b in blocs), [b["type"] for b in blocs])
_, blocs = sh.texte_et_blocs(syn, [], [], "https://x", "https://b/embed/rapports/a.gif")
_check("avec adresse → un bloc image", sum(b["type"] == "image" for b in blocs) == 1)
_, blocs = sh.texte_et_blocs(syn, [], [], "https://x", None, "l'adresse publique répond 404")
_check("image absente : la RAISON est écrite dans le message",
       "répond 404" in blocs[-1]["elements"][0]["text"])

tops = [{"keys": ["premio cantacronache"], "clicks": 2, "impressions": 25, "position": 8.6},
        {"keys": ["eventi a biella"], "clicks": 1, "impressions": 1, "position": 2.0}]
_, blocs = sh.texte_et_blocs(syn, [], tops, "https://x", None)
txt = blocs[3]["text"]["text"]
_check("requêtes : leur part du total est écrite (3 clics sur 70)",
       "font 3 clic(s) sur 70" in txt, txt)
_, blocs = sh.texte_et_blocs(sh.synthese(_jours(fin, 70, clics=0)), [], [], "https://x", None)
_check("zéro clic : pas de « 0 sur 0 » absurde (le cas qui doit passer)",
       "sur 0" not in blocs[3]["text"]["text"], blocs[3]["text"]["text"])

print("\n5. Le GIF est une animation, et se range dans son dossier")
gif = sh.rendre_gif(syn, "sc-domain:exemple", n_images=12)
im = Image.open(io.BytesIO(gif))
_check("plusieurs images", im.n_frames > 1, im.n_frames)
im.seek(im.n_frames - 1)
_check("l'état final reste à l'écran (≥ 3 s)", im.info.get("duration", 0) >= 3000,
       im.info.get("duration"))
with tempfile.TemporaryDirectory() as tmp:
    sh.DOSSIER_PUBLIC = Path(tmp)
    ch = sh.publier_gif(gif, fin)
    _check("nom = seo-hebdo-<date>-<empreinte>.gif",
           ch.name.startswith("seo-hebdo-2026-09-25-") and len(ch.stem) == len(
               "seo-hebdo-2026-09-25-") + 8, ch.name)

    print("\n6. La route publique ne sert que ces GIF-là")
    try:
        import app.app as appmod
    except ModuleNotFoundError as exc:     # Flask absent : on le dit, on ne le tait pas
        _check("import de app.app", False, exc)
    else:
        appmod._DOSSIER_RAPPORTS = Path(tmp)
        (Path(tmp) / "secret.txt").write_text("x")
        c = appmod.app.test_client()
        r = c.get(f"/embed/rapports/{ch.name}")
        _check("le GIF du bilan : 200 image/gif, sans connexion",
               r.status_code == 200 and r.mimetype == "image/gif", (r.status_code, r.mimetype))
        for nom in ("secret.txt", "..%2F..%2F.env", "seo-hebdo-2026-09-25-zzzzzzzz.gif",
                    "seo-hebdo-2026-09-25-00000000.gif"):
            r = c.get(f"/embed/rapports/{nom}")
            _check(f"refusé : {nom}", r.status_code == 404, r.status_code)

print("\n7. --demo ne part jamais")
_check("--demo --apply → code 2", sh.main(["--demo", "--apply"]) == 2)

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
