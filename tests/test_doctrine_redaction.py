#!/usr/bin/env python3
"""Fixture : la doctrine rédactionnelle servie aux agents (/doctrine, /doctrine.txt).

⚠️ AUCUN réseau, AUCUNE vraie note : de fausses notes Obsidian dans un dossier temporaire,
base jetable. On ne lit jamais `data/events.db`.

D'OÙ ÇA VIENT. Franck, 06/09/2026 : « c'est pénible quand je demande de la rédaction ici
sur Claude, je dois systématiquement expliquer que c'est via Obsidian, le ton, la
doctrine, le vocabulaire etc. » La réponse écrite jusqu'au 21/09 était « demande à Franck
de coller la sortie de deux commandes » — lui faire refaire à la main ce dont il se
plaignait. `utils/doctrine.py` assemble la doctrine et le back-office la sert.

CE QUE CETTE FIXTURE SURVEILLE — et surtout, les cas qui doivent PASSER, choisis près de
la frontière (CLAUDE.md, règle 3 : une fixture qui ne contient que des cas qui confirment
le design passe au vert sur un portillon faux) :

  1. doctrine complète depuis de fausses notes HORS dépôt → trois blocs, aucune alerte.
     ⚠️ C'EST LE CAS QUI DOIT PASSER de la détection « filet du dépôt » : sans lui, un
     détecteur qui crierait TOUJOURS « ce n'est pas Obsidian » serait indétectable ;
  2. la syntaxe Obsidian est nettoyée (wikilinks, tags, commentaires %% %%) ;
  3. ⚠️ LA FRONTIÈRE DU PLAFOND, l'incident du 05/09 rejoué : avec VOIX_MAX_CHARS juste
     SOUS la taille de la note, `load_voix()` (le pipeline) perd la fin, et la doctrine
     servie la garde ENTIÈRE. Le témoin est rouge d'un côté, vert de l'autre : c'est ce
     qui prouve que `voix_integrale()` sert à quelque chose ;
  4. vocabulaire injoignable → `interdits()` reste SILENCIEUX (choix de Franck du 05/09,
     « continuer sans filtre, silencieusement ») mais la doctrine, elle, CRIE : alerte
     dans le statut ET en tête du texte servi. Un rédacteur ne doit jamais croire qu'il a
     la liste alors qu'il ne l'a pas ;
  5. vault démonté (voix ET vocabulaire absents) → `vide`, et /doctrine.txt rend 503.
     Le 503 n'inclut pas la charte, qui est versionnée et répondrait toujours ;
  6. les deux clés d'entrée : session du back-office (Claude Chrome) et jeton (Cowork).
     Sans DOCTRINE_TOKEN réglé, la route est FERMÉE, jamais ouverte par défaut ;
  7. la page /doctrine se rend VRAIMENT (template exécuté), et porte l'adresse à jeton.

Et un contrôle de VOISINAGE, né d'une faute commise en écrivant ce fichier : `utils/
doctrine.py` existait déjà (la doctrine d'AFFICHAGE, lue par `scripts/panel_site.py`) et
je l'ai écrasée en créant le module. Le test 8 vérifie donc que les deux modules
coexistent — c'est le genre de collision qu'aucune relecture ne montre et qu'un import
attrape en une seconde.

Lancer : .venv/bin/python -m tests.test_doctrine_redaction
"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TMP = Path(tempfile.mkdtemp())
os.environ["DB_PATH"] = str(TMP / "fixture.db")          # base jetable, jamais data/

echecs = 0


def verifier(libelle, ok, detail=""):
    global echecs
    if ok:
        print(f"OK    {libelle}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}" + (f" — {detail}" if detail else ""))


# --------------------------------------------------------------------------- #
# De fausses notes Obsidian, HORS du dépôt (c'est le point : simuler le vault du VPS)
# --------------------------------------------------------------------------- #
VAULT = TMP / "vault"
VAULT.mkdir(parents=True)

NOTE_VOIX = VAULT / "Voix commune (synthese).md"
NOTE_VOIX.write_text(
    "---\ntags: [voix]\n---\n"
    "# Voix de la maison\n\n"
    "On écrit à hauteur de lecteur, jamais en communicant. #ton\n"
    "Voir [[Charte Agenda Sabauda|la charte]] pour la structure.\n"
    "%%note interne : ne pas publier ce paragraphe%%\n"
    "DERNIERE_PHRASE_DE_LA_NOTE : les Alpes ne sont pas une frontière.\n",
    encoding="utf-8")

NOTE_VOCAB = VAULT / "Vocabulaire interdit.md"
NOTE_VOCAB.write_text(
    "# Vocabulaire interdit\n\n"
    "| Terme interdit | Pourquoi | Alternative |\n"
    "| --- | --- | --- |\n"
    "| **« royaume de Sardaigne »** | anachronique | **les États de Savoie** "
    "*(IT : gli Stati sabaudi)* |\n"
    "| **« transfrontalier »** | jargon | Reformuler (dire les deux versants) |\n",
    encoding="utf-8")

os.environ["OBSIDIAN_VOIX_PATH"] = str(NOTE_VOIX)
os.environ["OBSIDIAN_VOCAB_PATH"] = str(NOTE_VOCAB)
os.environ["VOIX_MAX_CHARS"] = "8000"

from utils import doctrine_redaction as doctrine   # noqa: E402
from utils import voix as voixmod, vocabulaire as vocabmod   # noqa: E402

# --------------------------------------------------------------------------- #
# 1. Doctrine complète — et le cas qui doit PASSER de la détection « filet »
# --------------------------------------------------------------------------- #
st = doctrine.statut()
texte = doctrine.doctrine_texte(st)

verifier("trois blocs assemblés", len(st["blocs"]) == 3,
         [b["cle"] for b in st["blocs"]])
verifier("⚠️ CAS QUI DOIT PASSER : des notes hors dépôt ne déclenchent AUCUNE alerte",
         st["ok"] and not st["alertes"], st["alertes"])
verifier("la voix de la note est bien dans le texte servi",
         "hauteur de lecteur" in texte)
verifier("le vocabulaire interdit est là, avec son remplacement FR",
         "royaume de Sardaigne" in texte and "les États de Savoie" in texte)
verifier("le remplacement ITALIEN y est aussi (le site est bilingue)",
         "gli Stati sabaudi" in texte)
verifier("un conseil (alternative en prose) est rendu comme conseil, pas en mot à mot",
         "Reformuler" in texte)
verifier("la charte du dépôt est jointe (§ 7 dark patterns)",
         "dark pattern" in texte.lower())
verifier("l'en-tête dit la provenance de chaque bloc",
         str(NOTE_VOIX) in texte and str(NOTE_VOCAB) in texte)
verifier("l'en-tête date la lecture", st["lu_le"][:2] == "20" and st["lu_le"] in texte)

# 2. Syntaxe Obsidian nettoyée
verifier("wikilinks résolus en texte", "[[" not in texte and "la charte" in texte)
verifier("commentaires %% %% retirés", "ne pas publier ce paragraphe" not in texte)
verifier("frontmatter YAML retiré", "tags: [voix]" not in texte)

# --------------------------------------------------------------------------- #
# 3. ⚠️ LA FRONTIÈRE DU PLAFOND — l'incident du 05/09 rejoué dans les deux sens
# --------------------------------------------------------------------------- #
integrale = voixmod.voix_integrale()
# Plafond posé EXACTEMENT au début de la dernière phrase : un caractère de plus et le
# témoin ne serait plus rouge. C'est la frontière, pas une marge confortable.
os.environ["VOIX_MAX_CHARS"] = str(integrale.index("DERNIERE_PHRASE_DE_LA_NOTE"))
tronquee = voixmod.load_voix()
texte_court = doctrine.doctrine_texte()
verifier("le pipeline, lui, PERD la fin de la note (témoin rouge)",
         "DERNIERE_PHRASE_DE_LA_NOTE" not in tronquee, len(tronquee))
verifier("⚠️ mais la doctrine servie la garde ENTIÈRE (témoin vert)",
         "DERNIERE_PHRASE_DE_LA_NOTE" in texte_court)
verifier("et elle ANNONCE l'écart au lieu de le taire",
         "VOIX_MAX_CHARS" in texte_court and "de MOINS que toi" in texte_court)
os.environ["VOIX_MAX_CHARS"] = "8000"
verifier("⚠️ CAS QUI DOIT PASSER : plafond au-dessus de la note → aucun écart annoncé",
         "de MOINS que toi" not in doctrine.doctrine_texte())

# --------------------------------------------------------------------------- #
# 4. Vocabulaire injoignable : le pipeline se tait, la doctrine crie
# --------------------------------------------------------------------------- #
os.environ["OBSIDIAN_VOCAB_PATH"] = str(VAULT / "note-qui-n-existe-pas.md")
verifier("le pipeline reste SILENCIEUX (choix du 05/09)",
         vocabmod.interdits() == () and vocabmod.trouver("royaume de Sardaigne") == [])
st_muet = doctrine.statut()
texte_muet = doctrine.doctrine_texte(st_muet)
verifier("la doctrine, elle, le signale", not st_muet["ok"] and st_muet["alertes"])
verifier("et le signale EN TÊTE du texte, pas dans un log",
         "CE QUI MANQUE" in texte_muet.split("=" * 78)[0])
verifier("l'alerte nomme la note introuvable", "note-qui-n-existe-pas" in texte_muet)
verifier("mais la voix reste servie (une panne partielle n'efface pas le reste)",
         "hauteur de lecteur" in texte_muet)

# --------------------------------------------------------------------------- #
# 5. Filet du dépôt : la voix répond, mais ce n'est plus Obsidian
# --------------------------------------------------------------------------- #
os.environ["OBSIDIAN_VOIX_PATH"] = ""
os.environ["OBSIDIAN_VOCAB_PATH"] = str(NOTE_VOCAB)
st_filet = doctrine.statut()
bloc_voix = st_filet["blocs"][0]
verifier("une voix servie depuis le dépôt est signalée comme filet, pas comme Obsidian",
         "FILET VERSIONNÉ" in bloc_voix["alerte"], bloc_voix["alerte"][:80])
verifier("le filet reste du texte utile (le pipeline ne tombe pas)",
         bloc_voix["chars"] > 500, bloc_voix["chars"])

# --------------------------------------------------------------------------- #
# 6. Vault démonté : tout ce qui vit dans Obsidian manque → 'vide'
# --------------------------------------------------------------------------- #
os.environ["OBSIDIAN_VOIX_PATH"] = str(VAULT / "vault-demonte.md")
os.environ["OBSIDIAN_VOCAB_PATH"] = str(VAULT / "vault-demonte.md")
st_vide = doctrine.statut()
verifier("vault démonté → 'vide' (et donc 503 côté route)", st_vide["vide"])
verifier("la charte versionnée ne masque PAS la panne",
         st_vide["blocs"][2]["chars"] > 1000 and st_vide["vide"])

# --------------------------------------------------------------------------- #
# 7. Les routes : deux clés d'entrée, et fermée par défaut
# --------------------------------------------------------------------------- #
os.environ["OBSIDIAN_VOIX_PATH"] = str(NOTE_VOIX)
os.environ["OBSIDIAN_VOCAB_PATH"] = str(NOTE_VOCAB)
os.environ.pop("DOCTRINE_TOKEN", None)

from app.app import app                                   # noqa: E402

app.config["TESTING"] = True
client = app.test_client()

r = client.get("/doctrine.txt")
verifier("sans DOCTRINE_TOKEN réglé, la route est FERMÉE (503), jamais ouverte",
         r.status_code == 503, r.status_code)
verifier("et le refus EXPLIQUE quoi faire", b"DOCTRINE_TOKEN" in r.data)

os.environ["DOCTRINE_TOKEN"] = "jeton-de-fixture-0123456789"
verifier("jeton absent → 403", client.get("/doctrine.txt").status_code == 403)
verifier("mauvais jeton → 403",
         client.get("/doctrine.txt?token=presque-le-bon").status_code == 403)

r = client.get("/doctrine.txt?token=jeton-de-fixture-0123456789")
verifier("⚠️ CAS QUI DOIT PASSER : bon jeton en query → 200 + la doctrine",
         r.status_code == 200 and b"hauteur de lecteur" in r.data, r.status_code)
verifier("texte brut en UTF-8 (pas de HTML à décoder pour l'agent)",
         "text/plain" in r.headers["Content-Type"] and "utf-8" in r.headers["Content-Type"])
verifier("jamais mis en cache (une note éditée se voit tout de suite)",
         r.headers.get("Cache-Control") == "no-store")
verifier("non indexable (une adresse publique finit dans Google)",
         "noindex" in r.headers.get("X-Robots-Tag", ""))

r = client.get("/doctrine.txt",
               headers={"Authorization": "Bearer jeton-de-fixture-0123456789"})
verifier("⚠️ CAS QUI DOIT PASSER : bon jeton en en-tête Bearer → 200", r.status_code == 200)
r = client.get("/doctrine.txt",
               headers={"X-Doctrine-Token": "jeton-de-fixture-0123456789"})
verifier("⚠️ CAS QUI DOIT PASSER : bon jeton en en-tête X-Doctrine-Token → 200",
         r.status_code == 200)

with client.session_transaction() as sess:                 # Claude Chrome : le cookie
    sess["logged_in"] = True
verifier("⚠️ CAS QUI DOIT PASSER : session back-office → 200 SANS jeton",
         client.get("/doctrine.txt").status_code == 200)

r = client.get("/doctrine")
verifier("la page /doctrine se rend vraiment", r.status_code == 200, r.status_code)
html = r.data.decode("utf-8")
verifier("elle donne l'adresse à jeton, prête à coller",
         "/doctrine.txt?token=jeton-de-fixture-0123456789" in html)
verifier("elle montre le texte exact servi à l'agent", "hauteur de lecteur" in html)
verifier("le lien de nav existe dans base.html",
         '/doctrine"' in (ROOT / "app" / "templates" / "base.html").read_text(
             encoding="utf-8"))

# Vault démonté ET session valide : la page prévient, la route rend 503
os.environ["OBSIDIAN_VOIX_PATH"] = str(VAULT / "vault-demonte.md")
os.environ["OBSIDIAN_VOCAB_PATH"] = str(VAULT / "vault-demonte.md")
r = client.get("/doctrine.txt")
verifier("vault démonté → 503 même pour une session valide", r.status_code == 503,
         r.status_code)
verifier("et le corps dit ce qui manque (un code seul n'apprend rien)",
         b"CE QUI MANQUE" in r.data)

with client.session_transaction() as sess:
    sess.clear()
r = client.get("/doctrine")
verifier("la page reste derrière l'authentification", r.status_code == 302, r.status_code)

# --------------------------------------------------------------------------- #
# 8. Voisinage : les DEUX doctrines existent, celle-ci et celle de l'affichage
# --------------------------------------------------------------------------- #
from utils import doctrine as doctrine_affichage                    # noqa: E402

verifier("la doctrine d'AFFICHAGE est intacte (panel_site en dépend)",
         all(hasattr(doctrine_affichage, f) for f in
             ("load_doctrine", "doctrine_pour_prompt", "contredit_doctrine")))
verifier("et ce sont bien deux modules distincts",
         doctrine_affichage.__file__ != doctrine.__file__)

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
