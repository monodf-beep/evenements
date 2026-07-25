# Recette de build — FOOTER · agendasabauda.eu

*Recette de construction du pied de page. Ne modifie rien en ligne : c'est le plan à exécuter
dans WordPress. Stack : GeneratePress (thème) + The Events Calendar (données) + Crocoblock
JetThemeCore/JetEngine (Theme Part « Footer ») + Elementor (édition) + Polylang (FR/IT).*

Sources : `docs/BRIEF_DESIGN_AGENDA_SABAUDA.md` §5 (footer riche) · `docs/PLAN_DU_SITE_AGENDA_SABAUDA.md`
§1 (arborescence), §2.3 (nav thématique), §4 (À propos FR/IT) · `docs/STRATEGIE_MARQUE_ET_TERRITOIRES.md`
· `docs/legal/` (mentions, crédits photos) · `wordpress/design-system/tokens.css` (variables `--cs-*`).

> **Principe (charte GuidaTorino).** Le footer n'est pas un cul-de-sac décoratif : c'est un
> **outil SEO de maillage** (liens crawlables vers TOUS les hubs) + le lieu où **le bilinguisme
> et la mention éditeur se montrent** (« il ne se cache pas dans un coin », brief §9). Fond
> **deep** (bleu Savoie `--bg-deep`), texte beige `--fg-on-deep`, filets `--rule-on-deep`.

---

## 1. Structure (zones, de haut en bas)

```
┌─────────────────────────────────────────────────────────────────────┐
│ ZONE A — Bandeau newsletter (inline, 1 champ)                        │  fond légèrement teinté
│   « Le vendredi matin, l'essentiel des 4 territoires. » [email][→]   │  (bleu clair translucide)
├─────────────────────────────────────────────────────────────────────┤
│ ZONE B — Bloc marque                    │ ZONE C — 4 colonnes de liens│
│   Wordmark « Agenda Sabauda. » (. rouge)│  1. Explorer (temporels)    │
│   Baseline / tagline                    │  2. Catégories (11)         │
│   À-propos court (2 lignes)             │  3. Territoires (4 + villes) │
│   Réseaux sociaux (icônes trait)        │  4. Le projet (pages+RSS)   │
│   Commutateur FR | IT (texte)           │                             │
├─────────────────────────────────────────────────────────────────────┤
│ ZONE D — Nav thématique « Retrouvez sur Agenda Sabauda… » (1 ligne)  │  filet au-dessus
├─────────────────────────────────────────────────────────────────────┤
│ ZONE E — Barre légale (bottom bar)                                    │
│   © 2026 Agenda Sabauda · Édité par [Cultura Sabauda↗] ·             │
│   Mentions légales · Confidentialité · Crédits photos                │
└─────────────────────────────────────────────────────────────────────┘
```

- **Zone A (newsletter)** — 1 champ email + bouton, promesse datée. Répète le bloc newsletter
  home/fiche (brief §8.4). *Outil d'envoi : à décider — cf. §6.*
