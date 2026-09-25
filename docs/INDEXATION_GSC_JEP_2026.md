# Indexation Google des fiches des Journées du patrimoine — septembre 2026

Demandé par Franck le 24/09/2026 : « il faut indexer les nouveaux événements aussi… dans google search console via cowork », puis, le même jour : « faut demander plutôt les pages en italien pour ceux du Piémont qui aimeraient aller aux Journées européennes du patrimoine ».

## Ce qui est permis, et pourquoi pas plus

- **Pas d'API d'indexation Google** : elle est réservée aux offres d'emploi et aux diffusions en direct ; l'employer pour des événements expose à une sanction (`docs/AGENT_SEO_DASHBOARD_SPEC.md` §2).
- **Bing et les moteurs IndexNow** sont déjà prévenus à chaque publication par le snippet « CS - IndexNow » (Code Snippets n° 116, actif depuis le 30/07).
- **Google** : renvoi du sitemap (couvre tout) + demande manuelle d'indexation, **environ 10 par jour et par propriété** — d'où le tri ci-dessous.

## Pourquoi l'italien, et pas le français, pour le Piémont

Le public des Giornate piémontaises cherche en italien, sur google.it, des mots italiens
(« Giornate europee del patrimonio Torino », « apertura serale Racconigi »). La page
française de la même fiche a peu de chances de lui être montrée (c'est une
hypothèse raisonnable, pas une mesure : la Search Console le dira par langue dans
quelques semaines). Les dix demandes quotidiennes vont
donc aux pages **italiennes** des événements du Piémont, dans l'ordre de leur date ; les
pages françaises de la Vallée d'Aoste (plan précédent) passent au second rang.

## Vérifié avant de soumettre (24/09, vers 0h15)

