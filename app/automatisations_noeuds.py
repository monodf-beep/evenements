#!/usr/bin/env python3
"""LES FICHES DE LA CARTE DES AUTOMATISATIONS — le contenu, pas la mécanique.

Un nœud = un traitement, une décision, une file ou une sortie. Sa fiche est ce que le
panneau de droite affiche quand on clique dessus, sur `/process`.

POURQUOI CE FICHIER EST ÉCRIT À LA MAIN, et pas déduit des docstrings. Une docstring dit
ce que le script CROIT faire ; la fiche dit ce qu'il fait, seuil par seuil, avec les
désaccords quand il y en a (`cleanup_cinema` est plus sévère que le prompt de
l'évaluateur ; `venues` écrit un lieu vide là où `dates` a corrigé le même défaut). Ces
écarts-là ne se déduisent d'aucun texte : ils se lisent dans le code, une fois, et se
notent ici.

CE QUI N'EST PAS ÉCRIT ICI, ET POURQUOI. L'heure, la commande et le fichier de journal
ne sont PAS dans les fiches — ils sont LUS dans `crontab.txt` au moment de l'affichage
(voir `app/automatisations.py`). Un nœud déclare seulement `cron_cle`, un fragment de
commande qui l'identifie sans ambiguïté. Recopier l'horaire ici reproduirait exactement
le défaut de `_PIPELINE_SCHEDULE`, qui annonce encore un « pipeline de 6h05 » disparu du
crontab depuis des mois.

LE FILET. `tests/test_carte_automatisations.py` échoue si une ligne de `crontab.txt` n'a
pas son nœud. Un cron ajouté demain ne peut donc pas manquer sur la carte en silence —
c'est la règle « tout état terminal doit avoir quelqu'un qui le rouvre », appliquée à la
documentation elle-même.

Champs d'une fiche :
    id, label, icone, flux (onglet), kind, col/row (placement), resume,
    cron_cle (→ horaire lu dans le crontab), script (→ état lu par le chien de garde),
    detail = {fait, lit, ecrit, regles, decisions[{si, alors}], terminal{etat, rouvreur},
              slack, cout_ia, irreversible, notes, code, doc}
"""
from __future__ import annotations

ONGLETS = [
    {"id": "collecte", "titre": "Collecte", "icone": "📡",
     "resume": "De 8h00 à 8h52 — les flux RSS, les newsletters et les pages officielles "
               "entrent en base. Rien n'est encore trié : tout arrive au statut « pending »."},
    {"id": "tri", "titre": "Tri & datation", "icone": "🧮",
     "resume": "De 8h25 à 9h00 — dédoublonnage, dates, lieux, puis la note de l'évaluateur "
               "qui décide ce qui vivra. C'est ici que la plupart des fiches meurent."},
    {"id": "publication", "titre": "Rédaction & publication", "icone": "✍️",
     "resume": "9h30 — le lot du jour : l'article est rédigé, l'image choisie, la fiche "
               "poussée sur WordPress. C'est le seul chemin qui crée une page publique."},
    {"id": "editorial", "titre": "Traduction, SEO, images", "icone": "🌍",
     "resume": "De 10h30 à 12h00 — ce qui repasse APRÈS la publication : la version "
               "italienne, les métas de référencement, les visuels, le classement de la home."},
    {"id": "controles", "titre": "Contrôles & socle", "icone": "🛡️",
     "resume": "De 9h50 à 14h15 — personne ne relit le site à la main. Ces nœuds cherchent "
               "les écarts entre ce que la base croit et ce que WordPress montre, puis se "
               "taisent ou alertent."},
    {"id": "agents", "titre": "Les quatre agents", "icone": "🧠",
     "resume": "Quatre sessions Claude lancées en cron, aux droits très différents. Deux "
               "écrivent, deux ne peuvent pas — et c'est cette impuissance qui rend le "
               "contrôle honnête."},
    {"id": "hebdo", "titre": "Chaque semaine", "icone": "🗓️",
     "resume": "Dimanche et lundi — le grand ménage, la revue du code, la santé du site, "
               "la Search Console et le récapitulatif de la semaine."},
    {"id": "humain", "titre": "Ce que Franck déclenche", "icone": "👉",
     "resume": "Les boutons du backoffice. Tout ce qui est ici attend un clic : rien ne "
               "part tout seul."},
    {"id": "site", "titre": "Côté site (WordPress)", "icone": "🌐",
     "resume": "Le code qui vit DANS WordPress, pas dans ce dépôt. Il s'exécute à chaque "
               "page vue ou à chaque écriture — y compris pour refuser ce que le pipeline "
               "essaie d'écrire."},
]

# ══════════════════════════════════════════════════════════════════════════════
#  ONGLET 1 — COLLECTE
# ══════════════════════════════════════════════════════════════════════════════
_COLLECTE = [
    {"id": "src_rss", "label": "Flux RSS des institutions", "icone": "📰", "flux": "collecte",
     "kind": "declencheur", "col": 0, "row": 0, "sous_titre": "config/sources.txt",
     "resume": "La liste des sources, avec pour chacune son territoire et son niveau de confiance.",
     "detail": {
         "fait": ["Chaque ligne vaut `url;territoire;nom;tier[;lieu;ville]`.",
                  "Le « tier » décide qui gagne en cas de doublon : officielle (3), "
                  "institution (2), tourisme (1), radar (0).",
                  "Une source inconnue au registre est notée 1 par défaut, pas 0."],
         "lit": ["config/sources.txt", "config/broad_sources.txt (sources larges)",
                 "config/non_institutional_sources.txt"],
         "regles": ["Les colonnes `lieu` et `ville` sont lues par le chargeur mais PAS "
                    "écrites à l'insertion : elles servent au remplissage des lieux (8h50).",
                    "Une source « radar » sert à DÉTECTER un événement, jamais à le créditer "
                    "ni à le lier (charte)."],
         "cout_ia": "aucun",
         "code": ["config/sources.txt", "scripts/scraper_events.py"],
         "doc": ["docs/PIPELINE_COLLECTE.md"]}},

    {"id": "scraper", "label": "Collecte des sources", "icone": "🕸️", "flux": "collecte",
     "kind": "action", "col": 1, "row": 0, "cron_cle": "scripts/scraper_events.py",
     "script": "scraper_events",
     "resume": "Lit tous les flux RSS et insère les entrées nouvelles au statut « pending ».",
     "detail": {
         "fait": ["Télécharge chaque flux de `config/sources.txt` et lit ses entrées.",
                  "Insère les entrées dont l'adresse n'est pas déjà en base.",
                  "Repasse ensuite sur TOUT le stock « pending » pour rejeter ce qui est "
                  "hors périmètre ou hors sujet — y compris des fiches entrées les jours "
                  "précédents.",
                  "Porte aussi le schéma : c'est `init_db` qui crée la table et ajoute la "
                  "soixantaine de colonnes du pipeline."],
         "lit": ["Les flux RSS (réseau)", "config/sources.txt",
                 "config/perimeter_keywords.txt", "config/out_of_zone.txt",
                 "config/broad_sources.txt", "config/blocked_image_domains.txt",
                 "config/radar_cultural_exceptions.txt",
                 "events_raw.url_source (pour ne pas réinsérer)"],
         "ecrit": ["events_raw : titre, description, date brute, territoire, url_source, "
                   "url_image, source_name, organisateur, source_type",
                   "statut = « pending » (valeur par défaut de la colonne)",
                   "statut = « rejected » + llm_justification lors des deux nettoyages"],
         "regles": ["Dédoublonnage STRICT sur `url_source` : une adresse déjà vue est "
                    "ignorée, et la fiche existante n'est jamais mise à jour.",
                    "Le contenu d'une entrée est tronqué à 10 000 caractères.",
                    "Aucune limite sur le nombre d'entrées ni de flux par passage.",
                    "L'organisateur passe par un filtre (`utils.bylines`) : le champ "
                    "`author` d'un flux RSS est souvent le nom du journaliste, pas de "
                    "l'organisateur."],
         "decisions": [
             {"si": "le lien de l'entrée est vide", "alors": "ignorée, sans compteur"},
             {"si": "l'adresse est déjà en base", "alors": "ignorée — l'existante n'est pas mise à jour"},
             {"si": "source LARGE et le texte ne cite aucun lieu du périmètre",
              "alors": "jamais insérée (compteur « écartées »)"},
             {"si": "le texte correspond à `out_of_zone`", "alors": "jamais insérée"},
             {"si": "source « radar » sans marqueur culturel", "alors": "jamais insérée"},
             {"si": "l'image vient d'un domaine bloqué",
              "alors": "la fiche entre quand même, sans image"},
             {"si": "aucune source n'a pu être chargée", "alors": "le script sort en erreur (code 1)"}],
         "terminal": {
             "etat": "statut = « rejected » (nettoyage périmètre ou hors-sujet radar)",
             "rouvreur": "aucun code de ce script ne rouvre un rejet — il ne regarde que "
                         "les « pending ». La réouverture se fait à la main depuis "
                         "/triage, ou par `unreject_wp_online` quand la fiche est en ligne."},
         "cout_ia": "aucun — 100 % déterministe",
         "notes": ["Ce script n'a AUCUN dry-run : il écrit toujours."],
         "code": ["scripts/scraper_events.py"], "doc": ["docs/PIPELINE_COLLECTE.md"]}},

    {"id": "src_gmail", "label": "Newsletters Gmail", "icone": "📧", "flux": "collecte",
     "kind": "declencheur", "col": 0, "row": 1, "sous_titre": "label « Agenda »",
     "resume": "Les lettres d'information des lieux culturels, relevées par leur étiquette Gmail.",
     "detail": {
         "fait": ["Fenêtre : les 7 derniers jours (`GMAIL_LOOKBACK_DAYS`).",
                  "Étiquette lue : `GMAIL_LABEL`, « Agenda » par défaut."],
         "lit": ["Gmail API en lecture seule", "config/whitelist_gmail.txt (expéditeur ; territoire)"],
         "cout_ia": "aucun à ce stade",
         "code": ["config/whitelist_gmail.txt"], "doc": ["docs/PIPELINE_COLLECTE.md"]}},

    {"id": "ajouter_par_lien", "label": "Liens signalés", "icone": "🔗", "flux": "collecte",
     "kind": "action", "col": 1, "row": 5, "cron_cle": "scripts.ajouter_par_lien",
     "script": "ajouter_par_lien",
     "resume": "Fait entrer les événements que Franck signale par un lien, une fois leur page "
               "officielle trouvée en session.",
     "detail": {
         "fait": ["Lit config/liens_signales.tsv, rempli par une session Claude qui a lu le "
                  "lien signalé (post Instagram, affiche…) et trouvé la page de l'organisateur.",
                  "Lit la page officielle et l'insère en « pending », avec le nom de "
                  "l'événement donné dans la ligne."],
         "lit": ["config/liens_signales.tsv", "la page officielle (texte)"],
         "ecrit": ["events_raw : titre, description, territoire, url_source = url_officiel "
                   "(la page officielle), source_name « signalement : <lien> » — statut « pending »"],
         "regles": ["Un réseau social ou un titre de presse n'est jamais accepté comme page "
                    "officielle : la ligne arrête tout.",
                    "Aucun passe-droit éditorial : la fiche franchit l'évaluateur comme les "
                    "autres. Seule priorité : elle passe en tête de la file de rédaction."],
         "decisions": [
             {"si": "la page est déjà en base (même adresse, à http/www/barre près)",
              "alors": "rien d'inséré, la fiche existante est nommée"},
             {"si": "la page ne répond pas", "alors": "rien d'inséré, retentée le lendemain"}],
         "cout_ia": "aucun — 100 % déterministe",
         "notes": ["Suivi : `.venv/bin/python -m scripts.ajouter_par_lien --etat`."],
         "code": ["scripts/ajouter_par_lien.py", "config/liens_signales.tsv"]}},

    {"id": "gmail_collect", "label": "Relève Gmail", "icone": "📬", "flux": "collecte",
     "kind": "action", "col": 1, "row": 1, "cron_cle": "scripts/gmail_collect.py",
     "script": "gmail_collect",
     "resume": "Fait extraire par un modèle la liste des événements de chaque mail, et les insère.",
     "detail": {
         "fait": ["Relève les mails étiquetés, non encore vus.",
                  "Vérifie que l'expéditeur est officiel avant de dépenser quoi que ce soit.",
                  "Demande au modèle la liste des événements contenus dans le mail.",
                  "Conserve le corps texte (`mail_corps`) et le HTML brut (table "
                  "`gmail_html`) — c'est cette matière que rejoueront les rattrapages de 8h47 et 8h48."],
         "lit": ["Gmail API (liste puis contenu complet)", "config/whitelist_gmail.txt",
                 "config/sources.txt et non_institutional_sources.txt (test « source officielle »)",
                 "table gmail_seen (mails déjà traités)"],
         "ecrit": ["events_raw : titre, description, date, lieu, ville, territoire, "
                   "url_source, source_name, mail_corps — statut « pending »",
                   "table gmail_seen (le mail ne sera plus jamais relu)",
                   "table gmail_html (HTML brut, plafonné à 500 000 caractères)"],
         "regles": ["`url_image` est posée VIDE exprès : l'image viendra du rattrapage de 8h48.",
                    "Quand le modèle ne rend pas d'adresse, l'adresse devient un bouchon "
                    "`gmail:<id du mail>#<n>` — c'est ce bouchon que le rattrapage de 8h20 remplace.",
                    "Les liens de désabonnement et de traçage sont retirés du HTML AVANT "
                    "l'extraction, pour ne pas être pris pour l'adresse de l'événement.",
                    "Corps tronqué à 6 000 caractères, description à 2 000."],
         "decisions": [
             {"si": "le mail a déjà été vu", "alors": "aucun appel au modèle — il ne sera jamais relu"},
             {"si": "l'expéditeur n'est pas reconnu officiel",
              "alors": "le mail est marqué vu, aucune extraction, aucune fiche"},
             {"si": "l'adresse d'expédition est illisible",
              "alors": "le mail est ACCEPTÉ (le test renvoie vrai par défaut)"},
             {"si": "l'API du modèle tombe en panne",
              "alors": "arrêt net SANS marquer vu — les mails restants repassent demain"},
             {"si": "la réponse du modèle n'est pas du JSON lisible",
              "alors": "aucune fiche, mais le mail est marqué vu — la matière est perdue pour ce script"}],
         "terminal": {
             "etat": "la ligne dans `gmail_seen` — un mail traité ou refusé ne repasse plus jamais",
             "rouvreur": "aucun script ne supprime une ligne de `gmail_seen`. Seul "
                         "`gmail_relink` (8h20) revient sur la matière, en rechargeant le "
                         "mail par son identifiant."},
         "cout_ia": "1 appel par mail accepté — modèle d'extraction (claude-sonnet-5 par "
                    "défaut), 2 048 jetons de réponse. Aucun plafond de dépense dans ce script.",
         "notes": ["Pas de dry-run : le script écrit toujours."],
         "code": ["scripts/gmail_collect.py"], "doc": ["docs/PIPELINE_COLLECTE.md"]}},

    {"id": "gmail_relink", "label": "Rattrapage des adresses", "icone": "🔗", "flux": "collecte",
     "kind": "action", "col": 2, "row": 1, "cron_cle": "scripts.gmail_relink",
     "script": "gmail_relink",
     "resume": "Remplace le bouchon « gmail:… » par la vraie adresse de l'article, en rejouant l'extraction.",
     "detail": {
         "fait": ["Reprend les fiches dont l'adresse est encore un bouchon.",
                  "Regroupe par mail : un seul appel au modèle, quel que soit le nombre de fiches.",
                  "Apparie chaque fiche à une adresse par recouvrement de mots du titre.",
                  "Remet `date_source` à « none » : la fiche repart dans la file de datation."],
         "lit": ["events_raw où url_source commence par « gmail: » et statut hors "
                 "rejected/merged", "Gmail API (le mail rechargé par son identifiant)"],
         "ecrit": ["events_raw.url_source", "events_raw.date_source = « none »"],
         "regles": ["Seuil d'appariement : 2 mots communs, ramenés à 1 si le titre a "
                    "moins de trois mots significatifs.",
                    "En cas d'égalité de score, le PREMIER candidat gagne.",
                    "`--cap` compte les MAILS rejoués, pas les fiches."],
         "decisions": [
             {"si": "l'adresse trouvée est déjà prise par une autre fiche",
              "alors": "rien n'est écrit, la fiche garde son bouchon — c'est à `dedupe` de trancher"},
             {"si": "l'API tombe en panne",
              "alors": "arrêt de la boucle, mais les adresses DÉJÀ trouvées sont quand même appliquées"}],
         "cout_ia": "1 appel par mail rejoué — et le coût est payé MÊME en dry-run : "
                    "`--execute` ne change que l'écriture, pas les appels.",
         "code": ["scripts/gmail_relink.py"]}},

    {"id": "pending", "label": "File « pending »", "icone": "📥", "flux": "collecte",
     "kind": "etat", "garage_cle": "pending", "col": 3, "row": 0, "sous_titre": "en attente d'évaluation",
     "resume": "Tout ce qui est entré et n'a pas encore été noté. C'est la file que lit l'évaluateur de 9h00.",
     "detail": {
         "fait": ["Statut par défaut de toute fiche insérée, par le scraper comme par Gmail.",
                  "Lue par le dédoublonnage (8h30), la datation (8h25 et 8h45) et "
                  "l'évaluateur (9h00)."],
         "regles": ["Une fiche « pending » n'est visible nulle part sur le site.",
                    "L'évaluateur en traite 100 par passage : au-delà, le reste attend demain."],
         "terminal": {"etat": "non — c'est une file d'attente, pas un état terminal",
                      "rouvreur": "sans objet"},
         "cout_ia": "aucun"}},

    {"id": "src_pages", "label": "Pages officielles", "icone": "🌍", "flux": "collecte",
     "kind": "declencheur", "col": 0, "row": 2, "sous_titre": "le site de l'organisateur",
     "resume": "La page d'où vient la fiche, rouverte pour combler ce qui manque.",
     "detail": {
         "fait": ["Utilisée par la moisson de 8h52 et par l'agent de 9h15.",
                  "Lue en JSON-LD, microdata et og:image — jamais interprétée par un modèle "
                  "dans la moisson."],
         "cout_ia": "aucun"}},

    {"id": "moisson", "label": "Moisson officielle", "icone": "🌾", "flux": "collecte",
     "kind": "action", "col": 1, "row": 2, "cron_cle": "scripts.moisson_officielle",
     "script": "moisson_officielle",
     "resume": "Télécharge UNE fois la page officielle et en tire d'un coup date, lieu, ville, image et infos pratiques.",
     "detail": {
         "fait": ["Vise les fiches retenues (evaluated, published_cs, published_sub) à qui "
                  "il manque une date, un lieu, une ville, une image, ou les infos pratiques.",
                  "Ne remplit QUE les champs vides — sauf la date de fin, réécrite quand le "
                  "début vient d'être posé depuis la même page.",
                  "Suit les redirections des pisteurs (Google News et compagnie) et refuse "
                  "les destinations qui ne sont pas la page de l'événement."],
         "lit": ["La page officielle (JSON-LD, microdata, og:image)",
                 "config/blocked_image_domains.txt", "config/sources.txt"],
         "ecrit": ["date_event_start/end, lieu, ville, url_image, url_officiel, infos_pratiques",
                   "date_source = « page », venue_source = « page », image_source = « og »"],
         "regles": ["Priorité aux fiches les mieux notées : tri par `llm_score` décroissant.",
                    "Plafond du cron : 120 pages par passage (présélection de 3×120).",
                    "Une image n'est remplacée que si elle est vide, une bannière de repli, "
                    "ou issue d'une banque — JAMAIS si elle a été posée à la main.",
                    "Une image de contenu n'est retenue qu'à partir de 400 px de petit côté."],
         "decisions": [
             {"si": "la page part d'un pisteur et arrive sur le même hôte",
              "alors": "abandon — « pisteur sans destination », la fiche est comptée morte"},
             {"si": "la page d'arrivée ne parle pas du titre",
              "alors": "abandon — on est tombé sur une page d'accueil"},
             {"si": "la destination n'est pas une source officielle", "alors": "abandon"},
             {"si": "un champ est déjà rempli", "alors": "il n'est jamais écrasé"}],
         "terminal": {"etat": "AUCUN, et c'est délibéré — le script ne pose ni délai de "
                              "carence ni marqueur d'échec",
                      "rouvreur": "sans objet : la fiche se représente au passage suivant"},
         "cout_ia": "aucun — analyse syntaxique pure",
         "code": ["scripts/moisson_officielle.py"]}},

    {"id": "dates_mail", "label": "Dates depuis les mails", "icone": "🗓️", "flux": "collecte",
     "kind": "action", "col": 1, "row": 3, "cron_cle": "scripts.dates_depuis_mail",
     "script": "dates_depuis_mail",
     "resume": "Retrouve la date d'une fiche née d'une newsletter en relisant le corps du mail.",
     "detail": {
         "fait": ["Vise les fiches sans date dont l'adresse est encore un bouchon « gmail: ».",
                  "Relit le corps gardé en base, ou recharge le mail dans Gmail.",
                  "Cherche la date à proximité du titre, en se servant des titres VOISINS "
                  "comme bornes — c'est ce qui évite d'attribuer à un événement la date du suivant."],
         "lit": ["events_raw.mail_corps", "Gmail API en repli"],
         "ecrit": ["date_event_start, date_event_end, date_source = « mail », date_checked_at",
                   "recopie le corps du mail dans les fiches sœurs où il manquait"],
         "regles": ["Aucun modèle : la lecture de date est celle, déterministe, de `dates.py`.",
                    "`--cap` (100) compte les mails TÉLÉCHARGÉS ; atteindre le plafond "
                    "ARRÊTE la boucle — les fiches suivantes ne sont pas examinées du tout."],
         "decisions": [
             {"si": "aucune date sûre près du titre",
              "alors": "rien n'est écrit, la fiche repasse demain"},
             {"si": "le mail a été supprimé de Gmail", "alors": "comptée « sans corps », rien"}],
         "terminal": {"etat": "aucun en cas d'échec",
                      "rouvreur": "sans objet — elle se représente chaque matin"},
         "cout_ia": "aucun",
         "code": ["scripts/dates_depuis_mail.py"]}},

    {"id": "completer_mail", "label": "Lieux et images des mails", "icone": "📮", "flux": "collecte",
     "kind": "action", "col": 1, "row": 4, "cron_cle": "scripts.completer_depuis_mail",
     "script": "completer_depuis_mail",
     "resume": "Complète lieu, ville et image d'une fiche née d'un mail, en relisant le bloc de l'annonce.",
     "detail": {
         "fait": ["Relit le HTML du mail et isole le bloc de l'annonce.",
                  "Cherche un lieu connu du registre, puis sa commune.",
                  "Mesure les images candidates et retient la première assez grande."],
         "lit": ["table gmail_html", "events_raw.mail_corps",
                 "config/lieux_villes.json et les registres de communes",
                 "les lieux déjà connus des autres fiches de la base"],
         "ecrit": ["ville, lieu + venue_source = « mail »", "url_image + image_source = « mail »"],
         "regles": ["Image : petit côté ≥ 270 px, grand côté ≥ 480 px, au plus 3 candidates "
                    "mesurées par fiche.",
                    "Les GIF, les SVG, les logos et les habillages de gabarit sont refusés "
                    "sans même être mesurés.",
                    "Si la fiche est marquée « plusieurs lieux », lieu et ville ne sont plus demandés."],
         "decisions": [
             {"si": "l'annonce cite DEUX lieux connus, ou deux communes différentes",
              "alors": "rien n'est écrit — l'ambiguïté vaut mieux qu'une erreur"},
             {"si": "la fiche a déjà un lieu et que la ville trouvée le contredit",
              "alors": "tout est refusé, ni ville ni lieu"},
             {"si": "le plafond de mails téléchargés est atteint",
              "alors": "la fiche continue sans HTML — donc sans image"}],
         "terminal": {"etat": "aucun, explicitement",
                      "rouvreur": "sans objet. Ce qui change d'un jour à l'autre, c'est le "
                                  "REGISTRE des lieux, pas le mail."},
         "cout_ia": "aucun",
         "notes": ["En dry-run, les images sont quand même MESURÉES : des appels réseau "
                   "réels ont lieu, seule l'écriture est retenue."],
         "code": ["scripts/completer_depuis_mail.py"]}},

    {"id": "file_completer", "label": "File « À compléter »", "icone": "🛠️", "flux": "collecte",
     "kind": "etat", "col": 3, "row": 3, "sous_titre": "visible dans le backoffice",
     "resume": "Les fiches retenues à qui il manque une donnée obligatoire. Trois rattrapages la vident chaque matin.",
     "detail": {
         "fait": ["Une fiche y entre dès qu'il lui manque un des six champs obligatoires : "
                  "date, lieu, ville, territoire, catégorie, image.",
                  "Trois dérogations : un événement récurrent n'a pas besoin de date, une "
                  "fiche « plusieurs lieux » n'a besoin ni de lieu ni de ville, et une "
                  "bannière de territoire compte comme image (sans être une « vraie » image)."],
         "lit": ["utils/completeness.py — la définition unique de « fiche complète »"],
         "regles": ["Périmètre : seulement les statuts retenus (evaluated, published_cs, "
                    "published_sub). Une fiche rejetée n'y figure pas."],
         "cout_ia": "aucun",
         "code": ["utils/completeness.py", "scripts/lister_a_completer.py"]}},
]

