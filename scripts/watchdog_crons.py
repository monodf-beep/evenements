#!/usr/bin/env python3
"""LE CHIEN DE GARDE — est-ce que les crons tournent encore ?

LE TROU QUE ÇA FERME, et c'était le plus sérieux de tous. Une vingtaine d'automatisations
font vivre ce site — le nombre exact est `len(ATTENDUS)`, et il n'est écrit nulle part
ailleurs exprès : la revue du 2026-08-04 a trouvé « quatorze » recopié dans trois fichiers
alors qu'il y en avait dix-neuf au crontab. Un chiffre dupliqué cesse d'être vrai le jour
où on en ajoute un, et personne ne le remarque. Le 2026-08-03, le constat était : **si le
scraper échoue demain matin, rien ne sonne**. `scripts/homepage_health.py` (13h) verrait la home se vider et
`scripts/site_audit.py` (14h) verrait le site diverger de la base — mais plusieurs jours
plus tard, et sur la CONSÉQUENCE, jamais sur la cause. Entre-temps le catalogue
vieillirait en silence.

C'est la forme la plus coûteuse du défaut que ce dépôt collectionne : un mécanisme qui
s'arrête sans que personne en soit averti. `utils/pipeline_status.record_run()` existait
depuis longtemps et enregistrait fidèlement chaque passage — mais RIEN ne lisait ce
journal pour s'inquiéter d'une absence. On savait ce qui avait tourné ; on ne savait pas
ce qui aurait DÛ tourner.

DEUX SIGNAUX, ET C'EST VOULU. Moins de la moitié des crons appellent `record_run()` :
instrumenter les autres aurait demandé de toucher autant de fichiers du chemin de
production pour un bénéfice de surveillance. Or ils écrivent tous un JOURNAL (`>> logs/x.log` dans le
crontab), et la date de dernière écriture d'un fichier est un signal universel, gratuit,
qui ne demande de modifier aucun script.
  1. `pipeline_runs` quand il existe — plus riche : on sait aussi si le run a ÉCHOUÉ ;
  2. la date du fichier de log sinon — on sait seulement qu'il a tourné, ce qui suffit
     à répondre à la question posée.
Un cron qui tourne mais dont le journal ne bouge pas est signalé quand même : c'est
l'anomalie, pas le contraire.

CE QU'IL NE FAIT PAS. Il ne relance rien, ne répare rien, n'écrit pas une ligne en base.
Un chien de garde qui essaie de réparer devient une deuxième source de panne — et
celle-là, personne ne la surveillerait.

Usage :
    .venv/bin/python scripts/watchdog_crons.py            # affiche l'état
    .venv/bin/python scripts/watchdog_crons.py --slack    # + alerte Slack si retard
"""
from __future__ import annotations
import argparse
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger

log = get_logger("watchdog-crons")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
LOGS = ROOT / "logs"