**Première mesure : 7 des 30 pages italiennes étaient en `noindex` et hors sitemap**
(10572, 10539, 10990, 10615, 10620, 11003, 11010). Motif : cs-completude, « source
officielle absente ». Les jumelles françaises portaient pourtant la page cultura.gov.it.
Cause : `refresh_deplacement` (10h55) republiait les traductions avec une source vide. Il
appelle `publish_to_as` directement, et seul `publish_batch_as` héritait la source de
l'original. La passe de minuit la remettait, celle de 10h55 l'effaçait. **Corrigé dans le
dépôt** (commit ff534b7 : l'héritage vit dans `publish_to_as`, pour tous les appelants).

**Réparé sur le site le 24/09** : 29 fiches à venir ont repris la source de leur jumelle
(sauvegarde : option `cs_source_jumelle_avant_20260924`, une ligne au journal de chaque
fiche). Leur complétude a été recalculée, et 22 sont sorties de la liste « hors index ».
Quatre fiches n'ont de source d'aucun côté (WP#14, 2215, 3709, 8284) : elles n'ont pas été
touchées. Dix jumelles italiennes des Plaisirs de Culture (120xx) avaient aussi perdu leur
source ; elles n'étaient pas encore exclues de l'index, elles l'auraient été à la passe
suivante.

**Remesuré ensuite, de l'extérieur, sur les 30 pages** : 30 en **200**, 30 en **`index`**,
30 avec **canonique = elle-même**, 30 présentes dans `tribe_events-sitemap.xml`. Cinq
lectures avaient d'abord dépassé 40 s ; relancées une à une, elles ont toutes répondu en
2 s.

À savoir : l'ADRESSE des pages italiennes reprend le slug français de l'original. C'est
voulu depuis la création des traductions (« URL commune à la paire »). Google l'accepte ;
c'est le titre et le texte qui portent la langue.

## Consigne pour la session Cowork (à coller telle quelle, une fois par jour, avec la liste du jour — les adresses sont en /it/, c'est voulu)

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

## Jour 1 — 24/09 (événements du 26)

- https://agendasabauda.eu/it/evenement/musees-royaux-de-turin-ouverture-en-soiree-et-appartement-de-2/  — Musei Reali di Torino : apertura serale e appartamento di Margherita di Savoia (WP#10527)
- https://agendasabauda.eu/it/evenement/palazzo-carignano-les-appartements-des-princes-ouverts-en-soiree-2/  — Palazzo Carignano : Appartamenti dei Principi aperti in serata (WP#10525)
- https://agendasabauda.eu/it/evenement/reouverture-du-forte-di-gavi-avec-deux-expositions-fammi-un-quadro-2/  — Riapertura del Forte di Gavi con due mostre (WP#10570)
- https://agendasabauda.eu/it/evenement/coucher-de-soleil-a-lalto-forte-une-visite-exceptionnelle-a-gavi-2/  — Tramonto all’Alto Forte : visita guidata straordinaria a Gavi (WP#12361)
- https://agendasabauda.eu/it/evenement/visite-nocturne-au-forte-di-gavi-hommage-a-emily-dickinson-et-2/  — Visita serale al Forte di Gavi : omaggio a Emily Dickinson (WP#10572)
- https://agendasabauda.eu/it/evenement/racconigi-ouvre-en-soiree-son-premier-etage-noble-pour-voir-specchi-2/  — Racconigi apre in serata il primo piano nobile (Specchi del Giappone) (WP#10538)
- https://agendasabauda.eu/it/evenement/a-racconigi-une-matinee-dans-le-jardin-secret-des-principini-2/  — Racconigi : una mattina nel giardino segreto dei Principini (WP#10536)
- https://agendasabauda.eu/it/evenement/vitae-il-sentimento-della-natura-ouverture-nocturne-au-chateau-daglie-2/  — Vitae. Il sentimento della Natura : apertura serale ad Agliè (WP#10526)
- https://agendasabauda.eu/it/evenement/journees-europeennes-du-patrimoine-a-labbaye-de-vezzolano-2/  — Giornate europee del patrimonio all’Abbazia di Vezzolano (WP#10535)
- https://agendasabauda.eu/it/evenement/industria-la-ville-romaine-se-raconte-avec-les-archeologues-2/  — Industria : la città romana raccontata dagli archeologi (WP#10575)

## Jour 2 — 25/09 (événements du 26)

- https://agendasabauda.eu/it/evenement/aperitivo-in-vigna-un-verre-au-coucher-du-soleil-dans-la-vigne-de-2/  — Aperitivo in Vigna a Villa della Regina (WP#10539)
- https://agendasabauda.eu/it/evenement/nutrire-il-benessere-un-chef-spatial-et-un-medecin-nutritionniste-2/  — Nutrire il benessere : uno chef spaziale a Villa della Regina (WP#11672)
- https://agendasabauda.eu/it/evenement/passeggiata-botanica-a-villa-della-regina-la-vigne-du-xviie-siecle-2/  — Passeggiata botanica a Villa della Regina (WP#11674)
- https://agendasabauda.eu/it/evenement/tra-acqua-terra-e-memoria-leri-e-lucedio-le-patrimoine-qui-renait-2/  — Tra acqua, terra e memoria : Leri e Lucedio (WP#11673)
- https://agendasabauda.eu/it/evenement/une-visite-guidee-retrace-lhistoire-du-chateau-de-serralunga-dalba-2/  — Visita guidata al castello di Serralunga d’Alba (WP#10990)
- https://agendasabauda.eu/it/evenement/novare-ouvre-ses-archives-sceaux-et-actes-anciens-a-decouvrir-2/  — Archivio sicuro, documenti protetti (Novara) (WP#10651)
- https://agendasabauda.eu/it/evenement/giornate-europee-del-patrimonio-a-larchivio-di-stato-di-asti-2/  — Giornate europee del patrimonio all’Archivio di Stato di Asti (WP#10568)
- https://agendasabauda.eu/it/evenement/cappella-di-san-sebastiano-les-fresques-inedites-de-caprauna-ouvertes-2/  — Cappella di San Sebastiano : affreschi inediti di Caprauna (WP#10612)
- https://agendasabauda.eu/it/evenement/les-trains-racontent-leurs-histoires-une-apres-midi-en-famille-2/  — I treni raccontano le loro storie (Savigliano) (WP#10615)
- https://agendasabauda.eu/it/evenement/a-lu-luigi-onetti-1876-retrouve-ses-tresors-le-museo-se-renove-2/  — A Lu, Luigi Onetti ritrova i suoi tesori (WP#10620)

## Jour 3 — 26/09 (événements du 27)

- https://agendasabauda.eu/it/evenement/facce-da-medaglia-frappez-votre-propre-medaille-aux-musei-reali-2/  — Facce da Medaglia ai Musei Reali (WP#11001)
- https://agendasabauda.eu/it/evenement/au-palazzo-avec-carlo-alberto-activites-pour-familles-aux-musei-reali-2/  — A Palazzo con Carlo Alberto : attività per famiglie (WP#12357)
- https://agendasabauda.eu/it/evenement/chasse-au-tresor-a-la-margaria-de-racconigi-les-enfants-sur-2/  — Caccia al tesoro alla Margaria di Racconigi (WP#12362)
- https://agendasabauda.eu/it/evenement/reincanto-aux-giovani-cantori-di-torino-2/  — Reincanto : i Giovani Cantori di Torino a Villa della Regina (WP#10994)
- https://agendasabauda.eu/it/evenement/a-la-decouverte-daugusta-bagiennorum-2/  — Alla scoperta di Augusta Bagiennorum (WP#10996)
- https://agendasabauda.eu/it/evenement/visite-guidee-au-castello-biandrate-de-foglizzo-et-au-musee-des-balais-2/  — Castello Biandrate di Foglizzo e museo delle scope (WP#11003)
- https://agendasabauda.eu/it/evenement/archivio-di-stato-di-alessandria-ouvre-ses-portes-2/  — L’Archivio di Stato di Alessandria apre le porte (WP#10989)
- https://agendasabauda.eu/it/evenement/archeologie-en-piemont-conference-sur-les-collections-etrusques-et-2/  — Archeologia in Piemonte : conferenza al Castello di Agliè (WP#10988)
- https://agendasabauda.eu/it/evenement/messi-sullavviso-bandits-et-rebelles-des-archives-du-vercellais-1700-2/  — Messi sull’avviso : banditi e ribelli negli archivi del Vercellese (WP#11010)
- https://agendasabauda.eu/it/evenement/un-nouveau-site-archeo-minier-ouvre-a-bioglio-dans-loasi-zegna-2/  — A Bioglio un nuovo sito archeo-minerario nell’Oasi Zegna (WP#11012)

## Second rang — pages françaises de la Vallée d'Aoste (si le quota du jour n'est pas épuisé)

Plan d'origine, vérifié le 24/09 à 1h50 (200, canonique, sans noindex, dans le sitemap).
À ne prendre qu'après la liste italienne du jour.

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
