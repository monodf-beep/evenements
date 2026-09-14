# Titres — doctrine proposée, mesures, et ce qui manque aujourd'hui

**Statut : PROPOSITION à arbitrer par Franck (2026-09-15).** Rien ici n'est déployé. Les
sections 1 à 3 sont des mesures et des lectures de code ; les sections 4 à 8 sont des
règles proposées ; la section 9 est le tableau de décision.

Point de départ, Franck, 15/09 : « les titres doivent être compréhensibles du panel de
personas. Un francophone ne sait pas forcément à quoi correspondent les références qu'un
italophone saura : *Dopo l'8 settembre '43. Meridionali nella Resistenza* — qu'est-ce que
c'est, le 8 septembre ? Et si c'est long comme *Terra Madre Salone del Gusto quitte le
Lingotto pour investir le centre historique de Turin*, le francophone fatigue. »

---

## 1. Ce qu'on a mesuré (146 fiches en ligne, relevé du 10/09)

| mesure | valeur |
|---|---|
| mots par titre H1 | **médiane 12**, min 1, max 23 |
| titres > 10 mots | **107 / 146 — 73 %** |
| titres > 14 mots | 22 / 146 — 15 % |
| caractères | **médiane 73** ; > 70 car. : 82 / 146 — 56 % |
| titres FR au schéma « Nom : angle » | 47 / 110 |
| titres de 1 à 3 mots (nom nu) | 6 |

Les deux extrêmes cohabitent, et ce sont deux défauts différents :

- **trop long** — *La dernière fois qu'on a vu Bernard Stasi : le texte lauréat 2025 en
  mise en espace au Théâtre national de Nice (TNN)* (23 mots) ; *Bra's 2026 : quatre jours
  pour la saucisse, le fromage, le pain et le riz de Bra* (17) ;
- **nom nu** — *Chopin*, *Boîte Crânienne*, *Una Historia Americana*, *Shiftwork Festival* :
  le lecteur ne sait ni quoi, ni où.

Et une fiche viole une règle déjà écrite dans la charte (casse) : *pizza show a vercelli!*

Google tronque un `<title>` vers 60 caractères et un H1 n'a pas de limite technique — mais
un lecteur, si. 70 caractères, c'est deux lignes sur mobile.

## 2. Ce que la doctrine dit AUJOURD'HUI sur les titres

Une ligne. `docs/CHARTE_EDITORIALE.md` §4 : « **Titre** — informatif et incarné, pas
racoleur ». Et le prompt d'`enrich` répète exactement la même chose :
`"titre": "<titre informatif et incarné, pas racoleur>"`.

Rien sur la longueur. Rien sur la langue. Rien sur ce qu'on fait d'un nom propre italien
dans une fiche française. Rien sur les référents que l'autre public ne connaît pas. Rien
sur la ville. Le modèle remplit ce vide avec son réflexe de titreur de presse — le verbe
d'actualité (« quitte », « investit », « revient », « ravive »), la subordonnée, la
précision qui rallonge. **La médiane à 12 mots n'est pas une dérive du modèle, c'est
l'absence de consigne.**

Autocritique : ces trois derniers jours j'ai travaillé le **titre SEO** (clé en tête,
suffixe de marque, 60 caractères) pendant que le **H1 — celui que le lecteur lit** —
n'avait aucune règle. J'ai optimisé pour Yoast la partie que le lecteur ne voit pas.

## 3. Une fiche a QUATRE titres, écrits à trois moments par trois prompts

| champ | qui l'écrit | quand | où il sert |
|---|---|---|---|
| `title` (scrapé) | la source | scraping | repli si rien d'autre ; portillons de traduction |
| `article.titre` → **H1** | `enrich` | enrichissement | **ce que le lecteur voit** ; og:title |
| `seo_title` | `seo_batch` | après, séparément | `<title>` de la page (Google) |
| `seo_slug` | `seo_batch` | après | URL — **sauf la traduction, qui recopie le slug FR** |
| `image_alt` | publisher | publication | = `seo_keyphrase`, sinon `title` |

Trois conséquences, toutes vérifiées dans le code :

1. **Ils dérivent.** Le H1 est écrit avant que la clé SEO soit choisie ; la clé est choisie
   sur le corps, pas sur le H1. Un H1 qui dit « Terra Madre Salone del Gusto quitte le
   Lingotto… », un `<title>` qui dit « Terra Madre Turin 2026 — Agenda Sabauda », un slug
   qui dit `du-24-au-27-septembre-terra-madre-…` : trois formulations, et Google lit les
   trois.
