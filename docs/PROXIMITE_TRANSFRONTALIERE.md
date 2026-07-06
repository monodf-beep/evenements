# Proximité transfrontalière — « aller de l'autre côté pour tel événement »

*Le module « ça vaut le déplacement » (ex. « Aller à Turin pour X », « Aller en Savoie pour Y »)
est l'angle de marque le plus défendable d'Agenda Sabauda : personne (ni GuidaTorino, ni les OT)
ne relie les deux versants. Mais il ne marche que sur les VRAIES adjacences géographiques. Ce doc
fixe la carte des franchissements et les règles éditoriales.*

---

## 1. Le fait structurant : DEUX grappes, pas un cercle

Les 4 territoires ne sont pas équidistants. Ils forment **deux ensembles** reliés par des passages
précis — et **entre les deux grappes, il n'y a pas de proximité** (Nice ↔ Aoste ≈ 4-5 h : jamais
de cross-sell).

- **Grappe NORD (alpine)** : Haute-Savoie · Savoie · Vallée d'Aoste · Piémont — nouées autour du
  **tunnel du Mont-Blanc** et du **tunnel du Fréjus**. C'est ici que le module est le plus fort.
- **Grappe SUD (méditerranéenne)** : Nice/Alpes-Maritimes · Monaco · Cuneo (Piémont sud) · Ligurie —
  nouées par le **littoral** et le **col/tunnel de Tende**.

Le Piémont est le seul territoire présent dans les DEUX grappes (Turin au nord, Cuneo au sud).

## 2. Tableau des proximités (à valoriser en priorité)

| Depuis (audience) | Voisin transfrontalier | Franchissement | Temps porte-à-porte | Grande destination à mettre en avant | Saison |
|---|---|---|---|---|---|
| **Haute-Savoie** (Chamonix) | Vallée d'Aoste | Tunnel du Mont-Blanc | ~1 h (Chamonix–Aoste) | Aoste, Courmayeur | toute l'année |
| **Savoie** (Maurienne) | Piémont | Tunnel du Fréjus | ~2 h (Modane–Turin) | **Turin**, Susa, Bardonecchia | toute l'année |
| **Savoie** (Tarentaise) | Vallée d'Aoste | Col du Petit-Saint-Bernard | ~1 h 30 (Bourg-St-Maurice–Aoste) | Aoste, La Thuile | **été seulement** (col fermé l'hiver) |
| **Savoie** (Haute-Maurienne) | Piémont | Col du Mont-Cenis | ~1 h 30 (Val-Cenis–Susa) | Susa, Turin | **été seulement** |
| **Vallée d'Aoste** | Piémont | Autoroute A5 | ~1 h 15 (Aoste–Turin) | **Turin** | toute l'année |
| **Vallée d'Aoste** | Haute-Savoie / Savoie | Tunnel du Mont-Blanc | ~1 h (Aoste–Chamonix) | Chamonix, Megève, Annecy (~1 h 30) | toute l'année |
| **Piémont** (Turin) | Vallée d'Aoste | A5 | ~1 h 15 | Aoste, Cogne, Cervinia | toute l'année |
| **Piémont** (Turin/Susa) | Savoie | Fréjus / Mont-Cenis | ~2 h | Maurienne, Chambéry, Val Cenis | toute l'année (Fréjus) |
| **Alpes-Maritimes** (Nice) | **Monaco** | littoral (A8 / train) | ~30 min | Monaco (spectacles, expos, sport) | toute l'année |
| **Alpes-Maritimes** (Roya) | Piémont (Cuneo) | Col / tunnel de Tende | ~2 h (Nice–Cuneo) | Cuneo, Limone Piemonte | ⚠ tunnel : vérifier la réouverture ; col = été |
| **Alpes-Maritimes** (Nice) | Ligurie (IT, *hors périmètre*) | A8 / frontière | ~45 min (Nice–Vintimille) | Vintimille, San Remo | toute l'année (bonus découverte) |

> ⚠ **Tunnel de Tende** : endommagé (tempête Alex, 2020), réouverture partielle en cours — vérifier
> l'état avant de promettre « 2 h ». En attendant, la liaison Nice–Cuneo est plus longue.
> **Cols saisonniers** (Petit-Saint-Bernard, Mont-Cenis) : ne valoriser qu'en été.

## 3. Règles éditoriales (pour ne pas se tirer une balle dans le pied)

1. **Uniquement les TRÈS gros événements** (score élevé, disons ≥ 8) : on ne demande à personne de
   traverser un tunnel pour un vide-grenier. Long terme, pas au lancement.
2. **Toujours étiqueter le trajet réel** : « **Turin — 2 h par le Fréjus** », « **Aoste — 1 h par
   le Mont-Blanc** ». C'est l'information qui déclenche (ou non) le déplacement. Jamais « à côté »
   sans le temps/moyen.
3. **Respecter les grappes** : un module Nice ne propose JAMAIS Aoste/Savoie (trop loin) — il
   propose **Monaco**, puis **Cuneo/Ligurie**. Un module Savoie propose **Turin/Aoste**.
4. **Prérequis de sourcing** : n'afficher le module que si le voisin est réellement sourcé. Un
   « De l'autre côté des Alpes » à moitié vide décrédibilise. Mieux vaut pas de module que faux.
5. **Saisonnalité** : masquer les entrées « col d'été » d'octobre à mai.

## 4. Où ça vit dans le design

- **Principalement sur le HUB TERRITOIRE** (contextuel, fort en SEO) : sur `/territoire/savoie/`,
  un encart **« De l'autre côté des Alpes »** → 2-3 pépites d'Aoste/Turin avec le trajet. C'est la
  version canonique (déjà prévue dans la stratégie).
- **Optionnellement sur la HOME** : un petit module **« Ça vaut le déplacement »** avec les 2-3
  plus gros rendez-vous transfrontaliers du moment (chacun étiqueté du trajet). Comme la home n'a
  pas de territoire actif, on y montre les paires **de façon générique** (« Turin, 2 h par le
  Fréjus »), pas « depuis chez toi ».
- **Un dossier éditorial récurrent** (« Le fil ») : « 5 raisons de passer le tunnel ce mois-ci » —
  du contenu à forte valeur, pile dans l'angle Sabaudo, que Cultura Sabauda peut signer.

## 5. Implémentation (plus tard — pas au lancement)

Modélisable comme un `feed: "voisin"` dans `utils/home_modules.py` : pour un territoire T, requête
= événements **du/des territoire(s) voisin(s) de T** (table §2), score ≥ 8, à venir, limite 3.
La carte de proximité ci-dessus = la table de correspondance. **Bloqué tant que** (a) le voisin
n'est pas sourcé et (b) le hub territoire n'existe pas — donc post-lancement.
