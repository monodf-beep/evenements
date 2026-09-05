# Curiosités — une série d'articles, pas une catégorie d'événements

**Décision de Franck, 05/09/2026** : « il faudrait que les articles répondent à des intentions
de recherche et des titres catchy comme "12 curiosités de Turin", "les 7 curiosités de
Chambéry" ». Ce document dit ce qu'on a en main, ce que les SERP montrent vraiment, et dans
quel ordre faire la série. Il ne contient aucun article.

## 1. D'où ça vient

La home a un bloc « Tuiles secondaires » (2 × 2 : Concerts, Musées, Curiosités, En famille).
La tuile Curiosités mène à la **catégorie d'événements** `curiosites` (terme 344 FR, 346 IT).
Vérifié le 05/09 par l'API : **zéro fiche, dans les deux langues, depuis toujours** — la page
répond 200 et n'affiche rien. Le pipeline ne connaît que onze catégories, l'évaluateur ne
rangera jamais rien là-dedans : la page restera vide tant qu'on ne change pas de nature.

Et la catégorie porte déjà du contenu, au mauvais endroit : sa **description** WordPress
contient cinq anecdotes rédigées (le taureau de la piazza San Carlo, le doigt de Christophe
Colomb, Ciamberì l'exonyme de Chambéry, Nizza Marittima contre Nizza Monferrato, les sigles
des provinces). Personne ne lit une description de catégorie vide. Ce sont des articles en
puissance.

## 2. Ce que disent les SERP (relevé du 05/09, requêtes FR et IT)

Notre propre doctrine (`docs/INTENTIONS_RECHERCHE_SEO.md` §1) dit : **ne pas se battre sur
l'intention A** (« que faire à [ville] », listicle intemporel tenu par les géants). « 12
curiosités de Turin » est de l'intention A. Il faut donc regarder qui tient la sous-niche
« curiosités / insolite », pas se contenter de la règle.

| Requête | Qui occupe la première page | Verdict |
|---|---|---|
| « curiosités Turin insolite » (FR) | Vanupied, The Wom Travel, La Souris globe-trotteuse, Voyages et Enfants, Viator | blogs de voyage à autorité moyenne, pas TripAdvisor/Routard |
| « Torino curiosità cose strane » (IT) | guidatorino, tolove.it, Torino Cronaca, blogs perso | presse locale + blogs : dense, verrouillé pour un site neuf |
| « Chambéry insolite curiosités » (FR) | TripAdvisor, Carnet d'escapades, Savoie News, OT Chambéry Montagnes | dense |
| « Chambéry curiosità cosa vedere » (IT) | Ti racconto un viaggio, itabus, informagiovani-italia, valigia2mezzo | **mince** : pas de presse, pas d'OT, blogs génériques |
| « Annecy curiosità cose insolite » (IT) | Viator, Fasthotel, worldcitytrail, hotels.com | **mince**, et surtout commercial |
| « Aosta curiosità insolite » (IT) | lovevda.it, comuni-italiani, blogs perso | moyen |
| « Aoste curiosités insolites » (FR) | lovevda.it, Le Bon Roadtrip, Generation Voyage | moyen |
| « Nice insolite curiosités » (FR) | livre « Nice secret et insolite », La Souris globe-trotteuse, Funbooker, nicesecret.co | dense |

Sur agendasabauda.eu, Search Console (90 jours, 91 requêtes vues) ne montre **aucune**
impression sur « curiosit », « insolite » ou « secret » : le sujet part de zéro, et ce zéro a
son dénominateur.

**Ce que ça donne.** Frontalement, dans la langue du lecteur local, on perd (Turin en italien,
Chambéry en français). **Là où le bilinguisme fait la différence, c'est en langue croisée** :
un Turinois qui cherche Chambéry ou Annecy en italien tombe sur des blogs génériques ; un
Savoyard qui cherche Turin ou Aoste en français tombe sur trois blogs de voyage. C'est
exactement la promesse de l'agenda — « l'autre versant » — et c'est le seul angle où un site
neuf a une chance. Chaque article existe dans les deux langues de toute façon ; c'est l'ORDRE
de production et le soin apporté à la version croisée qui changent.

## 3. Les règles de la série

1. **Une source officielle par curiosité, ou pas de curiosité.** Franck, 05/09 : « on se
   base uniquement sur les infos officielles ». Sources admises : MuseoTorino (encyclopédie
   officielle de la Ville), comune.torino.it, Treccani, Città di Aosta et lovevda.it, Ville
   de Chambéry et Chambéry Montagnes, Ville de Nice et Nice Tourisme, Ville et musées
   d'Annecy, monuments historiques (POP / Mérimée). Un blog de voyage sert à trouver la
   piste, jamais à la sourcer.
