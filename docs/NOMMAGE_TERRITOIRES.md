# Convention de nommage — territoires, sous-divisions, exonymes FR/IT

*Référence unique pour nommer les lieux sur Agenda Sabauda (pages, breadcrumbs, filtres,
libellés). Bilingue FR/IT. Deux niveaux : le **territoire** (les 4 de l'espace sabaudo) et,
sous lui, la **sous-division administrative** — **département** côté France, **province** côté
Italie. Motif : « Territoire (dept. NN) » en France, « Territoire (prov. Nom) » en Italie.*

---

## 1. Les 4 territoires (nom FR / nom IT)

| Territoire | FR | IT | Slug taxo |
|---|---|---|---|
| Savoie / Haute-Savoie | **Savoie et Haute-Savoie** | **Savoia** | `savoie-haute-savoie` |
| Piémont | **Piémont** | **Piemonte** | `piemonte` |
| Vallée d'Aoste | **Vallée d'Aoste** | **Valle d'Aosta** | `vallee-aoste` |
| Nice / Alpes-Maritimes | **Nice / Alpes-Maritimes** | **Nizza Marittima / Alpi Marittime** | `nice-alpes-maritimes` |

## 2. Sous-divisions (dept. côté FR · prov. côté IT)

Motif de libellé : `FR = "Piémont (prov. Alessandria)"` · `IT = "Piemonte (prov. Alessandria)"`.
Seuls **« Piémont/Piemonte »** et **« dept./prov. »** se traduisent ; **le nom de la province/du
département reste dans sa forme officielle** (sauf exonyme courant, cf. §3).

### Savoie / Haute-Savoie — 2 départements
| FR | IT | Chef-lieu |
|---|---|---|
| Savoie (dept. 73) | Savoia (prov. Chambéry) | Chambéry |
| Haute-Savoie (dept. 74) | Savoia (prov. Annecy) | Annecy |

### Piémont — 8 provinces (nom conservé en FR)
| FR | IT |
|---|---|
| Piémont (prov. Turin) | Piemonte (prov. Torino) |
| Piémont (prov. Cuneo) | Piemonte (prov. Cuneo) |
| Piémont (prov. Alessandria) | Piemonte (prov. Alessandria) |
| Piémont (prov. Asti) | Piemonte (prov. Asti) |
| Piémont (prov. Biella) | Piemonte (prov. Biella) |
| Piémont (prov. Novara) | Piemonte (prov. Novara) |
| Piémont (prov. Verbano-Cusio-Ossola) | Piemonte (prov. Verbano-Cusio-Ossola) |
| Piémont (prov. Vercelli) | Piemonte (prov. Vercelli) |

### Vallée d'Aoste — région à collectivité unique
Pas de provinces → **pas de sous-division** : on reste au niveau territoire
(FR « Vallée d'Aoste » / IT « Valle d'Aosta »).

### Nice / Alpes-Maritimes — 1 département
| FR | IT |
|---|---|
| Alpes-Maritimes (dept. 06) | Alpi Marittime (dept. 06) |

## 3. Exonymes (villes à traduire FR ↔ IT)

| FR | IT |
|---|---|
| **Nice** | **Nizza Marittima** *(la ville ; « Nizza » reste utilisé dans le corps pour la portée SEO)* |
| **Turin** | **Torino** |
| **Aoste** | **Aosta** |

*Les autres villes gardent leur nom d'origine (pas d'exonyme courant) : Chambéry, Annecy, Cuneo,
Alessandria, Menton, Courmayeur…*

---

## 4. Portée & mise en œuvre

- **Immédiat** : appliquer les noms FR/IT du §1 et l'exonyme Nizza Marittima (§3) sur les **pages
  hub** et leurs métas (cf. `docs/GABARIT_PAGES_HUB.md`).
- **Plus tard (taxonomie fine)** : afficher la **sous-division** (prov./dept.) par événement — ex.
  breadcrumb « Piémont › prov. Alessandria › Acqui Terme » — nécessite un **mapping ville →
  province/département** (données non encore présentes : les événements portent `as_ville` et la
  taxo `territoire`, mais pas la province). À bâtir quand on voudra les breadcrumbs/filtres à ce
  niveau. Ce doc fige déjà le **wording** à utiliser le jour venu.
