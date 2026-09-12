# Plan réseaux sociaux — Agenda Sabauda (Instagram + Threads + Facebook)

*Référence unique du partage social. Décisions validées avec Franck. Sert aussi de brief
à Claude design (gabarits) et à Claude Cowork (tâches manuelles/engagement).*

---

## 1. Architecture — 1 compte par territoire

**4 comptes**, chacun publie **comme sa colonne sur la homepage** : les **principaux
événements de SON territoire** (les mieux notés, à venir) + de temps en temps un
**🌟 « ça vaut le détour »** (un événement fort d'un autre territoire).

| Compte | Territoire | Langue des posts |
|---|---|---|
| Savoie | Savoie / Haute-Savoie | 🇫🇷 Français |
| Piémont | Piemonte | 🇮🇹 Italien |
| Vallée d'Aoste | Vallée d'Aoste | 🇫🇷 Français **puis** 🇮🇹 Italien (bilingue) |
| Nice | Nice / Alpes-Maritimes | 🇫🇷 Français |

**Sélection auto** : les « principaux » = top score à venir du territoire (même logique
que la homepage). Le « vaut le détour » = **bouton éditorial** `worth_trip` sur la fiche
(Franck choisit), affiché sur les autres comptes dans leur langue.

## 2. Types de contenu, outils, coûts

| Type | Format | Outil | Coût |
|---|---|---|---|
| Post simple | carré 1080×1080 | Pillow / Canva (autofill) | **0 €** |
| Carrousel | portrait 1080×1350 (accroche → détails → CTA) | Pillow / Canva | **0 €** |
| Story | 1080×1920 (reprend le visuel du post) | Pillow / Canva | **0 €** |
| Reel | vidéo verticale | Higgsfield (motion sur la vraie photo) | **crédits — rare** |

Le **texte** (légende FR/IT + hashtags + alt) est généré sans coût (`utils/social.py`).
Les **visuels statiques** sont générés sans coût (`utils/social_image.py` / Canva).

## 3. Cadence & budget (le curseur crédits)

- **Posts/semaine/compte : 3** — tous gratuits (~2 simples + 1 carrousel).
- **Reels : 0 au lancement** (on rode la chaîne en gratuit), **puis plafond 2/semaine
  pour les 4 comptes réunis** (les meilleurs events / « vaut le détour »).
- **Plafond « Reels/semaine » dans le back-office** (comme la page Coûts API) : au-delà
  du quota, plus de génération vidéo. Dépense **bornée et visible**.
- Ordre de grandeur : ~**48 posts gratuits/mois** + **≤ 8 Reels/mois** une fois lancé.

## 4. Un contenu = 3 canaux (portée gratuite)

Le même visuel + légende part sur **Instagram**, **Threads** et la **Page Facebook**
liée au compte. Aucune refabrication → on triple la portée du travail gratuit.

## 5. Ce qui est AUTOMATIQUE (API) vs ManyChat / Cowork / manuel

| Élément | Auto via API ? | Qui / note |
|---|---|---|
| Posts, carrousels, stories | ✅ | Back-office (gratuit) |
| Quota de publication | ✅ **100 posts / 24 h / compte** | large marge |
| Légendes FR/IT + hashtags + **alt_text** | ✅ | Back-office |
| **1ᵉʳ commentaire** (hashtags/lien) | ✅ via un appel séparé après publication | Back-office |
| **Modération** (masquer/supprimer, mots interdits) | ✅ | Back-office — activé dès le départ |
| **Insights** (portée, saves, abonnés) | ✅ | Back-office (tableau) / Cowork (reporting) |
| **Reels d'essai** (non-abonnés d'abord) | ✅ `trial_params` | tester un Reel sans risque avant crédits |
| Reels (musique **libre**) | ✅ | Higgsfield + notre musique |
| Reels (musique **tendance/sous licence**) | ❌ bascule en « rappel » | **manuel / Cowork** dans l'app |
| **Géolocalisation** du post | ❌ non fiable en API | **manuel** sur les posts importants (ou on s'en passe) |
| **Collab** (co-auteur) + **miniature** de Reel | ❌ limité | app / manuel |
| Répondre aux commentaires / DM | ✅ possible | **ManyChat** (mot-clé → DM) ou **Cowork** (réponses fines) |

⚠️ **Instagram encadre l'automatisation.** L'engagement de masse propre passe par
**ManyChat** (officiel). Claude **Cowork** = assister/rédiger + les exceptions (Reel à
son tendant, réponse délicate), **pas** du volume automatisé qui risque le blocage.

## 6. Règle IA & authenticité (NON négociable)

- **La vraie photo de l'événement prime.** On n'invente jamais prix/date/lieu.
- **Pas de photoréaliste IA d'un lieu réel** (l'audience locale repère les incohérences).
- Higgsfield = **mouvement sur la vraie photo** (Reel), **fond abstrait/graphique**, ou
  **illustration clairement stylisée** — jamais une fausse scène de l'événement.
- **Drapeau `is_ai_generated` : NON utilisé** (décision Franck). Justifié car on ne
  produit pas de faux-réel trompeur. *(Meta peut poser son propre label s'il détecte de
  l'IA — hors de notre contrôle. Si un jour on faisait du photoréaliste, on rouvre la
  question.)*

## 7. Phases de mise en œuvre

1. **Gratuit d'abord** *(en cours)* : légendes ✅ + visuels post/carrousel ✅ →
   tableau « Réseaux par territoire » + stories + cross-post Threads/Facebook +
   modération + insights.
2. **Publication auto** : upload visuel → médiathèque WordPress (URL publique) →
   API Instagram (conteneur → publication), par compte. Simple + carrousel.
3. **ManyChat** (engagement) : « commente AGENDA → programme en DM ».
4. **Reels capés** : Higgsfield (musique libre) + Reels d'essai, sous le plafond.

## 8. Prérequis Meta (une fois — obstacle à lever pour l'auto)

Par compte : Instagram **Pro (Business/Creator)** + **Page Facebook** liée. Une **app
Meta** (une seule pour les 4) avec la permission de publication → **App Review** (quelques
jours). Jetons longue durée par compte, à rafraîchir.

---

*État code au moment de ce doc : `utils/social.py` (légendes FR/IT + hashtags + alt),
`utils/social_image.py` (post 1080² + carrousel 1080×1350), panneau « 📣 Partage
Instagram » dans la fiche (`/preview`). Reste à faire : tableau Réseaux par territoire,
connexion Canva (autofill/export), couche publication API, Higgsfield motion, ManyChat.*
