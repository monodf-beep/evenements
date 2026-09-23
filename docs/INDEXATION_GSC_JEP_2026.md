# Indexation Google des fiches des Journées du patrimoine — septembre 2026

Demandé par Franck le 24/09/2026 : « il faut indexer les nouveaux événements aussi… dans google search console via cowork ».

## Ce qui est permis, et pourquoi pas plus

- **Pas d'API d'indexation Google** : elle est réservée aux offres d'emploi et aux diffusions en direct ; l'employer pour des événements expose à une sanction (`docs/AGENT_SEO_DASHBOARD_SPEC.md` §2).
- **Bing et les moteurs IndexNow** sont déjà prévenus à chaque publication par le snippet « CS - IndexNow » (Code Snippets n° 116, actif depuis le 30/07).
- **Google** : renvoi du sitemap (couvre tout) + demande manuelle d'indexation, **environ 10 par jour et par propriété** — d'où le tri ci-dessous.

## Vérifié avant de soumettre (24/09, 1h50)

Les 82 fiches créées depuis le 23/09 : toutes en **200**, **canonique = elle-même**, **aucun noindex**, **présentes dans `tribe_events-sitemap.xml`** (378 adresses). 72 sont encore à venir après le 24/09 ; elles sont listées ici.

Les pages **italiennes** ne consomment pas de demande manuelle : Google les découvre par le hreflang de leur jumelle française et par le sitemap. Priorité aux pages françaises, dans l'ordre de la date de l'événement.

## Consigne pour la session Cowork (à coller telle quelle, une fois par jour, avec la liste du jour)

```
Dans Google Search Console, propriété agendasabauda.eu :
1. (Seulement le premier jour) Menu Sitemaps : renvoyer https://agendasabauda.eu/sitemap_index.xml
   et https://agendasabauda.eu/tribe_events-sitemap.xml (bouton « Envoyer » ; noter l'état affiché).
2. Pour CHAQUE adresse de la liste du jour, dans l'ordre : coller l'adresse dans la barre
   « Inspecter une URL », attendre le résultat, puis :
   - si « L'URL est sur Google » : ne rien demander, noter « déjà indexée » ;
   - sinon : cliquer « Demander l'indexation », attendre la confirmation, noter « demandée ».
   - si Google signale un QUOTA ATTEINT : s'arrêter là et noter où on s'est arrêté.
3. Ne rien modifier d'autre dans la Search Console.
4. Rendre un tableau : adresse | état avant (sur Google / pas sur Google + motif affiché) | action.
```

## Jour 1 — 24/09 (événements du 25 et 26)

- https://agendasabauda.eu/evenement/oltre-laffresco-les-coulisses-du-restauro-du-chateau-dissogne/  — Les coulisses de la restauration du château d’Issogne (2026-09-23 → 2026-09-25)
- https://agendasabauda.eu/evenement/memorie-darchivio/  — Mémoires d’archives à Issogne : deux siècles de Vallée d’Aoste par les (2026-09-25 → 2026-09-25)
- https://agendasabauda.eu/evenement/architettura-ad-alta-quota-evoluzione-storica-del-bivacco/  — L’évolution du bivouac alpin racontée par Luca Gibello : « Architettura ad alta quota » (2026-09-25 → 2026-09-25)
- https://agendasabauda.eu/evenement/a-turin-la-recherche-sort-des-laboratoires-pour-investir-le-parc/  — À Turin, la recherche sort des laboratoires pour investir le Parc du V (2026-09-25 → 2026-09-26)
- https://agendasabauda.eu/evenement/storie-di-terra-di-pietra-e-di-uomini/  — Visite guidée à la Maison Gargantua de Gressan : histoires de terre, d (2026-09-23 → 2026-09-26)
- https://agendasabauda.eu/evenement/le-lunette-del-castello-di-issogne/  — Les lunettes peintes du château d’Issogne face aux costumes reconstitu (2026-09-23 → 2026-09-26)
- https://agendasabauda.eu/evenement/una-rilettura-dei-monumenti-cittadini/  — Relire Aoste par ses statues et ses places (2026-09-23 → 2026-09-26)
- https://agendasabauda.eu/evenement/le-chateau-dussel-rouvre-ses-tours-aux-dessins-de-francesco-corni/  — Le château d’Ussel rouvre ses tours aux dessins de Francesco Corni (2026-09-26 → 2026-09-27)
- https://agendasabauda.eu/evenement/i-segreti-della-maison-de-thomas-trois-siecles-de-savoir-faire-alpin/  — Les secrets de la Maison de Thomas : trois siècles de savoir-faire alp (2026-09-26 → 2026-09-26)
- https://agendasabauda.eu/evenement/dallautoma-al-telefono-il-genio-di-innocenzo-manzetti/  — De l’automate au téléphone : le génie d’Innocenzo Manzetti (2026-09-26 → 2026-09-26)