- **Zone B (marque)** — wordmark HTML réel (jamais en image, brief §3), **point final rouge**
  `--cs-rouge`, baseline, à-propos court (2 phrases tirées du §4 PLAN), rangée réseaux sociaux
  (icônes trait, **pas d'emoji**), commutateur **FR | IT en TEXTE — jamais de drapeaux** (brief §5).
- **Zone C (4 colonnes)** — le maillage SEO. Tous liens = **texte HTML crawlable**.
- **Zone D (nav thématique)** — la phrase « Retrouvez sur Agenda Sabauda… » (PLAN §2.3), reprise
  du pattern GuidaTorino. Optionnelle : peut être fusionnée dans la Zone B sur mobile.
- **Zone E (barre légale)** — copyright + **mention éditeur « Édité par Cultura Sabauda » + lien
  vers culturasabauda.eu** (obligatoire, brief §1.1 / §5) + les 3 liens légaux.

---

## 2. Contenu prêt à coller

### 2.1 Zone A — Newsletter

| | FR | IT |
|---|---|---|
| Titre | La lettre du vendredi | La newsletter del venerdì |
| Promesse | Le vendredi matin, l'essentiel des sorties sur les 4 territoires. | Il venerdì mattina, l'essenziale degli eventi sui 4 territori. |
| Placeholder | Votre e-mail | La tua e-mail |
| Bouton | S'inscrire | Iscriviti |
| RGPD (petit) | Désinscription en 1 clic. Voir la [confidentialité](/fr/confidentialite/). | Disiscrizione con 1 clic. Vedi la [privacy](/it/privacy/). |

### 2.2 Zone B — Marque

- **Wordmark** : `Agenda Sabauda` + `<span class="wm-dot">.</span>` (le point en `--cs-rouge`).
- **Baseline / tagline** *(à figer — piste PLAN §6.4)* :
  - FR : « L'agenda des 4 territoires alpins, de Chambéry à Turin. »
  - IT : « L'agenda dei 4 territori alpini, da Chambéry a Torino. »
- **À-propos court** (condensé du §4 PLAN) :
  - FR : « L'agenda culturel de l'espace alpin occidental — Savoie & Haute-Savoie, Piémont,
    Vallée d'Aoste, Nice. Ce qui commence, ce qui se termine, ce qu'il ne faut pas manquer. »
  - IT : « L'agenda culturale dello spazio alpino occidentale — Savoia & Alta Savoia, Piemonte,
    Valle d'Aosta, Nizza. Ciò che inizia, ciò che finisce, ciò da non perdere. »
- **Réseaux sociaux** : Facebook · Instagram (+ éventuellement une icône RSS). *Comptes à confirmer
  — cf. §6.* Icônes en trait simple (SVG inline), `aria-label` par réseau.
- **Commutateur langue** : `FR | IT` (texte). Le lien mène à **la page équivalente** dans l'autre
  langue (repli hub parent, brief §9). En pratique = widget de langue Polylang, stylé en texte.

### 2.3 Zone C — Les 4 colonnes (liens mappés sur l'arborescence PLAN §1)

**Colonne 1 — Explorer** (accès temporel)

| Libellé FR | URL FR | Libellé IT | URL IT |
|---|---|---|---|
| Aujourd'hui | `/fr/aujourdhui/` | Oggi | `/it/oggi/` |
| Ce week-end | `/fr/ce-week-end/` | Questo weekend | `/it/questo-weekend/` |
| Cette semaine | `/fr/cette-semaine/` | Questa settimana | `/it/questa-settimana/` |
| Les 10 du week-end | `/fr/les-10-du-week-end/` | I 10 del weekend | `/it/i-10-del-weekend/` |
| Tout l'agenda | `/fr/evenements/` | Tutti gli eventi | `/it/eventi/` |

**Colonne 2 — Catégories** (les 11)

| Libellé FR | URL FR | Libellé IT | URL IT |
|---|---|---|---|
| Expositions & Patrimoine | `/fr/evenements/expositions-patrimoine/` | Mostre & Patrimonio | `/it/eventi/mostre-patrimonio/` |
| Concerts & Musique | `/fr/evenements/concerts-musique/` | Concerti & Musica | `/it/eventi/concerti-musica/` |
| Spectacle vivant | `/fr/evenements/spectacle-vivant/` | Spettacolo dal vivo | `/it/eventi/spettacolo-dal-vivo/` |
| Festivals | `/fr/evenements/festivals/` | Festival | `/it/eventi/festival/` |
| Gastronomie & Sagre | `/fr/evenements/gastronomie-sagre/` | Gastronomia & Sagre | `/it/eventi/gastronomia-sagre/` |
| Marchés & Foires | `/fr/evenements/marches-foires/` | Mercati & Fiere | `/it/eventi/mercati-fiere/` |
| Sport | `/fr/evenements/sport/` | Sport | `/it/eventi/sport/` |
| Cinéma | `/fr/evenements/cinema/` | Cinema | `/it/eventi/cinema/` |
| Jeune public & Famille | `/fr/evenements/jeune-public-famille/` | Per bambini & Famiglia | `/it/eventi/bambini-famiglia/` |
| Conférences & Rencontres | `/fr/evenements/conferences-rencontres/` | Conferenze & Incontri | `/it/eventi/conferenze-incontri/` |
| Fêtes & Traditions populaires | `/fr/evenements/fetes-traditions/` | Feste & Tradizioni popolari | `/it/eventi/feste-tradizioni/` |

*(Slugs IT à confirmer au moment du réglage Polylang des taxonomies — cf. §6.)*

**Colonne 3 — Territoires** (les 4 — libellés officiels brief §1.2)

| Libellé FR | URL FR | Libellé IT | URL IT |
|---|---|---|---|
| Savoie / Haute-Savoie | `/fr/territoire/savoie-haute-savoie/` | Savoia / Alta Savoia | `/it/territorio/savoia-alta-savoia/` |
| Piémont | `/fr/territoire/piemont/` | Piemonte | `/it/territorio/piemonte/` |
| Vallée d'Aoste | `/fr/territoire/vallee-d-aoste/` | Valle d'Aosta | `/it/territorio/valle-d-aosta/` |
| Nice / Alpes-Maritimes | `/fr/territoire/nice-alpes-maritimes/` | Nizza / Alpi Marittime | `/it/territorio/nizza-alpi-marittime/` |

> Pas de pilule colorée dans le footer (fond deep → les 4 couleurs territoire passent mal). Liens
> texte simples. Le sous-niveau **villes** (Turin, Nice, Annecy, Chambéry, Aoste) est **v2** :
> ajouter en fin de colonne quand les hubs ville existeront (seuil ≥15 événements).

**Colonne 4 — Le projet**

| Libellé FR | URL FR | Libellé IT | URL IT |
|---|---|---|---|
| À propos | `/fr/a-propos/` | Chi siamo | `/it/chi-siamo/` |
| Proposer un événement | `/fr/proposer-un-evenement/` | Proponi un evento | `/it/proponi-un-evento/` |
| Newsletter | `/fr/newsletter/` | Newsletter | `/it/newsletter/` |
| Contact | `/fr/contact/` | Contatti | `/it/contatti/` |
| Crédits photos | `/fr/credits-photos/` | Crediti fotografici | `/it/crediti-foto/` |
| Flux RSS | `/fr/feed/` | Feed RSS | `/it/feed/` |

### 2.4 Zone D — Nav thématique (PLAN §2.3)

- FR : **Retrouvez sur Agenda Sabauda tout ce qu'il ne faut pas manquer :** Que faire ce week-end ·
  Les 4 territoires · Expositions & patrimoine · Concerts, spectacles & festivals · Gastronomie,
  sagre & marchés · En famille.
- IT : **Ritrovate su Agenda Sabauda tutto ciò da non perdere:** Cosa fare questo weekend · I 4
  territori · Mostre & patrimonio · Concerti, spettacoli & festival · Gastronomia, sagre & mercati ·
  In famiglia.

*(Chaque segment est un lien vers le hub correspondant. Optionnel au lancement — c'est un renfort
de maillage, pas une obligation.)*

### 2.5 Zone E — Barre légale + mention éditeur

- **Copyright** :
  - FR : `© 2026 Agenda Sabauda` *(année dynamique)*
  - IT : `© 2026 Agenda Sabauda`
- **Mention éditeur (obligatoire, brief §1.1 / §5)** :
  - FR : « Édité par **[Cultura Sabauda](https://culturasabauda.eu)** », média culturel bilingue de
    l'espace alpin occidental. *(Option : petit logo Cultura Sabauda 24 px avant le texte, comme sur
    la newsletter — brief §3.)*
  - IT : « Edito da **[Cultura Sabauda](https://culturasabauda.eu)** », testata culturale bilingue
    dello spazio alpino occidentale.
- **Liens légaux inline** :
  - FR : [Mentions légales](/fr/mentions-legales/) · [Confidentialité](/fr/confidentialite/) · [Crédits photos](/fr/credits-photos/)
  - IT : [Note legali](/it/note-legali/) · [Privacy](/it/privacy/) · [Crediti fotografici](/it/crediti-foto/)

---

## 3. Recette de build (JetThemeCore Theme Part « Footer »)

**Voie retenue : Theme Part JetThemeCore, éditée avec Elementor.** (Alternative GeneratePress en §3.4.)

### 3.1 Créer le Theme Part
1. **Crocoblock → Theme Builder** (JetThemeCore) → **Add New** → Type = **Footer**.
2. Nommer `footer-fr`. Éditeur = **Elementor** (« Edit with Elementor »).
3. **Conditions d'affichage** : `Include → Entire Site` (tout le site). Pas d'exclusion au
   lancement (le footer est global). *(Si un jour une landing sans footer : exclure via condition.)*

### 3.2 Monter les zones (colonnes Elementor)
- **Zone A** — Section pleine largeur, fond `rgba(100,134,186,.14)` (bleu clair translucide sur
  deep). Widget **formulaire newsletter** (selon l'outil retenu — §6 : shortcode MailPoet/Brevo,
  ou widget JetForm). Titre + champ + bouton `--cs-rouge`.
- **Zone B** — Section 2 colonnes (desktop) / empilées (mobile). Colonne gauche = bloc marque
  (widget **Heading** pour le wordmark + `.wm-dot`, **Text Editor** pour la baseline + à-propos,
  **Icon List/HTML** pour les réseaux, **widget de langue Polylang** stylé texte). Colonne droite =
  Zone C (voir ci-dessous), ou faire de C une section 4-colonnes séparée sous B.
- **Zone C** — Section **4 colonnes** (Elementor `Inner Section` ou colonnes natives) ; chaque
  colonne = un widget **Nav Menu** (menus WP dédiés, voir 3.3) ou **Icon List** de liens. 4 colonnes
  desktop → 2 colonnes tablette → 1 colonne (accordéons optionnels) mobile.
- **Zone D** — Section 1 colonne, widget **Text Editor** / **HTML** avec la phrase liée.
- **Zone E** — Section pleine largeur, filet supérieur `--rule-on-deep`. Colonne gauche =
  copyright + éditeur (HTML) ; colonne droite = liens légaux (Nav Menu ou HTML).

### 3.3 Menus WordPress (recommandé pour les colonnes)
Créer sous **Apparence → Menus** (traductibles par Polylang) :
- `footer-explorer` (5 liens) · `footer-categories` (11) · `footer-territoires` (4) ·
  `footer-projet` (6) · `footer-legal` (3).
Les afficher via le widget **Nav Menu** dans chaque colonne → contenu maintenable sans toucher au
template, et **Polylang traduit chaque menu par langue** automatiquement (voir §5).

### 3.4 Alternative sans JetThemeCore — zone de widgets GeneratePress
Si on veut éviter un template Jet : **GeneratePress → Customizer → Layout → Footer** (jusqu'à 5
zones de widgets « Footer Widgets »). Poser 4 widgets **Navigation Menu** + 1 zone marque/légale.
Le fond deep se met via `.site-footer{background:var(--bg-deep)}` (CSS §4). *Moins flexible que
JetThemeCore pour la Zone A newsletter et la barre légale — préférer le Theme Part.*

### 3.5 Ordre de build
1. Créer les 5 menus (3.3) en FR, puis leurs traductions IT.
2. Créer le Theme Part `footer-fr`, monter les 5 zones (3.2).
3. Coller le CSS (§4) dans **Code Snippets (scope site-css)** — cohérent avec `apply-tokens.mjs` —
   ou dans l'onglet CSS du template.
4. Dupliquer en `footer-it` / créer la traduction (§5).
5. Vérifier contraste (§4) + responsive (mobile 1 colonne) + liens crawlables (voir-source HTML).

---

## 4. CSS (classes + variables `--cs-*`)

Les variables sont déjà chargées globalement (`design-system/tokens.css`). Le footer réutilise
`--bg-deep` (bleu `#18365E`), `--fg-on-deep` (beige `#F7F1E8`), `--rule-on-deep`.

```css
/* ===== FOOTER Agenda Sabauda — fond deep (bleu Savoie) ===== */
.as-footer{
  background: var(--bg-deep);
  color: var(--fg-on-deep);
  font-family: var(--font-body);
  font-size: var(--fs-body-sm);
  line-height: var(--lh-body);
}
.as-footer a{
  color: var(--fg-on-deep);          /* beige sur bleu = contraste AA large */
  text-decoration: none;
}
.as-footer a:hover,
.as-footer a:focus-visible{
  text-decoration: underline;
  text-underline-offset: 3px;
}
.as-footer a:focus-visible{          /* focus visible = rouge accent (non-texte, safe) */
  outline: 2px solid var(--cs-rouge);
  outline-offset: 2px;
}

/* ---- Zone A : newsletter ---- */
.as-footer__news{
  background: rgba(100,134,186,.14); /* --cs-bleu-clair translucide */
  border-bottom: 1px solid var(--rule-on-deep);
  padding: var(--s-6) var(--s-5);
}
.as-footer__news h2{
  font-family: var(--font-editorial);
  font-size: var(--fs-h4);
  margin: 0 0 var(--s-2);
}
.as-footer__news form{ display:flex; gap: var(--s-2); flex-wrap:wrap; max-width: 34rem; }
.as-footer__news input[type=email]{
  flex:1 1 14rem; padding: var(--s-3) var(--s-4);
  border:1px solid var(--rule-on-deep); border-radius: var(--r-2);
  background: rgba(247,241,232,.06); color: var(--fg-on-deep);
}
.as-footer__news input::placeholder{ color: rgba(247,241,232,.55); }
.as-footer__news button{
  padding: var(--s-3) var(--s-5); border:0; border-radius: var(--r-2); cursor:pointer;
  background: var(--cs-rouge); color: var(--cs-beige); font-weight:700;
}

/* ---- Layout général ---- */
.as-footer__inner{ max-width: var(--page-max); margin:0 auto; padding: var(--s-8) var(--s-5); }

/* ---- Zone B : marque ---- */
.as-footer__brand{ margin-bottom: var(--s-7); max-width: 32rem; }
.as-footer__wordmark{
  font-family: var(--font-editorial);
  font-size: var(--fs-h3); font-weight:800; letter-spacing: var(--tracking-caps);
  color: var(--fg-on-deep); line-height: var(--lh-title);
}
.as-footer__wordmark .wm-dot{ color: var(--cs-rouge); }   /* le point rouge du logotype */
.as-footer__baseline{ color: var(--cs-bleu-clair); margin-top: var(--s-2); }
.as-footer__about{ color: rgba(247,241,232,.82); font-size: var(--fs-meta); margin-top: var(--s-3); }
.as-footer__social{ display:flex; gap: var(--s-4); margin-top: var(--s-4); }
.as-footer__social a{ display:inline-flex; }         /* icônes SVG trait, 20px */
.as-footer__lang{ margin-top: var(--s-4); letter-spacing: var(--tracking-caps); }
.as-footer__lang [aria-current="true"]{ font-weight:800; }
.as-footer__lang .sep{ opacity:.5; margin:0 var(--s-2); }

/* ---- Zone C : 4 colonnes ---- */
.as-footer__cols{
  display:grid; grid-template-columns: repeat(4, 1fr); gap: var(--s-6);
  border-top: 1px solid var(--rule-on-deep); padding-top: var(--s-6);
}
.as-footer__col h3{
  font-family: var(--font-editorial);
  font-size: var(--fs-meta); text-transform:uppercase; letter-spacing: var(--tracking-eyebrow);
  color: var(--cs-bleu-clair); margin:0 0 var(--s-3);
}
.as-footer__col ul{ list-style:none; margin:0; padding:0; display:grid; gap: var(--s-2); }

/* ---- Zone D : nav thématique ---- */
.as-footer__themes{
  border-top: 1px solid var(--rule-on-deep);
  margin-top: var(--s-6); padding-top: var(--s-5);
  font-size: var(--fs-meta); color: rgba(247,241,232,.82);
}
.as-footer__themes strong{ color: var(--fg-on-deep); }

/* ---- Zone E : barre légale ---- */
.as-footer__legal{
  border-top: 1px solid var(--rule-on-deep);
  margin-top: var(--s-6); padding: var(--s-5) 0 0;
  display:flex; flex-wrap:wrap; justify-content:space-between; gap: var(--s-3);
  font-size: var(--fs-meta); color: rgba(247,241,232,.75);
}
.as-footer__legal a{ color: rgba(247,241,232,.85); }
.as-footer__editeur img{ height:24px; width:auto; vertical-align:middle; margin-right: var(--s-2); }

/* ---- Responsive ---- */
@media (max-width: 1024px){
  .as-footer__cols{ grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 480px){
  .as-footer__cols{ grid-template-columns: 1fr; }
  .as-footer__legal{ flex-direction:column; }
}
```

**Contraste (WCAG AA).** Beige `#F7F1E8` sur bleu `#18365E` ≈ ratio **11:1** → AA/AAA texte OK.
Titres de colonne en `--cs-bleu-clair` `#6486BA` sur deep ≈ **3.2:1** : réservé aux **eyebrows /
petites capitales de rubrique** (rôle décoratif), jamais du corps lisible. Le **rouge `--cs-rouge`
n'est utilisé que pour le point du wordmark, le bouton newsletter (texte beige dessus) et le focus**
— jamais comme couleur de lien-texte sur deep (ratio insuffisant).

---

## 5. Notes Polylang FR/IT

- **Un footer par langue.** JetThemeCore stocke les Theme Parts dans un CPT ; activer sa traduction
  dans **Polylang → Réglages → Types de publication** (cocher `jet-theme-core` / les templates), puis
  créer `footer-fr` + sa **traduction `footer-it`**. Polylang sert alors le template de la langue
  courante (les deux gardent la condition « Entire Site »).
- **Menus** : Polylang gère un jeu de menus **par langue**. Créer `footer-*` en FR puis leurs
  homologues IT ; les assigner par langue. Les liens pointent vers les URLs `/it/…` du §2.3.
- **Chaînes fixes** (titres de colonnes, newsletter, baseline, mention éditeur) : si le template est
  dupliqué, saisir directement les libellés IT du §2 dans `footer-it`. Sinon (template unique)
  passer par **Polylang → Traductions de chaînes**.
- **Commutateur FR|IT** : utiliser le **Language Switcher Polylang** (widget/shortcode
  `[language_switcher]`) réglé en **texte, sans drapeau**, et « aller à la traduction » (repli hub
  parent si non traduit — brief §9).
- **Longueur** : prévoir chaînes IT +10-15 % (brief §9) — les colonnes en grille l'absorbent.
- **Dates/année** : copyright en année dynamique (shortcode ou `date('Y')`), identique aux 2 langues.

---

## 6. Incertitudes / décisions à confirmer

1. **Outil newsletter (Zone A)** — **À DÉCIDER.** Options : MailPoet (natif WP, RGPD, double
   opt-in), Brevo/Sendinblue (shortcode), ou JetForm + webhook. À aligner sur l'ESP déjà utilisé
   par la newsletter Cultura Sabauda existante (« le vendredi matin »). Impacte le widget de la
   Zone A et la page `/fr/newsletter/`.
2. **Comptes réseaux sociaux** — lesquels existent pour Agenda Sabauda (vs Cultura Sabauda) ?
   Facebook / Instagram confirmés ? URL exactes ? *(Si aucun au lancement : masquer la rangée.)*
3. **Tagline / baseline** — non figée (piste « L'agenda des 4 territoires alpins, de Chambéry à
   Turin » — PLAN §6.4). À valider par Franck avant de la graver dans le footer.
4. **Logo éditeur Cultura Sabauda 24 px** — récupérer l'asset (même que la newsletter) et l'héberger
   en médiathèque, ou rester en texte seul « Édité par Cultura Sabauda ». *(Chercher dans le design
   system : `assets/logos/*`.)*
5. **Slugs IT des taxonomies** (catégories/territoires) — ceux du §2.3 sont proposés ; à confirmer
   au réglage Polylang des taxonomies TEC (`tribe_events_cat`) + `territoire`.
6. **JetThemeCore vs GeneratePress footer widgets** — recette principale = JetThemeCore (§3).
   Confirmer que JetThemeCore est bien activé (la doc `BUILD_WORDPRESS_CROCOBLOCK.md` évoque une
   variante Bricks/Gutenberg « pas Elementor » pour la perf ; **le stack décidé ici est
   GeneratePress + Elementor + Jet** — surveiller le poids CWV du footer, le garder léger).
7. **Zone D (nav thématique)** — la garder au lancement ou la réserver au bas de l'À propos
   seulement ? (redondance partielle avec les 4 colonnes). Décision éditoriale.
8. **Sous-niveau villes (colonne Territoires)** — v2 (seuil ≥15 événements). Rien à afficher au
   lancement.
```