# ══════════════════════════════════════════════════════════════════════════════
#  ONGLET 2 — TRI & DATATION
# ══════════════════════════════════════════════════════════════════════════════
_TRI = [
    {"id": "e_pending", "label": "File « pending »", "icone": "📥", "flux": "tri",
     "kind": "etat", "garage_cle": "pending", "col": 0, "row": 1, "sous_titre": "ce qui est entré ce matin",
     "resume": "Le stock brut. Cinq traitements le préparent avant que l'évaluateur ne tranche.",
     "detail": {"fait": ["Voir l'onglet Collecte pour savoir comment une fiche y entre."],
                "cout_ia": "aucun"}},

    {"id": "dates_1", "label": "Datation gratuite", "icone": "📅", "flux": "tri",
     "kind": "action", "etage_cle": "date", "col": 1, "row": 0, "cron_cle": "scripts/dates.py --no-fetch",
     "script": "dates",
     "resume": "Premier passage, sans réseau ni modèle : il lit les dates écrites dans le titre et la description.",
     "detail": {
         "fait": ["Lit la date dans le texte déjà en base (six motifs d'expression régulière).",
                  "Sert surtout à ARMER le dédoublonnage de 8h30 : sans date, la garde "
                  "« deux fiches distantes de plus de 14 jours ne se fusionnent pas » ne "
                  "protège pas les fiches scrapées le matin même.",
                  "Ré-arme les fiches dont la matière a changé depuis le dernier échec."],
         "lit": ["events_raw : titre, description, titre d'article"],
         "ecrit": ["date_event_start, date_event_end, date_source = « parsed » ou « none »",
                   "date_checked_at"],
         "regles": ["L'année est déduite : on garde l'année en cours tant que la date n'est "
                    "pas à plus de 60 jours dans le passé, sinon année suivante.",
                    "La date de fin n'est écrite QUE si la fiche n'en a pas déjà une.",
                    "Les traductions sont exclues de cette passe."],
         "decisions": [
             {"si": "le texte nomme un jour de la semaine qui contredit la date lue",
              "alors": "la fiche n'est PAS datée du tout — elle reste à compléter plutôt "
                       "que de porter une date fausse"},
             {"si": "rien n'est trouvé et la fiche n'a jamais été vue",
              "alors": "`date_source = none` et horodatage — elle entre dans la file de 8h45"}],
         "cout_ia": "aucun — les trois drapeaux `--no-fetch --no-llm --no-republish` "
                    "coupent le réseau, le modèle et la republication",
         "notes": ["C'est le MÊME script qu'à 8h45, lancé deux fois avec des droits "
                   "différents. Le chien de garde ne connaît qu'une entrée « dates » : "
                   "les deux passages partagent donc la même pastille d'état."],
         "code": ["scripts/dates.py"]}},

    {"id": "dedupe", "label": "Dédoublonnage", "icone": "🧬", "flux": "tri",
     "kind": "action", "col": 1, "row": 1, "cron_cle": "scripts/dedupe.py", "script": "dedupe",
     "resume": "Regroupe les fiches d'un même territoire qui racontent le même événement et élit une gagnante.",
     "detail": {
         "fait": ["Compare les fiches DEUX À DEUX, uniquement à l'intérieur d'un même territoire.",
                  "Élit une gagnante : d'abord le niveau de confiance de la source, puis la richesse.",
                  "Transfère à la gagnante les champs qui lui manquent et la description la "
                  "plus substantielle.",
                  "Range les perdantes en `statut = merged` avec un instantané de "
                  "défusionnage (`unmerge_data`)."],
         "lit": ["events_raw (pending, ou tout le stock retenu avec `--rescan`)",
                 "config/annulation_keywords.txt", "le registre des communes"],
         "ecrit": ["statut = « merged » + duplicate_of sur les perdantes",
                   "les champs manquants et la description de la gagnante",
                   "unmerge_data (les deux côtés)",
                   "les colonnes d'annulation, quand une annulation est suspectée"],
         "regles": ["Écart de dates supérieur à 14 jours : pas d'appariement. Une fiche non "
                    "datée ne bloque rien.",
                    "Richesse : +25 si image, +5 par champ rempli, +15 si adresse propre, "
                    "plus la longueur de la description.",
                    "Niveau de confiance : officielle 3, institution 2, tourisme 1, radar 0. "
                    "Une source inconnue vaut 1, pas 0.",
                    "Les appariements par simple COÏNCIDENCE de lieu et de date sont "
                    "seulement LISTÉS, jamais fusionnés sans le drapeau `--coincidence`."],
         "decisions": [
             {"si": "les deux titres portent une année à quatre chiffres et qu'elles diffèrent",
              "alors": "pas de fusion — deux éditions annuelles ne se confondent pas"},
             {"si": "les deux fiches nomment deux communes connues différentes",
              "alors": "pas de fusion"},
             {"si": "un membre du groupe porte un marqueur d'annulation dans son titre",
              "alors": "le groupe entier est retenu, AUCUNE fusion, et une alerte part une fois"},
             {"si": "une perdante est déjà en ligne sur WordPress",
              "alors": "elle n'est pas fusionnée — le doublon en ligne se traite ailleurs"}],
         "terminal": {
             "etat": "statut = « merged » + duplicate_of",
             "rouvreur": "`scripts/unmerge.py`, qui rejoue l'instantané `unmerge_data`. "
                         "Réversible, donc, mais jamais automatiquement."},
         "cout_ia": "aucun — 100 % déterministe",
         "slack": "🔴 « Annulation suspectée », une seule fois par fiche, à la première détection.",
         "notes": ["Le mode par défaut ÉCRIT : il n'y a pas de `--apply` ici, c'est "
                   "`--dry-run` qui simule."],
         "code": ["scripts/dedupe.py", "scripts/unmerge.py"], "doc": ["docs/DEDOUBLONNAGE.md"]}},

    {"id": "dates_2", "label": "Datation complète", "icone": "🗓️", "flux": "tri",
     "kind": "action", "etage_cle": "date", "garage_cle": "date_garage", "col": 1, "row": 2, "cron_cle": "scripts/dates.py >>", "script": "dates",
     "resume": "Le passage qui paie : il télécharge les pages, interroge un modèle, et republie les traductions réalignées.",
     "detail": {
         "fait": ["Passe 1 : relit le texte (comme à 8h25).",
                  "Passe 2 : télécharge jusqu'à 200 pages et y lit les données structurées "
                  "(JSON-LD, microdata, balise `time`). Ne lit JAMAIS le texte libre.",
                  "Passe 3 : jusqu'à 150 appels à un modèle rapide sur ce qui résiste.",
                  "Passe 4 : recopie les dates sur les traductions et republie jusqu'à 30 "
                  "fiches sur WordPress."],
         "lit": ["Les pages d'événement (réseau)", "events_raw"],
         "ecrit": ["date_event_start/end, date_source (page, page_corroboree, llm, llm_none, nodate)",
                   "date_tentatives, date_matiere (empreinte de la matière)",
                   "sur WordPress : republication des traductions réalignées"],
         "regles": ["Passe 2 : seulement les fiches encore devant nous (date de fin ≥ aujourd'hui).",
                    "Passe 3 : ce filtre « à venir » n'est PAS appliqué — la passe payante "
                    "peut donc dater un événement déjà terminé.",
                    "Corroboration : un début n'est retenu que si la fin lue correspond "
                    "exactement à celle qu'on connaît déjà. Deux débuts contradictoires "
                    "annulent tout.",
                    "Délai de carence de 7 jours entre deux tentatives, 3 tentatives au maximum."],
         "decisions": [
             {"si": "le modèle rend un mois entier (du 1er au dernier jour) alors que la "
                    "matière ne cite aucun quantième",
              "alors": "la réponse est JETÉE — c'est un mois inventé, pas une date lue"},
             {"si": "le plafond de l'API est atteint",
              "alors": "arrêt net, aucun verdict n'est écrit pour les fiches restantes"},
             {"si": "3 tentatives ont échoué sur la même matière",
              "alors": "la fiche est GARÉE jusqu'à ce que son texte change"}],
         "terminal": {
             "etat": "`date_source` à « nodate » ou « llm_none » avec 3 tentatives",
             "rouvreur": "automatique dès que l'empreinte du titre, de la description ou de "
                         "l'adresse change ; ou `--retry`, qui ignore délai et compteur."},
         "cout_ia": "jusqu'à 150 appels à un modèle rapide (claude-haiku-4-5 par défaut), "
                    "150 jetons de réponse, matière tronquée à 4 000 caractères.",
         "code": ["scripts/dates.py"]}},

    {"id": "venues", "label": "Lieux", "icone": "📍", "flux": "tri",
     "kind": "action", "etage_cle": "lieu", "garage_cle": "venue_garage", "col": 1, "row": 3, "cron_cle": "scripts/venues.py", "script": "venues",
     "resume": "Renseigne lieu et ville en trois passes : le lieu par défaut de la source, la page, puis un modèle.",
     "detail": {
         "fait": ["Passe 0 : applique le lieu déclaré pour la source dans `config/sources.txt`.",
                  "Passe 1 : lit la page (JSON-LD, microdata, puis les libellés « Lieu / "
                  "Luogo / Où » et le bloc qui les suit).",
                  "Passe 2 : jusqu'à 150 appels à un modèle rapide."],
         "lit": ["Les pages d'événement", "config/sources.txt (colonnes lieu et ville)",
                 "config/lieux_villes.json et les registres de communes"],
         "ecrit": ["lieu, ville, venue_source (source, page, novenue, llm, llm_none), venue_checked_at"],
         "regles": ["Périmètre : seulement les fiches encore devant nous.",
                    "La ville se déduit dans cet ordre : commune reconnue dans l'adresse, "
                    "puis dans le nom du lieu, puis le domaine de l'URL. Jamais le domaine seul.",
                    "Une valeur de lieu est refusée si elle fait moins de 3 ou plus de 120 "
                    "caractères, si elle ressemble à une rubrique, ou si elle contient une adresse web.",
                    "Toute valeur est tronquée à 160 caractères."],
         "decisions": [
             {"si": "la page ne donne rien",
              "alors": "`venue_source = novenue` — et le lieu est réécrit à VIDE, "
                       "inconditionnellement"}],
         "terminal": {
             "etat": "`venue_source` à « llm_none » ou « novenue »",
             "rouvreur": "automatique après 7 jours, sans plafond de tentatives (contrairement "
                         "à la datation). `--retry` force, sauf pour les fiches déjà tentées le jour même."},
         "cout_ia": "jusqu'à 150 appels à un modèle rapide, 150 jetons de réponse.",
         "notes": ["Écriture inconditionnelle du lieu vide quand la page échoue : c'est le "
                   "défaut que `dates.py` a corrigé chez lui (il n'écrit la date que s'il "
                   "en a trouvé une) et que `venues.py` porte encore. Sans conséquence "
                   "tant que la fiche n'avait pas de lieu, mais le motif est différent."],
         "code": ["scripts/venues.py", "utils/lieux.py"]}},

    {"id": "cleanup_cinema", "label": "Tri des séances de cinéma", "icone": "🎬", "flux": "tri",
     "kind": "action", "col": 1, "row": 4, "cron_cle": "scripts.cleanup_cinema",
     "script": "cleanup_cinema",
     "resume": "Ne garde du cinéma que les festivals et les projections en plein air. Tout le reste est rejeté et corbeillé.",
     "detail": {
         "fait": ["Reprend toutes les fiches de catégorie Cinéma, y compris celles qu'il a "
                  "lui-même rejetées aux passages précédents.",
                  "Fait classer chaque groupe FR/IT par un modèle, puis tranche lui-même.",
                  "Rejette et met à la corbeille WordPress ce qui n'est ni festival ni plein air.",
                  "Rétablit les fiches qu'il avait rejetées à tort — il est auto-correcteur."],
         "lit": ["events_raw où la catégorie est Cinéma ou Cinema"],
         "ecrit": ["statut = « rejected », llm_score = 0, justification marquée « nettoyage cinéma »",
                   "en rétablissement : statut published_sub ou evaluated, llm_score FORCÉ à 7",
                   "sur WordPress : mise à la corbeille par la route maison cs/v1/trash"],
         "regles": ["Un seul appel de modèle par groupe FR/IT, pas par fiche.",
                    "300 fiches par passage au maximum, une demi-seconde entre deux appels."],
         "decisions": [
             {"si": "le type rendu n'est pas exactement « festival » ou « plein air »",
              "alors": "retrait — c'est un test déterministe qui ÉCRASE la décision du modèle"},
             {"si": "la mise à la corbeille échoue",
              "alors": "le rejet est quand même appliqué en base — la fiche reste en ligne "
                       "et sera reprise au passage suivant"},
             {"si": "le modèle ne répond pas", "alors": "le groupe entier est laissé intact"}],
         "terminal": {
             "etat": "statut = « rejected » avec la mention « nettoyage cinéma »",
             "rouvreur": "LUI-MÊME : sa requête réintègre ses propres rejets à chaque passage "
                         "et les rétablit si le verdict change. C'est le seul état terminal "
                         "du dépôt qui porte son rouvreur dans le même fichier."},
         "cout_ia": "1 appel par groupe FR/IT, 300 jetons — et le coût est payé MÊME en "
                    "dry-run, la boucle de classement précédant le test de `--execute`.",
         "notes": ["Sa doctrine est PLUS SÉVÈRE que celle de l'évaluateur de 9h00, qui garde "
                   "rétrospectives, hommages et avant-premières événementielles. Les deux "
                   "coexistent : l'évaluateur les retient, celui-ci les retire le lendemain."],
         "code": ["scripts/cleanup_cinema.py"]}},

    {"id": "evaluator", "label": "Évaluation", "icone": "⚖️", "flux": "tri",
     "kind": "action", "etage_cle": "evalue", "col": 2, "row": 1, "cron_cle": "scripts/evaluator.py", "script": "evaluator",
     "resume": "Le tri principal : 100 fiches par jour, quatre refus gratuits puis une note de 0 à 10.",
     "detail": {
         "fait": ["Prend 100 fiches « pending » par passage.",
                  "Applique quatre refus DÉTERMINISTES avant de dépenser quoi que ce soit.",
                  "Fait noter les survivantes de 0 à 10 sur cinq critères.",
                  "Aiguille vers rejeté, mise en avant, ou catalogue."],
         "lit": ["events_raw (statut pending)", "config/excluded_event_keywords.txt",
                 "config/communes_comte_de_nice.json",
                 "les corrections de note de Franck, injectées dans le prompt"],
         "ecrit": ["llm_score, llm_categorie, llm_justification, llm_score_detail, llm_model",
                   "statut : rejected, evaluated ou published_sub", "territoire"],
         "regles": ["100 fiches par passage — le reste attend le lendemain.",
                    "Description tronquée à 800 caractères dans le prompt.",
                    "Les instructions sont mises en cache pour ne pas être refacturées à chaque fiche.",
                    "Le territoire rendu par le modèle ne remplace celui de la fiche que "
                    "s'il fait partie des quatre reconnus."],
         "decisions": [
             {"si": "le titre ou le texte correspond à une règle éditoriale du fichier "
                    "d'exclusions", "alors": "rejeté, score 0, sans aucun appel de modèle"},
             {"si": "la ville est une commune de l'arrondissement de Grasse",
              "alors": "rejeté — le Comté de Nice, c'est l'arrondissement de Nice. Une ville "
                       "VIDE ne tranche pas : le modèle reprend la main"},
             {"si": "la date de fin est strictement antérieure à aujourd'hui",
              "alors": "rejeté, « événement passé ». Sans date, on continue"},
             {"si": "le texte correspond à l'un des 14 motifs d'article de presse "
                    "(circulation, conseil municipal, enquête publique, incendie…)",
              "alors": "rejeté, « article de presse, pas un événement »"},
             {"si": "le modèle répond « hors périmètre », « pas un événement » ou "
                    "« public professionnel »", "alors": "rejeté, score forcé à 0"},
             {"si": "la note atteint 7", "alors": "statut « evaluated » — file de mise en avant"},
             {"si": "la note est inférieure à 7", "alors": "statut « published_sub » — catalogue"},
             {"si": "l'API tombe en panne",
              "alors": "le lot entier s'arrête, les fiches restent « pending »"}],
         "terminal": {
             "etat": "statut = « rejected »",
             "rouvreur": "aucun script ne remet un statut à « pending ». La réouverture se "
                         "fait à la main depuis /triage ou /events, ou par "
                         "`unreject_wp_online` quand la fiche est en ligne malgré son rejet."},
         "cout_ia": "1 appel par fiche ayant passé les quatre refus gratuits. Modèle du "
                    "profil réglé dans /reglages : haiku en profil éco, sonnet en qualité. "
                    "1 536 jetons de réponse.",
         "code": ["scripts/evaluator.py", "utils/eventness.py", "scripts/perimetre.py"],
         "doc": ["docs/PIPELINE_EVALUATION.md", "docs/CHARTE_EDITORIALE.md"]}},

    {"id": "note", "label": "La note sur 10", "icone": "🎯", "flux": "tri",
     "kind": "decision", "col": 3, "row": 1, "sous_titre": "cinq critères, seuil à 7",
     "resume": "Ce que mesure la note : l'IMPORTANCE de l'événement, pas sa profondeur culturelle.",
     "detail": {
         "fait": ["Notoriété du lieu (0 à 3) : emblématique très cité, reconnu, local modeste, "
                  "confidentiel — pondéré par la taille de la commune.",
                  "Moyens de l'organisateur (0 à 2) : institution ou grand festival, ville ou "
                  "association structurée, petit organisateur informel.",
                  "Édition et tradition (0 à 2) : rendez-vous historique, récurrent établi, "
                  "première ou ponctuel.",
                  "Rayonnement (0 à 2) : international ou transfrontalier, régional, local.",
                  "Spécificité territoriale (0 à 1) : identitaire, ou générique."],
         "regles": ["Total de 0 à 10. Seuil de mise en avant : 7.",
                    "Consigne explicite : ne pas exclure le grand public, le sport, la "
                    "gastronomie ni les marchés. Ne noter bas que le très confidentiel et le "
                    "purement commercial — en épargnant les salons et foires grand public.",
                    "Un méga-concert de tournée est admis, sans bonus de territoire.",
                    "Une séance de cinéma ordinaire reçoit la note 0 mais reste un événement : "
                    "elle va au catalogue, et c'est le tri de 8h55 qui la retire vraiment."],
         "decisions": [
             {"si": "note ≥ 7", "alors": "file « À valider » — candidate à la mise en avant"},
             {"si": "note < 7", "alors": "catalogue — publiée, mais pas mise en avant"}],
         "cout_ia": "compris dans l'appel de l'évaluateur",
         "notes": ["Le calibrage de cette grille est mesuré chaque lundi par "
                   "`audit_calibrage`, à partir des notes que Franck corrige à la main."],
         "code": ["scripts/evaluator.py", "utils/score_memory.py"]}},

    {"id": "e_rejected", "label": "Rejeté", "icone": "🚫", "flux": "tri",
     "kind": "etat", "col": 4, "row": 0, "sous_titre": "statut = rejected",
     "resume": "La sortie la plus fréquente. Aucun script ne rouvre un rejet automatiquement.",
     "detail": {
         "fait": ["Huit motifs mènent ici : règle éditoriale, arrondissement de Grasse, "
                  "événement passé, article de presse, réponse illisible du modèle, hors "
                  "périmètre, pas un événement, public professionnel.",
                  "Plus les rejets du tri cinéma et du nettoyage de périmètre du scraper."],
         "regles": ["Une fiche rejetée n'apparaît dans aucune file de travail et n'est jamais "
                    "republiée."],
         "terminal": {
             "etat": "statut = « rejected » — c'est le cul-de-sac principal du dépôt",
             "rouvreur": "À LA MAIN, depuis /triage ou /events. Deux exceptions "
                         "automatiques : `cleanup_cinema` rouvre ses propres rejets cinéma, "
                         "et `unreject_wp_online` rouvre une fiche rejetée qui est pourtant "
                         "en ligne sur le site."},
         "cout_ia": "aucun",
         "doc": ["docs/ETATS_TERMINAUX.md"]}},

    {"id": "e_evaluated", "label": "À valider (note ≥ 7)", "icone": "⭐", "flux": "tri",
     "kind": "etat", "col": 4, "row": 1, "sous_titre": "statut = evaluated",
     "resume": "Les fiches jugées importantes. Ce sont elles que le lot de 9h30 fait rédiger en priorité.",
     "detail": {"fait": ["Visible dans le backoffice sous « À valider »."],
                "cout_ia": "aucun"}},

    {"id": "e_published_sub", "label": "Catalogue (note < 7)", "icone": "📚", "flux": "tri",
     "kind": "etat", "col": 4, "row": 2, "sous_titre": "statut = published_sub",
     "resume": "Retenues mais pas mises en avant. Elles sont publiées et enrichies comme les autres.",
     "detail": {
         "regles": ["Le seuil de 7 départage la MISE EN AVANT, pas la publication : le "
                    "plancher de rédaction est à 1, et il n'y a aucun seuil de score pour "
                    "publier."],
         "cout_ia": "aucun"}},
]

