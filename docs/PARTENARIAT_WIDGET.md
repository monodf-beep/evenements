# Widget embeddable & page « Travailler avec nous »

Un bloc « prochains événements » que des partenaires (offices de tourisme, mairies,
blogs, hôtels…) collent sur **leur** site. Il affiche les prochains événements de
l'Agenda et renvoie vers **agendasabauda.eu**. Double bénéfice : la marque s'affiche
partout **et** chaque intégration crée un lien retour (référencement).

Tout part d'un **flux public unique** servi par le backoffice :
`https://backoffice.agendasabauda.eu/embed/events.json` (CORS ouvert, cache 10 min).

## Où le configurer

Backoffice → **Partenariat / widget** (`/partenariat`) : on choisit le territoire, la
ville, la langue, le nombre et la couleur, on voit l'**aperçu en direct**, et on copie
le code prêt à coller. Deux intégrations au choix.

### Option 1 — script (recommandé)
S'intègre dans la page hôte, styles isolés (Shadow DOM), largeur adaptative.

```html
<script src="https://backoffice.agendasabauda.eu/embed/widget.js"
        data-territoire="savoie-haute-savoie"
        data-limit="6"></script>
```

Attributs `data-*` (tous optionnels) :

| Attribut         | Rôle                              | Exemple                    |
|------------------|-----------------------------------|----------------------------|
| `data-territoire`| filtre par territoire (slug)      | `piemont`                  |
| `data-ville`     | filtre par ville                  | `Annecy`                   |
| `data-lang`      | langue des fiches                 | `fr` ou `it`               |
| `data-limit`     | nombre d'événements (1–20)        | `6`                        |
| `data-title`     | titre du bloc                     | `À l'affiche en Savoie`    |
| `data-accent`    | couleur d'accent (hex)            | `#7a5b3a`                  |

Slugs de territoire : `savoie-haute-savoie`, `piemont`, `vallee-d-aoste`,
`nice-alpes-maritimes` (vide = tous).

### Option 2 — iframe (isolation totale)
Page autonome, aucun risque de conflit CSS. À privilégier pour un site rigide.

```html
<iframe src="https://backoffice.agendasabauda.eu/embed/widget?t=piemont&limit=6"
        width="100%" height="520" style="border:0;max-width:640px"
        loading="lazy" title="Agenda Sabauda"></iframe>
```

Mêmes paramètres, en query-string : `t`, `ville`, `lang`, `limit`, `title`, `accent`.

## Texte prêt à coller — page « Travailler avec nous » / « Partenaires »

> ### Affichez l'Agenda Sabauda chez vous
>
> Vous animez un office de tourisme, une commune, un lieu culturel ou un média local ?
> Intégrez **gratuitement** l'agenda culturel de l'espace sabaudo sur votre site. Un bloc
> léger, à votre image, **mis à jour tout seul** : vos visiteurs voient les prochains
> rendez-vous près de chez eux, et repartent vers la fiche complète.
>
> - **Gratuit et sans engagement.**
> - **Toujours à jour** — aucune maintenance de votre côté.
> - **À vos couleurs** — titre et teinte personnalisables.
> - **Par territoire** — n'affichez que votre secteur si vous le souhaitez.
>
> *[Bouton : Obtenir mon widget]* — ou écrivez-nous à **contact@agendasabauda.eu**.
>
> **Vous êtes annonceur ?** Découvrez nos [emplacements publicitaires](#) *(→ page régie).*

## Notes techniques

- Le flux ne renvoie que des événements **en ligne** sur l'Agenda (`wp_post_id_as`),
  **datés**, dont la fin est **≥ aujourd'hui**, triés par date croissante.
- Chaque fiche pointe vers `WP_AS_URL/?p=<id>` (redirige vers le permalien).
- Aucune donnée personnelle, aucun cookie posé par le widget.
- Endpoints publics (sans auth) : `/embed/events.json`, `/embed/widget.js`,
  `/embed/widget`. Le générateur `/partenariat` reste protégé (backoffice).