# (nom lisible, script, fichier de log, tolérance en heures)
#
# LA TOLÉRANCE, C'EST LA CADENCE + UNE MARGE. Un cron quotidien est en retard au bout de
# ~30 h : la marge absorbe un décalage d'horloge, un run qui déborde, un serveur redémarré
# pendant la nuit. Trop serré, l'alerte crie pour rien et on cesse de la lire ; trop large,
# on découvre la panne trois jours après. 30 h laisse passer UN oubli, jamais deux.
#
# La traduction a été absente de cette table tant que son cron restait commenté :
# surveiller un cron qu'on a éteint exprès produirait une alerte quotidienne parfaitement
# inutile, le genre qui apprend à ignorer les alertes. Elle y est entrée le 2026-08-04,
# LE JOUR de sa réactivation — la consigne écrite ici disait de le faire, elle a été suivie
# le jour même plutôt que remise à plus tard.
ATTENDUS = [
    ("Collecte des sources",      "scraper_events",  "scraper.log",          30),
    # Ajouté le 2026-08-11 : sans cette ligne, l'arrêt du contradicteur de dates serait
    # invisible — il ne parle que quand il trouve quelque chose, donc son silence est
    # AMBIGU par construction. C'est exactement le genre d'outil qu'il faut surveiller.
    ("Contradicteur de dates",    "verifier_dates",  "verifier_dates.log",   30),
    ("Contradicteur de lieux",    "verifier_lieux",  "verifier_lieux.log",   30),
    ("Relève Gmail",              "gmail_collect",   "gmail.log",            30),
    # Ajoutée le 04/09 avec le cron : le script existait depuis des semaines, écrit et
    # correct, mais jamais planifié (audit du 31/08 §2.2). Un silence ici ressemblerait
    # à « aucune fiche gmail: à rattraper aujourd'hui », son cas le plus fréquent.
    ("Rattrapage URL Gmail",      "gmail_relink",    "gmail_relink.log",     30),
    ("Dates",                     "dates",           "dates.log",            30),
    ("Dédoublonnage",             "dedupe",          "dedupe.log",           30),
    ("Lieux",                     "venues",          "venues.log",           30),
    # Ajoutée le 04/09 avec le cron, même motif que « Rattrapage URL Gmail » ci-dessus.
    ("Tri des séances de cinéma", "cleanup_cinema",  "cleanup_cinema.log",   30),
    # Ajoutés le 2026-08-11 AVEC leurs crons, comme la consigne au-dessus le demande.
    # Tous deux sont silencieux quand ils ne trouvent rien — c'est même leur cas le plus
    # fréquent — donc leur panne ressemble trait pour trait à leur fonctionnement normal.
    ("Dates depuis les mails",    "dates_depuis_mail", "dates_mail.log",     30),
    ("Moisson officielle",        "moisson_officielle", "moisson.log",       30),
    # L'agent quotidien se surveille comme la revue du dimanche : il peut légitimement
    # ne RIEN trouver à compléter, donc son silence ressemble à son fonctionnement normal.
    ("Agent quotidien",           "agent_quotidien", "agent_quotidien.log",  30),
    ("Évaluation",                "evaluator",       "evaluator.log",        30),
    ("Lot quotidien",             "daily_batch",     "daily_batch.log",      30),
    ("Référencement",             "seo_batch",       "seo_batch.log",        30),
    # Ajoutée le 04/09 avec le cron, même motif que « Rattrapage URL Gmail » plus haut :
    # écrit depuis des semaines, jamais planifié avant ce jour (audit du 31/08 §2.2).
    ("Photo paysage (images_wide)", "images_wide",   "images_wide.log",      30),
    # Ajouté le 2026-08-03 avec le cron lui-même : un rafraîchissement de classement qui
    # s'arrête ne casse rien de visible — la section continue d'afficher un tri, seulement
    # il vieillit. C'est précisément le genre de panne qu'on découvre trois semaines plus
    # tard en se demandant pourquoi un événement passé est encore en tête.
    ("Tri « Ça vaut le déplacement »", "refresh_deplacement", "refresh_deplacement.log", 30),
    # Le bilan de 11h se surveille lui aussi. On pourrait croire son absence évidente — pas
    # de message Slack le matin — mais c'est exactement le raisonnement qui a laissé passer
    # l'incident du 2026-07-31 : personne ne remarque un message qui NE vient PAS.
    ("Bilan du matin",             "bilan_matin",     "bilan_matin.log",      30),
    # Ajouté le 2026-08-28 : le cerveau lui-même a tourné SANS surveillance mécanique
    # pendant trois jours (26→28/08) — sa panne (crontab jamais installé après un
    # déploiement en échec) n'avait été vue que par la lecture prose du bilan de 11h,
    # pas par ce chien de garde. Exactement le défaut que cette liste existe pour
    # fermer : un silence qui ressemble à un jour sans rien à faire.
    ("Cerveau du matin",          "cerveau",         "cerveau.log",          30),
    # Ajoutée le 2026-08-04 avec la réactivation du cron. Elle était volontairement absente
    # tant que la ligne était commentée — surveiller l'absence d'un cron qui n'existe pas
    # aurait sonné tous les jours pour rien, et une alerte qui crie à tort finit par ne plus
    # être lue. Elle entre ici le jour même où la ligne repart, pas un jour plus tard : une
    # traduction qui s'arrête ne casse rien de visible, elle assèche seulement le vivier
    # italien — exactement la panne silencieuse que ce chien de garde existe pour attraper.
    ("Traduction FR/IT",           "translate_events", "translate.log",       30),
    ("Santé de la home",          "homepage_health", "homepage_health.log",  30),
    ("Relecture du site",         "site_audit",      "site_audit.log",       30),
    ("Sauvegarde de la base",     "backup_db",       "backup.log",           30),
    ("Grand ménage hebdomadaire", "weekly_audits",   "weekly_audits.log",   200),
    ("Récapitulatif hebdomadaire", "weekly_digest",  "weekly_digest.log",   200),
    # ⚠️ OUBLIÉE JUSQU'AU 2026-08-04, trouvée par la revue : le calibrage tourne le lundi à
    # 8h05 depuis la veille et n'était surveillé par rien. Personne ne l'aurait vu s'arrêter
    # — il est SILENCIEUX tant que l'écart reste sous le seuil, donc son absence ressemble
    # trait pour trait à son fonctionnement normal. C'est la panne la plus invisible du lot.
    ("Calibrage de l'évaluateur", "audit_calibrage", "calibrage.log",       200),
    # La revue du dimanche se surveille comme le bilan du matin, et pour la même raison :
    # elle peut légitimement ne RIEN trouver, donc son silence ressemble à son
    # fonctionnement normal. Sans cette ligne, une revue en panne serait indiscernable
    # d'une semaine sans défaut — et c'est précisément la semaine où l'on aimerait savoir.
    ("Revue du code",             "revue_hebdo",     "revue_hebdo.log",     200),
    # ── SEPT OUBLIS TROUVÉS PAR L'AUDIT DE SIMPLIFICATION DU 2026-08-31 ──────────────
    # Tous remplissent le critère d'inclusion écrit plus haut : ils sont SILENCIEUX quand
    # tout va bien, donc leur panne ressemble trait pour trait à leur fonctionnement
    # normal. Deux d'entre eux ont déjà coûté quelque chose :
    #
    #   • `auto_deploiement` est le SEUL mécanisme qui installe le crontab — s'il meurt,
    #     ce fichier cesse d'avoir le moindre effet. C'est arrivé du 26 au 28/08 : le cron
    #     du cerveau était committé, déployé, et jamais installé. Trois matins perdus,
    #     signalés chaque jour par le bilan sans que rien ne les comble ;
    #   • `site_health_check` s'annonçait « tourne chaque semaine en cron » dans son propre
    #     commentaire alors qu'il n'avait jamais été relancé — deux semaines de faux points
    #     affichés (crontab.txt, ligne de cette tâche).
    #
    # Et `slack_digest` est le cas le plus grave dans son genre : c'est le SEUL canal vers
    # Franck. S'il casse, l'absence de messages ressemble exactement à un jour calme.
    ("Déploiement autonome",      "auto_deploiement", "auto_deploiement.log", 30),
    ("Digest Slack",              "slack_digest",    "slack_digest.log",     30),
    ("Doublons publiés",          "verifier_doublons_publies", "verifier_doublons.log", 30),
    # ⚠️ `sante.log` et non `publier_sante.log` : le nom du journal suit la REDIRECTION du
    # crontab, pas le nom du script. Vérifié ligne à ligne — une entrée qui viserait le
    # mauvais fichier crierait tous les jours, et un chien de garde qui crie à tort finit
    # par ne plus être lu.
    ("Relevé d'état (WordPress)", "publier_sante",   "sante.log",            30),
    ("Santé des gabarits",        "gabarit_health",  "gabarit_health.log",   30),
    ("Search Console",            "gsc_report",      "gsc_report.log",      200),
    ("Santé du site (hebdo)",     "site_health_check", "site_health_check.log", 200),
]


