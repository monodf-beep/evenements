/**
 * CS - Ne pas cacher les colonnes vides (partout : desktop/tablette/mobile),
 * demande Franck 2026-07-23. Trois problemes distincts corriges :
 *
 * 1) Des regles CSS existantes ('.as-home-desktop > .wp-block-group:has(.jet-listing-not-found)'
 *    notamment) cachent une colonne JetEngine sans resultat -- mais la regle est trop
 *    large : la section 3 colonnes elle-meme porte aussi les classes .wp-block-group et
 *    .as-home-desktop, donc des qu'UNE SEULE colonne est vide, les 3 colonnes disparaissent
 *    entierement. Neutralise avec !important (source des regles d'origine introuvable en
 *    base -- probablement generee par un plugin tiers).
 *
 * 2) La section 3 colonnes (Nouveautes/En evidence/Agenda a venir) n'a AUCUN equivalent
 *    mobile dans le post_content (_element_id "nouveautes"/"evidence"/"venir" n'apparaissent
 *    qu'UNE fois chacun, contrairement a "ala-une"/"jour" qui ont 2 occurrences = 1 mobile +
 *    1 desktop) : elle est entierement masquee sur mobile/tablette via la classe generique
 *    .as-home-desktop{display:none}. On la rend visible partout en ciblant PRECISEMENT le
 *    wrapper .as-home-desktop qui contient .as-desktop-cols3 (via :has()), pour ne PAS
 *    demasquer les AUTRES blocs .as-home-desktop du site qui, eux, ont deja un vrai
 *    equivalent mobile separe (les demasquer aussi creerait des doublons).
 *
 * 3) .as-desktop-cols3 a un grid-template-columns FIXE ("1.5fr 1fr 1fr", gap 40px)
 *    pense uniquement pour desktop (il etait avant masque sur mobile via display:none,
 *    donc jamais teste en dessous de 900px). Applique tel quel sur mobile (point 2
 *    ci-dessus), il ecrase 3 colonnes serrees au lieu d'empiler -- pas responsive.
 *    On repasse en 1 colonne sous le seuil mobile/desktop du site (900px, cf. snippet
 *    12 "CS Composants (styles)").
 *
 * 4) Le rail "jour" MOBILE (id="jour", classes .as-home.as-day-rail -- version mobile
 *    du bloc "7 prochains jours") se retrouvait FORCE visible sur desktop aussi : la
 *    regle !important du point 1 sur .as-day-rail ecrasait la regle .as-home{display:
 *    none} du site (@media min-width:900px), puisque cet element porte les DEUX
 *    classes en meme temps. Exclu via :not(.as-home) -- laisse .as-home reprendre la
 *    main sur desktop, garde le fix "colonne vide" pour les autres rails desktop.
 *
 * 5) "A la une" (id="ala-une") : la home mobile est en grille 2 colonnes (4 items =
 *    2 lignes completes), la home desktop en 3 colonnes. L'allocateur (snippet 44)
 *    ne fournit qu'UNE liste partagee entre les deux -- passee a 4 items (plein pour
 *    mobile) ; sur desktop on masque le 4e via nth-child pour garder 3 (une ligne
 *    complete a 3 colonnes), demande Franck 2026-07-24.
 *
 * 6) "Les 7 prochains jours" (id="jour") : demande Franck 2026-07-24 -- MOBILE
 *    toujours 4 evenements (jamais plus, meme si plus sont disponibles) ; DESKTOP
 *    4 minimum ou 8 si assez disponibles (jamais 5/6/7, jamais >8). Le row_size=4
 *    de l'allocateur (snippet 44) donne deja le comportement 4-ou-8 cote desktop
 *    (arrondi a la baisse au multiple de 4). Cote mobile on plafonne en plus a 4
 *    via nth-child, meme si l'allocateur en a fourni 8.
 */