# ══════════════════════════════════════════════════════════════════════════════
#  ONGLET 3 — RÉDACTION & PUBLICATION
# ══════════════════════════════════════════════════════════════════════════════
_PUBLICATION = [
    {"id": "e_retenues", "label": "Fiches retenues", "icone": "⭐", "flux": "publication",
     "kind": "etat", "col": 0, "row": 1, "sous_titre": "evaluated + published_sub",
     "resume": "Tout ce qui a survécu à l'évaluation. La rédaction les prend par note décroissante.",
     "detail": {"regles": ["Sélection : note ≥ 1, jamais enrichie (ou en erreur depuis plus "
                           "de 7 jours), non doublon, non traduction, avec une date de début, "
                           "et encore devant nous.",
                           "Dix fiches par passage, triées par note décroissante."],
                "cout_ia": "aucun"}},

    {"id": "daily_batch", "label": "Lot quotidien", "icone": "📦", "flux": "publication",
     "kind": "action", "garage_cle": "enrich_erreur", "col": 1, "row": 1, "cron_cle": "scripts/daily_batch.py",
     "script": "daily_batch",
     "resume": "Le chef d'orchestre de 9h30 : il fait rédiger, re-vérifie chaque fiche, puis ne fait publier que les complètes.",
     "detail": {
         "fait": ["Sélectionne dix fiches.",
                  "Appelle la rédaction dans le même processus.",
                  "Re-contrôle CHAQUE fiche après rédaction, avant de la laisser partir.",
                  "Appelle la publication sur les seules fiches complètes.",
                  "Re-contrôle une seconde fois APRÈS publication, et dit ce qui a vraiment atterri."],
         "lit": ["events_raw", "utils/completeness.py (les six champs obligatoires)"],
         "ecrit": ["rien lui-même — toutes les écritures viennent de la rédaction et de la publication",
                   "une ligne dans `pipeline_runs` (le registre des passages)"],
         "regles": ["Dix fiches par lot, et le plafond de la rédaction (dix aussi) s'applique "
                    "de toute façon."],
         "decisions": [
             {"si": "il manque un champ obligatoire après rédaction",
              "alors": "non publiée, comptée avec son motif"},
             {"si": "la date de fin est antérieure à aujourd'hui", "alors": "non publiée, « déjà passé »"},
             {"si": "la fiche vient d'une source RADAR sans page officielle résolue",
              "alors": "non publiée — le radar détecte, il ne crédite pas"},
             {"si": "après publication, aucun identifiant WordPress n'est revenu",
              "alors": "🔴 « NON PUBLIÉE » dans le bilan — le constat vient d'une relecture, "
                       "pas du code de retour"}],
         "cout_ia": "aucun en propre — tout le coût vient de la rédaction qu'il appelle.",
         "slack": "Un bilan par passage : publiées, incomplètes regroupées par cause, échecs.",
         "code": ["scripts/daily_batch.py"]}},

    {"id": "enrich", "label": "Rédaction de l'article", "icone": "✍️", "flux": "publication",
     "kind": "agent", "etage_cle": "redige", "garage_cle": "matiere_polluee", "col": 2, "row": 0,
     "resume": "Un agent rassemble la matière officielle, rédige l'article, puis le fait relire par un panel de lecteurs.",
     "detail": {
         "fait": ["Rassemble la matière : description propre, doublons, page officielle, dossiers de presse.",
                  "Fait rédiger l'article, en mode COURT (sans recherche web) ou LONG selon le réglage.",
                  "Fait relire par un panel de personas — habitants et visiteurs — un appel par persona.",
                  "Fait réécrire si le panel est sévère, puis relire à nouveau.",
                  "Calcule le score de mise en avant sur la home.",
                  "Vérifie les affiches par un appel de vision, au plus deux par fiche."],
         "lit": ["Les pages officielles (réseau)", "docs/personas/", "la voix éditoriale et "
                 "le vocabulaire interdit lus dans Obsidian", "config/non_institutional_sources.txt"],
         "ecrit": ["enrich_status, enrich_data (le JSON complet), article_title, article_md",
                   "home_score, time_start, url_image_portrait, url_image_wide, url_officiel",
                   "table `checks` : les points à vérifier signalés par la relecture"],
         "regles": ["Trois fiches en parallèle.",
                    "Mode court : 2 600 jetons, modèle rapide. Mode long : 24 000 jetons, "
                    "modèle de qualité, réservé aux notes ≥ 7.",
                    "Matière tronquée à 6 000 caractères par source, 20 000 pour le test de "
                    "pertinence d'une page.",
                    "Réécriture déclenchée si la note moyenne des lecteurs locaux tombe sous 3, "
                    "ou si la moitié d'entre eux signale du superflu."],
         "decisions": [
             {"si": "le texte correspond à un motif d'article de presse",
              "alors": "rejeté immédiatement, AUCUN appel de modèle"},
             {"si": "la description vient d'un agrégateur (Google News)",
              "alors": "`enrich_status = matiere_polluee` — la fiche sort de la file"},
             {"si": "les pages lues ne contiennent aucun mot du titre",
              "alors": "le verrou `url_officiel` est LEVÉ : on avait mémorisé la mauvaise page"},
             {"si": "l'accès à l'API est bloqué",
              "alors": "tout s'arrête et une alerte part — rien n'est tenté tant que "
                       "l'heure de rétablissement annoncée n'est pas passée"}],
         "terminal": {
             "etat": "`enrich_status` = enriched (jamais repris), error, api_error, ou matiere_polluee",
             "rouvreur": "« error » se rouvre seul après 7 jours ; « api_error » dès le run "
                         "suivant ; « enriched » ne se rouvre QUE par un appel explicite sur "
                         "l'identifiant ; « matiere_polluee » par "
                         "`scripts/repair_polluted_descriptions.py`, lancé chaque dimanche."},
         "cout_ia": "le poste le plus cher. Par fiche : 1 rédaction, puis 1 appel par persona "
                    "du panel, et en cas de révision une réécriture plus un panel entier. "
                    "Plus jusqu'à 2 appels de vision pour les affiches. La dépense se coupe "
                    "dans /reglages (mode court, long, ou désactivé).",
         "slack": "🚨 quand l'accès à l'API est bloqué.",
         "code": ["scripts/enrich.py", "utils/personas.py", "utils/voix.py"],
         "doc": ["docs/CHARTE_EDITORIALE.md"]}},

    {"id": "portes_pub", "label": "Les six portillons", "icone": "🚦", "flux": "publication",
     "kind": "decision", "col": 3, "row": 1, "sous_titre": "avant tout envoi sur le site",
     "resume": "Six refus successifs, appliqués dans cet ordre. Chacun retient la fiche sans rien écrire.",
     "detail": {
         "fait": ["Une sonde réseau d'abord : si le site ne répond pas, RIEN n'est tenté et "
                  "aucune fiche n'est marquée."],
         "decisions": [
             {"si": "1 — un champ obligatoire manque",
              "alors": "retenue (sauf `--allow-incomplete`, ou publication par identifiants)"},
             {"si": "2 — la fiche vient du radar sans page officielle résolue",
              "alors": "retenue — SAUF si elle est déjà en ligne, auquel cas on la republie"},
             {"si": "3 — le titre correspond à une règle éditoriale d'exclusion", "alors": "retenue"},
             {"si": "4 — l'article fait moins de 40 mots",
              "alors": "retenue, mais UNIQUEMENT s'il s'agit d'une création. Entre 40 et 250 "
                       "mots, simple compteur de surveillance"},
             {"si": "5 — la ville est dans l'arrondissement de Grasse", "alors": "retenue"},
             {"si": "6 — l'événement est trop loin dans le temps",
              "alors": "retenue. Une fenêtre n'existe QUE pour les temps forts nommés dans "
                       "`config/temps_forts.json` ; sans fenêtre, aucun plafond"},
             {"si": "garde-fou ultime : création sans date et non récurrente",
              "alors": "refusée, même avec des identifiants explicites"}],
         "regles": ["Publier par identifiants (`--ids`) lève le statut, la date, le score et "
                    "la complétude — mais PAS le radar, les exclusions, la substance, le "
                    "périmètre, la saison ni le garde-fou final."],
         "cout_ia": "aucun",
         "code": ["scripts/publish_batch_as.py", "utils/substance.py"]}},

    {"id": "publish", "label": "Envoi sur WordPress", "icone": "🚀", "flux": "publication",
     "kind": "action", "etage_cle": "publie", "col": 4, "row": 1,
     "resume": "Construit le contenu, téléverse les images, et poste sur la route maison cs/v1/event.",
     "detail": {
         "fait": ["Construit le corps : l'article, puis le lien vers la source officielle et "
                  "le lien vers le hub du territoire.",
                  "Téléverse l'image de carte, le grand visuel 16:9 et une copie non recadrée "
                  "pour les réseaux.",
                  "Pose une trentaine de métas `as_*` : score, mise en avant, tarif, horaire, "
                  "billetterie, crédit photo, lieu, ville.",
                  "Pose le slug SANS DATE, et seulement à la création."],
         "lit": ["events_raw (la ligne entière)"],
         "ecrit": ["wp_post_id_as, wp_permalink_as, wp_raw_image_url_as, published_as_date",
                   "wp_deleted_at remis à vide", "wp_gel_at / wp_gel_champs / wp_gel_motif "
                   "— une COPIE de ce que le site répond, jamais une décision locale"],
         "regles": ["L'adresse ne porte jamais de millésime : un événement annuel garde UNE "
                    "adresse d'édition en édition. Le titre, lui, garde son année.",
                    "`--skip-media` ne s'applique jamais à une création.",
                    "Une traduction hérite de l'image de son original seulement si celle-ci "
                    "est de meilleure provenance (manuelle 5, page 4, web 3, banque 2, bannière 1).",
                    "Les étiquettes sont envoyées VIDES exprès, pour nettoyer celles que "
                    "WordPress aurait gardées."],
         "decisions": [
             {"si": "la source est un pisteur (Google News et compagnie)",
              "alors": "aucune adresse de source n'est publiée — et sans source, pas de date "
                       "de vérification affichée"},
             {"si": "aucune date exploitable",
              "alors": "un avertissement est écrit et la fiche part QUAND MÊME — c'est le "
                       "portillon précédent qui refuse, pas celui-ci"}],
         "terminal": {
             "etat": "`wp_post_id_as` renseigné = « présente sur l'agenda ». Le statut "
                     "éditorial n'est PAS touché.",
             "rouvreur": "sans objet — mais attention : un identifiant en base ne prouve PAS "
                         "que la page est en ligne. Il survit à une mise à la corbeille. "
                         "Seule l'API REST, interrogée par NUMÉRO, sépare les trois états."},
         "cout_ia": "aucun",
         "code": ["scripts/publish_batch_as.py", "scripts/publisher_as.py"],
         "doc": ["docs/PIPELINE_DIFFUSION.md", "docs/CONTRAT_META_AS.md"]}},

    {"id": "wp_event", "label": "La page publique", "icone": "🌐", "flux": "publication",
     "kind": "sortie", "col": 5, "row": 1, "sous_titre": "agendasabauda.eu",
     "resume": "L'événement tel que le visiteur le voit. C'est la seule sortie visible du pipeline.",
     "detail": {
         "fait": ["Créée ou mise à jour par la route maison `cs/v1/event`.",
                  "La route est idempotente : elle retrouve une fiche par son titre et sa "
                  "date même si l'identifiant a été perdu en base."],
         "notes": ["Deux garde-fous du site peuvent la refuser après coup : le contrôle de "
                   "complétude la repasse en brouillon quinze minutes plus tard si la source "
                   "officielle manque ou si le corps est indigent ; et le gel du texte refuse "
                   "de réécrire ce qui a été retravaillé à la main. Voir l'onglet « Côté site »."],
         "cout_ia": "aucun",
         "code": ["deploy/wordpress/cs-publish.php"]}},

    {"id": "e_matiere_polluee", "label": "Matière polluée", "icone": "🕳️", "flux": "publication",
     "kind": "etat", "garage_cle": "matiere_polluee", "col": 3, "row": 3, "sous_titre": "enrich_status",
     "resume": "La description vient d'un agrégateur : impossible d'en tirer un article. La fiche sort de la file.",
     "detail": {
         "terminal": {
             "etat": "`enrich_status = matiere_polluee`",
             "rouvreur": "`scripts/repair_polluted_descriptions.py --apply --cap 25`, lancé "
                         "chaque dimanche par le grand ménage. Le nombre de fiches garées est "
                         "recompté et affiché à chaque passage de la rédaction."},
         "cout_ia": "aucun", "doc": ["docs/ETATS_TERMINAUX.md"]}},
]

