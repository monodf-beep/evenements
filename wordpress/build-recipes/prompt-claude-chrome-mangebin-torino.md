# Prompt Claude dans Chrome — récupérer la liste Mangébin de Torino

*Créé le 2026-09-06. La liste « Mangébin à Torino » est rendue en JavaScript : elle
n'apparaît pas dans le HTML servi, et le navigateur de la session Claude Code est bloqué
par le proxy sur `turismotorino.org` (`ERR_CONNECTION_RESET`). La liste « hors Torino »,
elle, est server-rendered et a déjà été récupérée : 10 établissements.*

**Ce qu'on en fera** : l'article « Où manger à Turin — les restaurants Mangébin », premier
rayon du hub `/ou-manger/`. Mangébin est le réseau des restaurants de cuisine piémontaise
typique de Turin et sa province, porté par **Turismo Torino e Provincia** — donc une source
institutionnelle, au même titre que la Cuisine Nissarde pour Nice.

---

## À coller dans Claude, dans Chrome

> Ouvre cette page et attends qu'elle soit complètement chargée (la liste des restaurants
> arrive en JavaScript, quelques secondes après le reste) :
>
> **https://turismotorino.org/fr/decouvrir/a-voir-a-faire/vins-et-gastronomie/mangebin/mangebin-a-torino**
>
> Puis relève **tous** les établissements listés sur cette page. Pour chacun, donne-moi,
> dans cet ordre et en une ligne :
>
> `Nom du restaurant | adresse complète si affichée | quartier ou zone si affiché | l'URL de sa fiche`
>
> Consignes :
> - **N'invente rien.** Si l'adresse ou le quartier n'est pas affiché sur la page, écris
>   `—` à la place. Un champ vide est une information ; une adresse devinée est une faute.
> - **Ne complète pas depuis tes connaissances** ni depuis une autre source : je veux
>   exactement ce que cette page affiche, ce jour-là.
> - S'il y a une **pagination** ou un bouton « voir plus / charger plus », clique jusqu'au
>   bout et donne-moi la liste complète.
> - Dis-moi **combien** d'établissements tu as relevés au total, et si un chiffre est
>   annoncé quelque part sur la page (« X restaurants »), donne-le aussi : s'il ne
>   correspond pas à ton relevé, signale l'écart au lieu de le lisser.
> - Si la page ne charge pas, ou si la liste reste vide, **dis-le** plutôt que de me
>   donner une liste plausible.
>
> Fais ensuite la même chose pour la page voisine, que je veux pouvoir recouper :
>
> **https://turismotorino.org/fr/decouvrir/a-voir-a-faire/vins-et-gastronomie/mangebin/mangebin-horse-de-torino**
>
> *(oui, l'URL dit bien « horse », c'est une coquille du site, pas de moi)*

---

## Ce qu'on a déjà, pour recoupement

Liste **hors Torino**, extraite du HTML le 2026-09-06 — 10 établissements :

Alpeggio Menzio · Ca' Praudin · Il Poggio Agrisport · La Table Dlouz Amis ·
Agriturismo Crè Seren · L'Fouie · Fermata Alpi Graie · Ristorante Freidour ·
Trattoria Bel Deuit · Ristorante L'Incontro

Si le relevé de Chrome donne autre chose pour cette page, c'est le relevé de Chrome qui
fait foi (le site a pu changer), mais **l'écart doit être signalé** et pas absorbé en
silence.

---

## Pourquoi ce détour plutôt qu'un scraper

Trois canaux ont été essayés depuis la session, le 06/09, tous en échec :

| Canal | Résultat |
|---|---|
| `curl` sur la page | HTTP 200, mais 66 liens seulement, aucune fiche : la liste est en JS |
| Chromium local + Playwright | `ERR_CONNECTION_RESET`, y compris via le proxy de la session |
| version italienne de la page | HTTP 404, elle n'existe pas sous ce chemin |

Un quatrième essai a bien marché pour la page « hors Torino », mais par chance : cette
page-là est server-rendered, pas l'autre. Il n'y a donc pas de scraper à écrire, seulement
un navigateur à ouvrir — et Franck en a un.