2. **La traduction hérite du slug français** (`translate_events.py` l.740-741, « la fiche
   traduite reprend le slug de l'original », délibéré). 12 fiches italiennes publiées ont
   une URL en français, mesuré le 15/09.
3. **L'`alt` de l'image décrit l'événement, pas l'image.** Yoast s'en satisfait ; un
   lecteur d'écran, non.

## 4. Règles proposées — la FORME du titre H1

Déterministe partout où c'est possible : une règle qu'un script peut vérifier vaut mieux
qu'un jugement qu'un panel doit rendre.

**R1 — Schéma unique : `[Genre] Nom : angle`.** Le nom de l'événement d'abord,
deux-points, puis un angle qui dit *quoi* et, si le nom ne le dit pas, *où*. 47 titres FR
sur 110 le font déjà ; on généralise.

**Avec un mot de GENRE devant le nom quand celui-ci est dans l'autre langue** (Franck,
15/09 : « il faut que le lecteur francophone se raccroche à du français dans les premiers
mots »). Un seul mot, dans la langue du lecteur, qui dit ce que c'est avant le nom qu'il
ne connaît pas : *Festival Musicastelle Autumn Edition : …*, *Foire Bra's 2026 : …*,
*Salon Terra Madre : …*, *Fête de la Saint-Ours : …* (déjà le cas). Le francophone lit
« Festival » avant de lire un nom qu'il ne sait pas prononcer ; la marque reste dans les
premiers mots pour la requête et pour Yoast ; et sur la fiche italienne, c'est l'inverse
qui s'applique — *Fiera di Saint-Ours*, *Festival Musicastelle*. Pas de mot de genre quand
le nom est déjà dans la langue de la fiche (*Foire de Saint-Ours* n'a pas besoin de
« Fête »), ni quand il le porte (*Shiftwork Festival*).

**R2 — Longueur : 6 à 12 mots, 70 caractères au plus, angle ≤ 8 mots.** Le plancher
interdit le nom nu ; le plafond interdit la dépêche. C'est vérifiable par un script au
moment de la rédaction, avec une relance sur dépassement (contrôle déterministe, pas
« le LLM est stochastique »).

**R3 — Ce qui se garde dans sa langue, ce qui se traduit, ce qui sort du titre.**
Corrigé le 15/09 après l'objection de Franck : « *Dopo l'8 settembre '43*, est-ce
important, est-ce que ça apporte quelque chose au francophone ? Il pourrait être en
français. Par contre *Musicastelle Autumn Edition*, c'est le nom de l'événement, sa
marque. » La première version de cette règle mettait tout « nom propre » dans le même
sac ; il y a trois cas, et la distinction se fait sur **ce que le nom fait pour le
lecteur**, pas sur sa langue :

- **R3a — la MARQUE se garde telle quelle.** Le nom qu'on tape pour chercher l'événement,
  qu'on lit sur le billet et sur l'affiche : *Musicastelle Autumn Edition*, *Terra Madre
  Salone del Gusto*, *Bra's*, *Foire de Saint-Ours*. Le traduire ferait perdre le lecteur
  à l'entrée et perdre la requête à Google. Test : *quelqu'un cherche-t-il l'événement
  avec ces mots-là ?* Un nom d'édition, un festival, un salon, une fête récurrente :
  presque toujours oui.
- **R3b — le TITRE DESCRIPTIF se traduit.** Une conférence, une projection, une lecture,
  une exposition dont le « nom » est en fait une phrase qui dit le sujet : *Dopo l'8
  settembre '43. Meridionali nella Resistenza* n'est pas une marque, c'est un intitulé.
  Personne ne le tape dans Google en français, et il n'apporte rien au francophone qu'une
  traduction n'apporterait mieux. Le H1 français le dit en français : *Les partisans du
  Sud dans la Libération italienne : projection et débat au Polo del '900, Turin*.
  L'intitulé original va **dans le chapô**, en italique, pour que le lecteur le reconnaisse
  sur place. Test : *le nom est-il une phrase, ou un nom ?*
- **R3c — l'ŒUVRE ÉTABLIE prend le titre sous lequel la langue de la fiche la connaît.**
  *Le avventure di Pinocchio* → *Les Aventures de Pinocchio* ; *Il nome della rosa* → *Le
  Nom de la rose*. S'il n'existe pas de titre établi dans cette langue, l'original reste
  (R3a). Ni le rédacteur ni le détecteur n'ont à trancher seuls : c'est un fait qui se
  vérifie.