## Jour 2 — 25/09 (événements du 26)

- https://agendasabauda.eu/evenement/microdanze-trois-pieces-de-danse-contemporaine-dans-les-vestiges-de/  — MicroDanze : trois pièces de danse contemporaine dans les vestiges de  (2026-09-26 → 2026-09-26)
- https://agendasabauda.eu/evenement/nutrire-il-benessere-un-chef-spatial-et-un-medecin-nutritionniste/  — Un chef spatial et un médecin nutritionniste à la Villa della Regina (2026-09-26 → 2026-09-26)
- https://agendasabauda.eu/evenement/passeggiata-botanica-a-villa-della-regina-la-vigne-du-xviie-siecle/  — Promenade botanique à la Villa della Regina : la vigne du XVIIe siècle (2026-09-26 → 2026-09-26)
- https://agendasabauda.eu/evenement/tra-acqua-terra-e-memoria-leri-e-lucedio-le-patrimoine-qui-renait/  — Entre eau, terre et mémoire : Leri et Lucedio, le patrimoine qui renaî (2026-09-26 → 2026-09-26)
- https://agendasabauda.eu/evenement/cappella-di-san-giuseppe-dix-ans-de-restauration-sachevent-a-gressoney/  — Chapelle Saint-Joseph de Gressoney : dix ans de restauration s’achèven (2026-09-26 → 2026-09-26)
- https://agendasabauda.eu/evenement/chatel-argent-e-il-valore-culturale-delle-rovine/  — Châtel-Argent : la valeur culturelle des ruines (2026-09-26 → 2026-09-26)
- https://agendasabauda.eu/evenement/tissus-dhistoire/  — Tissus d’histoire à Sarre (2026-09-26 → 2026-09-26)
- https://agendasabauda.eu/evenement/larte-del-legno/  — L’art du bois : visite et ateliers à Saint-Vincent (2026-09-26 → 2026-09-26)
- https://agendasabauda.eu/evenement/il-castello-di-saint-germain-unicona-della-valle-daosta-medievale/  — Château de Saint-Germain : fouilles ouvertes au public lors des Journé (2026-09-26 → 2026-09-26)
- https://agendasabauda.eu/evenement/cercami-tra-il-bianco-della-neve/  — Un atelier d’illustration naturaliste au château de Saint-Pierre (2026-09-26 → 2026-09-26)

## Jour 3 — 26/09 (événements du 26-27)

- https://agendasabauda.eu/evenement/il-volo-della-colomba-franco-perrotti-au-ciel-anthropise-courmayeur/  — Franco Perrotti à l’église vaudoise de Courmayeur : « Il volo della co (2026-09-26 → 2026-09-27)
- https://agendasabauda.eu/evenement/dalla-terra-alla-cura-les-plantes-qui-soignent-au-jardin-des-anciens/  — Les plantes qui soignent au Jardin des Anciens Remèdes de Jovençan (2026-09-26 → 2026-09-27)
- https://agendasabauda.eu/evenement/impara-larte-della-tessitura/  — Apprendre le tissage du chanvre à Donnas et Champorcher (2026-09-26 → 2026-09-27)
- https://agendasabauda.eu/evenement/viaggio-alla-scoperta-della-cultura-walser/  — À la découverte de la culture walser : visite guidée gratuite à Gresso (2026-09-26 → 2026-09-27)
- https://agendasabauda.eu/evenement/dai-segnali-di-fuoco-alle-onde-elettromagnetiche-storia-e-futuro/  — Au fil des ondes : la Vallée d’Aoste et l’histoire des télécommunicati (2026-09-26 → 2026-09-27)
- https://agendasabauda.eu/evenement/il-cuore-idroelettrico-di-montjovet/  — À l’intérieur de la centrale hydroélectrique de Montjovet (2026-09-27 → 2026-09-27)
- https://agendasabauda.eu/evenement/il-castello-di-introd-e-larmonia-della-trasformazione-continua/  — Au château d’Introd, une visite sur les traces de ses reconstructions (2026-09-27 → 2026-09-27)
- https://agendasabauda.eu/evenement/dal-segno-al-gioco/  — Les enfants enquêtent sur les croix sculptées au MAV de Fénis (2026-09-27 → 2026-09-27)
- https://agendasabauda.eu/evenement/la-chiave-della-rinascita-di-un-tesoro-del-1462/  — Gignod : la renaissance d’un grenier de 1462 (2026-09-23 → 2026-09-27)
- https://agendasabauda.eu/evenement/piccoli-custodi-delle-erbe-di-ieri/  — Un mini-herbier à créer pour les enfants à la Maison des Anciens Remèd (2026-09-26 → 2026-09-26)

