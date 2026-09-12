# Doctrine d'affichage — choix délibérés, jamais des manques

Ce fichier existe pour UNE raison : sans lui, un persona qui lit le site compare ce
qu'il voit à son intuition, et son intuition ne connaît pas nos choix. Exemple qui a
motivé ce fichier (Franck, 2026-08-05) : « il ne faut pas qu'un persona dise "il n'y a
pas le prix" — c'est décidé qu'il n'y en ait pas, juste gratuit/payant. »

**Comment ce fichier est utilisé** (`utils/doctrine.py`) : chaque entrée est injectée
dans le prompt de CHAQUE persona qui lit le site (premier filtre, gratuit — mieux vaut
ne pas générer une fausse critique que la filtrer après coup) ET revérifiée par le
coordinateur avant de transmettre une trouvaille (second filet, pour le cas où un
persona l'aurait quand même ignorée).

**Format** : un titre `##`, une ligne de doctrine, éventuellement une justification.
Ajoute une entrée dès qu'un persona se trompe sur un choix intentionnel — c'est lui-même
qui, en se trompant une fois, désigne ce qu'il faut ajouter ici.

## Pas de prix chiffré

Aucune fiche n'affiche de prix précis, nulle part sur le site (ni la home, ni les pages
territoire, ni les cartes d'événement) — seulement un badge **gratuit** ou **payant**.
Décision du 2026-08-05. Un persona qui signale « il manque le prix » se trompe : ce
n'est pas un manque, c'est le choix éditorial.
