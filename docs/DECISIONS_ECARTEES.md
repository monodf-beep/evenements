# Décisions écartées — et POURQUOI (à ne pas ré-explorer)

*Registre des pistes qu'on a envisagées puis rejetées. But : ne pas y revenir. Si une de ces
idées ressurgit, relire la colonne « Pourquoi ça ne marche pas » avant d'en rediscuter.*

*La décision retenue est dans `STRATEGIE_MARQUE_ET_TERRITOIRES.md` (version simple, définitive).*

---

## A. Architecture & territoires

### ❌ Sous-domaines par ville/territoire (`annecy.agendasabauda.eu`)
**Pourquoi non** : Google traite chaque sous-domaine comme un **site séparé** → l'autorité SEO
(déjà faible, site neuf) est **fragmentée**, chacun repart de zéro. + gérer ça sur un WordPress
= Multisite, lourd et fragile.
**À la place** : **un domaine, des sous-répertoires** (`/fr/territoire/savoie/`, `/fr/ville/annecy/`).

### ❌ Sites séparés par territoire (un site Savoie, un site Piémont…)
**Pourquoi non** : pour un opérateur solo, **4× l'autorité SEO à bâtir**, 4× la maintenance,
4× les pages légales, et on **perd la signature « Sabaudo »** (le transfrontalier, le concept
unique). Le FR/IT se gère par `/fr/` `/it/` sur un seul domaine, pas par des sites distincts.
**À la place** : un seul site, un seul domaine.

### ❌ Lancer un seul territoire (Savoie) puis déployer le reste
**Pourquoi non** : on serait **catalogués « site savoyard » pour toujours** ; quand le Piémont
arrive, le Piémontais dit « pas pour nous ». **Un positionnement de départ colle et ne se
rattrape pas.** Modèle inverse (bon) : Nos Alpes / Le Alpi = bilingue transfrontalier dès le
jour 1.
**À la place** : **les 4 territoires, bilingue, d'emblée.**

---

## B. Home & détection du territoire (le débat le plus long)

### ❌ Personnaliser la home en devinant le territoire (« cercles concentriques »)
**Pourquoi non** : ça oblige à **détecter** le territoire de l'utilisateur — or aucune détection
n'est fiable (voir ci-dessous). Sur-ingénierie. GuidaTorino (le modèle) n'a **aucune** perso et
marche par la **profondeur de contenu + le SEO**.
**À la place** : home = **orientation** ; le « local d'abord » se fait dans les hubs (l'URL = le
territoire) + le choix explicite d'une porte.

### ❌ Détection automatique par IP
**Pourquoi non** : en itinérance, le **« home routing »** tunnelle le trafic jusqu'au pays
d'origine → **une SIM française à Turin sort en IP française**. L'IP géolocalise au domicile,
pas à la position réelle. **Non fiable** pour exactement le cas qui compte (le voyageur).

### ❌ Cookie qui redirige/ancre silencieusement vers le dernier territoire
**Pourquoi non** : **il t'ancre** — si tu bouges (Savoyard à Turin), il te sert quand même la
Savoie. Mauvaise expérience.
**À la place** : le cookie = **raccourci mémorisé PROPOSÉ** (« ↩ Reprendre en Savoie ») +
bandeau, **jamais imposé** par redirection.

### ❌ Popup de géolocalisation (GPS) à l'arrivée
**Pourquoi non** : intrusif, souvent refusé. On ne demande pas la position à l'entrée.
**À la place** : bouton **opt-in « 📍 Près de moi »** (GPS déclenché **par l'utilisateur** quand
il veut du local autour de lui) — **en v2**, pas au lancement.

### ❌ Home = feed de tous les événements des 4 territoires
**Pourquoi non** : c'est **le bruit qu'on refuse depuis le début** (un Savoyard ne veut pas un
mur d'événements niçois). C'est le piège dans lequel la « vitrine » peut retomber.
**À la place** : home = **best-of curé et ÉQUILIBRÉ** (1-2 temps forts/territoire), pas exhaustif.

### ❌ Deux axes co-égaux « territoire » et « activité » sur la home
**Pourquoi non** : ça **disperse**. Le premier filtre d'un humain = **où je suis**.
**À la place** : **territoire primaire** (on entre dans son territoire), **activité à
l'intérieur**. Les vues « activité transversale » (ex. toutes les sagre des 4 territoires) =
**bonus de découverte**, pas le cœur.

---

## C. Bilinguisme

### ❌ Traduire toutes les fiches (≈1900) dans les deux langues
**Pourquoi non** : **intenable en solo** ; et la **traduction automatique en masse** est
signalée comme **spam par Google** (+ contraire à la charte « ne pas obfusquer »).
**À la place** : **interface/hubs 100 % bilingues** ; **fiches en langue d'origine** ; traduction
**manuelle des seuls temps forts**.

---

## D. SEO / indexation (pièges techniques, déjà tranchés)

### ❌ Compter sur le carrousel « Événements » de Google
**Pourquoi non** : **pas disponible en France ni en Italie** (régions non supportées). Le schema
Event reste utile (indexation propre + moteurs IA), mais **pas** pour ce widget chez nous.

### ❌ Google Indexing API / services « d'indexation instantanée » pour les événements
**Pourquoi non** : l'Indexing API est **réservée à JobPosting et BroadcastEvent** (lives vidéo),
**pas** aux événements culturels ; les services « instant » la détournent → indexation éphémère
+ **risque de révocation**.
**À la place** : sitemaps + `lastmod` fiable + liens internes + **IndexNow (Bing)** +
demande GSC manuelle pour 2-3 temps forts/semaine.

### ❌ « Instant Indexing » Google de RankMath
**Pourquoi non** : il utilise l'Indexing API restreinte. → **IndexNow OUI (Bing), Instant
Indexing Google NON.**

### ❌ News sitemap pour les fiches événements
**Pourquoi non** : réservé à l'**actualité quotidienne** (critères Google News) — un agenda n'y
est pas éligible.

### ❌ Faire tourner l'agent SEO (LLM) sur toute la masse d'événements
**Pourquoi non** : coût ingérable ; la masse doit être **parfaite par le gabarit** (template).
**À la place** : agent SEO **réservé aux événements phares** (5-15) ; le JSON-LD (gratuit) pour
tous.

---

## E. Ce qu'on garde en tête comme risque (pas une idée écartée, un point de vigilance)
- **Déséquilibre de couverture** : tu sources beaucoup en Savoie, le meilleur est souvent à
  Turin → risque de paraître « site savoyard » OU « site turinois ». **Forcer l'équilibre** sur
  la home et dans le sourcing.
- **Le vrai enjeu n'est pas l'UX, c'est le contenu** (profond, équilibré, vraiment bilingue) +
  les **backlinks locaux**. Ne pas re-sur-concevoir l'interface au détriment du contenu.
