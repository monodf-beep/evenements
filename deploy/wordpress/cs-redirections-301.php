<?php
/*
Plugin Name: Agenda Sabauda - Redirections 301 (slugs territoire + selections)
Description: Redirige les anciennes URL de territoire vers les nouveaux slugs (savoie,
  savoia, comte-de-nice, contea-di-nizza). Demande Franck 2026-07-22. Rollback: supprimer.
  2026-09-12 : ajoute les coquilles du type « Selections » vers leur vraie page.
*/
if (!defined('ABSPATH')) { exit; }

add_action('template_redirect', function () {
    $uri = isset($_SERVER['REQUEST_URI']) ? $_SERVER['REQUEST_URI'] : '';
    $path = parse_url($uri, PHP_URL_PATH);
    if (!$path) { return; }
    $path = '/' . trim($path, '/') . '/';
    $map = array(
        '/territoire/savoie-haute-savoie/'     => '/territoire/savoie/',
        '/it/territoire/savoia-alta-savoia/'   => '/it/territoire/savoia/',
        '/territoire/nice-alpes-maritimes/'    => '/territoire/comte-de-nice/',
        '/it/territoire/nizza-alpi-marittime/' => '/it/territoire/contea-di-nizza/',

        // LES COQUILLES DU TYPE « SELECTIONS » (2026-09-12, Franck : « /selections/
        // ce-week-end/ devrait laisser la place a /ce-week-end/ »). Le carousel de la
        // home lie cinq cartes vers ce type de contenu ; or MESURE faite ce jour-la :
        // les onze posts « selection » ont un contenu VIDE, et la page rendue liste 8
        // evenements generiques — les MEMES sur les trois pages testees — quand la vraie
        // page en liste 47. Les deux URL portent le meme titre, aucune n'est en noindex,
        // et chacune se declare canonique d'elle-meme : doublon pour le lecteur comme
        // pour Google.
        //
        // Seules les paires VERIFIEES sont ici : une coquille dont la page canonique
        // existe, repond 200, et porte le meme sujet. Les sept autres « selections »
        // (Les nouveautes, Ca vaut le deplacement, Quelle sagre ce mois, Novita, Vale il
        // viaggio, Cuneo., Quale sagra questo mese) n'ont AUCUNE page equivalente : les
        // rediriger au jugé enverrait le lecteur ailleurs que là où la carte promet de
        // l'emmener. Elles attendent l'arbitrage de Franck — creer la page, ou retirer
        // la carte du carousel.
        // ── DOUBLONS D'ARTICLES : on REDIRIGE, on ne corbeille pas ──────────────
        // 2026-09-15, arbitrage de Franck : « il vaut mieux faire des redirections si on
        // a créé plusieurs articles identiques ou similaires ».
        //
        // CE QUE J'AVAIS FAIT DE TRAVERS. Un rapport Search Console signalait quatre URL
        // Vicoforte en concurrence. J'ai vérifié en base — une seule en ligne, une à la
        // corbeille, deux effacées — et j'ai conclu « rien à faire ». C'était faux à
        // moitié : une URL MORTE qui a reçu des impressions rend 404, et un 404 jette
        // tout ce qu'elle avait accumulé. La 301, elle, le reverse sur la page qui reste.
        // Vérifié ce jour-là : /it/…-rendez-vous-du-7-septembre/ → 404 (63 impressions,
        // 0 clic), /la-foire-du-sanctuaire-vicoforte/ → 404 (1 impression).
        //
        // La règle qui en sort, pour toutes les fois suivantes : un doublon qu'on a
        // CRÉÉ SOI-MÊME se redirige vers la fiche gagnante. La corbeille reste pour ce
        // qui n'aurait jamais dû être publié (hors périmètre, non-événement) ; elle
        // n'est pas le bon geste pour une adresse que Google connaît déjà.
        //
        // ⚠️ PAS BESOIN D'AGIR quand WordPress le fait seul : un slug RENOMMÉ redirige
        // tout seul en 301 (mesuré ici sur /la-grande-fiera-del-santuario-di-vicoforte-2/,
        // qui pointe déjà sur la bonne page). N'ajouter ici que les adresses qui rendent
        // vraiment 404 — une ligne inutile est une ligne qui divergera un jour.
        //
        // ⚠️ LA LIGNE /it/ CHANGE DE LANGUE, et c'est un pis-aller assumé : la fiche 2255
        // n'a pas de jumelle italienne. Mieux vaut la bonne page dans l'autre langue
        // qu'un 404. LE JOUR OÙ 2255 EST TRADUITE, cette ligne doit pointer sur sa
        // jumelle — sinon on envoie durablement un lecteur italien sur du français.
        '/evenement/la-foire-du-sanctuaire-vicoforte/'
            => '/evenement/la-foire-du-sanctuaire-de-vicoforte/',
        '/it/evenement/la-fiera-du-santuaire-di-vicoforte-rendez-vous-du-7-septembre/'
            => '/evenement/la-foire-du-sanctuaire-de-vicoforte/',

        // 2026-09-15 : Pinocchio au Forte di Bard, TROIS posts publiés pour un spectacle
        // (6413 fr, 7201 it, 8901 fr). 8901 est le doublon français : 180 mots, et il
        // annonce « le 6 septembre » pour un spectacle des 19-20. Une page publique qui
        // donne une date fausse ne reste pas en ligne, quels que soient ses clics —
        // corbeillé (réversible), et son adresse suit vers la fiche qui reste.
        '/evenement/pinocchio-en-scene-au-forte-di-bard-pour-les-200-ans-de-carlo-collodi/'
            => '/evenement/pinocchio-traverse-les-alpes-quand-un-bicentenaire-ravive-la-vallee-daoste/',

        // 2026-09-16 : « Caveau » (Torino, expo Fondazione FICO), DEUX posts publiés pour
        // le même événement, même contenu français republié tel quel sous un chemin /it/
        // par erreur (6423 en ligne depuis fin juillet, 9266 depuis le 15/09). Repéré via
        // une liste de pages noindex de la Search Console — 9266 est celui du garde-fou de
        // complétude, PAS un vrai contenu italien. On garde le plus ancien (déjà indexé
        // plus longtemps), 9266 est corbeillé (réversible), son adresse suit.
        '/it/evenement/caveau-nasce-a-torino-un-nuovo-progetto-artistico-tra-mostre-gratuite-e-spazi-inediti-2/'
            => '/evenement/caveau-nasce-a-torino-un-nuovo-progetto-artistico-tra-mostre-gratuite-e-spazi-inediti/',

        // 2026-09-17 : « EVO 2026 » (tournoi de jeux de combat, Nice), TROIS posts pour
        // le même événement — repéré par l'audit de doublons quotidien, mais son
        // groupement par coïncidence (ville + dates + jetons) avait aussi attrapé à
        // tort la paire FR/IT saine 8954↔9302 (vérifié : liée en Polylang, pas un
        // doublon). Le seul vrai doublon était 7639 : un troisième article FR isolé,
        // sans jumelle, publié le 17/08 sous un angle différent. Corbeillé (réversible),
        // son adresse suit vers la fiche qui reste.
        '/evenement/evo-france-2026-nice-accueille-le-circuit-mondial-de-jeux-de-combat/'
            => '/evenement/evo-2026-a-nice-trois-jeux-inedits-et-1-000-places-supplementaires/',

        // 2026-09-17 : deux paires FR/IT complètes en double sur le même sujet — un
        // niveau au-dessus des doublons habituels (un post isolé). Tranché par clics
        // GSC cumulés sur les DEUX pages de chaque paire (règle de Franck du 15/09 :
        // « la fiche qui a les clics, pas la plus récente ni la mieux écrite »), lus
        // par Claude dans Chrome sur 28 jours.
        //
        // Aix-les-Bains, Journées du patrimoine : paire « palaces, danse et train du
        // Revard » (8892 fr / 9189 it) l'emporte — 20 impressions cumulées contre 0
        // pour « les sites de l'eau » (8884 fr / 9688 it). Aucune des deux ne clique,
        // mais l'une a au moins de la visibilité.
        //
        // ⚠️ SEULE LA LIGNE FR EST ICI. 8884 (fr) est corbeillé, sa ligne marche. La
        // ligne IT (9688) est VOLONTAIREMENT ABSENTE : ce post est contaminé — son
        // titre ET son corps appartiennent à un autre événement (« Mobilità dolce a
        // Aix-les-Bains », id local 5690, écrasé dessus le 17/09 à 10h54, aucune autre
        // page pour lui sur le site). Rediriger cette adresse ferait disparaître la
        // seule page publique de Mobilità dolce avant de l'avoir sauvée. À ajouter
        // SEULEMENT une fois 5690 republié sous son propre post et 9688 corbeillé.
        '/evenement/journees-du-patrimoine-a-aix-les-bains-les-sites-de-leau/'
            => '/evenement/journees-du-patrimoine-2026-a-aix-les-bains-palaces-danse-et-train-du-revard/',

        // EuroVolley Palavela : paire établie début septembre (8083 fr / 8126 it)
        // l'emporte largement — 1 clic, 54 impressions cumulées, contre 0/0 pour la
        // paire créée le 17/09 au matin (9619 fr / 9660 it), trop récente pour avoir
        // été explorée par Google (effet de fraîcheur déjà repéré sur ce rapport GSC,
        // pas un signal de faiblesse — mais la duplication, elle, est réelle).
        '/evenement/eurovolley-2026-huitiemes-et-quarts-de-finale-au-palavela-de-turin-du-20-au-23-septembre/'
            => '/evenement/eurovolley-2026-hommes-huitiemes-et-quarts-de-finale-au-palavela-de-turin/',
        '/it/evenement/eurovolley-2026-huitiemes-et-quarts-de-finale-au-palavela-de-turin-du-20-au-23-septembre-2/'
            => '/it/evenement/eurovolley-2026-hommes-huitiemes-et-quarts-de-finale-au-palavela-de-turin-2/',

        '/selections/ce-week-end/'                    => '/ce-week-end/',
        '/it/selections/questo-weekend/'              => '/it/questo-weekend/',
        '/selections/que-faire-a-annecy-ce-week-end/' => '/que-faire-a-annecy/ce-week-end/',
        '/it/selections/torino/'                      => '/it/cosa-fare-a-torino/',
    );
    // GARDE-FOU : jamais de redirection vers soi-meme (boucle infinie, site injoignable).
    // Le cout d'une erreur ici est le meme que celui du mu-plugin casse d'aout : tout le
    // site, y compris la porte qui permettrait de le reparer.
    if (isset($map[$path]) && $map[$path] === $path) { return; }
    if (!isset($map[$path])) { return; }
    $base   = home_url('/');
    $scheme = parse_url($base, PHP_URL_SCHEME);
    $host   = parse_url($base, PHP_URL_HOST);
    if (!$scheme) { $scheme = is_ssl() ? 'https' : 'http'; }
    $qs   = parse_url($uri, PHP_URL_QUERY);
    $dest = $scheme . '://' . $host . $map[$path] . ($qs ? '?' . $qs : '');
    wp_redirect($dest, 301);
    exit;
}, 0);