def _dernier_run(script: str) -> tuple[datetime | None, dict | None]:
    """Dernier passage enregistré dans pipeline_runs (None si le script n'y écrit pas)."""
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        r = conn.execute("SELECT * FROM pipeline_runs WHERE script=? "
                         "ORDER BY ran_at DESC LIMIT 1", (script,)).fetchone()
        conn.close()
    except sqlite3.Error:
        return None, None
    if not r:
        return None, None
    try:
        return datetime.fromisoformat(r["ran_at"]), dict(r)
    except (ValueError, TypeError):
        return None, dict(r)


def _dernier_log(fichier: str) -> datetime | None:
    """Date de dernière écriture du journal — le signal universel."""
    p = LOGS / fichier
    try:
        return datetime.fromtimestamp(p.stat().st_mtime)
    except OSError:
        return None


def etat(maintenant: datetime | None = None) -> list[dict]:
    """Un dict par cron attendu, avec son retard et sa source d'information."""
    now = maintenant or datetime.now()
    out = []
    for libelle, script, fichier, tolerance in ATTENDUS:
        vu_run, detail = _dernier_run(script)
        vu_log = _dernier_log(fichier)
        # On retient le plus RÉCENT des deux : un script instrumenté qui a planté AVANT
        # son record_run() a quand même laissé une trace dans son journal, et c'est cette
        # trace-là qui dit la vérité sur « a-t-il tourné ».
        vu = max([d for d in (vu_run, vu_log) if d], default=None)
        source = ("aucune trace" if vu is None
                  else "journal + registre" if vu_run and vu_log
                  else "registre" if vu_run else "journal")
        retard_h = None if vu is None else (now - vu).total_seconds() / 3600
        out.append({
            "libelle": libelle, "script": script, "fichier": fichier, "vu": vu,
            "source": source, "retard_h": retard_h, "tolerance": tolerance,
            "en_retard": vu is None or retard_h > tolerance,
            # Un run enregistré EN ERREUR est une anomalie distincte du retard : le cron a
            # bien tourné, il a échoué. Les deux méritent d'être dits, jamais confondus.
            "erreurs": (detail or {}).get("error_count") or 0,
        })
    return out


