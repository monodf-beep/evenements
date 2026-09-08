#!/usr/bin/env python3
"""Fixture : le classement des sources par PROVINCE (utils.provinces).

Aucun réseau, aucune base — lit les fichiers réels du dépôt (config/provinces_*.json)
et vérifie la logique de résolution sur des cas connus.

D'OÙ ÇA VIENT — Franck, 2026-08-31 : « trier les sources par province, ça nous permet
de voir les manques. » Le piège du 06/08 s'applique ici aussi : un classement qui
DEVINE une province plutôt que de dire « je ne sais pas » fabrique un chiffre faux, pire
qu'un manque affiché comme tel.

Lancer : .venv/bin/python -m tests.test_provinces
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.provinces import province_de  # noqa: E402

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


print("──── la VILLE, quand elle existe, fait foi ────")
_check("Chambéry → Savoie (73)", province_de("Savoie", "Chambéry") == "Savoie")
_check("Annecy → Haute-Savoie (74)", province_de("Savoie", "Annecy") == "Haute-Savoie")
_check("Torino → province de Torino", province_de("Piemonte", "Torino") == "Torino")
_check("Cossato → province de Biella (pas Cossato elle-même)",
       province_de("Piemonte", "Cossato") == "Biella")
_check("Domodossola → Verbano-Cusio-Ossola",
       province_de("Piemonte", "Domodossola") == "Verbano-Cusio-Ossola")

print("\n──── à défaut, la commune est cherchée dans le NOM ────")
_check("« OT Coeur de Tarentaise (Moûtiers) » → Savoie",
       province_de("Savoie", "", "OT Coeur de Tarentaise (Moûtiers)") == "Savoie")
_check("« UTMB Mont-Blanc (Chamonix…) » → Haute-Savoie",
       province_de("Savoie", "", "UTMB Mont-Blanc (Chamonix, ultra-trail)")
       == "Haute-Savoie")
_check("« Comune di Cossato » → Biella",
       province_de("Piemonte", "", "Comune di Cossato") == "Biella")

print("\n──── ⚠️ LE CAS QUI DOIT ÉCHOUER — jamais deviner ────")
# Une source RÉGIONALE, sans ville dédiée : la classer de force fabriquerait un chiffre
# faux — c'est la faute que ce module existe pour empêcher, symétrique du piège du 06/08
# (un portillon qui refuse tout n'a rien prouvé ; un classeur qui range tout non plus).
_check("« Piemonte dal Vivo » (portail régional) → aucune province, PAS devinée",
       province_de("Piemonte", "", "Piemonte dal Vivo") is None)
_check("« Interreg ALCOTRA (transfrontalier) » → aucune, pas de commune dans le nom",
       province_de("Savoie", "", "Interreg ALCOTRA (transfrontalier)") is None)
_check("« Département de la Haute-Savoie » → Haute-Savoie EST dans le nom, donc reconnue "
       "(cas limite qui doit passer : le nom EST le nom du département lui-même)",
       province_de("Savoie", "", "Département de la Haute-Savoie") == "Haute-Savoie")

print("\n──── les deux territoires à UNE seule province ────")
_check("Vallée d'Aoste : toujours 'Vallée d'Aoste', sans registre à charger",
       province_de("Vallee-Aoste", "", "n'importe quoi") == "Vallée d'Aoste")
_check("Comté de Nice : toujours 'Comté de Nice'",
       province_de("Nice", "", "n'importe quoi") == "Comté de Nice")

print("\n──── un territoire hors périmètre ne casse rien ────")
_check("un territoire inconnu rend None plutôt que lever",
       province_de("Grasse", "Cannes", "") is None)

print("\n──── AUCUNE LISTE DE COMMUNES RECOPIÉE (audit du 31/08) ────")
# D'OÙ ÇA VIENT : la première version de utils/provinces.py, écrite le matin même,
# chargeait un `config/provinces_savoie.json` de 45 communes écrites À LA MAIN — alors
# que `config/communes_savoie_dept.json` en portait 552 avec leur département depuis le
# 24/08. Les deux avaient divergé le jour de leur création (dix entrées fantômes, dont
# des stations qui ne sont pas des communes). C'est l'incident « Venise des Alpes »
# rejoué en une heure. Cette fixture interdit qu'il se rejoue une troisième fois.
from utils.provinces import _TABLES  # noqa: E402
_check("le registre savoyard vient du fichier des 552, pas d'une liste à la main",
       len(_TABLES["savoie"]) > 500, len(_TABLES["savoie"]))
_check("   et le fichier écrit à la main a bien disparu",
       not (ROOT / "config" / "provinces_savoie.json").exists())
# ⚠️ CÔTÉ PIÉMONT, le fichier reste — et c'est justifié : `communes_italiennes.json`
# liste les communes SANS dire leur province, l'information est donc neuve, pas recopiée.
# Ce qu'il faut garder, c'est qu'aucune commune ne reçoive DEUX provinces (erreur franche,
# invisible à la lecture d'un JSON de 8 listes).
import json as _json  # noqa: E402
from utils.lieux import plie  # noqa: E402

_brut = _json.loads((ROOT / "config" / "provinces_piemonte.json").read_text(encoding="utf-8"))
_vues, _doublons = set(), []
for _prov, _communes in _brut.items():
    if _prov.startswith("_"):
        continue
    for _c in _communes:
        if plie(_c) in _vues:
            _doublons.append(_c)
        _vues.add(plie(_c))
_check("aucune commune piémontaise n'est rangée dans deux provinces à la fois",
       not _doublons, _doublons)
# MESURE, pas verdict : combien de communes du registre italien n'ont pas encore de
# province ? Le registre s'assume incomplet (`_piemont_incomplet`), donc un écart n'est
# pas une faute — mais il doit se VOIR, sinon il grandit en silence (règle 6).
_ital = _json.loads((ROOT / "config" / "communes_italiennes.json").read_text(encoding="utf-8"))
_connues = {plie(c) for c in _ital.get("piemont", [])}
_sans_province = sorted(_connues - set(_TABLES["piemonte"]))
print(f"      · {len(_connues - set(_sans_province))} des {len(_connues)} communes du "
      f"registre italien ont une province ; {len(_sans_province)} n'en ont pas encore"
      + (f" ({', '.join(_sans_province[:6])}…)" if _sans_province else ""))

print("\n──── l'audit tourne sur les VRAIES données et trouve un vrai manque ────")
# Contre-épreuve avec les fichiers réels du dépôt. Jusqu'au 31/08, Novara n'avait ni
# source RSS ni newsletter suivie — un manque resté invisible tant que le compteur
# restait agrégé au niveau « Piemonte ». Comblé le 31/08 (recherche exhaustive demandée
# par Franck : newsletter « Restiamo in contatto » du Comune di Novara, vérifiée en
# ligne). L'assertion porte maintenant sur ce qui reste réellement à 0 : aucune source
# RSS pour Novara (la newsletter ne remplace pas un flux à scraper).
import scripts.audit_sources_provinces as asp  # noqa: E402
rap = asp.rapport()
_check("Novara reste sans aucune source RSS (newsletter comblée le 31/08)",
       "| Novara | 0 | 1 |" in rap, rap[rap.find("## Piemonte"):rap.find("## Piemonte") + 900])
_check("le rapport dit le TOTAL de provinces connues (pas de zéro sans dénominateur)",
       "provinces connues" in rap)
_check("les sources régionales sans ville restent comptées, jamais silencieuses",
       "non classées" in rap)

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