add_action('wp_head', function () {
    echo '<style id="cs-no-hide-empty-cols">'
        . '.as-desktop-cols3.as-home-desktop.wp-block-group{ display: grid !important; }'
        . '.as-desktop-col.wp-block-group,'
        . '.as-day-rail:not(.as-home)'
        . '{ display: block !important; }'
        . '.as-home-desktop > div:has(+ .wp-block-group .jet-listing-not-found)'
        . '{ display: block !important; }'
        . '.as-home-desktop:has(> .as-desktop-cols3)'
        . '{ display: block !important; }'
        . '@media (max-width: 899px) {'
        . '  .as-desktop-cols3.as-home-desktop.wp-block-group{ grid-template-columns: 1fr !important; gap: 32px !important; margin-top: 24px !important; padding-left: 0 !important; }'
        . '  .as-home-desktop:has(> .as-desktop-cols3){ max-width: 480px !important; margin-left: auto !important; margin-right: auto !important; }'
        . '}'
        . '.as-home-desktop #ala-une .jet-listing-grid__item:nth-child(n+4){ display: none !important; }'
        . '.as-home #jour .jet-listing-grid__item:nth-child(n+5){ display: none !important; }'
        . '/* A la une mobile 2 colonnes : jamais un nombre impair de cartes au-dela de 1 (demande Franck 2026-09-24 : soit 2 soit 4 suivant le stock). Le snippet 44 en fournit jusqu a 4. */'
        . '@media (max-width: 899px){ .as-home #ala-une .jet-listing-grid__item:nth-child(odd):last-child:not(:first-child){ display: none !important; } }'
        . '/* Dots carrousel a la charte (valide Franck 2026) */'
        . '.jet-listing-grid__slider.swiper,.jet-engine-swiper-pagination-wrapper{--swiper-pagination-color:#DC5D45;--swiper-pagination-bullet-inactive-color:#C9BFAD;--swiper-pagination-bullet-inactive-opacity:1;--swiper-pagination-bullet-width:8px;--swiper-pagination-bullet-height:8px;--swiper-pagination-bullet-horizontal-gap:4px;}'
        . '.jet-engine-swiper-pagination-wrapper{display:flex!important;justify-content:center;align-items:center;margin-top:14px;}'
        . '.jet-engine-swiper-pagination-wrapper .swiper-pagination-bullet{width:8px!important;height:8px!important;background-color:#C9BFAD!important;opacity:1!important;border-radius:50%!important;margin:0 4px!important;transition:width .22s ease,background-color .22s ease,border-radius .22s ease;}'
        . '.jet-engine-swiper-pagination-wrapper .swiper-pagination-bullet-active{width:22px!important;background-color:#DC5D45!important;border-radius:4px!important;}'
        . '/* Footer mobile : nuage de villes resserre + FR|IT a part */'
        . '.as-footer-mobile__group--meta{ gap:5px 6px !important; line-height:1.5 !important; }'
        . '.as-footer-mobile__group--lang{ margin-top:12px !important; display:block !important; text-align:center !important; line-height:1.4 !important; }.as-footer-mobile__group--lang a{ display:inline !important; }'
        . '/* Anti-flash Swiper pre-init -- 2026-08-01 (Franck) : la vraie classe presente
           AVANT l\'init Swiper est .jet-listing-grid__item (pas .swiper-slide, que
           Swiper ajoute lui-meme APRES coup) -- les regles .swiper-slide etaient donc
           sans effet avant l\'initialisation reelle, laissant les cartes apparaitre un
           court instant sans le style final (coins carres, position differente), avant
           que Swiper ne les restructure. On cible desormais la VRAIE classe pre-init
           en plus de .swiper-slide (garde par securite pour d\'autres carrousels). */'
        . '.jet-listing-grid__slider.swiper:not(.swiper-initialized){overflow:hidden!important;}'
        . '.jet-listing-grid__slider.swiper:not(.swiper-initialized) .swiper-wrapper{display:flex!important;flex-wrap:nowrap!important;transform:none!important;}'
        . '.jet-listing-grid__slider.swiper:not(.swiper-initialized) .swiper-slide,'
        . '.jet-listing-grid__slider.swiper:not(.swiper-initialized) .jet-listing-grid__item'
        . '{ flex: 0 0 100% !important; width: 100% !important; max-width: 100% !important; }'
        . '.jet-listing-grid__slider.swiper:not(.swiper-initialized) .swiper-slide:not(:first-child),'
        . '.jet-listing-grid__slider.swiper:not(.swiper-initialized) .jet-listing-grid__item:not(:first-child)'
        . '{ visibility: hidden !important; }'
        . '/* Resserrer le bloc bas (cols3) sur mobile */@media (max-width:899px){.as-desktop-cols3.as-home-desktop.wp-block-group{gap:16px!important;row-gap:16px!important;padding-top:12px!important;margin-top:12px!important;}}'
        . '/* Commune + date sur cards -- 2026-08-02 : aligne sur le systeme de carte unifie (snippet 12). Ce bloc est injecte a la priorite 999, donc APRES la feuille de styles principale : il gagnait la cascade et maintenait la date en 13px rouge alors que les grilles la rendaient en 11px noir. Le rouge est un accent de marque, pas un porteur de donnee a repeter des dizaines de fois par page. NB : ce fichier concatene des chaines PHP entre apostrophes -- ne JAMAIS mettre une apostrophe dans ces commentaires, elle ferme la chaine et casse tout le snippet (donc le style cs-no-hide-empty-cols, donc la disparition des colonnes sur mobile). */.cs-card-commune{font-size:12px!important;font-weight:400!important;color:#6F6B62!important;margin-top:3px!important;line-height:1.3!important;}.cs-card-date{font-size:11px!important;font-weight:700!important;color:#1D1D1B!important;margin-top:2px!important;}'
        . '</style>';
}, 999);