def _action(l: dict) -> str:
    """La commande concrète à essayer — pas juste le constat.

    Ajouté le 2026-08-06 : Franck sur l'alerte « JAMAIS VUE » — « soit elle est
    compréhensible et je fais quelque chose, soit on l'enlève. » Le message d'origine
    disait CE qui n'allait pas (retard, tolérance) mais jamais QUOI FAIRE — un non-
    développeur qui relaie l'alerte n'a aucun moyen d'agir sans deviner. Les deux causes
    RÉELLEMENT rencontrées à ce jour : un cron ajouté à crontab.txt mais jamais réinstallé
    sur le VPS (JAMAIS VUE dès le premier passage attendu), ou un script qui plante avant
    même d'écrire son journal (EN RETARD après avoir déjà tourné). Le geste de diagnostic
    ne change pas d'un script à l'autre — lire le journal, vérifier le crontab installé —
    donc une seule formule couvre tous les cas plutôt qu'une commande par script qui
    suppose des options CLI qu'on ne connaît pas toutes ici."""
    fichier = l["fichier"]
    if l["vu"] is None:
        return (f"→ `crontab -l | grep {l['script']}` sur le VPS : ligne absente → "
               f"`crontab crontab.txt` (réinstalle depuis le fichier du dépôt) ; ligne "
               f"présente → `tail -50 logs/{fichier}` pour l'erreur.")
    return f"→ `tail -50 logs/{fichier}` sur le VPS pour la dernière erreur."


FUSEAU_ATTENDU = "Europe/Paris"