## Le reste (sitemap seulement, sauf quota disponible)

- https://agendasabauda.eu/it/evenement/oltre-laffresco-les-coulisses-du-restauro-du-chateau-dissogne-2/ [it] (2026-09-23 → 2026-09-25)
- https://agendasabauda.eu/it/evenement/storie-di-terra-di-pietra-e-di-uomini-2/ [it] (2026-09-23 → 2026-09-26)
- https://agendasabauda.eu/it/evenement/le-lunette-del-castello-di-issogne-2/ [it] (2026-09-23 → 2026-09-26)
- https://agendasabauda.eu/it/evenement/una-rilettura-dei-monumenti-cittadini-2/ [it] (2026-09-23 → 2026-09-26)
- https://agendasabauda.eu/it/evenement/la-chiave-della-rinascita-di-un-tesoro-del-1462-2/ [it] (2026-09-23 → 2026-09-27)
- https://agendasabauda.eu/it/evenement/deux-expositions-de-barbara-tutino-a-cogne-et-au-forte-di-bard-2/ [it] (2026-08-08 → 2026-10-11)
- https://agendasabauda.eu/it/evenement/dialogos-artisanat-et-images-de-devotion-exposition-itinerante-2/ [it] (2026-09-15 → 2027-02-07)
- https://agendasabauda.eu/it/evenement/architettura-ad-alta-quota-evoluzione-storica-del-bivacco-2/ [it] (2026-09-25 → 2026-09-25)
- https://agendasabauda.eu/it/evenement/memorie-darchivio-2/ [it] (2026-09-25 → 2026-09-25)
- https://agendasabauda.eu/it/evenement/a-turin-la-recherche-sort-des-laboratoires-pour-investir-le-parc-2/ [it] (2026-09-25 → 2026-09-26)
- https://agendasabauda.eu/evenement/alla-scoperta-del-complesso-dei-balivi/ [fr] (2026-09-26 → 2026-09-26)
- https://agendasabauda.eu/evenement/il-presbiterio-di-sarre-ritrova-il-suo-splendore-2/ [fr] (2026-09-26 → 2026-09-26)
- https://agendasabauda.eu/it/evenement/nutrire-il-benessere-un-chef-spatial-et-un-medecin-nutritionniste-2/ [it] (2026-09-26 → 2026-09-26)
- https://agendasabauda.eu/it/evenement/tra-acqua-terra-e-memoria-leri-e-lucedio-le-patrimoine-qui-renait-2/ [it] (2026-09-26 → 2026-09-26)
- https://agendasabauda.eu/it/evenement/passeggiata-botanica-a-villa-della-regina-la-vigne-du-xviie-siecle-2/ [it] (2026-09-26 → 2026-09-26)
- https://agendasabauda.eu/it/evenement/il-presbiterio-di-sarre-ritrova-il-suo-splendore/ [it] (2026-09-26 → 2026-09-26)
- https://agendasabauda.eu/it/evenement/il-castello-di-saint-germain-unicona-della-valle-daosta-medievale-2/ [it] (2026-09-26 → 2026-09-26)
- https://agendasabauda.eu/it/evenement/alla-scoperta-del-complesso-dei-balivi-2/ [it] (2026-09-26 → 2026-09-26)
- https://agendasabauda.eu/it/evenement/chatel-argent-e-il-valore-culturale-delle-rovine-2/ [it] (2026-09-26 → 2026-09-26)
- https://agendasabauda.eu/it/evenement/dallautoma-al-telefono-il-genio-di-innocenzo-manzetti-2/ [it] (2026-09-26 → 2026-09-26)
- https://agendasabauda.eu/it/evenement/cercami-tra-il-bianco-della-neve-2/ [it] (2026-09-26 → 2026-09-26)
- https://agendasabauda.eu/it/evenement/tissus-dhistoire-2/ [it] (2026-09-26 → 2026-09-26)
- https://agendasabauda.eu/it/evenement/cappella-di-san-giuseppe-dix-ans-de-restauration-sachevent-a-gressoney-2/ [it] (2026-09-26 → 2026-09-26)
- https://agendasabauda.eu/it/evenement/larte-del-legno-2/ [it] (2026-09-26 → 2026-09-26)
- https://agendasabauda.eu/it/evenement/piccoli-custodi-delle-erbe-di-ieri-2/ [it] (2026-09-26 → 2026-09-26)
- https://agendasabauda.eu/it/evenement/i-segreti-della-maison-de-thomas-trois-siecles-de-savoir-faire-alpin-2/ [it] (2026-09-26 → 2026-09-26)
- https://agendasabauda.eu/it/evenement/coucher-de-soleil-a-lalto-forte-une-visite-exceptionnelle-a-gavi-2/ [it] (2026-09-26 → 2026-09-26)
- https://agendasabauda.eu/it/evenement/le-chateau-dussel-rouvre-ses-tours-aux-dessins-de-francesco-corni-2/ [it] (2026-09-26 → 2026-09-27)
- https://agendasabauda.eu/it/evenement/viaggio-alla-scoperta-della-cultura-walser-2/ [it] (2026-09-26 → 2026-09-27)
- https://agendasabauda.eu/it/evenement/dai-segnali-di-fuoco-alle-onde-elettromagnetiche-storia-e-futuro-2/ [it] (2026-09-26 → 2026-09-27)
- https://agendasabauda.eu/it/evenement/il-volo-della-colomba-franco-perrotti-au-ciel-anthropise-courmayeur-2/ [it] (2026-09-26 → 2026-09-27)
- https://agendasabauda.eu/it/evenement/impara-larte-della-tessitura-2/ [it] (2026-09-26 → 2026-09-27)
- https://agendasabauda.eu/it/evenement/dalla-terra-alla-cura-les-plantes-qui-soignent-au-jardin-des-anciens-2/ [it] (2026-09-26 → 2026-09-27)
- https://agendasabauda.eu/it/evenement/parfum-de-deveteya-2/ [it] (2026-09-26 → 2026-09-27)
- https://agendasabauda.eu/evenement/piante-ieri-oggi-e-domani/ [fr] (2026-09-27 → 2026-09-27)
- https://agendasabauda.eu/it/evenement/il-cuore-idroelettrico-di-montjovet-2/ [it] (2026-09-27 → 2026-09-27)
- https://agendasabauda.eu/it/evenement/il-castello-di-introd-e-larmonia-della-trasformazione-continua-2/ [it] (2026-09-27 → 2026-09-27)
- https://agendasabauda.eu/it/evenement/dal-segno-al-gioco-2/ [it] (2026-09-27 → 2026-09-27)
- https://agendasabauda.eu/it/evenement/piante-ieri-oggi-e-domani-2/ [it] (2026-09-27 → 2026-09-27)
- https://agendasabauda.eu/it/evenement/au-palazzo-avec-carlo-alberto-activites-pour-familles-aux-musei-reali-2/ [it] (2026-09-27 → 2026-09-27)
- https://agendasabauda.eu/it/evenement/chasse-au-tresor-a-la-margaria-de-racconigi-les-enfants-sur-2/ [it] (2026-09-27 → 2026-09-27)
- https://agendasabauda.eu/it/evenement/torna-in-valle-daosta-il-grand-continent-summit-valledaostaglocal-it-2/ [it] (2026-12-03 → 2026-12-06)
