#!/usr/bin/env python3
"""Fixture : les règles de CLAUDE.md, vérifiées MÉCANIQUEMENT sur tout le dépôt.

Franck, 2026-08-11 : « alors fais en sorte d'apprendre ».

Le constat qui rend ce fichier nécessaire est le mien : le 11/08, j'ai reproduit TROIS
défauts dont la règle était déjà écrite dans CLAUDE.md — le passé mélangé à l'à-venir, un
repli qui bouche la place, un garde-fou qui coupe ses propres cibles. Les trois fois,
Franck les a vus avant moi. La prose informe au début d'une session ; elle ne se rappelle
pas à moi au moment où j'écris un script, deux heures plus tard.

Un test, si. Il tourne, il échoue, et il refuse de passer au vert.

CE QUI EST VÉRIFIÉ ICI, ET SEULEMENT ÇA. On ne teste que ce qui est mécaniquement
décidable à la lecture du source. Deux règles s'y prêtent :

  RÈGLE 5 — un script qui LISTE ou DÉCIDE (audit_, trier_, repair_, purge_, reconcile_)
  et qui interroge events_raw doit filtrer sur la date de fin. Sans ça, il mélange le
  passé et l'à-venir, et « fabrique du travail au lieu d'en désigner ».

  RÈGLE 4 — un script qui ÉCRIT en base doit avoir un --apply (ou --execute), sinon il
  agit sans qu'on ait pu lire ce qu'il allait faire.

LES DÉROGATIONS SONT DANS CE FICHIER, AVEC LEUR RAISON. C'est le vrai mécanisme
d'apprentissage : ajouter un script au dépôt oblige soit à respecter la règle, soit à
écrire ici POURQUOI elle ne s'applique pas. Une dérogation sans phrase ne passe pas — la
liste est un dictionnaire, pas un ensemble.

⚠️ CE TEST NE PROUVE PAS QUE LE CODE EST JUSTE. Il attrape un oubli de structure, pas une
erreur de jugement : la purge qui voulait dépublier la Saint-Ours contenait bien un filtre
de date. Les défauts de jugement restent l'affaire de la revue adversariale du dimanche
(config/consigne_revue_hebdo.txt), et de Franck. Celui-ci ferme la porte la plus basse,
celle par laquelle je passe le plus souvent.

Lancer : .venv/bin/python -m tests.test_regles_du_depot
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"

# LANÇABLE DES DEUX FAÇONS. Sans cette ligne, le fichier ne passe qu'en `-m
# tests.test_regles_du_depot` : lancé par son chemin, l'import de
# `scripts.completer_verifie` (plus bas) échoue en ModuleNotFoundError, et le test rend 1
# alors que RIEN n'est en faute. Découvert le 2026-08-12 en passant toute la suite d'un
# coup — le seul rouge de la soirée était le test lui-même.
#
# Ce n'est pas cosmétique : un contrôle qui casse selon la manière dont on l'appelle finit
# par être rangé parmi les « celui-là échoue toujours », et c'est le jour où il a raison
# qu'on ne le croit pas.
sys.path.insert(0, str(ROOT))

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label}\n      {detail}")


# ── RÈGLE 5 : passé et à-venir ne se mélangent pas dans un rapport ──────────────
# Préfixes des scripts qui PRÉSENTENT quelque chose à un humain ou décident du sort
# d'une fiche. Un script du pipeline (dates.py, venues.py…) travaille sur toute la base,
# c'est normal : il RÉPARE, il ne rapporte pas.
_PREFIXES_RAPPORT = ("audit_", "trier_", "repair_", "purge_", "reconcile_", "diag_")

# Dérogations à la règle 5, avec la raison. Ajouter une ligne ici est un acte : il faut
# pouvoir écrire pourquoi le passé compte dans CE script précis.
_SANS_DATE_OK = {
    "audit_wp_ghosts.py":
        "compare la base au site : un post FANTÔME est justement une fiche passée "
        "restée en ligne (règle 2 — les listes REST excluent le passé).",
    "audit_coherence.py":
        "contrôle d'intégrité du schéma, pas une file de travail : une incohérence sur "
        "une fiche passée est quand même une incohérence.",
    "reconcile_wp_deleted.py":
        "horodate ce que WordPress a supprimé, y compris des fiches passées — c'est la "
        "trace du site, pas une liste de correctifs.",
    "purge_out_of_zone.py":
        "une commune hors périmètre l'est quelle que soit la date ; la charte ne se "
        "périme pas.",
    "audit_sources_bloquees.py":
        "juge des SOURCES, pas des événements : leur santé ne dépend pas d'une date.",
    "purge_radar.py":
        "le tier radar est sorti du catalogue en entier, sans considération de date.",
    "audit_non_events.py":
        "ce qui n'est pas un événement ne l'a jamais été, passé ou non.",
    "audit_excluded_events.py":
        "vérifie des exclusions déjà posées : leur date n'entre pas en compte.",
    "purge_sources_non_officielles.py":
        "compte le passé À PART et l'annonce (voir sa sortie) plutôt que de le filtrer, "
        "pour que le total reste comparable au dry-run précédent.",
    "audit_dedupe_damage.py":
        "DÉROGATION SOUS SURVEILLANCE : c'est le script que Franck a repris le "
        "2026-08-03 (« 94 cas dont le tiers datait du 10 juillet »). S'il reste ici "
        "sans filtre, c'est à corriger, pas à excuser.",
    "trier_sans_date.py":
        "ne sélectionne QUE des fiches sans date : le filtre de fin n'aurait aucun "
        "effet, et une fiche sans date n'est pas passée (règle 5, première précaution).",
}

# ── LE CLIQUET : la dette connue est tolérée, la dette NOUVELLE ne l'est pas ────
# Ces scripts existaient avant ce test et ne respectent pas la règle. Les mettre dans
# _SANS_DATE_OK aurait fait passer le test au vert en faisant disparaître le problème :
# c'est le « faux vert » qu'on reproche aux fixtures complaisantes. Ils sont donc listés
# ICI, comptés et affichés à chaque exécution, et le test échoue si la liste GRANDIT.
# L'effet visé est précis : le code que j'écris aujourd'hui doit respecter la règle,
# sans que le passé bloque tout.
_DETTES_DATE = {
    # Trouvées le 2026-08-11 par ce test, à sa première exécution. Chacune est une file
    # ou un rapport qui présente aujourd'hui du passé à un humain — donc du travail
    # fabriqué. Aucune n'est urgente, toutes sont à reprendre.
    "audit_annulations.py":
        "une annulation sur un événement terminé n'appelle plus aucun geste.",
    "audit_article_quality.py":
        "note la qualité d'articles passés qui ne seront jamais republiés.",
    "audit_bad_sources.py":
        "juge des fiches, pas des sources, malgré son nom — à filtrer ou à renommer.",
    "audit_couts.py":
        "SANS OBJET SANS DOUTE : compte des appels API, pas des fiches. À reclasser hors "
        "des préfixes de rapport plutôt qu'à filtrer.",
    "audit_radar_published.py":
        "liste les fiches radar en ligne : une fiche passée y figure encore.",
    "audit_translation_langs.py":
        "contrôle la langue de traductions passées, sans effet possible.",
    "audit_wp_ids_local_match.py":
        "apparie base et site ; à voir s'il relève plutôt de la règle 2 comme "
        "audit_wp_ghosts.",
    "diag_wp_orphans.py":
        "même famille que le précédent : diagnostic d'appariement, pas file de travail.",
    "repair_polluted_descriptions.py":
        "répare une pollution de description ; sur une fiche passée, la réparation ne "
        "sert personne. À filtrer.",
    "repair_translation.py": "répare des traductions, passé compris. À filtrer.",
    "repair_translation_cycles.py": "idem. À filtrer.",
}

print("──── RÈGLE 5 : un rapport ne mélange pas le passé et l'à-venir ────")
for f in sorted(SCRIPTS.glob("*.py")):
    if not f.name.startswith(_PREFIXES_RAPPORT):
        continue
    src = f.read_text(encoding="utf-8")
    if "events_raw" not in src:
        continue
    filtre = "date_event_end" in src or "devant_nous" in src or "_devant(" in src
    if f.name in _SANS_DATE_OK:
        _check(f"{f.name:42} dérogation motivée", bool(_SANS_DATE_OK[f.name].strip()))
        continue
    if f.name in _DETTES_DATE:
        print(f"DETTE {f.name:42} {_DETTES_DATE[f.name][:60]}")
        continue
    _check(f"{f.name:42} filtre sur la date de fin", filtre,
           "Aucun filtre de date : ce script mélangera le passé et l'à-venir. "
           "Ajouter le filtre, ou une dérogation MOTIVÉE dans _SANS_DATE_OK.")

# ── RÈGLE 4 : ce qui écrit en base doit se laisser lire avant d'agir ────────────
_ECRIT = re.compile(r"conn\.execute\(\s*f?[\"'](?:UPDATE|DELETE|INSERT)", re.I)

# Dérogations : les scripts du PIPELINE écrivent à chaque passage, c'est leur métier, et
# ils tournent sous cron sans humain devant. Le dry-run n'aurait aucun sens pour eux.
_SANS_APPLY_OK = {
    "dates.py", "venues.py", "visuals.py", "evaluator.py", "enrich.py", "dedupe.py",
    "scraper_events.py", "gmail_collect.py", "publish_batch_as.py", "seo_batch.py",
    "translate_events.py", "daily_batch.py", "publisher.py", "publisher_as.py",
    "autocomplete.py", "moisson_officielle.py", "sans_api.py", "weekly_audits.py",
    "refresh_deplacement.py", "conform_articles.py", "image_audit.py", "dates_web.py",
    "venues_web.py", "images_web.py", "images_wide.py", "organizer_handles.py",
    "refill_images_as.py", "link_translations_as.py", "cleanup_cinema.py",
    "panel_site.py", "gmail_relink.py", "backup_db.py", "site_audit.py",
    "homepage_health.py", "watchdog_crons.py", "weekly_digest.py", "audit_calibrage.py",
    "unlink_bad_translations.py", "slack_send.py", "repair_polluted_descriptions.py",
    # Migrations ponctuelles et outils de production, ajoutés le 2026-08-11 quand ce
    # test les a révélés : un backfill ne se rejoue pas, une newsletter et un kit presse
    # écrivent leur propre trace, audit_annulations n'écrit que sur --resolu explicite.
    "audit_annulations.py", "backfill_home_score.py", "backfill_permalinks_as.py",
    "ig_scheduler.py", "newsletter.py", "press_kits.py", "seed_seo_trial.py",
    "upgrade_category_banners_as.py",
}

print("\n──── RÈGLE 4 : ce qui écrit en base demande --apply ────")
manquants = []
for f in sorted(SCRIPTS.glob("*.py")):
    src = f.read_text(encoding="utf-8")
    if not _ECRIT.search(src) or f.name in _SANS_APPLY_OK:
        continue
    if "--apply" not in src and "--execute" not in src:
        manquants.append(f.name)
_check("aucun script d'écriture sans --apply ni dérogation", not manquants,
       "Ces scripts écrivent en base sans drapeau : " + ", ".join(manquants) +
       "\n      Ajouter --apply (dry-run par défaut), ou une dérogation dans "
       "_SANS_APPLY_OK si c'est un script de pipeline sous cron.")

# ── Le mécanisme lui-même : une dérogation doit porter une raison ───────────────
print("\n──── les dérogations sont motivées ────")
vides = [n for n, r in _SANS_DATE_OK.items() if len(r.strip()) < 30]
_check("chaque dérogation à la règle 5 porte une phrase", not vides, str(vides))
fantomes = [n for n in _SANS_DATE_OK if not (SCRIPTS / n).exists()]
_check("aucune dérogation ne vise un script disparu", not fantomes,
       "Ces dérogations n'ont plus d'objet : " + ", ".join(fantomes))
fantomes2 = [n for n in _SANS_APPLY_OK if not (SCRIPTS / n).exists()]
_check("aucune dérogation --apply ne vise un script disparu", not fantomes2,
       "À retirer : " + ", ".join(fantomes2))

# Le cliquet ne vaut que s'il se resserre : une dette réparée doit sortir de la liste,
# sinon elle protège indéfiniment un script devenu correct.
print("\n──── le cliquet se resserre ────")
reparees = [n for n in _DETTES_DATE
            if (SCRIPTS / n).exists()
            and ("date_event_end" in (SCRIPTS / n).read_text(encoding="utf-8"))]
_check("aucune dette déjà réparée ne traîne dans la liste", not reparees,
       "Ces scripts filtrent désormais : les retirer de _DETTES_DATE — " + ", ".join(reparees))
print(f"\n{len(_DETTES_DATE)} dette(s) connue(s), tolérée(s) mais comptée(s).")

print("\n──── aucune fiche écrite deux fois dans une table de valeurs ────")
# Erreur n°20 du 2026-08-11 : « 3279 : récurrent » a écrasé « 3279 : ville=Torino » écrit
# trois heures plus tôt. Dans un dictionnaire Python la dernière clé gagne, SANS ERREUR —
# le script tourne, écrit, annonce un succès, et une valeur a disparu.
#
# Le contrôle vit dans scripts/completer_verifie.py et s'exécute à l'IMPORT. On l'importe
# donc ici pour qu'il tourne avec la suite, et pas seulement quand quelqu'un lance le
# script : un garde-fou que personne ne déclenche n'est pas un garde-fou (règle 3).
try:
    import scripts.completer_verifie  # noqa: F401
    _check("scripts/completer_verifie : aucune fiche en double", True)
except SystemExit as exc:
    _check("scripts/completer_verifie : aucune fiche en double", False, str(exc))

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