# ══════════════════════════════════════════════════════════════════════════════
#  ONGLET 4 — TRADUCTION, SEO, IMAGES
# ══════════════════════════════════════════════════════════════════════════════
_EDITORIAL = [
    {"id": "e_enligne", "label": "Fiche en ligne", "icone": "🌐", "flux": "editorial",
     "kind": "etat", "col": 0, "row": 2, "sous_titre": "wp_post_id_as renseigné",
     "resume": "Tout ce qui suit ne concerne QUE les fiches déjà publiées. Rien ici ne crée une page.",
     "detail": {"cout_ia": "aucun"}},

    {"id": "seo_batch", "label": "Métas de référencement", "icone": "🔍", "flux": "editorial",
     "kind": "action", "etage_cle": "seo", "col": 1, "row": 0, "cron_cle": "scripts/seo_batch.py", "script": "seo_batch",
     "resume": "Fait écrire titre SEO, méta-description, réponse courte et questions fréquentes, puis les pousse sur le site.",
     "detail": {
         "fait": ["Génère les métas dans la langue de la fiche.",
                  "Les stocke en base, puis republie la fiche en TEXTE SEUL pour qu'elles arrivent.",
                  "Repêche les retardataires : les fiches dont les métas existent mais ne sont "
                  "jamais arrivées sur le site."],
         "lit": ["events_raw"],
         "ecrit": ["seo_title, seo_meta, seo_answer, seo_faq, seo_keyphrase, seo_slug, seo_tags, seo_at",
                   "seo_pushed_at — la preuve que la méta est ARRIVÉE"],
         "regles": ["25 fiches par passage, 20 retardataires.",
                    "Le seuil de note 7 ne s'applique QU'AUX fiches pas encore en ligne : "
                    "toute fiche publiée entre, quel que soit son score.",
                    "« Arrivée » est prouvée par une date de publication qui a BOUGÉ, jamais "
                    "par le code de retour de la republication.",
                    "Une fiche annulée est exclue."],
         "decisions": [
             {"si": "le texte de la fiche est GELÉ (retravaillé à la main sur le site)",
              "alors": "elle sort des DEUX files, génération et poussée. C'est la règle : le "
                       "dernier qui écrit est un humain"},
             {"si": "les métas produites ne sont pas dans la bonne langue",
              "alors": "rien n'est écrit, la fiche est comptée à part"},
             {"si": "la clé d'API manque",
              "alors": "aucune génération, mais les retardataires sont quand même repoussés — "
                       "eux ne coûtent rien"}],
         "terminal": {
             "etat": "`seo_at` posé sort de la file de génération ; `wp_gel_at` sort des deux files",
             "rouvreur": "`--redo` ou un appel par identifiants pour la génération. Pour le "
                         "gel : le dégel côté site, ou `scripts/gel_texte.py --degel <id> "
                         "--apply`. Le nombre de fiches gelées est affiché à chaque passage."},
         "cout_ia": "1 appel par fiche, modèle rapide, 1 024 jetons. Les retardataires et les "
                    "republications ne coûtent RIEN.",
         "slack": "Bilan du passage, dont le nombre de fiches gelées et de métas en mauvaise langue.",
         "code": ["scripts/seo_batch.py", "utils/seo.py"],
         "doc": ["docs/SEO_QUI_FAIT_QUOI.md"]}},

    {"id": "images_wide", "label": "Les deux orientations", "icone": "🖼️", "flux": "editorial",
     "kind": "action", "etage_cle": "image", "col": 1, "row": 1, "cron_cle": "scripts.images_wide", "script": "images_wide",
     "resume": "Complète le haut du panier avec l'affiche officielle en portrait ET en paysage.",
     "detail": {
         "fait": ["Relit la page officielle et y cherche jusqu'à douze images.",
                  "Fait vérifier chaque candidate par un appel de vision.",
                  "Écrit les deux orientations et republie la fiche."],
         "lit": ["Les pages officielles", "config/blocked_image_patterns.txt"],
         "ecrit": ["url_image_wide, url_image_portrait", "image_wide_at (délai de carence de 7 jours)"],
         "regles": ["15 fiches par passage, note minimale 7.",
                    "Petit côté d'au moins 700 px. Paysage à partir d'un rapport de 1,3 ; "
                    "portrait en dessous de 0,9.",
                    "Une même image ne peut servir qu'à DEUX fiches : au-delà, elle est "
                    "écartée avant même d'être téléchargée.",
                    "Jamais sur une fiche en bannière de repli ou sans source d'image identifiée."],
         "decisions": [
             {"si": "la candidate est en PORTRAIT",
              "alors": "son NOM DE FICHIER doit d'abord contenir un indice d'affiche "
                       "(affiche, locandina, manifesto, poster, flyer…) avant tout appel de "
                       "vision. Asymétrie voulue : le paysage n'a pas cette exigence"},
             {"si": "la page officielle ne donne rien",
              "alors": "un second étage de RECHERCHE WEB existe, mais il est ÉTEINT par "
                       "défaut — chiffré dans l'aide à 0,20 $ l'appel et 1,80 $ l'image trouvée"}],
         "terminal": {
             "etat": "les deux orientations remplies sortent la fiche définitivement de la sélection",
             "rouvreur": "aucun, et c'est l'intention. `--drop-portrait` / `--drop-wide` "
                         "effacent et republient, à la main. Le délai de carence de 7 jours, "
                         "lui, se lève tout seul."},
         "cout_ia": "1 appel de vision par candidate retenue, modèle rapide. Le second étage "
                    "de recherche web est éteint par défaut.",
         "code": ["scripts/images_wide.py", "utils/images.py"], "doc": ["docs/IMAGES.md"]}},

    {"id": "translate", "label": "Traduction FR ↔ IT", "icone": "🇮🇹", "flux": "editorial",
     "kind": "action", "etage_cle": "traduit", "garage_cle": "traduction_garage", "col": 1, "row": 2, "cron_cle": "scripts/translate_events.py",
     "script": "translate_events",
     "resume": "Crée la fiche jumelle dans l'autre langue, la publie, et lie les deux par Polylang.",
     "detail": {
         "fait": ["Traduit le titre, la description, puis l'article.",
                  "Crée une NOUVELLE fiche en base (31 colonnes recopiées) et la publie.",
                  "Lie les deux pages par la route Polylang du site."],
         "lit": ["events_raw (fiches en ligne, sans jumelle)",
                 "la voix éditoriale et le vocabulaire interdit"],
         "ecrit": ["une nouvelle ligne : translation_of, translated_lang, "
                   "url_source = « translated:<id>:<langue> »",
                   "sur l'original : translated_at",
                   "traduction_tentatives et traduction_matiere en cas de refus"],
         "regles": ["25 fiches par passage, trois en parallèle, note minimale 1 au cron.",
                    "La jumelle hérite du slug de l'original : même adresse, versant différent.",
                    "Trois refus sur une matière inchangée garent la fiche."],
         "decisions": [
             {"si": "la description de l'original est incohérente",
              "alors": "refus AVANT tout appel de modèle"},
             {"si": "le titre traduit semble être resté en français",
              "alors": "refus. C'est le portillon qui a coûté deux appels par jour sur la "
                       "fiche 3588, dont le titre était un NOM PROPRE — d'où l'exigence "
                       "d'écrire pourquoi le prochain passage donnerait un autre résultat"},
             {"si": "les paragraphes du corps sont dans la mauvaise langue",
              "alors": "l'article n'est pas traduit, la fiche n'est pas publiée"},
             {"si": "l'original n'est plus public sur WordPress", "alors": "refus"},
             {"si": "le lien Polylang échoue",
              "alors": "`translated_at` est POSÉ quand même — la jumelle existe. Le geste de "
                       "réparation est `repair_lien_polylang`, lancé chaque dimanche"}],
         "terminal": {
             "etat": "`translated_at` sur l'original ; ou 3 tentatives de traduction refusées",
             "rouvreur": "`translated_at` est effacé automatiquement si la jumelle a disparu ; "
                         "le compteur de refus est remis à zéro dès que l'empreinte de la "
                         "matière change."},
         "cout_ia": "2 appels par fiche (titre et description, puis article), modèle de "
                    "qualité. Un troisième seulement si le premier est tronqué.",
         "notes": ["Cette ligne du crontab enchaîne DEUX commandes : la traduction, puis le "
                   "rafraîchissement du classement de la home."],
         "code": ["scripts/translate_events.py"], "doc": ["docs/GO_NOGO_TRADUCTION.md"]}},

    {"id": "refresh_depl", "label": "Classement de la home", "icone": "🔃", "flux": "editorial",
     "kind": "action", "col": 1, "row": 3, "cron_cle": "scripts.refresh_deplacement",
     "script": "refresh_deplacement",
     "resume": "Recalcule chaque jour les deux valeurs datées qui rangent « Ça vaut le déplacement » et « À la une ».",
     "detail": {
         "fait": ["Recalcule les deux valeurs pour toutes les fiches en ligne.",
                  "Ne republie QUE celles dont au moins une valeur a changé.",
                  "Interroge WordPress par NUMÉRO avant de republier — jamais par liste, "
                  "car le calendrier masque les événements passés de ses collections."],
         "ecrit": ["deplacement_now_publie, une_now_publie — la trace de ce qui a réellement été envoyé",
                   "sur WordPress : les deux métas, en republication texte seul"],
         "regles": ["200 republications par passage au maximum.",
                    "Une valeur nulle devient une chaîne VIDE, jamais « 0 » : une fiche passée "
                    "doit SORTIR de la section, pas s'y ranger en dernier.",
                    "« Jamais publié » et « publié vide » sont distingués : le premier passage "
                    "est donc un rattrapage complet."],
         "decisions": [
             {"si": "la fiche a été publiée le jour même et qu'une valeur manque",
              "alors": "la valeur est enregistrée SANS republier — WordPress l'a déjà reçue ce matin"},
             {"si": "la page n'est pas publique",
              "alors": "aucune écriture, la fiche reste candidate au prochain passage"}],
         "cout_ia": "aucun",
         "code": ["scripts/refresh_deplacement.py"]}},

    {"id": "yoast", "label": "Notes Yoast", "icone": "📊", "flux": "editorial",
     "kind": "action", "col": 1, "row": 4, "cron_cle": "scripts.yoast_scores",
     "script": "yoast_scores",
     "resume": "Calcule les notes SEO et lisibilité hors navigateur, avec le vrai moteur de Yoast, et les réécrit dans WordPress.",
     "detail": {
         "fait": ["Demande à WordPress la liste des contenus modifiés depuis le dernier passage.",
                  "Lance le moteur Yoast en JavaScript, localement.",
                  "Réécrit les deux notes dans WordPress, par lots de 50.",
                  "Classe les critères qui coincent le plus souvent."],
         "lit": ["WordPress : la route maison `cs/v1/yoast-papers`"],
         "ecrit": ["sur WordPress : les deux métas de note, et la reconstruction de l'index. "
                   "RIEN en base locale."],
         "regles": ["300 contenus par passage au cron.",
                    "Le filtre incrémental vit CÔTÉ WORDPRESS : la date de notation est "
                    "comparée à la date de modification.",
                    "Un critère compte comme mauvais à partir d'une note de 5 ou moins.",
                    "Une fiche sans expression clé ne reçoit que la note de lisibilité — la "
                    "clé arrive avec les métas de 10h30."],
         "decisions": [
             {"si": "Node ou le paquet Yoast est absent",
              "alors": "une erreur franche, jamais un « 0 noté » — une panne est une panne"}],
         "cout_ia": "aucun appel de modèle : c'est un moteur JavaScript local.",
         "notes": ["Ajouté au chien de garde le 21/09, en même temps que « Lieux et images "
                   "des mails » : c'est la carte qui a montré que ni l'un ni l'autre "
                   "n'était surveillé, en croisant `crontab.txt` avec la liste `ATTENDUS`."],
         "code": ["scripts/yoast_scores.py", "deploy/wordpress/cs-yoast-scores.php"]}},

    {"id": "republi", "label": "Republication texte seul", "icone": "♻️", "flux": "editorial",
     "kind": "action", "col": 2, "row": 1,
     "resume": "Le chemin commun : la même route que la publication, mais sans retéléverser les images.",
     "detail": {
         "fait": ["Utilisé par les métas de référencement, le classement de la home et "
                  "l'annulation d'un événement.",
                  "Passe par les mêmes portillons que la publication."],
         "regles": ["Le drapeau qui saute les images n'est effectif que sur une fiche DÉJÀ en "
                    "ligne : une création téléverse toujours.",
                    "Une republication peut être INTERCEPTÉE par le gel du texte côté site : "
                    "les dates, le lieu, la catégorie et les métas passent, le texte non."],
         "cout_ia": "aucun",
         "code": ["scripts/publish_batch_as.py"]}},

    {"id": "cowork_seo", "label": "SEO final (Cowork)", "icone": "🧑‍💻", "flux": "editorial",
     "kind": "agent", "garage_cle": "gelees", "col": 3, "row": 0, "sous_titre": "lancé à la main",
     "resume": "Le dernier étage : une session Claude reprend à la main le référencement des "
               "meilleures fiches. Après elle, plus rien ne repasse.",
     "detail": {
         "fait": ["Reprend dans WordPress ce que le cron a posé à 10h30 : expression clé, "
                  "titre de référencement, méta-description, chapô, intertitres.",
                  "Ne traite que le haut du panier — le cron continue de s'occuper de tout le reste.",
                  "Déclare son passage dans le journal de la fiche, une ligne par article "
                  "(route `cs/v1/journal`, `qui: cowork`)."],
         "lit": ["les fiches publiées, dans WordPress",
                 "la doctrine éditoriale, relue à l'instant dans Obsidian (`/doctrine.txt`)"],
         "ecrit": ["directement dans WordPress : titre, corps, extrait, et les trois métas Yoast",
                   "RIEN en base SQLite — et c'est la limite du dispositif, voir « À savoir »"],
         "regles": ["**Le sens de marche est unique** : création de l'article en français et "
                    "en italien, puis le cron de référencement, puis Cowork. Jamais l'inverse. "
                    "Arbitrage de Franck du 21/09 : « si Cowork a travaillé le SEO, on ne doit "
                    "pas pouvoir revenir dessus avec le cron. »",
                    "Chaque étage peut écraser ce que le précédent a posé ; aucun ne peut "
                    "écraser le suivant.",
                    "Le gel n'a PAS besoin d'être demandé : modifier le texte suffit, "
                    "l'empreinte s'en charge. Le demander explicitement ne sert qu'à protéger "
                    "une fiche jugée bonne SANS y avoir touché."],
         "decisions": [
             {"si": "Cowork a modifié l'un des six champs éditoriaux",
              "alors": "la fiche est GELÉE au passage suivant du pipeline, et sort des deux "
                       "files de référencement"},
             {"si": "la fiche est ensuite annulée",
              "alors": "le titre est forcé malgré le gel — seule exception, parce que le "
                       "préfixe « ANNULÉ » est ce qu'un lecteur doit voir coûte que coûte"},
             {"si": "la reprise date d'AVANT l'installation du gel (21/09, 17h)",
              "alors": "aucune empreinte de référence n'existe : rien ne peut deviner qu'on "
                       "y a touché. Ces fiches-là se protègent par leur liste d'identifiants, "
                       "avec `scripts/gel_texte.py --wp --gel <ids> --apply`"}],
         "terminal": {
             "etat": "texte gelé — la fiche quitte la file de génération SEO et celle de poussée",
             "rouvreur": "la case « Texte retravaillé à la main » de l'encadré Journal dans "
                         "l'éditeur WordPress, ou `scripts/gel_texte.py --degel <id> --apply`. "
                         "Le compte des fiches gelées part sur Slack tous les jours avec le "
                         "bilan du cron de référencement."},
         "cout_ia": "une session Claude, lancée à la main — pas un cron, donc rien ici ne "
                    "part tout seul et rien n'est surveillé par le chien de garde.",
         "notes": ["La page Cowork du backoffice porte aujourd'hui le prompt de "
                   "l'AUTOCOMPLÉTION, pas celui du SEO : ce second rôle n'a pas de prompt "
                   "rangé dans le dépôt, il ne vit que dans `docs/SEO_QUI_FAIT_QUOI.md`.",
                   "Le dispositif ne fait PAS remonter le texte retouché dans la base : "
                   "SQLite garde la version du pipeline, le site porte la version "
                   "retravaillée. L'aperçu du backoffice et les audits qui jugent le texte "
                   "publié en le lisant EN BASE raisonnent donc sur l'ancienne version pour "
                   "ces fiches-là. C'est le chantier suivant ; en attendant, le nombre de "
                   "fiches concernées est affiché chaque jour.",
                   "Il ne protège pas non plus les IMAGES : une photo posée à la main se "
                   "protège autrement."],
         "code": ["deploy/wordpress/cs-gel-texte.php", "scripts/gel_texte.py"],
         "doc": ["docs/SEO_QUI_FAIT_QUOI.md"]}},

    {"id": "e_gel", "label": "Texte gelé", "icone": "🧊", "flux": "editorial",
     "kind": "etat", "garage_cle": "gelees", "col": 4, "row": 0, "sous_titre": "le cron ne repasse plus",
     "resume": "L'état qui protège une reprise humaine. Il est posé par le SITE, jamais par la base.",
     "detail": {
         "fait": ["Le site compare une empreinte des six champs éditoriaux à celle que le "
                  "pipeline avait laissée. Si elle a changé, quelqu'un d'autre a écrit.",
                  "Ce qui ne descend plus : titre, corps, extrait, titre Yoast, "
                  "méta-description, expression clé, et l'adresse.",
                  "Ce qui continue de descendre, et c'est voulu : dates, heure, lieu, ville, "
                  "catégorie, territoire, langue, prix, source officielle, toutes les métas "
                  "de classement, et l'image à la une."],
         "regles": ["Le gel protège un TEXTE, il ne met pas la fiche à la retraite — sinon "
                    "ce serait un cul-de-sac, et une date corrigée ne serait jamais republiée.",
                    "`wp_gel_at` en base n'est qu'une COPIE de ce que le site répond. "
                    "« Pas de gel » et « le mu-plugin n'est pas en ligne » ne doivent jamais "
                    "se confondre : la seule source de vérité est le site, interrogé par "
                    "`scripts/gel_texte.py --liste`."],
         "terminal": {
             "etat": "fiche gelée — hors de la file de génération SEO et de celle de poussée",
             "rouvreur": "la case de l'encadré Journal dans l'éditeur WordPress, ou "
                         "`scripts/gel_texte.py --degel <id> --apply`. Le compte des fiches "
                         "garées se voit à trois endroits : le message Slack quotidien du "
                         "cron SEO, le journal du lot de publication, et `--liste`."},
         "cout_ia": "aucun",
         "code": ["deploy/wordpress/cs-gel-texte.php"], "doc": ["docs/SEO_QUI_FAIT_QUOI.md"]}},

    {"id": "polylang", "label": "Lien FR ↔ IT", "icone": "🔗", "flux": "editorial",
     "kind": "sortie", "col": 2, "row": 2, "sous_titre": "route cs/v1/link-translations",
     "resume": "Ce qui fait apparaître le sélecteur de langue sur la fiche publique.",
     "detail": {
         "fait": ["Déclare à Polylang que deux pages sont la même fiche en deux langues."],
         "notes": ["Un échec ici ne bloque pas la traduction : la jumelle existe, elle n'est "
                   "simplement pas reliée. Le contrôle de 9h55 le mesure, et le grand ménage "
                   "du dimanche le répare."],
         "cout_ia": "aucun",
         "code": ["deploy/wordpress/cs-polylang.php", "scripts/repair_lien_polylang.py"]}},
]