2. **Le nombre du titre est le nombre réel.** « 12 curiosités » = douze entrées sourcées. Le
   slug ne porte PAS le nombre (`/curiosites-turin/`, `/curiosita-torino/`) : le titre peut
   passer de 7 à 12 sans casser l'adresse.
3. **Le vocabulaire de l'agenda** (`config/vocabulaire_interdit.json`) s'applique : jamais
   « royaume de Sardaigne », « espace alpin », « Venise des Alpes ». La description actuelle
   de la catégorie contient « Sous le royaume de Sardaigne » — à corriger en reprenant le
   texte (proposé : « Au XIXe siècle, l'administration sarde italianisait les toponymes »).
4. **Une curiosité est un fait vérifiable et datable**, pas une activité commerciale (le
   « vol en parapente insolite » des SERP d'Annecy n'a rien à faire ici).
5. **Le lien vers l'agenda** : chaque article se termine par un renvoi vers la page hub de la
   ville (« et ce week-end à Turin »), pour que l'intention A nourrisse l'intention B, la
   nôtre.

## 4. Où ça vit

- Type `post`, comme les six guides existants (« Expositions à Turin 2026 », « Où manger
  niçois »…), qui sont dans la catégorie d'articles `guides` / `guide-it`.
- **Nouvelle catégorie d'articles** `curiosites` (FR) / `curiosita` (IT) — catégorie de
  POSTS, à ne pas confondre avec la catégorie d'ÉVÉNEMENTS du même nom, qui sort de la tuile
  et du menu.
- La tuile « Curiosités » du bloc 2 × 2 (pages WP 928 / 1717) pointe vers l'archive de cette
  catégorie d'articles **le jour où elle contient au moins trois articles**. Avant, elle
  reste une tuile vers une page vide ; si la série tarde, la retirer est préférable.
- Titres FR / IT :
  « Les 12 curiosités de Turin que les Turinois eux-mêmes oublient » /
  « Le 12 curiosità di Torino che anche i torinesi dimenticano ».
  Le gabarit : *[N] curiosités de [Ville]* + une promesse courte. Pas d'année dans le titre
  (contenu intemporel, à l'inverse des guides).

## 5. Le stock, et l'ordre

| Ville | Langue à soigner d'abord | Déjà rédigé | Pistes relevées dans les SERP, **à sourcer avant usage** | Cible |
|---|---|---|---|---|
| Turin | FR | taureau San Carlo, doigt de Colomb | Fetta di Polenta (Antonelli, 54 cm), Portone del Diavolo (via XX Settembre), sous-marin Andrea Provana au Valentino, bestiaire sculpté des façades, tunnels du siège de 1706, Villaggio Leumann | 12 |
| Chambéry | IT | Ciamberì | Fontaine des Éléphants « quatre sans cul », trompe-l'œil de la cathédrale, éléphants au sol du parcours, allées et passages couverts, les Charmettes | 7 |
| Aoste | FR | — | cryptoportique, acoustique du théâtre romain, cimetière aux inscriptions françaises, cadrans solaires du centre, Arc d'Auguste et son toit | 7 |
| Annecy | IT | — | le Thiou, 3,5 km, un des plus courts de France ; les cinq vies du Palais de l'Île ; Pont des Amours | 7 |
| Nice | IT | Nizza Marittima | boulets de 1543 dans les façades, Catherine Ségurane, chapelle au premier étage, cascade de Gairaut, cimetière russe | 10 |
| Piémont (provinces) | FR | sigles des provinces | — | article transversal, plus tard |

Ordre proposé : **Turin FR → Chambéry IT → Aoste FR → Annecy IT → Nice IT**, chacun avec
sa jumelle dans l'autre langue. Cinq articles, dix pages. On mesure à 90 jours dans Search
Console (les requêtes « curiosit / insolite / curiosità » par ville) avant d'en écrire
d'autres.

## 6. Ce que ça ne change pas

La priorité SEO reste « que faire ce week-end à [ville] » (`docs/INTENTIONS_RECHERCHE_SEO.md`
§3). Cette série est un pari latéral, borné à cinq villes, qui rend au passage une tuile de
la home honnête. Elle ne passe pas par le pipeline d'événements : ce sont des textes
éditoriaux, relus par Franck avant publication comme les guides.
