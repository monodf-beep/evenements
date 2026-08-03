# `rapports/` — la boîte aux lettres entre les deux sessions

## Pourquoi ce dossier existe

Deux Claude travaillent sur ce projet : celui du **dépôt** (qui lit et écrit le code, sans
accès au serveur ni à la base) et celui du **VPS** (qui voit la vraie base, le vrai site,
les vrais journaux, mais dont la sortie s'affiche dans un terminal). Jusqu'au 2026-08-03,
tout ce que l'un constatait ne parvenait à l'autre que si **Franck faisait l'intermédiaire**
— capture d'écran, recopie à la main, ou rien.

Le terminal du VPS n'est pas copiable-collable facilement (constat de Franck, 2026-08-03 :
« ce qui est chiant, c'est que je peux pas faire de copier pour coller ici »). Résultat :
soit il retape, soit une observation se perd. Les deux sont mauvais — et faire de l'humain
un tuyau de transmission est exactement ce qu'on cherche à supprimer.

**Le dépôt sert donc de boîte aux lettres.** Ce qui est écrit ici est poussé, puis lu de
l'autre côté sans que personne ait à recopier quoi que ce soit.

## Pourquoi pas `logs/`

`logs/` est dans `.gitignore`, et doit y rester : ce sont des dizaines de mégaoctets
réécrits chaque jour, sans intérêt hors du serveur. `rapports/` contient l'inverse — peu de
fichiers, écrits exprès, destinés à être lus par quelqu'un d'autre.

## Comment s'en servir

Côté VPS, quand une observation mérite d'être transmise plutôt que résumée :

```
.venv/bin/python -m scripts.<audit> > rapports/2026-08-03-audit-fantomes.md
git add rapports/ && git commit -m "rapport : ..." && git push
```

Côté dépôt : `git pull`, et le fichier est là, en entier — pas un résumé, pas une capture
d'écran illisible.

## La règle, parce qu'un dossier fourre-tout devient vite illisible

- **nom** : `AAAA-MM-JJ-sujet.md`, la date d'abord pour que l'ordre alphabétique soit
  l'ordre chronologique ;
- **une sortie brute vaut mieux qu'un résumé** : c'est justement ce qu'on n'arrivait pas à
  transmettre. Le résumé, on sait le refaire ; le détail, non ;
- **ce qui a été traité se supprime.** Un rapport n'est pas une archive : il a servi ou il
  n'a pas servi. Les garder tous ramènerait le problème qu'on résout — beaucoup de texte
  où personne ne cherche plus rien. La base et les journaux, eux, gardent l'historique.
