#!/usr/bin/env python3
"""Fixture : le relevé de santé déposé sur WordPress (scripts.publier_sante).

D'OÙ ÇA VIENT — Franck, 2026-08-17 : « fais les deux accès. » Le relevé sert à ce qu'une
session Claude LISE l'état du serveur — files, crons, crédit API, révision déployée — sans
accès au serveur et sans qu'un secret soit dupliqué quelque part.

CE QUE LA FIXTURE PROTÈGE, dans l'ordre d'importance :

  1. **aucun secret ne sort.** Le relevé part vers une option WordPress lisible par tout
     compte capable d'éditer le site : une clé Anthropic ou un webhook qui s'y glisserait
     serait une fuite, pas un bug d'affichage ;
  2. **et pourtant le portillon ne refuse pas à tort.** Un relevé de coût API porte
     légitimement `tokens_utilises` : c'est le cas près de la frontière qui doit PASSER.
     `token` seul figurait dans la liste des motifs, il a été retiré pour cette raison —
     un faux refus bloque le relevé entier, donc rend le dispositif muet ;
  3. **la structure est stable** : quatre sections, parce que ce sont les quatre questions
     qui ont provoqué des allers-retours ce jour-là (est-ce déployé ? les crons tournent-ils ?
     où sont les files ? le crédit est-il revenu ?).

Lancer : .venv/bin/python -m tests.test_publier_sante
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.publier_sante import (  # noqa: E402
    MOTS_INTERDITS, contient_un_secret, releve,
)

echecs = 0


def verifier(libelle, ok, detail=""):
    global echecs
    if ok:
        print(f"OK    {libelle}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}" + (f" — {detail}" if detail else ""))


# ── 1. Ce qui doit être REFUSÉ ──────────────────────────────────────────────────
fuites = {
    "clé Anthropic": {"api": {"cle": "sk-ant-api03-XXXXXXXXXXXX"}},
    "webhook Slack": {"slack": {"url": "https://hooks.slack.com/services/T00/B00/xxxx"}},
    "jeton de bot Slack": {"slack": {"bot": "xoxb-123456-abcdef"}},
    "mot de passe d'application": {"wp": {"app_password": "abcd efgh ijkl"}},
    "champ nommé api_key": {"conf": {"api_key": ""}},
    "en-tête d'autorisation": {"http": {"Authorization": "Basic abcdef"}},
}
for quoi, objet in fuites.items():
    verifier(f"REFUSÉ : {quoi}", bool(contient_un_secret(objet)),
             f"{objet} est passé")

# ── 2. LE CAS QUI DOIT PASSER, choisi près de la frontière ──────────────────────
# Un relevé de coût API parle de « tokens ». Il ne doit PAS être refusé : un faux refus
# rend le relevé muet, et c'est exactement le défaut que CLAUDE.md reproche aux portillons.
legitimes = {
    "un relevé de coût API": {"api": {"tokens_utilises": 12345, "tokens_entree": 900}},
    "un relevé normal": {"git": {"head": "68c328f", "branche": "claude/quirky-davinci-jvqrnw"},
                         "files": {"goulot": "datation", "etages": [{"nom": "dates",
                                                                    "restants": 150}]},
                         "api": {"api_error": 12, "dernier_enrichissement": "2026-08-14"}},
    "un nom de script contenant « pass »": {"crons": {"passe_3": {"il_y_a_h": 2.0}}},
}
for quoi, objet in legitimes.items():
    faute = contient_un_secret(objet)
    verifier(f"ACCEPTÉ : {quoi}", not faute, f"refusé à tort sur « {faute} »")

# ── 3. La liste des motifs couvre les secrets RÉELS de ce dépôt ─────────────────
for motif in ("sk-ant", "hooks.slack.com", "xoxb-", "app_password", "api_key"):
    verifier(f"le motif « {motif} » est surveillé", motif in MOTS_INTERDITS)
verifier("« token » seul n'est PAS un motif (faux refus sur tokens_utilises)",
         "token" not in MOTS_INTERDITS)

# ── 4. La structure du relevé, et sa robustesse hors production ─────────────────
# Ici, ni base ni journal : le relevé doit quand même se composer et le DIRE, sans lever.
r = releve()
for section in ("date", "git", "crons", "files", "api"):
    verifier(f"le relevé porte la section « {section} »", section in r, list(r))
verifier("le relevé composé sur une machine sans base ne contient aucun secret",
         not contient_un_secret(r), contient_un_secret(r))
verifier("une base absente est DITE, pas passée sous silence",
         "erreur" in r["files"] or r["files"].get("etages") is not None, r["files"])

# ── 5. Les coûts : le champ ajouté pour répondre « et si on fait 10 fiches/jour ? » ──
from scripts.publier_sante import etat_couts  # noqa: E402

c = etat_couts()
verifier("la section coûts existe et ne lève pas, même sans base",
         isinstance(c, dict), str(type(c)))
if "erreur" not in c:
    verifier("elle rend le dénominateur avec le total (un coût par fiche sans fiches "
             "publiées ne veut rien dire)",
             "fiches_publiees" in c and "cout_usd_total" in c, str(sorted(c)))
    verifier("elle dit combien d'appels ont été MESURÉS — un total bas peut venir d'une "
             "instrumentation incomplète, pas d'une chaîne sobre",
             "appels_mesures" in c, str(sorted(c)))
    verifier("sans fiche publiée, le coût par fiche est None, jamais 0",
             c.get("fiches_publiees") or c.get("cout_usd_par_fiche") is None, str(c))
verifier("aucun secret ne s'est glissé dans les coûts", not contient_un_secret(c),
         contient_un_secret(c))

# ── 6. La provenance : code ou modèle ? La question de Franck du 18/08 ──────────
from scripts.publier_sante import (  # noqa: E402
    PROVENANCES_GRATUITES, PROVENANCES_PAYANTES, etat_provenance,
)

verifier("« page » (données structurées) compte comme GRATUIT",
         "page" in PROVENANCES_GRATUITES)
verifier("« llm » et « web » comptent comme PAYANTS",
         "llm" in PROVENANCES_PAYANTES and "web" in PROVENANCES_PAYANTES)
# Le piège : un champ NON RÉSOLU n'est pas une économie. Le compter avec les gratuits
# ferait passer un échec pour une réussite — le défaut de périmètre du 11/08.
for echec in ("llm_none", "nodate", "none", "(vide)"):
    verifier(f"« {echec} » n'est compté ni gratuit ni payant",
             echec not in PROVENANCES_GRATUITES and echec not in PROVENANCES_PAYANTES)
pv = etat_provenance()
verifier("la mesure ne lève pas, même sans base", isinstance(pv, dict), str(type(pv)))
verifier("aucun secret dans la provenance", not contient_un_secret(pv), contient_un_secret(pv))

# ── 7. Le diagnostic : un échec doit DIRE sa cause, pas la faire deviner ────────
# D'OÙ ÇA VIENT : le 2026-08-18, le dépôt a échoué sur un « ConnectTimeoutError » nu.
# J'en ai déduit un filtrage sur l'agent utilisateur — c'était faux, et il a fallu deux
# allers-retours avec Franck pour l'écarter. Un dispositif fait pour rendre autonome ne
# peut pas rendre un message qui ouvre une enquête.
#
# La fixture reste HORS RÉSEAU : elle vérifie la seule branche qui se teste sans dépendre
# d'Internet — un nom qui ne se résout pas — plus les deux invariants qui comptent partout.
from scripts.publier_sante import diagnostic  # noqa: E402

d = diagnostic("https://ceci-nexiste-pas.agendasabauda.invalid")
verifier("un nom introuvable ne fait pas lever le diagnostic", isinstance(d, str), str(type(d)))
verifier("il DÉSIGNE le DNS comme cause, au lieu de rendre un code d'erreur nu",
         "DNS" in d and "se résout pas" in d, d)
verifier("et il écarte explicitement WordPress — c'est ce qui économise l'aller-retour",
         "WordPress n'est pas en cause" in d, d)
verifier("le diagnostic ne transporte aucun secret", not contient_un_secret({"d": d}),
         contient_un_secret({"d": d}))

# ── 8. L'AFFICHAGE ne doit pas jeter le chiffre qu'on est venu chercher ────────
# D'OÙ ÇA VIENT — 2026-08-18, et c'est la faute la plus bête de la journée. La sortie
# terminal était `json.dumps(relevé)[:2000]` ; la provenance est la DERNIÈRE section du
# relevé. Elle a donc été calculée puis coupée trois fois de suite, en silence, et j'en ai
# conclu que le script ne la produisait pas. Trois allers-retours avec Franck pour un
# `[:2000]`. La fixture reproduit exactement ce cas : un relevé dont les sections amont
# sont ÉNORMES, et une provenance minuscule tout au bout.
import io  # noqa: E402
import contextlib  # noqa: E402

from scripts.publier_sante import afficher  # noqa: E402

faux = {
    "date": "2026-08-18T12:00:00",
    "git": {"head": "abc1234"},
    # Volontairement gigantesque : c'est ce qui poussait la provenance hors de la coupe.
    "files": {"etages": [{"nom": f"etage-{i}", "restants": i} for i in range(200)]},
    "api": {"api_error": 2},
    "provenance": {
        "date_source": {"detail": {"page": 300, "llm": 12},
                        "gratuit": 300, "payant": 12, "non_resolu": 5,
                        "part_gratuite_pct": 96},
    },
}
tampon = io.StringIO()
with contextlib.redirect_stdout(tampon):
    afficher(faux)
vu = tampon.getvalue()

verifier("la provenance survit à un relevé énorme (le défaut du [:2000])",
         "date_source" in vu and "300" in vu and "96" in vu, vu[-300:])
verifier("la part du code est LUE en clair, pas à reconstituer",
         "part du code" in vu, vu[:200])
verifier("l'abrègement de l'état est DIT, jamais silencieux",
         "abrégé" in vu, vu[-300:])
# Le cas près de la frontière qui doit PASSER : un relevé SANS provenance ne doit pas
# faire lever l'affichage ni mentir — il doit dire qu'il n'y a rien.
tampon = io.StringIO()
with contextlib.redirect_stdout(tampon):
    afficher({"date": "x", "git": {}, "provenance": {"erreur": "base absente"}})
vu2 = tampon.getvalue()
verifier("une provenance absente est DITE, pas passée sous silence",
         "indisponible" in vu2 and "base absente" in vu2, vu2)

# ── 9. Le classement des provenances : la faute qui INVERSAIT la conclusion ─────
# D'OÙ ÇA VIENT — 2026-08-18. La première liste des provenances était écrite de mémoire.
# Elle ignorait `parsed`, `manuel`, `page_corroboree` et `novenue` — quatre valeurs bien
# présentes en base. Faute d'y figurer, ces champs RÉSOLUS tombaient dans « non résolu »,
# et le relevé annonçait « 27 % venus du code » là où la mesure dit 59 %. Ce n'est pas une
# imprécision : c'est la conclusion à l'envers, sur le chiffre qui décide de brancher ou
# non une couche payante.
from scripts.publier_sante import classer  # noqa: E402

# LES CHIFFRES RÉELS DU VPS, relevés le 2026-08-18. Une fixture sur des valeurs inventées
# n'aurait pas vu la faute : c'est la base qui la contenait.
reel_dates = {"llm_none": 550, "none": 346, "parsed": 175, "nodate": 112, "llm": 91,
              "page": 39, "manuel": 36, "web": 23, "mail": 4, "page_corroboree": 2}
d = classer(reel_dates)
verifier("« parsed » (175 dates lues par le code) compte comme RÉSOLU, pas comme un échec",
         d["gratuit"] >= 175, str(d))
verifier("« manuel » est à part : ni code ni modèle — une saisie humaine ne se répétera pas",
         d["humain"] == 36, str(d))
verifier("la part du code sur les dates est bien 59 %, pas 27 %",
         d["part_gratuite_pct"] == 59, str(d["part_gratuite_pct"]))

reel_lieux = {"llm": 438, "(vide)": 403, "llm_none": 317, "none": 93, "source": 61,
              "novenue": 32, "page": 18, "web": 16}
v = classer(reel_lieux)
verifier("« novenue » est SANS OBJET, pas un travail restant (pas de lieu unique)",
         v["sans_objet"] == 32 and v["non_resolu"] == 813, str(v))
verifier("et le lieu reste massivement payé au modèle : 15 %", v["part_gratuite_pct"] == 15,
         str(v["part_gratuite_pct"]))

# L'INVARIANT QUI EMPÊCHE LA FAUTE DE REVENIR : rien ne se perd. Si demain un script écrit
# une valeur neuve, elle ne peut pas être avalée par une famille — elle doit ressortir.
for nom, detail in (("dates", reel_dates), ("lieux", reel_lieux),
                    ("valeur inédite", {"page": 10, "provenance_inventee_demain": 7})):
    c = classer(detail)
    total = (c["gratuit"] + c["payant"] + c["humain"] + c["non_resolu"]
             + c["sans_objet"] + sum(c["non_classe"].values()))
    verifier(f"tout le total est rendu ({nom}) — aucune valeur ne disparaît",
             total == sum(detail.values()), f"{total} ≠ {sum(detail.values())}")
verifier("une valeur inconnue est SIGNALÉE au lieu d'être comptée comme un échec",
         classer({"provenance_inventee_demain": 7})["non_classe"] == {"provenance_inventee_demain": 7},
         str(classer({"provenance_inventee_demain": 7})))
verifier("le périmètre voyage avec le nombre (règle 6)",
         "règle 5" in d["perimetre"] and "RÉSOLUS" in d["perimetre"], d["perimetre"])

# ── 10. Une panne de production ne doit pas se déguiser en incident d'outillage ──
# D'OÙ ÇA VIENT — 2026-08-18, 13h05 : le port 443 du site cesse de s'ouvrir DEPUIS LE VPS,
# alors que le déploiement joint GitHub en 443 à la même minute et que le site répond en
# deux secondes depuis ailleurs. Or toute la publication passe par ce port. Annoncer ça
# « relevé de santé non déposé » enterrerait l'arrêt de la publication sous un incident
# d'outillage — le défaut de périmètre du 11/08, transposé aux alertes.
from scripts.publier_sante import message_echec  # noqa: E402

injoignable = message_echec("ConnectTimeoutError…\n— diagnostic —\nTCP 443 : REFUSÉ/SANS "
                            "RÉPONSE après 10.0 s (TimeoutError)")
verifier("site injoignable → l'alerte NOMME l'arrêt de la publication, pas le relevé",
         "publication" in injoignable and "à l'arrêt" in injoignable, injoignable[:200])
verifier("elle donne le moyen de savoir si c'est revenu", "curl" in injoignable,
         injoignable[:200])

# LE CAS VOISIN QUI NE DOIT PAS ESCALADER : le site répond, seul le dépôt a raté. Sans ce
# cas, l'alerte crierait au feu à chaque hoquet et on cesserait de la lire.
ordinaire = message_echec("401 — identifiants WordPress refusés")
verifier("dépôt raté mais site debout → pas d'alarme de production",
         "publication" not in ordinaire and "Relevé de santé non déposé" in ordinaire,
         ordinaire[:200])

print("\nSUCCÈS — 0 problème(s)." if echecs == 0 else f"\n{echecs} problème(s).")
raise SystemExit(0 if echecs == 0 else 1)