- **R3d — les NOMS DE PERSONNES ne sont dans le H1 que si le lecteur de la langue de la
  fiche les connaît.** *Nina Zilli et Mannarino* portent la fiche italienne ; dans la
  française, l'angle dit ce qu'ils sont — *deux voix de la pop italienne* — et les noms
  passent au chapô, où le lecteur curieux les trouve. **Qui juge « connu » ? Le persona de
  l'autre langue (P2)**, et personne d'autre : ni le rédacteur, ni un script, ni moi.
  C'est précisément le jugement pour lequel le panel existe.

**Conséquence, et elle est importante : les deux versions d'une fiche n'ont PAS le même
titre.** Ce n'est pas une traduction, c'est deux titres écrits pour deux lecteurs qui ne
partagent pas les mêmes référents — exactement ce que la charte §6 bis appelle
« ré-appliquer la charte en italien, pas translittérer ». Le portillon de traduction (§7)
doit donc juger la *cohérence* des deux titres (même événement, même lieu), jamais leur
*ressemblance*.

> FR : *Festival Musicastelle Autumn Edition : deux voix de la pop italienne à Saint-Vincent*
> IT : *Musicastelle Autumn Edition: Nina Zilli e Mannarino in concerto a Saint-Vincent*

(Le titre actuel — *Musicastelle Autumn Edition : Nina Zilli et Mannarino, week-end
concert-hébergement les 3 et 4 octobre* — cumule R3d et R2 : les dates sont dans
l'encadré, pas dans le titre.)

**R3a contre R3b — qui décide ?** Le test « nom ou phrase » est net sur les cas de
Franck, mais *Sotto i portici del Risorgimento*, *Donne controcorrente*, *Carla With Love*
sont entre les deux : des intitulés de programme que l'organisateur utilise comme des
marques. **C'est le panel qui tranche** (Franck, 15/09 : « ça doit être le panel de
personas justement ») — le persona de la langue de la fiche reçoit le nom seul et dit s'il
le reconnaîtrait sur une affiche ou s'il a besoin qu'on lui dise ce que c'est. Et **en cas
de doute persistant, on garde l'original avec un mot de genre et une glose** (R1 + R5) :
un nom gardé à tort coûte un mot de plus ; un nom traduit à tort fait perdre le lecteur à
l'entrée et perd la requête.

Ce qui reste vrai de la première version : **un nom, quel qu'il soit, n'est jamais le
titre à lui seul** — *Chopin*, *Musicastelle Autumn Edition* nus sont interdits.

**R4 — L'angle est TOUJOURS dans la langue de la fiche.** C'est la seule partie du titre
où l'on juge la langue. Le nom propre est un îlot autorisé ; l'angle, non.

