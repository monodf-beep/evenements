# Prompt pour Claude Design — Agenda Sabaudo

*À coller dans Claude Design pour produire la maquette. Version alignée sur la décision finale
(simple, sans personnalisation). Copie tout ce qui est entre les lignes.*

---

Tu conçois l'UX/UI de **Agenda Sabaudo**, l'agenda culturel **transfrontalier bilingue FR/IT** de
l'espace alpin occidental — **4 territoires** : Savoie/Haute-Savoie, Piémont, Vallée d'Aoste,
Nice/Alpes-Maritimes. Édité par le média **Cultura Sabauda**. Site WordPress.

**Modèle d'expérience : guidatorino.com** — un guide urbain sobre et dense qui « marche » par la
clarté et le contenu, pas par des effets. On en reprend l'esprit (cartes à date visible, pages
catégorie et lieu, hubs « ce week-end » evergreen) en **plus moderne et responsive**.

## Principes NON négociables (anti-« design slop »)
- **Sobriété éditoriale = le branding.** Interdits : dégradés SaaS violet/bleu, glassmorphism,
  blobs, hero vide à slogan centré, sections « features », carrousels automatiques, animations
  décoratives, emoji en guise d'icônes. Chaque pixel sert une **date, un lieu, un titre, une
  photo**.
- **Tout est du texte HTML réel** (jamais de titre ou de date dans une image).
- **Mobile-first**, responsive, accessible (contrastes AA, focus visibles).
- **Bilingue** : commutateur **« FR | IT » en texte** (jamais de drapeau).

## Charte (applique-la, la DA reste à toi)
- **Marine profond** `#1a2b4a` (marque : titres, header, footer).
- **Rouge de Savoie** `#c8102e` = **le seul accent** (CTA, filets, urgences). Rare = signifiant.
- **Couleurs territoire** (pilules) : Savoie bleu `#1a56b0` · Piémont rouge `#b3261e` · Vallée
  d'Aoste vert `#1e7d34` · Nice orange `#b25e00`.
- Logotype « Agenda Sabaudo » + point rouge ; mention « édité par Cultura Sabauda » discrète.
- Typo : à toi (piste : serif éditoriale pour les titres + sans lisible pour les données). Icônes
  au trait, pas d'emoji dans l'UI.

## La règle de fond (à respecter absolument)
- La **home n'est PAS un flux** de tous les événements, et elle **ne devine PAS** le territoire de
  l'utilisateur (pas de géoloc, pas de personnalisation). Elle est une **page de marque +
  d'orientation** : elle prouve que l'espace Sabaudo vit, et elle **oriente**.
- **Axe PRIMAIRE = le territoire** : la 1ʳᵉ décision du visiteur est « où ? » (les 4 territoires).
  L'**activité (catégorie) vient à l'intérieur** du territoire. Ce ne sont PAS deux menus égaux.
- Le **local d'abord** se vit **dans les pages territoire/ville**, pas sur la home.

## Écrans à produire (desktop + mobile)

1. **Home** (marque + orientation) :
   - header (logo, nav temporelle : Aujourd'hui · Ce week-end · Cette semaine · Agenda ; loupe ;
     FR|IT) ;
   - héro : 1-2 temps forts de l'espace Sabaudo ;
   - **best-of ÉQUILIBRÉ** : quelques temps forts avec **au moins 1-2 par territoire** (ni « site
     savoyard » ni « site turinois ») ;
   - **les 4 portes TERRITOIRE** (bloc majeur, chacune sa couleur) — l'axe primaire ;
   - rail des 11 catégories (dont « Gastronomie & Sagre ») ;
   - « Dernière chance » (expos qui finissent) ; bloc newsletter ; lien listicle « Les 10 du
     week-end » ; footer riche (4 territoires, 11 catégories, projet, FR|IT).
   - lien discret « ↩ Reprendre en [dernier territoire] » (proposé, jamais imposé).

2. **Hub territoire** (ex. Savoie) — LE cas d'usage local : H1 + intro ; « ce week-end en Savoie » ;
   flux local **filtrable par activité** (barre de filtres date + catégorie) ; bloc villes ;
   encart « De l'autre côté des Alpes » (2-3 pépites du Piémont — la signature transfrontalière).

3. **Hub catégorie** (ex. Concerts & Musique) : par défaut dans un territoire, + option vue
   transversale « les 4 territoires ».

4. **Fiche événement — MODE MINIMAL D'ABORD** (le cas majoritaire : beaucoup d'événements n'ont
   PAS d'article rédigé) : héro image (ou bannière territoire) + crédit photo ; badges d'état ;
   catégorie ; H1 ; lieu · ville · pilule territoire ; **bloc pratique** (dates humanisées,
   horaires, lieu + carte, prix / « Gratuit », bouton « Réserver — site officiel ») ; description
   courte ; « Vérifié le JJ/MM » ; **3 rails liés** (mêmes dates près d'ici · même territoire ·
   même catégorie). Puis le **mode riche** (avec article : chapô + corps + encadré « En pratique »).

5. **Hub temporel « Ce week-end »** : H1 avec dates + chapô éditorial + filtres territoire/
   catégorie + grille.

## Le composant central : la carte événement (4 variantes)
Invariants : image (ratio unique ~3:2), **date lisible SANS clic**, titre 2 lignes max, lieu +
ville, badge catégorie, **pilule territoire (sa couleur)**, badges d'état, « Gratuit » si
applicable, carte entièrement cliquable.
Variantes : **héro** · **standard** (grille) · **compacte/liste** (mobile, dense) · **dernière
chance** (bandeau d'urgence rouge).

## Badges d'état (système fermé)
`En cours` · `Dernier week-end` / `Plus que X jours` (rouge) · `Date à confirmer` (gris) ·
`Gratuit` · `Annulé`/`Reporté`.

## Livrables prioritaires
Si tu ne fais que trois choses, fais-les justes : **(1) la carte événement**, **(2) la fiche en
mode minimal**, **(3) la home (marque + 4 portes territoire + best-of équilibré)**. Si ces trois
sont justes, le site est juste.

## Ce qu'il ne faut PAS faire
Pas de home-feed, pas de sélecteur de territoire imposé à l'entrée, pas de géoloc, pas de deux
menus territoire/activité co-égaux, pas de carte sans date, pas de carrousel auto, pas de
drapeaux, pas d'emoji-icônes, pas de texte dans les images.