# ══════════════════════════════════════════════════════════════════════════════
#  ONGLET 5 — CONTRÔLES & SOCLE
# ══════════════════════════════════════════════════════════════════════════════
_CONTROLES = [
    {"id": "auto_deploiement", "label": "Déploiement autonome", "icone": "🚢", "flux": "controles",
     "kind": "action", "col": 1, "row": 5, "cron_cle": "scripts.auto_deploiement",
     "script": "auto_deploiement",
     "resume": "Rejoue toute la suite de fixtures sur le code candidat, déploie si c'est vert, et réinstalle le crontab.",
     "detail": {
         "fait": ["Compare le code du serveur à la branche de travail.",
                  "Rejoue TOUTES les fixtures dans un dépôt jetable, sur le code candidat.",
                  "Déploie si le verdict le permet, puis réinstalle `crontab.txt`.",
                  "Compte les jours où une fixture reste rouge."],
         "ecrit": ["le crontab de la machine (après sauvegarde dans logs/)",
                   "le registre des décisions, quand une fixture reste rouge trois jours"],
         "regles": ["C'est le SEUL mécanisme qui installe le crontab. S'il meurt, ce fichier "
                    "cesse d'avoir le moindre effet — c'est arrivé du 26 au 28/08."],
         "decisions": [
             {"si": "des fixtures sont rouges sur le candidat",
              "alors": "elles sont rejouées sur le code DÉJÀ déployé. Si aucune n'est une "
                       "régression, on déploie quand même"},
             {"si": "une même fixture reste rouge exactement 3 jours",
              "alors": "escalade au registre des décisions, une seule fois"},
             {"si": "le déploiement réussit mais que le code en place n'est pas celui attendu",
              "alors": "alerte, et code de retour en erreur malgré le succès apparent"}],
         "cout_ia": "aucun",
         "slack": "🚀 déployé · ⛔ refusé · ⚠️ en échec · 🌡️ environnement malade · 📅 crontab réinstallé",
         "code": ["scripts/auto_deploiement.py", "deploy/update.sh"]}},

    {"id": "backup_db", "label": "Sauvegarde de la base", "icone": "💾", "flux": "controles",
     "kind": "action", "col": 3, "row": 5, "cron_cle": "scripts/backup_db.py", "script": "backup_db",
     "resume": "Copie cohérente de la base à 3h du matin, avec rotation sur 14 exemplaires.",
     "detail": {
         "fait": ["Copie la base par l'interface de sauvegarde de SQLite, pas par un `cp`.",
                  "Garde les 14 dernières, supprime les plus anciennes."],
         "ecrit": ["data/backups/events-AAAAMMJJ-HHMMSS.db"],
         "regles": ["14 sauvegardes gardées (réglable par une variable d'environnement).",
                    "C'est LE filet du dépôt : avant toute opération de masse, on le relance "
                    "à la main."],
         "cout_ia": "aucun",
         "code": ["scripts/backup_db.py"]}},

    {"id": "verifier_doublons", "label": "Doublons publiés", "icone": "👯", "flux": "controles",
     "kind": "action", "col": 0, "row": 0, "cron_cle": "scripts.verifier_doublons_publies",
     "script": "verifier_doublons_publies",
     "resume": "Désigne les groupes de fiches publiées qui racontent le même événement — et vérifie sur WordPress qu'elles sont vraiment en ligne.",
     "detail": {
         "fait": ["Regroupe les fiches publiées par ressemblance, comme le dédoublonnage.",
                  "Interroge WordPress POSTE PAR POSTE pour confirmer que deux pages au moins "
                  "sont publiques.",
                  "Recommande laquelle retirer, et dit pourquoi."],
         "lit": ["events_raw (fiches avec un identifiant WordPress)",
                 "WordPress : un appel REST par poste, par NUMÉRO"],
         "ecrit": ["rien — lecture seule stricte. Il DÉSIGNE, Franck tranche."],
         "regles": ["Périmètre : seulement les fiches encore devant nous. Les récurrents sont "
                    "inclus, les fiches sans date aussi.",
                    "Le choix de la gagnante : d'abord le nombre de fiches portant un article "
                    "rédigé, puis la longueur des articles, puis les permaliens propres, puis "
                    "l'ancienneté. Égalité parfaite : aucune proposition."],
         "decisions": [
             {"si": "moins de deux pages du groupe sont réellement publiques",
              "alors": "le groupe est écarté — un identifiant en base ne prouve rien"},
             {"si": "tous les sondages sont muets",
              "alors": "bandeau « AUCUNE VÉRIFICATION N'A EU LIEU » et le nombre est marqué "
                       "« CHIFFRE NON FIABLE »"},
             {"si": "le groupe s'est formé par simple coïncidence de lieu et de date",
              "alors": "il est affiché mais n'entre JAMAIS dans la commande de retrait"}],
         "cout_ia": "aucun",
         "slack": "🔴 seulement s'il y a quelque chose. Silence total sinon.",
         "notes": ["Rappel de doctrine : un doublon QU'ON A CRÉÉ se REDIRIGE en 301, il ne se "
                   "corbeille pas. Une adresse que Google connaît et qui rend 404 jette tout "
                   "ce qu'elle avait accumulé."],
         "code": ["scripts/verifier_doublons_publies.py", "deploy/wordpress/cs-redirections-301.php"]}},

    {"id": "audit_langue", "label": "Langue Polylang", "icone": "🈯", "flux": "controles",
     "kind": "action", "col": 0, "row": 1, "cron_cle": "scripts.audit_langue_polylang",
     "script": "audit_langue_polylang",
     "resume": "Vérifie que chaque traduction publiée est bien rangée du bon versant du site.",
     "detail": {
         "fait": ["Compare le versant réel (présence ou non du préfixe /it/ dans le permalien) "
                  "à la langue demandée."],
         "ecrit": ["rien — aucune écriture, aucun réseau"],
         "regles": ["Périmètre : traductions publiées encore devant nous.",
                    "Trois familles : régression de code, adresse de forme provisoire, écart de versant."],
         "decisions": [
             {"si": "un écart existe et que l'original est en ligne",
              "alors": "geste faisable : une re-traduction ciblée"},
             {"si": "l'original n'est pas en ligne", "alors": "bloqué, signalé comme tel"}],
         "cout_ia": "aucun",
         "slack": "Part MÊME À ZÉRO, exprès : « ✅ 0 sur N examinées » dit que le contrôle a "
                  "eu lieu. Le 🔴 n'apparaît QUE pour une régression de code, jamais pour un "
                  "écart de versant.",
         "code": ["scripts/audit_langue_polylang.py"]}},

    {"id": "audit_langue_texte", "label": "Langue des textes publiés", "icone": "🔤",
     "flux": "controles", "kind": "action", "col": 2, "row": 2,
     "cron_cle": "scripts.audit_langue_texte", "script": "audit_langue_texte",
     "resume": "Relit le texte EN LIGNE de chaque fiche et vérifie qu'il est dans la langue "
               "de sa page.",
     "detail": {
         "fait": ["Lit chaque fiche encore devant nous par son numéro (API REST publique) et "
                  "compare la langue du texte au versant de la page (/it/ ou non)."],
         "ecrit": ["rien — lecture seule"],
         "regles": ["Complète « Langue Polylang », qui ne relit jamais le texte : le 23/09, "
                    "cinq paires retouchées à la main avaient leurs textes inversés, gelées, "
                    "invisibles des deux côtés.",
                    "Un texte trop court ou mêlé ne reçoit pas de verdict : compté, jamais "
                    "signalé comme écart."],
         "decisions": [
             {"si": "la fiche n'est pas gelée",
              "alors": "translate_events --retranslate <original> la réécrit"},
             {"si": "la fiche est gelée (retouche humaine)",
              "alors": "le texte est à remettre à sa place à la main — le 23/09, échange des "
                       "textes entre les deux jumelles"}],
         "cout_ia": "aucun",
         "slack": "Une ligne, même à zéro, avec le nombre de pages lues et de pages sans "
                  "verdict à côté.",
         "code": ["scripts/audit_langue_texte.py", "utils/lang.py"]}},

    {"id": "verifier_dates", "label": "Contradicteur de dates", "icone": "🕵️", "flux": "controles",
     "kind": "action", "col": 0, "row": 2, "cron_cle": "scripts.verifier_dates",
     "script": "verifier_dates",
     "resume": "Ne cherche pas une date : cherche les cas où le texte de la source RÉFUTE celle qu'on a.",
     "detail": {
         "fait": ["Relit le texte écrit pour des humains (titre, description, corps de mail) "
                  "et le confronte à notre date.",
                  "Ne signale que quatre familles : contredite, millésime différent, jour de "
                  "semaine impossible, borne voisine."],
         "ecrit": ["rien — lecture seule"],
         "regles": ["Périmètre : fiches datées, encore devant nous. Les RÉCURRENTS sont "
                    "EXCLUS ici, contrairement au contradicteur de lieux.",
                    "Un texte muet n'est jamais signalé.",
                    "Anti-répétition : un point classé sans suite revient dès que le texte ou "
                    "les dates changent — jamais au calendrier."],
         "decisions": [
             {"si": "le texte ne porte qu'UNE date et que ce n'est pas la nôtre",
              "alors": "« contredite » — le signalement le plus sûr"},
             {"si": "le texte nomme un jour de semaine impossible pour notre date",
              "alors": "prime sur tout le reste. Si une seule année est possible et qu'elle "
                       "est passée, le geste devient certain : à écarter"},
             {"si": "le texte porte deux dates ou plus, aucune n'étant la nôtre",
              "alors": "compté, mais listé seulement sur demande — trop incertain pour une file"}],
         "cout_ia": "aucun",
         "slack": "Silence s'il n'y a rien. Sinon 10 lignes au plus, avec la commande de détail.",
         "code": ["scripts/verifier_dates.py"]}},

    {"id": "verifier_lieux", "label": "Contradicteur de lieux", "icone": "🗺️", "flux": "controles",
     "kind": "action", "col": 0, "row": 3, "cron_cle": "scripts.verifier_lieux",
     "script": "verifier_lieux",
     "resume": "Confronte le couple lieu/ville à trois sources de contradiction. Seul de la famille, il sait corriger.",
     "detail": {
         "fait": ["① Le registre de savoir connaît ce lieu dans une AUTRE commune.",
                  "② Nos propres fiches se contredisent : le même lieu porte deux villes.",
                  "③ Le nom du lieu contient une commune différente de la ville déclarée."],
         "ecrit": ["sous `--apply` seulement : ville + venue_source = « registre », pour la "
                   "famille ① uniquement, avec recomptage en base après écriture"],
         "regles": ["Périmètre : fiches vivantes, récurrents INCLUS, fiches sans date INCLUSES.",
                    "Le cron de 11h35 NE PASSE PAS `--apply` : en production, ce script est en "
                    "dry-run permanent. Il signale, il ne corrige pas.",
                    "Les lieux génériques sont comptés à part : c'est une collision de fiches "
                    "lieu côté WordPress, pas un désaccord de données."],
         "decisions": [
             {"si": "le registre CONFIRME la ville",
              "alors": "arrêt net — le toponyme ne reprend pas la parole"},
             {"si": "la contradiction vient du nom du lieu",
              "alors": "« à confirmer », jamais « à corriger »"}],
         "cout_ia": "aucun",
         "slack": "Silence s'il n'y a rien. 5 lignes par famille au plus.",
         "code": ["scripts/verifier_lieux.py", "utils/lieux.py"]}},

    {"id": "boite", "label": "La boîte du jour", "icone": "📮", "flux": "controles",
     "kind": "etat", "col": 2, "row": 1, "sous_titre": "SLACK_DIGEST=1",
     "resume": "Tous les messages sont RANGÉS au lieu d'être envoyés. Deux vidages par jour les reversent en un seul message.",
     "detail": {
         "fait": ["Chaque message part dans un fichier du jour au lieu du webhook.",
                  "La source appelante est mémorisée pour que le digest dise qui parle."],
         "regles": ["Demande de Franck du 13/08, après une matinée à sept notifications : "
                    "« il m'en faut un ou deux, mais c'est tout ».",
                    "Un message marqué `urgent` COURT-CIRCUITE la boîte. Un seul l'utilise : "
                    "le chien de garde de midi.",
                    "Si le rangement échoue, le message part IMMÉDIATEMENT — la boîte ne doit "
                    "jamais avaler.",
                    "Tout est aussi archivé dans `logs/slack/`, avec la mention parti ou non parti."],
         "terminal": {"etat": "aucun — la boîte se vide deux fois par jour",
                      "rouvreur": "le digest de 11h45 et celui de 20h"},
         "cout_ia": "aucun",
         "code": ["utils/slack.py"]}},

    {"id": "slack_digest_matin", "label": "Récapitulatif du matin", "icone": "🌅", "flux": "controles",
     "kind": "action", "col": 3, "row": 0, "cron_cle": "🌅", "script": "slack_digest",
     "resume": "Vide la boîte en un seul message, les 🔴 en tête.",
     "detail": {
         "fait": ["Rapatrie d'abord les rapports que WordPress tient en réserve.",
                  "Renomme le fichier AVANT l'envoi : un script qui écrit pendant le vidage "
                  "alimente une boîte neuve au lieu de voir sa ligne disparaître.",
                  "Trie : tout message contenant 🔴 remonte en tête, dans son ordre d'arrivée.",
                  "Condense chaque rapport à 12 lignes, en gardant TOUTES les lignes d'alerte."],
         "regles": ["Le tri ne regarde QUE le caractère 🔴. Ni ⚠️, ni ⛔, ni 🚨.",
                    "L'en-tête porte toujours le nombre de rapports, et le nombre de ceux qui "
                    "demandent une décision.",
                    "Corps tronqué à 38 000 caractères (Slack coupe à 40 000).",
                    "Si l'envoi échoue, le contenu est REMIS en boîte : rien n'est perdu."],
         "decisions": [
             {"si": "la boîte est vide",
              "alors": "le message distingue les DEUX lectures possibles d'un zéro : matinée "
                       "calme, ou `SLACK_DIGEST` non posé"}],
         "cout_ia": "aucun",
         "code": ["scripts/slack_digest.py", "utils/slack.py"]}},

    {"id": "slack_digest_soir", "label": "Récapitulatif du soir", "icone": "🌆", "flux": "controles",
     "kind": "action", "col": 3, "row": 2, "cron_cle": "🌆", "script": "slack_digest",
     "resume": "Le second vidage, à 20h. Même mécanique que celui du matin.",
     "detail": {
         "fait": ["Reverse tout ce qui est arrivé dans la boîte depuis 11h45."],
         "cout_ia": "aucun",
         "code": ["scripts/slack_digest.py"]}},

    {"id": "slack", "label": "Slack #agendasabauda", "icone": "💬", "flux": "controles",
     "kind": "sortie", "col": 4, "row": 1, "sous_titre": "le seul canal vers Franck",
     "resume": "Un ou deux messages par jour, plus les urgences. C'est le seul endroit où le système parle.",
     "detail": {
         "regles": ["Si le digest casse, l'absence de messages ressemble EXACTEMENT à un jour "
                    "calme. C'est pour ça qu'il est surveillé par le chien de garde."],
         "notes": ["Avant de diagnostiquer une panne, lire ce canal : le bilan automatique y "
                   "porte souvent déjà le bon diagnostic."],
         "cout_ia": "aucun"}},

    {"id": "watchdog", "label": "Chien de garde", "icone": "🐕", "flux": "controles",
     "kind": "action", "col": 0, "row": 5, "cron_cle": "scripts/watchdog_crons.py",
     # Il ne peut pas figurer dans sa propre liste. Ce sont le bilan de 11h et le
     # récapitulatif du lundi qui le surveillent, en lisant l'âge de SON journal — et ils
     # le disent en premier au-delà de 30 h. Sans ce champ, la carte le compterait à tort
     # comme un angle mort.
     "surveille_par": "le bilan du matin (11h) et le récapitulatif du lundi, qui lisent "
                      "l'âge de son journal et le signalent EN PREMIER au-delà de 30 heures",
     "resume": "Répond à une seule question : est-ce que les automatisations tournent encore ?",
     "detail": {
         "fait": ["Tient la liste des automatisations attendues, avec leur tolérance. Son "
                  "propre commentaire dit pourquoi le nombre exact n'est écrit nulle part "
                  "ailleurs : un chiffre recopié cesse d'être vrai le jour où on en ajoute un.",
                  "Croise DEUX sources : le registre des passages en base, et la date "
                  "d'écriture du journal. Il retient la plus récente.",
                  "Vérifie aussi le FUSEAU HORAIRE réel du serveur.",
                  "Pour chaque retard, il donne la COMMANDE à taper — pas seulement le constat."],
         "lit": ["la table `pipeline_runs`", "la date de modification des fichiers de logs/",
                 "le fuseau horaire du système"],
         "ecrit": ["rien — un chien de garde qui répare devient une deuxième source de panne"],
         "regles": ["Tolérance de 30 h pour un cron quotidien : la cadence plus une marge. "
                    "Elle laisse passer UN oubli, jamais deux.",
                    "200 h pour les hebdomadaires.",
                    "Un cron qui a tourné MAIS compté des erreurs est une anomalie DISTINCTE "
                    "du retard : les deux sont dits, jamais confondus.",
                    "Le test de fuseau porte sur le DÉCALAGE RÉEL, pas sur le nom — une "
                    "première version validait `Africa/Lagos`."],
         "decisions": [
             {"si": "aucune trace, ni registre ni journal",
              "alors": "« JAMAIS VUE » — la cause habituelle est un cron ajouté au fichier et "
                       "jamais réinstallé sur le serveur"},
             {"si": "le fuseau a bougé",
              "alors": "c'est dit EN PREMIER, avant les retards : un décalage d'heure invalide "
                       "la liste des retards elle-même, et fait basculer du mauvais côté ce "
                       "qui est « passé »"}],
         "cout_ia": "aucun",
         "slack": "Silence total si tout va bien. Sinon 🐕, en URGENT — c'est le seul message "
                  "qui court-circuite la boîte du jour, parce que le vidage est lui-même un cron.",
         "notes": ["C'est LUI qui alimente les pastilles d'état de cette carte — et "
                   "inversement, c'est la carte qui a trouvé les deux crons qui manquaient "
                   "à sa liste le 21/09 (la complétion depuis les mails et les notes "
                   "Yoast), en croisant `crontab.txt` avec `ATTENDUS`. Chacun voit ce que "
                   "l'autre ne voit pas."],
         "code": ["scripts/watchdog_crons.py"]}},

    {"id": "publier_sante", "label": "Relevé d'état", "icone": "🩺", "flux": "controles",
     "kind": "action", "col": 2, "row": 5, "cron_cle": "scripts.publier_sante",
     "script": "publier_sante",
     "resume": "Dépose sur WordPress un relevé d'exploitation, pour qu'une session Claude lise l'état du serveur sans accès SSH.",
     "detail": {
         "fait": ["Rassemble : état git, derniers passages, files d'attente, goulot "
                  "d'étranglement, crédit API, coûts des 7 derniers jours, provenance des données.",
                  "Le dépose dans une boîte aux lettres côté WordPress. Sept relevés sont gardés."],
         "regles": ["Périmètre des coûts : 7 jours glissants. Périmètre de la provenance : "
                    "fiches encore devant nous, traductions exclues.",
                    "Trois tentatives, espacées de 30 s puis 120 s — l'échec réel est une "
                    "fenêtre anti-flood de l'hébergeur, que des délais plus courts ne "
                    "franchissaient pas."],
         "decisions": [
             {"si": "le relevé contient un mot qui ressemble à un secret",
              "alors": "REFUS d'envoi, vérifié DEUX fois (avant et pendant la publication)"},
             {"si": "les trois tentatives échouent",
              "alors": "un diagnostic réseau complet est lancé : DNS, sondes TCP sur adresses "
                       "littérales, IPv4 et IPv6 séparément. C'est la leçon du 18/08, où "
                       "quatre causes ont été annoncées comme établies sans être mesurées"}],
         "cout_ia": "aucun",
         "code": ["scripts/publier_sante.py", "deploy/wordpress/cs-sante.php"]}},

    {"id": "homepage_health", "label": "Santé de la home", "icone": "🏠", "flux": "controles",
     "kind": "action", "col": 1, "row": 0, "cron_cle": "scripts/homepage_health.py",
     "script": "homepage_health",
     "resume": "Télécharge la page d'accueil et vérifie que six sections ne sont pas vides.",
     "detail": {
         "fait": ["Compte les liens d'événement DISTINCTS dans la fenêtre qui suit chaque "
                  "marqueur de section."],
         "regles": ["Seuil de 1 carte pour cinq sections, de 2 pour « Ça vaut le déplacement » "
                    "— sous 2, ce n'est plus un vivier maigre, c'est une panne du module.",
                    "Liens comptés en DISTINCTS : une carte porte son lien deux fois, image et titre.",
                    "Sur plusieurs occurrences d'une section, on retient le MAXIMUM, jamais la "
                    "somme : additionner cinq fenêtres vides donnait cinq zéros sur une home "
                    "qui servait cinquante liens."],
         "decisions": [
             {"si": "le marqueur de section est INTROUVABLE",
              "alors": "c'est différent de « zéro carte » : ce n'est pas un vivier vide, c'est "
                       "le thème ou le module qui a changé. Les deux sont dits séparément"}],
         "cout_ia": "aucun",
         "slack": "🔴 si la home est injoignable ou si une section est vide. Rien sinon.",
         "code": ["scripts/homepage_health.py"]}},

    {"id": "site_audit", "label": "Relecture du site", "icone": "🔎", "flux": "controles",
     "kind": "action", "col": 1, "row": 1, "cron_cle": "scripts/site_audit.py", "script": "site_audit",
     "resume": "Relit 40 fiches publiées par jour, en rotation, et compare ce que la page montre à ce que la base dit.",
     "detail": {
         "fait": ["Télécharge la page de chaque fiche et lit ses données structurées.",
                  "Compare dates, titre, lieu et visuel.",
                  "Avance un curseur : le catalogue est relu par tranches."],
         "regles": ["40 fiches par passage, 0,8 s entre deux.",
                    "Le territoire n'est PAS audité, volontairement : il n'est servi nulle "
                    "part dans la page d'une fiche.",
                    "Pas d'alerte quand les données structurées ne portent pas de date de "
                    "fin : le générateur ne l'émet jamais, l'alerte toucherait tous les multi-jours.",
                    "Ce script n'applique AUCUN filtre de date : il relit aussi les fiches "
                    "d'événements passés."],
         "decisions": [
             {"si": "la page témoin du site ne répond pas",
              "alors": "RIEN n'est audité et une escalade part dès le premier jour. Aucune "
                       "conclusion n'est tirée sur les fiches"},
             {"si": "la page rend 404",
              "alors": "l'API REST est interrogée AVANT de crier — un post à la corbeille est "
                       "normal, pas une anomalie du site"},
             {"si": "les fiches à la corbeille sont les seules anomalies",
              "alors": "aucun message n'est envoyé"}],
         "cout_ia": "aucun",
         "slack": "🔍 avec les anomalies graves d'abord (15 au plus), puis les points à "
                  "vérifier (10 au plus), puis une ligne unique pour les corbeillés.",
         "code": ["scripts/site_audit.py"]}},

    {"id": "gabarit_health", "label": "Santé des gabarits", "icone": "🧱", "flux": "controles",
     "kind": "action", "col": 1, "row": 2, "cron_cle": "scripts/gabarit_health.py",
     "script": "gabarit_health",
     "resume": "Mesure sept signaux SEO de SITE et n'alerte que sur leur BASCULE — cassé comme réparé.",
     "detail": {
         "fait": ["Sept signaux : robots.txt, home indexable, sitemap, cache HTML, cache des "
                  "ressources, données d'organisation, langues alternatives.",
                  "Compare à l'état mémorisé sur disque."],
         "regles": ["L'alerte se déclenche sur le CHANGEMENT, pas sur la valeur : au moment "
                    "où ce contrôle a été écrit, la moitié des signaux étaient déjà au rouge. "
                    "Alerter sur l'état aurait produit un message quotidien illisible.",
                    "« Non mesuré » n'est jamais « faux » : une mesure impossible n'écrase pas "
                    "la référence et ne compte pas comme bascule.",
                    "Le premier passage est silencieux : il pose la référence."],
         "cout_ia": "aucun",
         "slack": "Uniquement en cas de bascule : 🔴 cassé, 🟢 réparé.",
         "code": ["scripts/gabarit_health.py"]}},
]

