# Donner la doctrine rédactionnelle à une session Claude, sans rien coller

**Franck, 06/09/2026** : « c'est pénible quand je demande de la rédaction ici sur Claude,
je dois systématiquement expliquer que c'est via Obsidian, le ton, la doctrine, le
vocabulaire etc. »

**Franck, 21/09/2026**, sur les dispositifs qui existaient déjà : « ça existe mais c'est
pas connecté directement à Obsidian, donc pas de mise à jour automatique de la doctrine. »
C'est exactement le défaut que ce dispositif-ci corrige.

---

## Le problème, formulé juste

Le pipeline automatique n'a jamais eu ce problème : `utils/voix.py` et
`utils/vocabulaire.py` **ouvrent les notes Obsidian du VPS à chaque exécution**. Franck
édite une note, le run suivant en tient compte. Aucune synchronisation, aucune copie.

Une session de chat, elle, ne tourne pas sur le VPS. La consigne écrite jusqu'au 21/09
(`CLAUDE.md`, skill `redaction-agenda-sabauda`) était : « demander à Franck de coller la
sortie de deux commandes ». Autrement dit, lui faire refaire à la main, à chaque texte,
précisément ce dont il se plaignait — et le lui faire refaire *à chaque fois*, puisqu'un
collage vieillit dès que la note change.

Et toute solution par **copie** (exporter les notes dans le dépôt, les recopier dans un
skill, les coller dans une mémoire) recrée le défaut nommé le 05/09 dans
`docs/VOCABULAIRE_OBSIDIAN.md` : le miroir du vocabulaire interdit avait divergé **dans
les deux sens** avant qu'on le supprime. Une doctrine recopiée n'est plus la doctrine.

## Le dispositif

Le back-office tourne **sur le même VPS que le vault** : il lit donc les mêmes notes, au
même instant, par le même code. Il les sert en deux endroits :

| Adresse | Pour qui | Clé d'entrée |
| --- | --- | --- |
| `/doctrine` | **Claude Chrome** — il pilote le navigateur de Franck, déjà connecté | le cookie de session du back-office |
| `/doctrine.txt?token=…` | **Cowork, Claude Code sur le web**, tout agent sans navigateur | `DOCTRINE_TOKEN` (`.env` du VPS) |

Les deux rendent **la même chose, relue à l'instant** : voix éditoriale + vocabulaire
interdit (Obsidian) + charte éditoriale (dépôt). Aucun cache (`Cache-Control: no-store`),
aucun fichier intermédiaire. Une note éditée dans Obsidian est visible au rafraîchissement
suivant — c'est la même propriété que le pipeline, étendue aux sessions de chat.

## Mise en service (une fois)

1. sur le VPS, ajouter au `.env` une ligne — la valeur est un mot de passe, donc long et
   pris au hasard :

   ```
   DOCTRINE_TOKEN=<longue chaîne aléatoire>
   ```

2. déployer : `cd ~/evenements && bash deploy/update.sh` ;
3. ouvrir `https://backoffice.agendasabauda.eu/doctrine` — la page affiche l'adresse
   complète à jeton, prête à copier, et **d'où vient chaque bloc**.

Sans `DOCTRINE_TOKEN`, `/doctrine.txt` répond **503** et reste fermée. C'est délibéré :
une adresse ouverte finit indexée, et le back-office n'a rien à exposer sans clé. Le jeton
n'ouvre que la doctrine — aucune écriture, aucune donnée d'événement.

## Ce qu'on dit à une session

> Avant d'écrire quoi que ce soit pour Agenda Sabauda, lis
> `https://backoffice.agendasabauda.eu/doctrine.txt?token=…` — c'est la doctrine vivante.

Pour Claude Chrome, l'adresse sans jeton (`/doctrine`) suffit.

## Ce que la page dit quand ça va mal — et pourquoi elle le dit fort

`utils/vocabulaire.interdits()` renvoie `()` **en silence** quand la note est injoignable.
C'est un choix de Franck du 05/09 (« continuer sans filtre, silencieusement ») : mieux vaut
un pipeline qui publie sans filtre qu'un pipeline arrêté. **Ce choix ne vaut pas ici** : le
lecteur est un rédacteur, et un silence lui ferait croire qu'il tient la doctrine alors
qu'il n'a rien. Donc :

- chaque bloc affiche **sa provenance, son chemin et sa taille** — le périmètre à côté du
  nombre (`CLAUDE.md`, règle 6) ;
- une voix servie par le **filet versionné du dépôt** (`docs/voix/VOIX.md`) est signalée
  comme telle : elle répond, mais ce n'est **pas** Obsidian, et les retouches du vault n'y
  sont pas ;
- une note manquante produit une alerte **en tête du texte servi**, pas dans un log ;
- si la voix **et** le vocabulaire manquent (vault démonté), `/doctrine.txt` répond
  **503**. La charte, elle, est versionnée : elle répondrait toujours, donc elle est
  exclue de ce test — sinon le 503 serait un témoin qui n'a jamais été rouge
  (journal du 14/09).

## Une mesure qui corrige une affirmation du dépôt

`CLAUDE.md` et le skill affirmaient : « ce conteneur n'atteint pas le VPS par lui-même —
pas de clé SSH, pas de route réseau directe ». **Mesuré le 21/09 depuis un conteneur
Claude Code** : `https://backoffice.agendasabauda.eu/` répond (302 vers `/login`, serveur
`gunicorn`) et `/embed/events.json` rend 200 avec de vraies fiches.

L'affirmation était vraie pour **SSH** et fausse pour **HTTPS** — les deux n'avaient jamais
été mesurées séparément, et la conclusion la plus large a été retenue pour les deux. C'est
la racine nommée dans `docs/ERREURS_2026-08-18.md` : quatre commandes qu'il fallait taper
à la première minute. Conséquence concrète : les sessions Claude Code sur le web peuvent
lire cette adresse elles aussi, sans que Franck soit dans la boucle.

## Fichiers

- `utils/doctrine_redaction.py` — assemble les trois blocs, avec provenance et alertes.
  **À ne pas confondre avec `utils/doctrine.py`**, qui existait avant et parle d'autre
  chose : la doctrine d'*affichage* (`config/doctrine_affichage.md`, lue par
  `scripts/panel_site.py`). Ici ce qu'on écrit, là-bas ce qu'on montre ;
- `app/app.py` — routes `/doctrine` et `/doctrine.txt` ;
- `app/templates/doctrine.html` — la page ;
- `tests/test_doctrine_redaction.py` — la fixture (aucun réseau, notes fabriquées).