**R5 — Une MARQUE opaque pour l'autre public → l'angle la glose.** Ne concerne que
R3a : un nom qu'on garde parce qu'il sert à retrouver l'événement, mais qui ne dit rien au
lecteur de l'autre langue (*Bra's*, *Cheese*, *Terra Madre*, un lieu-dit, un sigle).
L'angle dit ce que c'est en huit mots — *Bra's 2026 : la fête des produits du Piémont à
Bra* — et le lecteur n'a pas à le savoir d'avance. (Les intitulés descriptifs, eux,
relèvent de R3b : on ne glose pas ce qu'on peut traduire.)

**R6 — La ville dans l'angle quand le nom ne la porte pas.** Pour un lecteur de Nice, un
événement au « Lingotto » n'est nulle part ; « à Turin » le place. Pas de ville quand le
nom la contient déjà (*Bra's* est à Bra).

**R7 — Pas de verbe de dépêche.** « quitte », « investit », « revient », « ravive »,
« s'installe », « transforme » : le titre nomme et situe, il ne raconte pas. Le récit est
pour le chapô.

**R8 — Casse et interdits : ceux de la charte, appliqués.** Jamais tout en capitales,
jamais tout en minuscules, pas de point d'exclamation, pas de superlatif. *pizza show a
vercelli!* cumule trois fautes.

Exemples réécrits selon R1-R8 :

| aujourd'hui | proposé |
|---|---|
| Terra Madre Salone del Gusto quitte le Lingotto pour investir le centre historique de Turin (14) | **Salon Terra Madre : la biodiversité alimentaire au centre de Turin** (10) |
| Dopo l'8 settembre '43. Meridionali nella Resistenza (7, opaque) | **Les partisans du Sud dans la Libération italienne : projection et débat à Turin** (12) — intitulé original au chapô (R3b) |
| Musicastelle Autumn Edition : Nina Zilli et Mannarino, week-end concert-hébergement les 3 et 4 octobre (13) | **Festival Musicastelle Autumn Edition : deux voix de la pop italienne à Saint-Vincent** (12) — noms au chapô (R3d), mot de genre (R1) |
| Chopin (1) | **Chopin par Katherine Nikitine : récital au Foyer de l'Opéra de Nice** (11) |
| La dernière fois qu'on a vu Bernard Stasi : le texte lauréat 2025 en mise en espace au Théâtre national de Nice (TNN) (23) | **La dernière fois qu'on a vu Bernard Stasi : lecture du texte lauréat au TNN, Nice** (13, limite) |
| pizza show a vercelli! | **Pizza Show : les pizzaioli en démonstration à Vercelli** |

## 5. Le panel : aujourd'hui il ne juge PAS le titre

Lu dans `enrich.py` (`_persona_read`) : le persona reçoit `TITRE : …` en en-tête, puis
l'article, et la question posée est « est-ce que ça t'APPREND quelque chose d'utile et
de concret sur CET événement ». Il note la **substance de l'article**. Le titre est
affiché, jamais interrogé. *Dopo l'8 settembre '43* passe le panel sans qu'un seul
persona ait eu à dire s'il comprend ce que c'est.

Et le panel est **territorial, pas linguistique**. Pour un événement piémontais : locaux =
Manuela (Turin), Piera (Val Maira) ; visiteurs = Camille (frontalière), Chantal (Aoste).
Les francophones sont là — mais en mode « visite », où la consigne est « est-ce un motif
de déplacement », pas « comprends-tu le titre ». La question de Franck n'est donc jamais
posée à la personne qui pourrait y répondre.

**Proposition P1 — une question de titre, séparée, posée AVANT l'article.** Chaque
persona reçoit le titre SEUL et répond à trois questions fermées : *de quoi ça parle*
(en cinq mots, avec ses propres mots), *où c'est*, *un mot ou une référence que tu ne
comprends pas*. Si un persona ne peut pas dire *quoi* ou *où*, ou nomme un référent
opaque, le titre est **refondu** avant même que l'article soit relu.

**Proposition P2 — au moins un persona de CHAQUE langue lit le titre**, quel que soit le
territoire. Pour une fiche FR sur Turin, un francophone doit dire s'il comprend ; pour une
fiche IT sur Annecy, un italophone. C'est l'axe qui manque au panel : il croise les
territoires, pas les langues.

**Ce que le panel ne peut PAS faire, et il faut le dire :** ses verdicts sont un modèle
qui joue un rôle, pas un lecteur. Il attrape l'opacité franche (*8 settembre*) et la
longueur ; il ne mesure pas la compréhension réelle. C'est pourquoi R2, R4, R7 et R8 sont
des règles de **script**, et seuls R3, R5 et R6 — le jugement sur un référent — vont au
panel. Un panel qu'on charge de vérifier une longueur est un panel qu'on paie pour
compter des mots.

## 6. SEO : UNE clé, présente partout, choisie d'abord

Yoast vérifie la clé dans le `<title>`, la méta, le slug, l'intro, les sous-titres,
l'`alt`. Google, lui, lit aussi le H1. Aujourd'hui la clé est choisie **en dernier**,
d'après un corps écrit sans elle, et le H1 est écrit sans elle non plus (§3).

**Proposition S1 — la clé se choisit au moment du titre, et c'est la même règle : nom
propre + ville.** *Terra Madre Turin*, *Meridionali nella Resistenza Torino*, *Chopin
Nikitine Nice*. Elle naît avec le H1, puis `seo_batch` la reçoit au lieu de la deviner.
Le recalage posé le 10/09 (`recale_keyphrase`) reste comme ceinture, il n'est plus le
mécanisme principal.

**Proposition S2 — H1 et `<title>` peuvent différer, mais portent la même clé.** Le H1
parle au lecteur (R1-R8), le `<title>` parle à la requête (clé en tête, 60 caractères,
suffixe de marque si la place le permet — règle du 06/08). Deux textes, une clé.

**Proposition S3 — le slug est dans la langue de la fiche.** Pour la traduction, cela
signifie ne plus recopier le slug FR (l.740-741) : `seo_slug` italien, ou à défaut le
slug du titre italien. Changer les 12 slugs déjà publiés casse 12 adresses → 12 lignes de
301 (`cs-redirections-301.php`, doctrine du 15/09) : **arbitrage de Franck**, section 9.

**Proposition S4 — l'`alt` décrit l'image ET porte la clé.** « Affiche de Terra Madre
Salone del Gusto, Turin », pas la clé nue. Yoast y trouve sa clé, le lecteur d'écran y
trouve une image.

**Ce qui ne change pas :** la méta description (156 car., clé incluse — déjà en place),
le suffixe de marque et sa règle d'abandon sous contrainte de place.

## 7. Le détecteur de langue : il lit le titre entier, il devrait lire l'angle

Les refus du 15/09 — *Le avventure di Pinocchio*, *Riccardo Benassi: Le ultime fabbriche
rimaste…* — et la fiche 3588 avant eux (*La Rencontre Valdôtaine*, CLAUDE.md) ont la
même racine : `titre_semble_intraduit` et `titre_reecrit_mauvaise_langue` détectent la
langue **du titre entier**. Or un titre d'œuvre ou d'événement est un nom propre, dans la
langue qu'il a — italien dans une fiche française, français dans une italienne — et sur
quatre mots la détection est du bruit : « Le » y est lu comme un article français.

**Ce que R3 change pour le portillon :** avec R3b et R3d, un titre FR et son titre IT
peuvent ne partager AUCUN mot en dehors de la marque — et c'est voulu. Le portillon de
justesse (`verdict_titre_traduit`) compare déjà à l'identité factuelle (lieu, ville,
organisateur) et non à la ressemblance ; il tient. C'est le portillon de LANGUE qui casse.

**Proposition L1 — ne juger la langue que sur l'ANGLE (après le deux-points).** Avec R1
imposé, le titre a une structure ; la partie avant les deux-points est un îlot autorisé,
la partie après DOIT être dans la langue cible. C'est déterministe, ça supprime les trois
faux refus connus, et ça ne relâche rien : un angle italien dans une fiche française reste
refusé.

Fixture obligatoire, avec les cas-frontière qui doivent PASSER : *Le avventure di
Pinocchio: il classico di Collodi in marionette, ad Aosta* (fiche IT, nom + angle IT) ;
*Dopo l'8 settembre '43 : les partisans du Sud…, à Turin* (fiche FR, nom IT + angle FR).
Et les cas qui doivent ÉCHOUER : angle en français dans une fiche IT ; titre sans
deux-points recopié tel quel.

## 8. Le rattrapage : 146 titres en ligne

Refondre un H1 ne change pas l'URL (le slug est séparé) : c'est **réversible** — l'ancien
titre est dans `enrich_data`. Mais c'est un appel LLM par fiche, et une relecture panel.

Ordre proposé, par périmètre, du plus rentable au moins :
1. les **22 titres > 14 mots** et les **6 noms nus** — les deux défauts les plus lisibles ;
2. les fiches dont le nom porte un référent opaque (à désigner par le panel, P1) ;
3. le reste au fil des ré-enrichissements du chantier longueur, sans passe dédiée.

Et une règle pour ce rattrapage comme pour le précédent : **lire trois titres réécrits
avant d'en lancer quarante.** Un prompt qui passe de « informatif et incarné » à huit
règles peut produire des titres corrects et morts ; c'est la lecture qui le dira, pas la
fixture.

## 9. Tableau de décision

| # | décision | ce que ça change | réversible ? | coût |
|---|---|---|---|---|
| D1 | Adopter R1-R8 dans la charte et le prompt d'`enrich` | tous les titres écrits ensuite | oui (prompt) | nul |
| D2 | Contrôle déterministe R2/R4/R7/R8 avec relance | refus + une relance par titre hors règle | oui | +1 appel sur les hors-règle |
| D3 | P1 — question de titre au panel, avant l'article | refonte sur verdict « opaque » | oui | +1 appel court par persona |
| D4 | P2 — un persona de chaque langue sur le titre | le panel croise les langues | oui | idem |
| D5 | S1 — clé choisie avec le titre | `seo_batch` reçoit la clé au lieu de la deviner | oui | nul |
| D6 | S3 — slug dans la langue de la fiche, **nouvelles fiches** | URL italiennes en italien | oui | nul |
| D7 | S3 — **les 12 slugs publiés** aussi | 12 URL changent, 12 lignes de 301 | 301 posées : oui | une passe |
| D8 | S4 — `alt` descriptif + clé | accessibilité | oui | nul |
| D9 | L1 — langue jugée sur l'angle seul | fin des faux refus 3588/5106/3017 | oui | nul |
| D10 | Rattrapage 1 : 22 longs + 6 nus | 28 H1 refondus | oui (ancien dans `enrich_data`) | 28 appels + panel |

Ce que je recommande si tout n'est pas pris : **D1, D2, D9** d'abord — ce sont des règles
de script, gratuites, et D9 débloque des traductions aujourd'hui refusées à tort. Puis
D3/D4, qui donnent au panel la question qu'il n'a jamais eue. D7 est le seul qui touche
des adresses publiques : il se décide à part.