# ══════════════════════════════════════════════════════════════════════════════
#  ONGLET 6 — LES QUATRE AGENTS
# ══════════════════════════════════════════════════════════════════════════════
_AGENTS = [
    {"id": "agent_quotidien", "label": "Agent quotidien", "icone": "🤖", "flux": "agents",
     "kind": "agent", "col": 0, "row": 0, "cron_cle": "scripts/agent_quotidien.sh",
     "script": "agent_quotidien",
     "resume": "Ouvre les pages sources une par une pour retrouver ce qui manque aux fiches incomplètes.",
     "detail": {
         "fait": ["Lit la file « À compléter » et, pour chaque fiche, l'angle déjà tenté et "
                  "le PROCHAIN à essayer.",
                  "Six angles dans l'ordre : page de la fiche, site de l'organisateur, "
                  "commune ou office de tourisme, recherche par nom, fiche sœur, réseaux sociaux.",
                  "Note CHAQUE tentative : trouvé, muet, ou inaccessible.",
                  "Traite aussi trois files de contrôle : fiches datées avant leur propre "
                  "collecte, dates contredites, lieux contredits."],
         "ecrit": ["UNIQUEMENT par la porte contrôlée `completer_verifie` : six colonnes et "
                   "pas une de plus — lieu, ville, date de début, date de fin, adresse "
                   "officielle, image.",
                   "des fichiers dans logs/ (il est le seul des quatre à pouvoir écrire un fichier)"],
         "regles": ["20 fiches par passage. 15 lignes de compte rendu au maximum.",
                    "Chaque valeur posée doit citer LA PHRASE LUE, pas seulement le nom du site.",
                    "Une image doit faire au moins 700 px de petit côté.",
                    "Six angles épuisés : la fiche quitte la file et repasse dans 30 jours.",
                    "Arrêté au bout de 20 minutes."],
         "decisions": [
             {"si": "la date n'est pas certaine", "alors": "il ne la pose pas. Consigne "
                    "explicite : ne jamais deviner une date"},
             {"si": "il veut corriger une valeur existante",
              "alors": "il doit DÉCLARER l'ancienne valeur ; la porte refuse si la base a changé"},
             {"si": "l'événement est passé",
              "alors": "il peut proposer de l'écarter, avec date ET source longue. La porte "
                       "refuse si la date n'est pas réellement passée"},
             {"si": "il s'agit d'un choix éditorial",
              "alors": "il PROPOSE, Franck clique. Il n'écarte jamais pour raison éditoriale"}],
         "cout_ia": "une session Claude complète, plafonnée à 20 minutes.",
         "slack": "🤖 son compte rendu, ou un avertissement s'il n'a pas pu tourner.",
         "notes": ["Sa garantie de ne pas toucher à WordPress vient de sa CONSIGNE, pas de sa "
                   "liste d'outils : il a un accès Python générique."],
         "code": ["scripts/agent_quotidien.sh", "config/consigne_agent_quotidien.txt",
                  "scripts/completer_verifie.py"]}},

    {"id": "cerveau", "label": "Cerveau du matin", "icone": "🧠", "flux": "agents",
     "kind": "agent", "col": 0, "row": 1, "cron_cle": "scripts/cerveau.sh", "script": "cerveau",
     "resume": "Le seul agent qui AGIT : il relit les signalements en attente et pose lui-même le geste réversible, ou escalade.",
     "detail": {
         "fait": ["Tient un REGISTRE : tout signalement non inscrit y entre avec une clé stable.",
                  "Vérifie avant d'agir — WordPress interrogé par NUMÉRO, jamais par liste.",
                  "Fait un dry-run, LIT la sortie, puis applique.",
                  "Recompte en base après chaque écriture."],
         "lit": ["les récapitulatifs Slack archivés et les journaux du matin",
                 "les sorties des audits, en lecture seule",
                 "WordPress, par l'API REST et poste par poste",
                 "le registre des décisions"],
         "ecrit": ["en base : statuts, marqueurs de résolution, registre des décisions",
                   "sur WordPress : corbeille (route maison, réversible), publication, traduction",
                   "RIEN dans le dépôt — ni code, ni config, ni crontab"],
         "regles": ["10 fiches touchées par passage au maximum ; au-delà, il s'arrête et escalade.",
                    "Sauvegarde de la base obligatoire avant plus de 3 écritures.",
                    "Règle 5 : uniquement l'à-venir, l'en-cours et le récurrent.",
                    "Arrêté au bout de 15 minutes — et pas 20, parce que son CONTRÔLEUR passe "
                    "à 11h00, vingt minutes après. Un débordement ferait certifier un travail partiel.",
                    "Sa liste d'outils nomme chaque script UN PAR UN : pas de joker. Une "
                    "fixture refuse tout motif irréversible dans cette liste."],
         "decisions": [
             {"si": "le geste est RÉVERSIBLE (corbeille, changement de statut, pipeline normal)",
              "alors": "il le fait seul"},
             {"si": "le geste est IRRÉVERSIBLE ou ÉDITORIAL (suppression définitive, "
                    "défusion, re-classer une fiche que Franck a rejetée, un seuil, du code)",
              "alors": "il escalade en une ligne. Dans le doute : escalade"},
             {"si": "le site est muet", "alors": "aucune action dépendant du site"}],
         "cout_ia": "une session Claude complète, plafonnée à 15 minutes.",
         "slack": "🧠 trois sections : FAIT, DIFFÉRÉ, À TRANCHER. 10 lignes au maximum.",
         "code": ["scripts/cerveau.sh", "config/consigne_cerveau.txt", "utils/decisions.py"]}},

    {"id": "bilan_matin", "label": "Bilan du matin", "icone": "🌅", "flux": "agents",
     "kind": "agent", "col": 0, "row": 2, "cron_cle": "scripts/bilan_matin.sh", "script": "bilan_matin",
     "resume": "Le contrôleur. Lecture seule stricte — et c'est cette impuissance qui rend le contrôle honnête.",
     "detail": {
         "fait": ["Relit les journaux du matin (8h à 10h30).",
                  "Contrôle le chien de garde LUI-MÊME : s'il n'a pas tourné depuis plus de "
                  "30 heures, il le dit en premier.",
                  "Vérifie que les récapitulatifs de la veille sont bien PARTIS.",
                  "Relit ce que le cerveau a annoncé à 10h40, et cherche la TRACE de chaque "
                  "geste. Un geste annoncé sans trace, ou une trace sans annonce, se signale "
                  "en premier.",
                  "Relit les alertes Slack de la veille : traitées, ou toujours là ?"],
         "ecrit": ["rien. C'est le plus fermé des quatre : pas d'écriture de fichier, pas de "
                   "réseau, et le registre des décisions accessible en LECTURE seulement, "
                   "pour qu'il ne puisse pas amender la mémoire du cerveau."],
         "regles": ["5 lignes de bilan au maximum.",
                    "« Si tu ne sais pas dire si c'est traité, écris que tu ne sais pas. »",
                    "Une alerte sans suite est citée AVEC sa date de première apparition."],
         "cout_ia": "une session Claude complète. ⚠️ Aucun plafond de durée, contrairement "
                    "aux deux agents précédents.",
         "slack": "🌅 son bilan.",
         "code": ["scripts/bilan_matin.sh", "config/consigne_bilan_matin.txt"]}},

    {"id": "revue_hebdo", "label": "Revue du code", "icone": "🔍", "flux": "agents",
     "kind": "agent", "col": 0, "row": 3, "cron_cle": "scripts/revue_hebdo.sh", "script": "revue_hebdo",
     "resume": "Relecture adversariale du code des huit derniers jours. Chaque défaut doit être PROUVÉ par exécution.",
     "detail": {
         "fait": ["Neuf familles de défauts, classées par fréquence observée dans ce dépôt : "
                  "une fixture qui ne peut pas contredire son auteur ; un garde-fou qui exclut "
                  "sa propre cible ; une affirmation que rien ne vérifie ; un renvoi qui ne "
                  "mène nulle part ; un compteur qui ne dit pas ce qu'il compte ; un garde-fou "
                  "qui coupe sa propre moisson ; une valeur de repli qui devient un cul-de-sac ; "
                  "un champ recopié sans se demander ce qu'il contient ; une tâche que "
                  "personne ne peut fermer."],
         "regles": ["Périmètre : les fichiers Python les plus touchés des huit derniers jours. "
                    "Pas tout le dépôt.",
                    "Méthode non négociable : construire un cas concret et l'EXÉCUTER avant "
                    "de conclure, sur une base JETABLE — jamais sur la base de production.",
                    "3 lignes par défaut au maximum, le plus grave d'abord. Pas de compliments.",
                    "« Rien de confirmé cette semaine » est un résultat acceptable."],
         "ecrit": ["rien, ni dans le dépôt, ni en base, ni sur WordPress"],
         "cout_ia": "une session Claude complète. Aucun plafond de durée.",
         "slack": "🔍 la revue de la semaine.",
         "notes": ["⚠️ C'est le seul des quatre dont le script ne journalise PAS sa sortie en "
                   "cas d'échec : le correctif appliqué aux trois autres en septembre ne l'a "
                   "pas atteint. Un plantage y perd donc le message d'erreur."],
         "code": ["scripts/revue_hebdo.sh", "config/consigne_revue_hebdo.txt"]}},

    {"id": "porte_completer", "label": "La porte contrôlée", "icone": "🚪", "flux": "agents",
     "kind": "decision", "col": 1, "row": 0, "sous_titre": "completer_verifie",
     "resume": "Le seul chemin par lequel l'agent quotidien peut écrire en base. Elle refuse tout le reste.",
     "detail": {
         "regles": ["Six colonnes autorisées, et pas une de plus.",
                    "Aucun champ déjà rempli n'est écrasé.",
                    "Une source est obligatoire pour chaque valeur."],
         "decisions": [
             {"si": "une colonne autre que les six est demandée", "alors": "refus"},
             {"si": "une correction est proposée et que la base a changé depuis la lecture",
              "alors": "refus — l'agent a travaillé sur une version périmée"},
             {"si": "un écartement est proposé sur un événement qui n'est pas réellement passé",
              "alors": "refus"}],
         "cout_ia": "aucun",
         "code": ["scripts/completer_verifie.py"]}},

    {"id": "registre", "label": "Registre des décisions", "icone": "📒", "flux": "agents",
     "kind": "etat", "col": 1, "row": 1, "sous_titre": "la mémoire partagée",
     "resume": "Ce qui manquait pour que le cron et une session Claude sachent l'un de l'autre.",
     "detail": {
         "fait": ["Chaque signalement entre avec une clé stable, se résout ou s'escalade.",
                  "Le cerveau écrit dedans, le bilan du matin le lit — et ne peut pas l'écrire."],
         "regles": ["Une décision OUVERTE depuis plusieurs jours sans escalade, ou ROUVERTE "
                    "plusieurs fois, remonte dans « demande une décision de Franck »."],
         "terminal": {"etat": "une clé résolue", "rouvreur": "un nouveau signalement de la "
                      "même clé la ROUVRE automatiquement"},
         "cout_ia": "aucun",
         "code": ["utils/decisions.py", "scripts/decisions.py"]}},
]

