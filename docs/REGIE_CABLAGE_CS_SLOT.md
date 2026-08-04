# Câblage de `[cs_slot]` sur les blocs 1, 2 et 3

*Le modèle « override » a été validé par Franck le 2026-07-20 : toutes les pubs sont
AdSense par défaut, et la créative d'un annonceur vendu **remplace** l'AdSense du bloc
concerné le temps de sa campagne. Le mu-plugin `deploy/wordpress/cs-regie-serve.php` (v0.2)
expose la primitive qui fait ça. **Ce câblage n'a jamais été posé.** Tant qu'il ne l'est
pas, créer une campagne back-office sur le bloc 1, 2 ou 3 ne produit strictement RIEN sur
le site : l'API répond, le mu-plugin sait répondre, mais personne ne l'appelle.*

> Ce document décrit le **contrat** et la **manipulation**. Le déroulé de session Novamira
> (déploiement du mu-plugin, cartographie live, prompt à coller) est dans
> `docs/REGIE_CABLAGE_CSLOT.md` — nom voisin, contenu complémentaire, ne pas les confondre.
> Contexte et conflits : `docs/REGIE_MISE_EN_PLACE_SOCLE.md`.

---

## 1. Ce que fait exactement `[cs_slot]` (lu dans le code, pas supposé)

`deploy/wordpress/cs-regie-serve.php` :

| Élément | Comportement vérifié |
|---|---|
| `[cs_slot bloc="N"]…[/cs_slot]` (ligne 89) | Si campagne active pour `N` → **créative back-office**. Sinon → `do_shortcode()` du **contenu enveloppé**, rendu tel quel. |
| `cs_regie_slot('N', $html)` (ligne 96) | Même logique, pour un gabarit PHP. |
| Source des campagnes (ligne 45) | `GET {backoffice}/api/active-ads`, timeout 4 s, **transient 5 min**. Réponse ≠ 200 ou API muette → tableau vide → repli AdSense. |
| Purge du cache (ligne 59) | N'importe quelle URL du site avec `?cs_regie_refresh=1`. |
| Allowlist (lignes 37, 74) | Image **https sur `agendasabauda.eu`** (médiathèque du site) et lien **https sur `backoffice.agendasabauda.eu`**. Une seule condition non remplie → `''` → repli AdSense **silencieux**, aucun message d'erreur. |
| Consentement (lignes 77, 105-118) | La créative sort en `.cs-consent-gate`, `display:none` tant que le cookie `cmplz_marketing=allow` n'est pas posé (Complianz). Elle est donc **dans le HTML mais invisible** sans consentement. |
| Attribut manquant | `bloc=""` → aucune campagne ne correspond → repli AdSense. Une faute de numéro ne casse rien, elle **ne fait rien** : c'est exactement le mode de panne difficile à voir. |

Autrement dit : **le seul état d'échec de ce mécanisme est « l'AdSense reste affiché »**.
Rien ne remonte, rien ne loggue. D'où la section 7.

---

## 2. Où `[cs_slot]` s'applique — et où il ne faut PAS le mettre

| Bloc back-office | Nom | Flux | Qui le rend |
|---|---|---|---|
| 1 | Leaderboard (haut) | dans le flux | **`[cs_slot]` à poser** |
| 2 | Pavé in-article | dans le flux | **`[cs_slot]` à poser** |
| 3 | Bandeau bas sticky | dans le flux | **`[cs_slot]` à poser** |
| 4 | Habillage / Skin | hors flux | `cs-regie.php` v0.3 — **rien à faire** |
| 5 | Gouttière gauche | hors flux | `cs-regie.php` v0.3 — **rien à faire** |
| 6 | Gouttière droite | hors flux | `cs-regie.php` v0.3 — **rien à faire** |

`cs-regie.php` lit le back-office tout seul en `wp_footer` (`cs_regie_hf_slot('4'/'5'/'6')`,
lignes 89-91) et il est **déployé depuis le 2026-08-04**. Envelopper un bloc 4/5/6 dans un
`[cs_slot]` afficherait la même créative **deux fois**.

---

## 3. Les numéros du back-office font foi