def fuseau() -> tuple[str, bool]:
    """(fuseau du serveur, est-il celui attendu) — et pourquoi c'est ici.

    QUESTION DE FRANCK, 2026-08-04 : « es-tu sûr que les agents travaillent aux heures que
    tu donnes, dans le fuseau Paris-Rome ? » La réponse honnête était : je le crois, mais
    personne ne l'a jamais vérifié. Le commentaire en tête de crontab.txt l'AFFIRME depuis
    toujours (« heure locale du serveur, timezone Europe/Paris ») sans qu'aucun script ne
    le contrôle — une affirmation qui se répète et que rien ne teste finit par devenir
    vraie dans les têtes seulement.

    CE QUE COÛTERAIT UN DÉCALAGE, et ce n'est pas cosmétique. C'est l'heure du serveur qui
    décide de ce qui est « passé » : la règle 5 tout entière repose dessus, et à la
    frontière de minuit deux heures d'écart font basculer les événements du jour du mauvais
    côté. Un serveur réinstallé en UTC décalerait toute la chaîne du matin sans que rien ne
    sonne — le chien de garde mesure des retards avec 30 h de tolérance, il ne verrait
    jamais deux heures.

    Paris et Rome partagent le même fuseau : le site est bilingue, sa journée ne l'est pas.
    """
    from datetime import timezone
    tz = (os.getenv("TZ") or "").strip()
    if not tz:
        try:  # /etc/timezone (Debian) puis le lien /etc/localtime
            tz = (Path("/etc/timezone").read_text().strip()
                  or str(Path("/etc/localtime").resolve()).split("zoneinfo/")[-1])
        except OSError:
            tz = str(Path("/etc/localtime").resolve()).split("zoneinfo/")[-1] \
                if Path("/etc/localtime").exists() else "?"
    # Le NOM peut mentir (variable posée sans effet) : l'OFFSET, lui, est ce que voit
    # réellement datetime.now(), donc ce qui gouverne les comparaisons de dates.
    offset = datetime.now(timezone.utc).astimezone().utcoffset()
    heures = int(offset.total_seconds() // 3600) if offset else 0

    # ⚠️ CORRIGÉ LE 2026-08-04, quelques heures après avoir été écrit — la revue a montré
    # que la première version testait `heures in (1, 2)`, c'est-à-dire une PLAGE d'offsets
    # et non le fuseau. Elle laissait donc passer, à une heure près, des fuseaux qui n'ont
    # rien à voir : `Africa/Lagos` (UTC+1 toute l'année) validait en août, `Etc/GMT-2` en
    # janvier. Le cas UTC, lui, était bien attrapé — d'où l'illusion que le contrôle
    # marchait.
    #
    # C'est exactement le défaut que ce contrôle existe pour dénoncer : une vérification
    # approximative vaut une affirmation, et une affirmation est ce qu'on cherchait à
    # remplacer. On compare donc à l'offset RÉEL d'Europe/Paris à cet instant — ce qui
    # suit automatiquement le passage heure d'hiver / heure d'été, sans table à maintenir.
    try:
        from zoneinfo import ZoneInfo
        ref = datetime.now(ZoneInfo(FUSEAU_ATTENDU)).utcoffset()
        attendu = ref is not None and offset == ref
    except Exception:               # zoneinfo absent ou base de fuseaux non installée
        # Repli explicite : on ne sait pas conclure, on ne prétend donc pas que tout va
        # bien. Mieux vaut une alerte à vérifier qu'un silence trompeur.
        attendu = False
        tz = f"{tz or '?'} (comparaison impossible : base de fuseaux absente)"
    return f"{tz or '?'} (UTC{heures:+d})", attendu


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Vérifie que les crons tournent encore.")
    p.add_argument("--slack", action="store_true",
                   help="Envoie une alerte Slack s'il y a du retard (silence sinon).")
    args = p.parse_args(argv)

    lignes = etat()
    retards = [l for l in lignes if l["en_retard"]]
    en_erreur = [l for l in lignes if not l["en_retard"] and l["erreurs"]]

    tz, tz_ok = fuseau()
    print(f"\n{len(lignes)} automatisation(s) surveillée(s) — {len(retards)} en retard, "
          f"{len(en_erreur)} en erreur au dernier passage.")
    print(f"Fuseau du serveur : {tz}"
          + ("" if tz_ok else f"  ⛔ ATTENDU {FUSEAU_ATTENDU} (UTC+1 ou +2)") + "\n")
    if not tz_ok:
        # Une seule ligne, mais elle vaut toutes les autres : si l'heure du serveur a
        # bougé, tous les horaires de ce fichier sont faux ET le calcul du « passé »
        # (règle 5) l'est aussi, à la frontière de minuit.
        print("  ⛔ TOUS LES HORAIRES DU CRONTAB SONT DÉCALÉS, et le calcul de ce qui est\n"
              "     « passé » avec eux. Corriger avec : timedatectl set-timezone "
              f"{FUSEAU_ATTENDU}\n")
    for l in sorted(lignes, key=lambda x: (not x["en_retard"], x["libelle"])):
        if l["vu"] is None:
            quand, marque = "JAMAIS VUE", "⛔"
        else:
            h = l["retard_h"]
            quand = (f"il y a {h:.0f} h" if h >= 1 else f"il y a {h*60:.0f} min")
            marque = "⛔" if l["en_retard"] else ("⚠️ " if l["erreurs"] else "✅")
        print(f"  {marque} {l['libelle']:<28} {quand:<16} "
              f"({l['source']}, tolérance {l['tolerance']} h)"
              + (f" · {l['erreurs']} erreur(s)" if l["erreurs"] else ""))
        if l["en_retard"]:
            print(f"      {_action(l)}")

    if not args.slack:
        print("\n(lecture seule. --slack pour alerter en cas de retard.)\n")
        return 1 if retards else 0

    # SILENCE QUAND TOUT VA BIEN. Une notification quotidienne « rien à signaler » finit
    # par ne plus être lue, et le jour où elle manque, personne ne le remarque — ce serait
    # reproduire le défaut qu'on répare. On ne parle que s'il y a quelque chose à dire.
    if not retards and not en_erreur and tz_ok:
        log.info("Toutes les automatisations sont à l'heure — pas d'alerte envoyée.")
        return 0

    from utils import slack
    msg = ["🐕 *Chien de garde des automatisations*"]
    if not tz_ok:
        # EN TÊTE, avant les retards : si l'heure du serveur a bougé, les retards affichés
        # en dessous sont eux-mêmes faux. Un décalage de fuseau n'est pas une anomalie de
        # plus dans la liste, c'est ce qui invalide la liste.
        msg.append(f"⛔ *FUSEAU HORAIRE* — le serveur est en `{tz}`, attendu "
                   f"`{FUSEAU_ATTENDU}`. Tous les horaires du crontab sont décalés, et le "
                   f"calcul de ce qui est « passé » avec eux.\n"
                   f"_Corriger : `timedatectl set-timezone {FUSEAU_ATTENDU}`_")
    for l in retards:
        quand = "JAMAIS VUE" if l["vu"] is None else f"dernier passage il y a {l['retard_h']:.0f} h"
        msg.append(f"⛔ *{l['libelle']}* — {quand} (tolérance {l['tolerance']} h)\n"
                   f"{_action(l)}")
    for l in en_erreur:
        msg.append(f"⚠️ *{l['libelle']}* — a tourné, mais {l['erreurs']} erreur(s)\n"
                   f"→ `tail -50 logs/{l['fichier']}` pour le détail.")
    msg.append("\n_Rien n'a été relancé : ce contrôle ne répare pas, il prévient. "
               "Colle ce message et le résultat des commandes ci-dessus à Claude si tu "
               "veux de l'aide pour la suite._")
    # urgent=True : ce message NE VA PAS dans la boîte du jour (utils/slack.py). Il dit
    # que la chaîne est cassée — le différer de quelques heures le viderait de son sens,
    # et un vidage est lui-même un cron : si le cron est mort, le digest ne part pas non
    # plus. Le chien de garde doit pouvoir aboyer même quand le reste s'est tu.
    slack.notify("\n".join(msg), urgent=True)
    log.warning("Alerte envoyée : %d en retard, %d en erreur.", len(retards), len(en_erreur))
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