# ══════════════════════════════════════════════════════════════════════════════
#  ONGLET 7 — CHAQUE SEMAINE
# ══════════════════════════════════════════════════════════════════════════════
_HEBDO = [
    {"id": "weekly_audits", "label": "Grand ménage", "icone": "🧹", "flux": "hebdo",
     "kind": "action", "col": 0, "row": 0, "cron_cle": "scripts/weekly_audits.py",
     "script": "weekly_audits",
     "resume": "Dimanche 5h : enchaîne 28 audits et réparations, tous réversibles et déterministes, puis poste un seul bilan.",
     "detail": {
         "fait": ["Purges : hors zone, passés, incomplétables.",
                  "Corbeille : articles de presse publiés à tort, doublons nés dans WordPress.",
                  "Réconciliations : catalogue, posts supprimés côté site.",
                  "Réparations : descriptions polluées, pied de page RSS, liens de traduction, "
                  "liens Polylang, adresses officielles des traductions.",
                  "Audits en lecture seule : fantômes, temps du récit, lisibilité, liens morts, "
                  "orphelins, cohérence, exclusions, langue, annulations, sources bloquées.",
                  "Audit visuel des images (le seul poste payant du lot)."],
         "regles": ["Deux critères d'admission : réversible (corbeille ou rejet, jamais de "
                    "suppression dure) ET déterministe (pas de modèle qui DÉCIDE).",
                    "Une étape qui plante n'arrête pas la chaîne : elle est comptée en échec.",
                    "25 republications de sources fautives par passage, et une fiche n'est "
                    "republiée qu'une fois par empreinte de source.",
                    "La vérification des doublons publiés est appelée SANS `--apply` : c'est "
                    "un arbitrage éditorial."],
         "cout_ia": "deux postes seulement : l'audit visuel des images (jusqu'à 100 fiches) "
                    "et la reprise des liens Polylang (trois au plus, deux appels chacun).",
         "slack": "🧹 un bilan consolidé, ou ⚠️ avec la liste des étapes en échec.",
         "notes": ["Le code de retour de la vérification des liens n'est jamais testé : c'est "
                   "celui de l'audit des orphelins qui l'est, mais il est rapporté sous le "
                   "nom du premier. Un échec de la vérification des liens passe donc inaperçu."],
         "code": ["scripts/weekly_audits.py"]}},

    {"id": "site_health_check", "label": "Santé du site", "icone": "🩹", "flux": "hebdo",
     "kind": "action", "col": 0, "row": 1, "cron_cle": "scripts/site_health_check.py",
     "script": "site_health_check",
     "resume": "Parcourt le sitemap et vérifie que chaque adresse répond 200 sans redirection.",
     "detail": {
         "fait": ["Lit le sitemap, puis chaque sous-sitemap.",
                  "Interroge jusqu'à 1 500 adresses, cinq en parallèle.",
                  "Alimente la file de points SEO du backoffice, et REFERME ceux qui ont disparu."],
         "ecrit": ["les tables de points SEO (`seo_runs`, `seo_findings`)"],
         "regles": ["20 secondes au maximum par adresse.",
                    "Gravités : injoignable en haute, code 400 ou plus en critique, "
                    "redirection en moyenne (haute au-delà d'un saut).",
                    "Un point n'est refermé pour « ne figure plus au sitemap » que si "
                    "l'énumération du sitemap a RÉUSSI — sinon un sitemap muet refermerait tout."],
         "cout_ia": "aucun — entièrement déterministe",
         "code": ["scripts/site_health_check.py"]}},

    {"id": "gsc_report", "label": "Search Console", "icone": "📈", "flux": "hebdo",
     "kind": "action", "col": 0, "row": 2, "cron_cle": "scripts.gsc_report", "script": "gsc_report",
     "resume": "Archive chaque dimanche le relevé de trafic Google, pour constituer un historique.",
     "detail": {
         "fait": ["Interroge la Search Console en lecture seule, sur 30 jours.",
                  "Range clics, impressions, taux et position par page et par requête."],
         "ecrit": ["la table `gsc_perf` — rejouer une période ne duplique rien",
                   "jamais sur WordPress"],
         "regles": ["La fenêtre s'arrête 3 jours avant aujourd'hui : les données de la Search "
                    "Console ne sont pas fraîches avant. C'est ce décalage qui a fait prendre "
                    "trois semaines de retard pour de l'actuel, en septembre.",
                    "5 000 lignes par dimension."],
         "cout_ia": "aucun",
         "slack": "rien — ce cron est silencieux par construction.",
         "code": ["scripts/gsc_report.py"]}},

    {"id": "weekly_digest", "label": "Récapitulatif hebdomadaire", "icone": "📰", "flux": "hebdo",
     "kind": "action", "col": 1, "row": 0, "cron_cle": "scripts/weekly_digest.py",
     "script": "weekly_digest",
     "resume": "Lundi 8h : l'état des automatisations, le reste à faire, la qualité des fiches en ligne.",
     "detail": {
         "fait": ["Relit le registre des passages et dit ce qui a tourné.",
                  "Contrôle le chien de garde lui-même : plus de 30 heures sans passage, "
                  "c'est une ligne rouge.",
                  "Compte les fiches mises de côté à la main, les six plus anciennes nommées.",
                  "Mesure la qualité des fiches en ligne : image réelle, crédit, score de home."],
         "regles": ["Périmètre : fiches encore devant nous. Une bannière de territoire ne "
                    "compte pas comme « vraie image », et n'exige pas de crédit."],
         "cout_ia": "aucun",
         "code": ["scripts/weekly_digest.py"]}},

    {"id": "audit_calibrage", "label": "Calibrage de l'évaluateur", "icone": "🎚️", "flux": "hebdo",
     "kind": "action", "col": 1, "row": 1, "cron_cle": "scripts/audit_calibrage.py",
     "script": "audit_calibrage",
     "resume": "Mesure l'écart entre les notes du modèle et les corrections de Franck — sur-notation ou sous-notation.",
     "detail": {
         "fait": ["Relit les 200 dernières corrections de note.",
                  "Calcule le biais général, puis par territoire et par catégorie.",
                  "Compare la première moitié à la seconde pour voir si ça dérive."],
         "regles": ["Sous 10 corrections, il REFUSE de conclure.",
                    "Dérive franche à partir de 1,5 point d'écart moyen.",
                    "Un groupe de moins de 4 corrections n'est pas affiché."],
         "cout_ia": "aucun — il MESURE la qualité d'un modèle sans en appeler un.",
         "slack": "Uniquement en cas de dérive franche. Son silence est donc AMBIGU par "
                  "construction : c'est pour ça qu'il est surveillé.",
         "code": ["scripts/audit_calibrage.py", "utils/score_memory.py"]}},
]

# ══════════════════════════════════════════════════════════════════════════════
#  ONGLET 8 — CE QUE FRANCK DÉCLENCHE
# ══════════════════════════════════════════════════════════════════════════════
_HUMAIN = [
    {"id": "h_run", "label": "Lancer une tâche", "icone": "▶️", "flux": "humain",
     "kind": "humain", "col": 0, "row": 0, "sous_titre": "tableau de bord",
     "resume": "Onze boutons qui relancent à la main ce que le cron fait tout seul.",
     "detail": {
         "fait": ["Scraping RSS · Newsletters Gmail · Dossiers de presse · Dédoublonnage · "
                  "Datation · Évaluation · Enrichissement · Visuels · Tout compléter · "
                  "Auto-compléter · Brouillon de newsletter.",
                  "Chaque tâche part en arrière-plan, son journal va dans logs/, et la cloche "
                  "du bandeau en montre le résultat."],
         "regles": ["Une tâche déjà en cours est refusée.",
                    "Six d'entre elles COÛTENT des appels API, c'est écrit à côté du bouton.",
                    "Cinq acceptent une période, pour borner la dépense."],
         "decisions": [
             {"si": "la tâche est « Auto-compléter »",
              "alors": "elle POUSSE les fiches devenues complètes en brouillon sur le site"}],
         "cout_ia": "variable selon la tâche — indiqué sur chaque bouton.",
         "code": ["app/app.py"]}},

    {"id": "h_publier", "label": "Publier un lot", "icone": "🚀", "flux": "humain",
     "kind": "humain", "col": 0, "row": 1, "sous_titre": "page Tous les événements",
     "resume": "Publie jusqu'à 60 fiches d'un coup, soit par identifiants, soit toutes celles qui sont prêtes.",
     "detail": {
         "regles": ["Plafond dur de 60 ; le surplus est annoncé et non traité.",
                    "Écarte les rejetées, les sans date et les passées, avec le motif."],
         "decisions": [{"si": "aucun identifiant n'est donné",
                        "alors": "toutes les fiches rédigées, avec image et avec date"}],
         "cout_ia": "aucun",
         "code": ["app/app.py"]}},

    {"id": "h_action", "label": "Actions sur une fiche", "icone": "🎛️", "flux": "humain",
     "kind": "humain", "col": 0, "row": 2, "sous_titre": "aperçu, à valider, triage",
     "resume": "Publier, rejeter, marquer récurrent, marquer multi-lieux, vaut le déplacement, annuler.",
     "detail": {
         "fait": ["Publier sur l'un ou l'autre site · Rejeter · Récurrent (la date n'est plus "
                  "exigée) · Plusieurs lieux (lieu et ville ne sont plus exigés) · Vaut le "
                  "déplacement · Annuler."],
         "regles": ["Toutes réversibles : chacune a son inverse.",
                    "L'annulation préfixe le titre (ANNULÉ / ANNULLATO), l'applique à la "
                    "fiche JUMELLE, et republie."],
         "decisions": [
             {"si": "la fiche est annulée",
              "alors": "c'est la SEULE exception au gel du texte : le titre est forcé même "
                       "sur une fiche retravaillée à la main"}],
         "cout_ia": "aucun",
         "code": ["app/app.py"]}},

    {"id": "h_completer", "label": "Compléter à la main", "icone": "✏️", "flux": "humain",
     "kind": "humain", "col": 0, "row": 3, "sous_titre": "à compléter, aperçu",
     "resume": "Saisir date, lieu, ville, territoire, catégorie ou image. Une fiche devenue complète peut partir aussitôt.",
     "detail": {
         "regles": ["Liste blanche de champs : rien d'autre n'est accepté.",
                    "Un début sans fin recopie le début, et la provenance devient « manuel »."],
         "decisions": [{"si": "la fiche devient complète, à venir, et n'est pas encore en ligne",
                        "alors": "selon le chemin, elle est POUSSÉE immédiatement en brouillon"}],
         "cout_ia": "aucun",
         "notes": ["Deux versions de cette action existent dans le code sous la MÊME adresse, "
                   "avec des effets différents : l'une publie, l'autre non. À vérifier."],
         "code": ["app/app.py"]}},

    {"id": "h_triage", "label": "Triage en lot", "icone": "🧭", "flux": "humain",
     "kind": "humain", "col": 0, "row": 4, "sous_titre": "page Triage",
     "resume": "Marque en lot les fiches que le système propose comme récurrentes ou multi-lieux.",
     "detail": {
         "regles": ["La suggestion est RECALCULÉE au moment de l'action : les identifiants du "
                    "formulaire ne font pas foi.",
                    "Ne publie rien, n'invente rien. Entièrement réversible."],
         "cout_ia": "aucun", "code": ["app/app.py", "utils/triage.py"]}},

    {"id": "h_score", "label": "Corriger une note", "icone": "🎯", "flux": "humain",
     "kind": "humain", "col": 1, "row": 0, "sous_titre": "à compléter",
     "resume": "Renoter une fiche de 0 à 10. La correction est MÉMORISÉE et nourrit le prompt de l'évaluateur.",
     "detail": {
         "regles": ["C'est ce journal de corrections que lit le calibrage du lundi."],
         "cout_ia": "aucun", "code": ["app/app.py", "utils/score_memory.py"]}},

    {"id": "h_home", "label": "Mise en avant et cadrage", "icone": "🖼️", "flux": "humain",
     "kind": "humain", "garage_cle": "ecartes_home", "col": 1, "row": 1, "sous_titre": "aperçu",
     "resume": "Épingler ou exclure de la home, ordonner les épinglées, recadrer l'image.",
     "detail": {
         "regles": ["Épingler republie aussitôt la méta sur le site.",
                    "Changer l'ORDRE, en revanche, n'écrit qu'en base : la méta part à la "
                    "prochaine publication. C'est la même asymétrie que celle corrigée pour "
                    "la mise en avant en août.",
                    "Changer l'image remet le cadrage au centre, marque la provenance "
                    "« manuelle » et recalcule le crédit photo."],
         "cout_ia": "aucun", "code": ["app/app.py"]}},

    {"id": "h_reseaux", "label": "Publier sur Instagram", "icone": "📣", "flux": "humain",
     "kind": "humain", "col": 1, "row": 2, "sous_titre": "page Réseaux",
     "resume": "Le seul geste vraiment IRRÉVERSIBLE du backoffice : une publication passe en direct, sans brouillon.",
     "detail": {
         "fait": ["Génère le visuel, le téléverse dans la médiathèque, publie, et relaie sur "
                  "Facebook et Threads."],
         "regles": ["Refuse une fiche incomplète.",
                    "Refuse un doublon, sauf si on force.",
                    "Une date future range le post dans une file : c'est un cron séparé qui "
                    "publiera."],
         "decisions": [
             {"si": "le mode MANUEL est coché",
              "alors": "aucun appel à l'API Meta — c'est précisément pour éviter l'envoi "
                       "immédiat que ce mode existe"}],
         "irreversible": True,
         "cout_ia": "la réécriture de légende coûte un appel ; la publication, non.",
         "code": ["app/app.py", "utils/ig.py"]}},

    {"id": "h_newsletter", "label": "Newsletter Brevo", "icone": "📧", "flux": "humain",
     "kind": "humain", "col": 1, "row": 3, "sous_titre": "page Newsletter",
     "resume": "Compose la sélection de la semaine et crée un BROUILLON de campagne. Jamais d'envoi.",
     "detail": {
         "regles": ["L'ordre choisi est respecté.",
                    "Seul un brouillon est créé côté Brevo : l'envoi reste un geste humain, ailleurs."],
         "cout_ia": "aucun", "code": ["app/app.py", "utils/brevo.py"]}},

    {"id": "h_regie", "label": "Régie publicitaire", "icone": "💶", "flux": "humain",
     "kind": "humain", "col": 1, "row": 4, "sous_titre": "page Régie",
     "resume": "Créer, modifier, arrêter ou relancer une campagne. La suppression, elle, est définitive.",
     "detail": {
         "regles": ["Une campagne active REMPLACE l'AdSense de son bloc le temps de la campagne.",
                    "Le lien affiché passe toujours par le compteur de clics du backoffice, "
                    "jamais par l'adresse de l'annonceur en direct."],
         "decisions": [{"si": "on supprime une campagne",
                        "alors": "c'est la seule action de régie sans retour possible — il "
                                 "n'y a pas de corbeille"}],
         "irreversible": True,
         "cout_ia": "aucun", "code": ["app/app.py", "deploy/wordpress/cs-regie-serve.php"]}},

    {"id": "h_slack_cmd", "label": "Compléter depuis Slack", "icone": "💬", "flux": "humain",
     "kind": "humain", "col": 2, "row": 1, "sous_titre": "/agenda complete",
     "resume": "Une commande Slack qui complète une fiche et la pousse si elle devient publiable.",
     "detail": {
         "regles": ["Signature Slack vérifiée, avec protection contre le rejeu au-delà de 5 minutes.",
                    "Sans secret configuré, la route REFUSE tout."],
         "cout_ia": "aucun", "code": ["app/app.py"]}},

    {"id": "h_ig_webhook", "label": "Commentaires Instagram", "icone": "🔔", "flux": "humain",
     "kind": "sortie", "col": 2, "row": 2, "sous_titre": "webhook Meta",
     "resume": "Quand quelqu'un commente un post avec le mot-clé, il reçoit un message privé avec le lien.",
     "detail": {
         "fait": ["Retrouve l'événement par l'identifiant du média, compare le commentaire au "
                  "mot-clé de la fiche, puis envoie un message privé et deux boutons."],
         "regles": ["La signature de Meta est vérifiée — SAUF si le secret n'est pas "
                    "configuré, auquel cas le message est traité quand même, avec un simple "
                    "avertissement dans le journal.",
                    "La route répond toujours 200 à Meta, pour éviter les renvois en boucle."],
         "cout_ia": "aucun", "code": ["app/app.py"]}},

    {"id": "cowork_completer", "label": "Cowork : compléter au navigateur", "icone": "🧑‍💻",
     "flux": "humain", "kind": "humain", "col": 2, "row": 0, "sous_titre": "page Cowork",
     "resume": "Le dernier kilomètre : une session Claude ouvre les pages que le pipeline "
               "n'atteint pas et remplit les champs manquants dans le backoffice.",
     "detail": {
         "fait": ["Travaille dans la file « À compléter », les événements les plus proches d'abord.",
                  "Ouvre la source officielle de chaque fiche et n'y prend que ce qui est LU.",
                  "Marque « récurrent » une activité permanente plutôt que d'inventer une date."],
         "regles": ["À lancer APRÈS l'agent Python « Auto-compléter », qui est gratuit et "
                    "rapide : Cowork ne traite que le résidu — pages en JavaScript, dates "
                    "cachées, sites que le scraper n'atteint pas.",
                    "Environ 15 événements par session, une fois par jour après la collecte.",
                    "Règle d'or : ne jamais inventer. Mieux vaut un champ vide qu'une date "
                    "incertaine. Dans le doute, on passe.",
                    "Filet : une fiche complétée part en « À valider », pas en ligne."],
         "ecrit": ["les champs de la fiche, par la même porte que la complétion à la main",
                   "un rapport de passage horodaté (table `cowork_runs`), collé dans la page"],
         "cout_ia": "une session Claude, lancée à la main.",
         "notes": ["C'est ce prompt-là que la page Cowork du backoffice affiche. Le SEO final "
                   "est un AUTRE rôle de Cowork, sans prompt rangé dans le dépôt : voir "
                   "l'onglet « Traduction, SEO, images »."],
         "code": ["app/app.py"], "doc": ["docs/COWORK_AUTOCOMPLETION.md"]}},

    {"id": "h_widget", "label": "Widget partenaire", "icone": "🧩", "flux": "humain",
     "kind": "sortie", "col": 2, "row": 3, "sous_titre": "embed/events.json",
     "resume": "Un flux public et un script autonome que des sites partenaires posent chez eux.",
     "detail": {
         "fait": ["Le script crée un conteneur isolé, lit ses paramètres (territoire, ville, "
                  "langue, nombre), interroge le flux et rend la liste.",
                  "Une version en page autonome existe pour l'insertion en cadre."],
         "regles": ["Lecture seule, 20 événements au maximum, cache de 10 minutes."],
         "cout_ia": "aucun", "code": ["app/app.py"], "doc": ["docs/PARTENARIAT_WIDGET.md"]}},

    {"id": "h_doctrine", "label": "Doctrine pour agents", "icone": "📚", "flux": "humain",
     "kind": "sortie", "col": 2, "row": 4, "sous_titre": "doctrine.txt",
     "resume": "La voix, le vocabulaire interdit et la charte, relus dans Obsidian à l'instant, pour une session qui rédige.",
     "detail": {
         "regles": ["Accès par jeton, ou par la session du backoffice.",
                    "Codes parlants : 503 si le jeton n'est pas réglé, 403 s'il est faux, 503 "
                    "si la doctrine est vide.",
                    "Une alerte figure EN TÊTE du texte si un bloc manque."],
         "cout_ia": "aucun", "code": ["app/app.py"], "doc": ["docs/DOCTRINE_POUR_AGENTS.md"]}},
]