`app/app.py:1946` (`AD_BLOCKS`) définit les clés `"1"` à `"6"`. `/api/active-ads`
(`app/app.py:2135`) renvoie `{"ads": {"<bloc>": {...}}}` avec **la valeur brute de la colonne
`bloc`** de `ad_campaigns` ; `cs_regie_manual_ad()` compare cette clé à l'attribut `bloc` du
shortcode, en chaîne. La correspondance est donc **directe et sans traduction** : le `N` de
`[cs_slot bloc="N"]` est le numéro affiché dans `/regie`. Aucun mapping à tenir à jour.

Trois conditions pour qu'une campagne apparaisse dans l'API (SQL de `regie_active_ads`) :
`statut='active'`, **`image_url` ET `url` non vides**, et la date du jour dans
`[date_debut, date_fin]` (bornes vides = pas de limite). Un annonceur saisi sans image ne
sort jamais de l'API — et côté site, ça ressemble à un câblage cassé. Un seul annonceur par
bloc : à égalité, **l'`id` le plus élevé gagne**.

---

## 4. Les codes AdSense ne sont pas dans ce dépôt

Les blocs 1 à 4 ont été configurés en direct sur le serveur le 2026-07-17/18 (session
Novamira) : leur code vit dans l'**option WordPress `ad_inserter`**, en base. Une recherche
de `adsbygoogle` / `ca-pub-4040905402577097` dans le dépôt ne renvoie que de la
documentation et `cs-pub-slots-vides.php` — **aucun code AdSense réel n'est versionné**.

Conséquence pratique : **on ne peut pas préparer le contenu enveloppé hors ligne.** La manip
de la section 5 se fait forcément dans wp-admin (ou via Novamira), en lisant le code
existant sur place. Ce document ne peut pas donner le code AdSense du bloc 1 — l'inventer
serait pire qu'inutile. Ce qu'on sait des blocs (positions, slots, statuts) est dans
`docs/REGIE_MISE_EN_PLACE_SOCLE.md` §« Ce qui a été configuré ».

---

## 5. La manipulation, bloc par bloc

Pour chacun des blocs **1, 2 et 3**, dans **wp-admin → Réglages → Ad Inserter → onglet du
bloc** :

