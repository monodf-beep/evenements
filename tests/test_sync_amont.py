#!/usr/bin/env python3
"""Fixture : l'audit des fichiers partagés avec observatoire-business-sabaudo.

Arbre jetable, jamais le dépôt réel : on fabrique des fichiers marqués, on écrit un
manifeste à la main, et on vérifie le verdict rendu.

CE QU'IL PROTÈGE. Une dizaine de fichiers sont des copies verbatim partagées avec
l'autre dépôt. La seule garde était un commentaire en tête de fichier, et elle n'a pas
tenu : `config/blocked_image_domains.txt` avait divergé, ce qui a laissé passer 41
fiches illustrées par des photos de presse. Le jour où l'audit a été écrit, TROIS
reports étaient en attente, dont un que personne n'avait remarqué.

Les deux cas les plus importants sont les silencieux : un fichier marqué que personne
n'a déclaré au manifeste (cas 4), et une entrée dont l'en-tête a disparu (cas 5). Ce
sont eux qui font qu'un nouveau fichier partagé, ajouté par une autre session, ne passe
pas inaperçu.

Lancer : .venv/bin/python -m tests.test_sync_amont
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import audit_sync_amont as audit  # noqa: E402

EN_TETE = "# SYNCED FROM observatoire-business-sabaudo — ne pas diverger\n"

faux = Path(tempfile.mkdtemp())
(faux / "config").mkdir()
(faux / "utils").mkdir()
audit.ROOT = faux
audit.MANIFESTE = faux / "config" / "sync_amont.json"


def ecrire(rel: str, corps: str, marque: bool = True) -> None:
    chemin = faux / rel
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text((EN_TETE if marque else "") + corps, encoding="utf-8")


ecrire("utils/aligne.py", "inchange = True\n")
ecrire("utils/modifie.py", "valeur = 2\n")            # bougera après enregistrement
ecrire("config/assume.txt", "propre a l Agenda\n")
ecrire("utils/orphelin.py", "nouveau = True\n")       # marqué, absent du manifeste
ecrire("utils/demarque.py", "plus_synchronise = True\n", marque=False)
# Prose citant le marqueur SANS le porter en ligne 1 : ne doit pas être ramassée.
(faux / "README.md").write_text(
    "# Projet\n\nLes fichiers portent l'en-tête `SYNCED FROM observatoire`.\n",
    encoding="utf-8")

manifeste = {"fichiers": {
    "utils/aligne.py":   {"statut": "porte", "porte_le": "2026-08-01",
                          "sha256_porte": audit.empreinte(faux / "utils/aligne.py")},
    "utils/modifie.py":  {"statut": "porte", "porte_le": "2026-08-01",
                          "sha256_porte": audit.empreinte(faux / "utils/modifie.py")},
    "config/assume.txt": {"statut": "divergence_assumee", "note": "voulu"},
    "utils/demarque.py": {"statut": "porte", "porte_le": "2026-08-01",
                          "sha256_porte": "peu importe"},
}}
audit.MANIFESTE.write_text(json.dumps(manifeste, ensure_ascii=False), encoding="utf-8")

# Le fichier bouge APRÈS avoir été déclaré porté : c'est le cas nominal.
ecrire("utils/modifie.py", "valeur = 3   # correctif local, pas encore porte\n")

echecs = 0


def verifier(libelle: str, condition: bool, detail: str = "") -> None:
    global echecs
    if condition:
        print(f"OK    {libelle}")
    else:
        echecs += 1
        print(f"ÉCHEC {libelle}" + (f"\n      {detail}" if detail else ""))


print("──── détection des fichiers marqués ────")
marques = audit.fichiers_marques()
verifier("un fichier sans en-tête est ignoré", "utils/demarque.py" not in marques)
verifier("une PROSE citant le marqueur est ignorée (README)", "README.md" not in marques,
         f"marqués = {marques}")
verifier("les quatre fichiers marqués sont vus",
         set(marques) == {"utils/aligne.py", "utils/modifie.py",
                          "config/assume.txt", "utils/orphelin.py"},
         f"marqués = {marques}")

print("\n──── verdicts ────")
alignes, a_porter, assumees, anomalies = audit.auditer()
noms = lambda lot: sorted(x[0] for x in lot)  # noqa: E731
verifier("inchangé depuis le report = aligné", noms(alignes) == ["utils/aligne.py"])
verifier("modifié depuis le report = À PORTER", noms(a_porter) == ["utils/modifie.py"])
verifier("divergence assumée = pas d'action", noms(assumees) == ["config/assume.txt"])
verifier("marqué mais hors manifeste = anomalie (le cas silencieux)",
         any(r == "utils/orphelin.py" for r, _ in anomalies), f"anomalies = {anomalies}")
verifier("au manifeste mais en-tête disparu = anomalie",
         any(r == "utils/demarque.py" for r, _ in anomalies), f"anomalies = {anomalies}")

print("\n──── sortie du programme ────")
verifier("dérive détectée → code de sortie 1", audit.main([]) == 1)

print("\n──── --record referme, mais ne touche pas une divergence assumée ────")
audit.enregistrer()
alignes2, a_porter2, assumees2, anomalies2 = audit.auditer()
verifier("plus rien à porter après --record", a_porter2 == [])
verifier("l'orphelin est entré au manifeste", anomalies2 == [],
         f"anomalies = {anomalies2}")
verifier("la divergence assumée le reste",
         noms(assumees2) == ["config/assume.txt"])
verifier("rien à porter → code de sortie 0", audit.main([]) == 0)

# Une fin de ligne Windows ne doit pas être prise pour une divergence : le dépôt est
# édité depuis les deux systèmes, et git convertit au passage.
print("\n──── indifférence aux fins de ligne ────")
(faux / "utils/aligne.py").write_bytes(
    (faux / "utils/aligne.py").read_text(encoding="utf-8").replace("\n", "\r\n")
    .encode("utf-8"))
_, a_porter3, _, _ = audit.auditer()
verifier("un CRLF n'est pas une divergence", noms(a_porter3) == [],
         f"à porter = {a_porter3}")

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