# ══════════════════════════════════════════════════════════════════════════════
#  ONGLET 9 — CÔTÉ SITE (WORDPRESS)
# ══════════════════════════════════════════════════════════════════════════════
_SITE = [
    {"id": "w_auth", "label": "Porte d'entrée de l'API", "icone": "🔑", "flux": "site",
     "kind": "site", "col": 0, "row": 1, "sous_titre": "cs-rest-auth.php",
     "resume": "Authentifie le pipeline quand l'hébergeur supprime l'en-tête standard.",
     "detail": {
         "fait": ["Lit un en-tête maison et n'accepte que des mots de passe d'application valides.",
                  "N'intervient pas si WordPress a déjà identifié quelqu'un."],
         "regles": ["C'est le prérequis de tout le reste : sans lui, le gel du texte et le "
                    "relevé d'état ne répondent pas."],
         "cout_ia": "aucun", "code": ["deploy/wordpress/cs-rest-auth.php"]}},

    {"id": "w_publish", "label": "Route de publication", "icone": "📮", "flux": "site",
     "kind": "site", "col": 1, "row": 1, "sous_titre": "cs-publish.php · cs/v1/event",
     "resume": "Crée ou met à jour l'événement. C'est la porte par laquelle tout le pipeline écrit.",
     "detail": {
         "regles": ["Idempotente : elle retrouve une fiche par son titre et sa date même si "
                    "l'identifiant a été perdu en base.",
                    "Une clé absente du message n'écrase pas la valeur en place."],
         "notes": ["⚠️ Ce fichier ne vit PAS en mu-plugin : il est collé dans Code Snippets, "
                   "EN BASE WordPress. Aucun dépôt de fichier ne l'atteint — c'est la raison "
                   "pour laquelle le gel du texte INTERCEPTE au lieu de le modifier.",
                   "La route `cs/v1/version` dit ce que la version EN LIGNE dit d'elle-même. "
                   "Tant qu'elle répond 404, le correctif n'est pas passé."],
         "cout_ia": "aucun", "code": ["deploy/wordpress/cs-publish.php"],
         "doc": ["docs/DEPLOIEMENT_WORDPRESS.md"]}},

    {"id": "w_gel", "label": "Gel du texte", "icone": "🧊", "flux": "site",
     "kind": "site", "col": 2, "row": 0, "sous_titre": "cs-gel-texte.php",
     "resume": "Le garde-fou le plus important : il empêche le cron d'écraser ce qu'un humain a retravaillé.",
     "detail": {
         "fait": ["AVANT l'écriture : si la fiche est gelée, il REMPLACE le titre, le corps "
                  "et l'extrait du message par ce qui est déjà en ligne, retire les métas de "
                  "référencement, et supprime TOUJOURS le slug — jamais de renommage "
                  "d'adresse sur une fiche reprise à la main.",
                  "APRÈS l'écriture : il RELIT la base et RESTAURE si le texte a bougé quand "
                  "même. Prévenir suppose que l'interception marche ; vérifier le prouve.",
                  "Tient un JOURNAL par fiche : qui a écrit quoi, quand."],
         "regles": ["La détection se fait par EMPREINTE de six champs (titre, corps, extrait, "
                    "et les trois métas de référencement), jamais par la date de modification "
                    "— celle-ci bouge pour trois raisons techniques, ce qui produisait trois "
                    "faux gels par jour.",
                    "Ce qui PASSE malgré le gel, volontairement : dates, lieu, catégorie, "
                    "territoire, langue, métas de classement, image à la une.",
                    "Le journal COMMENCE à son installation : il ne reconstitue pas le passé."],
         "decisions": [
             {"si": "le texte a été retravaillé à la main sur le site",
              "alors": "la fiche est GELÉE et sort aussi des files de référencement"},
             {"si": "le message porte le champ « forcer_texte »",
              "alors": "ces champs-là sont écrits malgré le gel. Seul usage prévu : le titre, "
                       "pour une annulation"}],
         "terminal": {
             "etat": "fiche gelée — elle sort des files de génération et de poussée SEO",
             "rouvreur": "trois chemins : la case « texte retravaillé » de l'encadré dans "
                         "l'éditeur, la route de dégel, ou `scripts/gel_texte.py --degel <id> "
                         "--apply`. Le nombre de fiches gelées est affiché à chaque passage SEO."},
         "cout_ia": "aucun",
         "code": ["deploy/wordpress/cs-gel-texte.php"], "doc": ["docs/SEO_QUI_FAIT_QUOI.md"]}},

    {"id": "w_completude", "label": "Contrôle de complétude", "icone": "⛔", "flux": "site",
     "kind": "site", "col": 2, "row": 2, "sous_titre": "cs-completude.php",
     "resume": "Quinze minutes après une publication, il repasse la fiche en brouillon si la source manque ou si le corps est indigent.",
     "detail": {
         "regles": ["Le délai de quinze minutes est nécessaire : le pipeline écrit ses métas "
                    "JUSTE APRÈS l'insertion. Contrôler tout de suite refuserait tout."],
         "decisions": [{"si": "la source officielle manque ou le corps est trop maigre",
                        "alors": "retour en brouillon, motif enregistré, message sur Slack"}],
         "terminal": {"etat": "repassée en brouillon",
                      "rouvreur": "compléter puis republier — réversible"},
         "cout_ia": "aucun", "code": ["deploy/wordpress/cs-completude.php"]}},

    {"id": "w_301", "label": "Redirections 301", "icone": "↪️", "flux": "site",
     "kind": "site", "col": 2, "row": 3, "sous_titre": "cs-redirections-301.php",
     "resume": "Une table chemin → chemin, pour que les adresses que Google connaît continuent de servir.",
     "detail": {
         "fait": ["Trois familles : anciens slugs de territoire, coquilles de rubrique, et "
                  "doublons d'articles que le pipeline a créés."],
         "regles": ["Un doublon QU'ON A CRÉÉ se REDIRIGE ; la corbeille reste pour ce qui "
                    "n'aurait jamais dû être publié. Arbitrage de Franck du 15/09.",
                    "Garde-fou contre la redirection vers soi-même : une boucle rendrait le "
                    "site injoignable.",
                    "Ne rien ajouter ici quand WordPress redirige déjà tout seul (slug renommé).",
                    "La gagnante se choisit sur les clics et impressions cumulés, jamais sur "
                    "la fraîcheur ni sur la qualité d'écriture."],
         "decisions": [
             {"si": "la cible a été corbeillée depuis",
              "alors": "la ligne envoie une 301 vers un 404. C'est arrivé le 21/09 : une "
                       "ligne de septembre a dû être reciblée"}],
         "cout_ia": "aucun", "code": ["deploy/wordpress/cs-redirections-301.php"]}},

    {"id": "w_noindex", "label": "Sortie d'index", "icone": "🙈", "flux": "site",
     "kind": "site", "col": 2, "row": 4, "sous_titre": "cs-passe-noindex · cs-index-budget",
     "resume": "Deux modules qui retirent de l'index ce qui n'a plus de contenu propre — sans rien supprimer.",
     "detail": {
         "fait": ["Le premier vise les événements TERMINÉS : sans date de fin, il ne conclut "
                  "RIEN (règle 5).",
                  "Le second vise les pages sans contenu propre : lieux sans événement à venir, "
                  "fiches d'organisateur, vues « ce week-end / aujourd'hui / cette semaine » "
                  "des hubs. Mesuré le 10/09 : 496 pages."],
         "regles": ["Ces modules n'écrivent RIEN en base : une date corrigée vers l'avenir "
                    "rouvre la fiche toute seule.",
                    "Le retrait est « noindex, follow » : rien ne disparaît du site."],
         "cout_ia": "aucun",
         "code": ["deploy/wordpress/cs-passe-noindex.php", "deploy/wordpress/cs-index-budget.php"]}},

    {"id": "w_affichage", "label": "Affichage et requêtes", "icone": "🎨", "flux": "site",
     "kind": "site", "col": 3, "row": 1, "sous_titre": "une quinzaine de modules",
     "resume": "Ce qui décide de ce qu'on voit : fenêtres de dates, filtre de territoire persistant, sélections de la home.",
     "detail": {
         "fait": ["Fenêtres « ce week-end / aujourd'hui / cette semaine », en FR et en IT.",
                  "Territoire persistant sur tout le site, par cookie, injecté dans toutes "
                  "les requêtes.",
                  "Adresses lisibles pour le filtre de territoire.",
                  "« Ça vaut le déplacement » : sélection par QUOTA de territoire, un "
                  "événement garanti par territoire — le tri par score seul renvoyait deux "
                  "fois le Piémont.",
                  "Sur les cartes, seuls les huit termes racines de territoire sont affichés.",
                  "Bloc « Ajouter à mon agenda », menu italien, sélecteur de langue sur les archives."],
         "regles": ["L'ordre d'affichage est forcé en SQL, parce que le calendrier écrase "
                    "l'ordre demandé."],
         "cout_ia": "aucun",
         "code": ["deploy/wordpress/cs-agenda-list-shared.php",
                  "deploy/wordpress/cs-territoire-persistant.php",
                  "deploy/wordpress/cs-cvld-dynamique.php"]}},

    {"id": "w_garde_fous", "label": "Garde-fous du tableau de bord", "icone": "👀", "flux": "site",
     "kind": "site", "col": 3, "row": 3, "sous_titre": "lecture seule",
     "resume": "Quatre encadrés dans l'administration WordPress qui signalent sans jamais corriger.",
     "detail": {
         "fait": ["Langue déclarée qui ne correspond pas au contenu.",
                  "Formulations nationalisantes.",
                  "Défauts de structure du catalogue.",
                  "Gabarits de carte hors du vocabulaire commun.",
                  "Plus un extracteur qui mesure chaque jour les dix pages d'entrée."],
         "regles": ["Le périmètre des dix pages a été arbitré par Franck le 03/08 : ne pas y "
                    "ajouter les sous-territoires ni les pages de province."],
         "cout_ia": "aucun", "code": ["deploy/wordpress/cs-garde-fou-langue.php"]}},

    {"id": "w_regie", "label": "Régie côté site", "icone": "💶", "flux": "site",
     "kind": "site", "col": 3, "row": 5, "sous_titre": "cs-regie-serve.php",
     "resume": "Chaque emplacement est AdSense par défaut ; une campagne du backoffice le remplace le temps qu'elle dure.",
     "detail": {
         "fait": ["Interroge le backoffice et met en cache.",
                  "Pose aussi les emplacements hors flux : habillage et gouttières.",
                  "Masque les encarts vides."],
         "regles": ["La publicité est conditionnée au consentement.",
                    "Une campagne enregistrée ne s'affiche PAS tant que son bloc n'a pas été "
                    "enveloppé côté thème."],
         "cout_ia": "aucun", "code": ["deploy/wordpress/cs-regie-serve.php"],
         "doc": ["docs/REGIE_ANNONCEURS.md"]}},
]

NOEUDS = _COLLECTE + _TRI + _PUBLICATION + _EDITORIAL + _CONTROLES + _AGENTS + _HEBDO + _HUMAIN + _SITE


# ══════════════════════════════════════════════════════════════════════════════
#  LES LIENS
#  type : "flux" (le chemin normal) · "rejet" (la fiche sort) · "retour" (elle
#  revient dans une file). Seuls les liens dont les DEUX bouts sont dans le même
#  onglet sont dessinés — un lien vers un autre flux se raconte dans la fiche.
# ══════════════════════════════════════════════════════════════════════════════
LIENS = [
    # ── Collecte ──────────────────────────────────────────────────────────────
    {"de": "src_rss", "vers": "scraper"},
    {"de": "scraper", "vers": "pending", "label": "nouvelles fiches"},
    {"de": "src_gmail", "vers": "gmail_collect"},
    {"de": "gmail_collect", "vers": "gmail_relink", "label": "adresse en bouchon"},
    {"de": "gmail_collect", "vers": "pending"},
    {"de": "ajouter_par_lien", "vers": "pending", "label": "signalements"},
    {"de": "gmail_relink", "vers": "pending", "type": "retour", "label": "re-datation"},
    {"de": "src_pages", "vers": "moisson"},
    {"de": "moisson", "vers": "file_completer", "type": "retour"},
    {"de": "dates_mail", "vers": "file_completer", "type": "retour"},
    {"de": "completer_mail", "vers": "file_completer", "type": "retour"},
    {"de": "file_completer", "vers": "moisson", "type": "retour", "label": "ce qui manque"},

    # ── Tri & datation ────────────────────────────────────────────────────────
    {"de": "e_pending", "vers": "dates_1"},
    {"de": "dates_1", "vers": "dedupe", "label": "dates armées"},
    {"de": "dedupe", "vers": "dates_2"},
    {"de": "dates_2", "vers": "venues"},
    {"de": "venues", "vers": "cleanup_cinema"},
    {"de": "cleanup_cinema", "vers": "evaluator"},
    {"de": "evaluator", "vers": "note", "label": "4 refus gratuits passés"},
    {"de": "evaluator", "vers": "e_rejected", "type": "rejet", "label": "refus gratuit"},
    {"de": "note", "vers": "e_rejected", "type": "rejet"},
    {"de": "note", "vers": "e_evaluated", "label": "≥ 7"},
    {"de": "note", "vers": "e_published_sub", "label": "< 7"},
    {"de": "cleanup_cinema", "vers": "e_rejected", "type": "rejet", "label": "séance ordinaire"},
    {"de": "e_rejected", "vers": "cleanup_cinema", "type": "retour", "label": "rétablissement"},

    # ── Rédaction & publication ───────────────────────────────────────────────
    {"de": "e_retenues", "vers": "daily_batch"},
    {"de": "daily_batch", "vers": "enrich"},
    {"de": "enrich", "vers": "portes_pub"},
    {"de": "enrich", "vers": "e_matiere_polluee", "type": "rejet", "label": "agrégateur"},
    {"de": "portes_pub", "vers": "publish", "label": "complète"},
    {"de": "publish", "vers": "wp_event"},
    {"de": "e_matiere_polluee", "vers": "enrich", "type": "retour", "label": "réparation du dimanche"},

    # ── Traduction, SEO, images ───────────────────────────────────────────────
    {"de": "e_enligne", "vers": "seo_batch"},
    {"de": "e_enligne", "vers": "images_wide"},
    {"de": "e_enligne", "vers": "translate"},
    {"de": "e_enligne", "vers": "refresh_depl"},
    {"de": "e_enligne", "vers": "yoast"},
    {"de": "seo_batch", "vers": "republi"},
    {"de": "images_wide", "vers": "republi"},
    {"de": "refresh_depl", "vers": "republi"},
    {"de": "translate", "vers": "polylang"},
    {"de": "seo_batch", "vers": "cowork_seo", "label": "puis Cowork — jamais l'inverse"},
    {"de": "cowork_seo", "vers": "e_gel", "label": "l'empreinte change"},

    # ── Contrôles & socle ─────────────────────────────────────────────────────
    {"de": "verifier_doublons", "vers": "boite"},
    {"de": "audit_langue", "vers": "boite"},
    {"de": "verifier_dates", "vers": "boite"},
    {"de": "verifier_lieux", "vers": "boite"},
    {"de": "homepage_health", "vers": "boite"},
    {"de": "site_audit", "vers": "boite"},
    {"de": "gabarit_health", "vers": "boite"},
    {"de": "auto_deploiement", "vers": "boite"},
    {"de": "boite", "vers": "slack_digest_matin"},
    {"de": "boite", "vers": "slack_digest_soir"},
    {"de": "slack_digest_matin", "vers": "slack", "label": "un seul message"},
    {"de": "slack_digest_soir", "vers": "slack"},
    {"de": "watchdog", "vers": "slack", "type": "rejet", "label": "urgent — court-circuite la boîte"},

    # ── Les quatre agents ─────────────────────────────────────────────────────
    {"de": "agent_quotidien", "vers": "porte_completer"},
    {"de": "cerveau", "vers": "registre"},
    {"de": "registre", "vers": "cerveau", "type": "retour", "label": "décisions rouvertes"},
    {"de": "registre", "vers": "bilan_matin", "label": "lecture seule"},
    {"de": "cerveau", "vers": "bilan_matin", "type": "retour", "label": "contrôlé à 11h"},

    # ── Ce que Franck déclenche ───────────────────────────────────────────────
    {"de": "h_slack_cmd", "vers": "h_completer", "type": "retour"},
    {"de": "cowork_completer", "vers": "h_completer", "type": "retour",
     "label": "remplit par la même porte"},

    # ── Côté site ─────────────────────────────────────────────────────────────
    {"de": "w_auth", "vers": "w_publish"},
    {"de": "w_publish", "vers": "w_gel", "label": "intercepté avant écriture"},
    {"de": "w_gel", "vers": "w_publish", "type": "retour", "label": "contre-épreuve après coup"},
    {"de": "w_publish", "vers": "w_completude", "label": "+15 min"},
    {"de": "w_completude", "vers": "w_publish", "type": "rejet", "label": "retour en brouillon"},
]