1. **Copier le code existant ailleurs avant de le toucher** (la session de 2026-07-18
   sauvegardait chaque valeur de l'option `ad_inserter` dans
   `wp-content/uploads/ai-backup-<timestamp>.txt` — même réflexe, c'est le seul filet).
2. Dans la grande zone de code, **entourer** le code existant, sans y toucher autrement.
3. Activer le **traitement des shortcodes** du bloc (case « Process shortcodes » dans les
   réglages du bloc ; le libellé et l'onglet bougent selon la version d'Ad Inserter). Sans
   ça, `[cs_slot bloc="1"]` s'affiche **en toutes lettres sur le site**. C'est
   particulièrement critique pour le **bloc 3**, inséré en pied de page (`display_type=13`) :
   il ne passe pas par le filtre `the_content`, donc rien ne développera le shortcode à sa
   place.
4. Enregistrer, puis vérifier (section 7) **avant** de passer au bloc suivant.

**Avant** (contenu du bloc Ad Inserter aujourd'hui) :

```html
<script async src="https://pagead2.googlesyndication.com/…"></script>
<ins class="adsbygoogle" data-ad-client="ca-pub-…" data-ad-slot="5007380676" …></ins>
<script>(adsbygoogle = window.adsbygoogle || []).push({});</script>
```

**Après** (mêmes lignes, deux balises ajoutées autour — `N` = 1, 2 ou 3) :

```html
[cs_slot bloc="1"]
<script async src="https://pagead2.googlesyndication.com/…"></script>
<ins class="adsbygoogle" data-ad-client="ca-pub-…" data-ad-slot="5007380676" …></ins>
<script>(adsbygoogle = window.adsbygoogle || []).push({});</script>
[/cs_slot]
```

Rien d'autre ne change : ni la position d'insertion, ni les appareils, ni les conditions
d'URL, ni le gating de consentement déjà posé sur l'AdSense.

**Cas d'un code AdSense en dur dans un gabarit** (s'il s'en trouve un) : remplacer
`echo $code;` par
`echo function_exists('cs_regie_slot') ? cs_regie_slot('N', $code) : $code;` — le
`function_exists` garantit que le retrait du mu-plugin ne casse pas la page.

---

## 6. Le piège : deux numérotations de blocs qui se chevauchent

**Le numéro d'un bloc Ad Inserter n'a aucun rapport avec le numéro d'un bloc back-office.**
Ce sont deux plans de numérotation indépendants, tous les deux en 1-N, et ils se
contredisent — c'est le **conflit #1** de `docs/REGIE_MISE_EN_PLACE_SOCLE.md`, ouvert
depuis le 2026-07-17 et **toujours non tranché**.

| Bloc Ad Inserter | Ce que le design system en fait (fichier : ligne) | Ce que la session du 18/07 y a mis | Bloc back-office homonyme |
|---|---|---|---|
| 1 | Gouttière gauche 160×600 — `wordpress/design-system/homepage-template.php:52` | Leaderboard 970×90 | 1 = Leaderboard |
| 2 | Gouttière droite — `homepage-template.php:56` | Pavé in-article 300×250 | 2 = Pavé in-article |
| 3 | Pub sous carrousel 950×120 — `homepage-mobile.gutenberg.html:391` | Bandeau bas sticky | 3 = Bandeau bas sticky |
| 4 | Pub sous tuiles 950×90 — `homepage-mobile.gutenberg.html:441` | Habillage / Skin | 4 = Skin |
| 5 | Pavé 300×250 colonne — `homepage-mobile.gutenberg.html:595` | — | 5 = Gouttière gauche |
| **6** | **Barre sticky desktop 728×90** — `homepage-mobile.gutenberg.html:658` | — | **6 = Gouttière droite 160×600** |
| 7-12 | Emplacements mobiles — `homepage-mobile.gutenberg.html:90…323` | — | (n'existent pas) |

Le risque n'est pas théorique : `cs-pub-slots-vides.php` a été récupéré de la production le
2026-08-04 précisément parce que ces encarts `[adinserter block=N]` **sont bien dans le
`post_content` de la home en ligne** et affichaient des cadres vides que Franck voyait.

Deux dégâts concrets si on se trompe de plan :

- **Format aberrant.** Envelopper le bloc Ad Inserter 6 (barre sticky 728×90) dans
  `[cs_slot bloc="6"]` y ferait entrer la créative « gouttière droite » — un skyscraper
  **160×600** couché dans une barre de 90 px de haut. Et la même créative s'afficherait
  aussi dans la vraie gouttière, rendue en parallèle par `cs-regie.php`.
- **Double rendu.** Les blocs Ad Inserter 1 et 2 sont **actifs en insertion automatique**
  (« avant le contenu », « après le paragraphe 3 ») **et** appelés explicitement par
  `homepage-template.php` comme gouttières. Le même code s'insère donc deux fois sur la
  home — et une fois enveloppé, c'est la même créative back-office qui sort deux fois, à
  deux endroits sans rapport.

**Règle de sécurité, applicable sans attendre l'arbitrage :** avant d'écrire un `N`,
regarder **ce que le bloc Ad Inserter contient réellement**, pas son numéro. Le `N` du
`[cs_slot]` est celui de `/regie` ; il coïncide avec le numéro Ad Inserter par hasard, et
seulement pour les blocs 1-3 tels que configurés le 18/07. Le jour où les blocs 1-4 sont
renumérotés vers 13-16 (piste proposée du socle), **les `[cs_slot bloc="N"]` ne bougent
pas** : ils suivent le back-office, pas Ad Inserter.

---

## 7. Vérifier que le câblage marche

Dans cet ordre — chaque étape isole une cause différente :

1. **Le shortcode est-il enregistré et développé ?** Poser temporairement
   `[cs_slot bloc="99"]TEST-CS-SLOT[/cs_slot]` dans le bloc en cours de câblage. Attendu :
   la page affiche `TEST-CS-SLOT`. Si elle affiche `[cs_slot bloc="99"]TEST-CS-SLOT[/cs_slot]`
   en clair → traitement des shortcodes non activé (étape 3 de la section 5). Si elle
   n'affiche rien → le mu-plugin n'est pas chargé. **Retirer le test ensuite.**
2. **L'API voit-elle la campagne ?** Ouvrir `https://backoffice.agendasabauda.eu/api/active-ads`
   et vérifier que la clé du bloc visé est présente, avec `image` sur `agendasabauda.eu` et
   `link` en `https://backoffice.agendasabauda.eu/go/<id>`. Absente → campagne non active,
   hors fenêtre de dates, ou image/URL vide (section 3).
3. **Le site a-t-il rafraîchi ?** `https://agendasabauda.eu/?cs_regie_refresh=1` — sinon
   compter jusqu'à 5 min (transient) **plus** le cache page OVH de 300 s sur l'accueil
   (`cs-cache-control-home.php`), soit ~10 min dans le pire cas.
4. **Regarder avec le consentement marketing ACCEPTÉ.** Sans `cmplz_marketing=allow`, la
   créative est dans le HTML mais en `display:none` : chercher `cs-ad` et
   `data-cs-bloc="N"` dans la source suffit à prouver que le câblage fonctionne, même si
   l'écran ne montre rien.
5. **Vérifier les deux sens.** Terminer la campagne dans `/regie`, purger, et confirmer que
   **l'AdSense revient**. Un câblage qui ne sait pas revenir en arrière n'est pas câblé, il
   est bloqué.

Deux effets de bord à connaître pendant les tests :

- **AdSense est en « Examen requis » chez Google** (socle, conflit #3) : le « défaut »
  attendu est donc un emplacement **vide**, pas une pub. Ne pas en conclure que
  l'enveloppement a cassé quelque chose.
- **`cs-pub-slots-vides.php` ne masque que les encarts dont la zone intérieure est
  littéralement vide** (`>\s*</div>`, lignes 27-36). Dès qu'une créative est rendue —
  **même masquée par le gating de consentement** — la zone n'est plus vide : le cadre
  « Publicité » de la home réapparaît, éventuellement autour d'un vide visuel pour un
  visiteur qui a refusé le marketing.

---

## 8. Revenir en arrière

- **Un bloc** : rouvrir le bloc Ad Inserter, retirer les deux balises `[cs_slot …]` et
  `[/cs_slot]`. Le code AdSense n'a pas été modifié — c'est tout l'intérêt d'envelopper
  plutôt que de remplacer.
- **Tout, d'un coup** : dans `/regie`, terminer les campagnes des blocs 1-3. Le repli
  AdSense reprend en ≤ 5 min, sans toucher à WordPress. **C'est le rollback à privilégier**,
  parce qu'il ne demande aucune écriture sur le site.
- **Supprimer le mu-plugin** : possible, mais **pas propre** contrairement à ce
  qu'annonce l'en-tête de `cs-regie-serve.php` (ligne 23). WordPress laisse tel quel un
  shortcode qu'il ne connaît pas : les textes `[cs_slot bloc="1"]` et `[/cs_slot]`
  deviendraient **visibles à l'écran** autour de l'AdSense, qui lui continuerait de
  s'afficher. Si le fichier doit vraiment partir, déposer d'abord à sa place un
  passe-plat :

  ```php
  add_shortcode('cs_slot', function ($a, $c = '') { return do_shortcode((string) $c); });
  ```

  Les gabarits PHP, eux, sont protégés par le `function_exists('cs_regie_slot')` de la
  section 5.
- **`cs-regie.php` n'est pas concerné** : ses fonctions de repli (`function_exists`,
  lignes 35-64) lui permettent de continuer à servir les blocs 4/5/6 même sans
  `cs-regie-serve.php`.

---

## 9. Ce que ce document ne peut pas affirmer

Rédigé **hors ligne**, sur le dépôt seul. Restent à constater sur le site, avant de câbler :

- **`cs-regie-serve.php` est-il déployé** dans `wp-content/mu-plugins/`, et en v0.2 ? Seul
  `cs-regie.php` v0.3 a une pose datée et vérifiée (md5, 2026-08-04). L'étape 1 de la
  section 7 répond à la question sans avoir à lister le serveur.
- **Le contenu réel des blocs Ad Inserter 1-3** (option `ad_inserter`) — voir section 4.
- **Le bloc 2 s'insère-t-il seulement ?** `single-event-meta.php` rend le contenu via
  `get_the_content()` et non `the_content()` : Ad Inserter s'accroche au filtre
  `the_content`, donc ce bloc ne s'insérerait jamais sur les fiches événement. Point relevé
  le 2026-07-18, **jamais vérifié visuellement**. Câbler le bloc 2 avant d'avoir tranché ça
  revient à câbler un emplacement qui ne s'affiche pas.
- **`homepage-template.php` du dépôt est-il bien celui du serveur ?** Les numéros de la
  table de la section 6 viennent des fichiers versionnés ; la home en ligne a pu diverger,
  comme `cs-regie-serve.php` et `cs-pub-slots-vides.php` avaient divergé avant d'être
  récupérés.
