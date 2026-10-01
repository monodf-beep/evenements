/*
 * Prototype de défilement continu — pages de test « test-lecture-corps-* » (noindex) SEULEMENT.
 * Déposé dans wp-content/uploads/cs-tests/, appelé depuis le contenu de ces pages.
 * Écrit le 2026-10-01. Test : tests/navigateur/defilement_continu.js.
 *
 * Principe (choisi avec Franck, sur le modèle d'ItaliaOggi) :
 *  - Google ne fait pas défiler : il ne voit que le premier article, qui a sa propre adresse.
 *    L'article suivant n'est JAMAIS dans le HTML, il n'arrive qu'en JavaScript.
 *  - La suite ne se charge que si le lecteur RESTE en bas de l'article (ATTENTE). Un
 *    défilement rapide ou la touche Fin traversent la zone et atteignent le pied de page.
 *  - L'adresse et le titre de l'onglet suivent l'article lu (seuil : tiers supérieur de
 *    l'écran), pour que partager ou recharger donne le bon article. replaceState et non
 *    pushState : le bouton Retour doit ramener d'où l'on vient, pas d'article en article.
 *  - Au plus MAX articles ajoutés, puis un bouton. Un lien « Aller au pied de page »
 *    précède chaque zone de déclenchement, pour le clavier et les lecteurs d'écran.
 *  - « Lu » ne veut pas dire « chargé » : un article ajouté ne compte comme lu que quand
 *    sa moitié est passée à l'écran (window.__asDefilement.lus), sinon les pages vues
 *    gonflent sans rien dire (CLAUDE.md, règle 6).
 */
(function () {
  'use strict';
  var tl = document.querySelector('.tl[data-suite]');
  if (!tl || !window.fetch) return;

  var ATTENTE = 1000; // ms en bas de l'article avant de charger (aligné sur le test)
  var MAX = 2;        // articles ajoutés au plus
  var donnees = null, ajoutes = 0, enCours = false, fini = false, minuteur = null;
  var base = location.href.split('#')[0];
  var liensIt = Array.prototype.filter.call(document.querySelectorAll('a'), function (a) { return a.textContent.trim() === 'IT'; });
  var itOrig = liensIt.map(function (a) { return a.getAttribute('href'); });
  var arts = [{ url: base, titre: document.title, el: tl.querySelector('.tl-head'), it: null, lu: true }];
  var courant = 0;
  window.__asDefilement = { charges: [], lus: [], adresses: [] };

  var annonce = document.createElement('div');
  annonce.className = 'tl-sr';
  annonce.setAttribute('aria-live', 'polite');
  tl.appendChild(annonce);

  function esc(s) { var d = document.createElement('div'); d.textContent = s == null ? '' : String(s); return d.innerHTML; }
  function attr(s) { return esc(s).replace(/"/g, '&quot;'); }

  function pied() {
    var sel = ['.as-footer-mobile', '.site-footer', 'footer'];
    for (var i = 0; i < sel.length; i++) { var e = document.querySelector(sel[i]); if (e && e.offsetParent !== null) return e; }
    return null;
  }
  document.addEventListener('click', function (ev) {
    var a = ev.target.closest && ev.target.closest('.tl-saut');
    if (!a) return;
    ev.preventDefault();
    var f = pied(); if (!f) return;
    f.scrollIntoView();
    var l = f.querySelector('a, button');
    if (l) l.focus({ preventScroll: true });
  });

  // Déclencheur : la fin de l'article est à l'écran ET le lecteur ne bouge plus depuis
  // ATTENTE ms ET il n'est pas tout en bas de la page. Ce dernier point est mesuré : sur un
  // écran d'ordinateur de 1 000 px, la touche Fin montrait à la fois le pied de page et la
  // fin de l'article ; la suite se chargeait et repoussait le pied de page (test rouge du
  // 01/10). Être au bas absolu, c'est vouloir le pied de page.
  // Le minuteur repart à chaque défilement : seul un vrai arrêt compte, pas un passage.
  function sentinelle() { var s = tl.querySelectorAll('.tl-sentinelle'); return s.length ? s[s.length - 1] : null; }
  function enBasAbsolu() { return scrollY + innerHeight >= document.documentElement.scrollHeight - 4; }
  function enVue(s) { var r = s.getBoundingClientRect(); return r.top <= innerHeight && r.bottom >= 0; }
  function guetter() {
    clearTimeout(minuteur);
    if (enCours || fini) return;
    var s = sentinelle();
    if (!s || !enVue(s) || enBasAbsolu()) return;
    minuteur = setTimeout(function () { if (enVue(s) && !enBasAbsolu()) charger(); }, ATTENTE);
  }

  function charger() {
    if (enCours || fini) return;
    enCours = true;
    var p = donnees ? Promise.resolve(donnees)
      : fetch(tl.getAttribute('data-suite'), { credentials: 'same-origin' }).then(function (x) { return x.json(); });
    p.then(function (d) {
      donnees = d;
      var a = d.articles[ajoutes];
      if (!a) { fin(); return; }
      ajouter(a, d);
      ajoutes++;
      window.__asDefilement.charges.push(a.url);
      annonce.textContent = 'Article suivant : ' + a.titre;
      if (!(ajoutes < MAX && d.articles[ajoutes])) fin();
    }).catch(function () { /* échec réseau : on reste sur l'article, le pied de page est là */ })
      .then(function () { enCours = false; });
  }

  function ajouter(a, d) {
    var fil = (a.fil || []).map(function (f) { return '<a href="' + attr(f[1]) + '">' + esc(f[0]) + '</a>'; }).join('<span class="sep">&gt;</span>');
    var s = document.createElement('section');
    s.className = 'tl-art';
    s.setAttribute('data-url', a.url);
    s.innerHTML =
      '<div class="tl-sep" role="separator"><span>Article suivant</span></div>' +
      '<div class="tl-head">' +
        '<nav class="tl-haut tl-fil" aria-label="Fil d’Ariane"><span>' + fil + '</span></nav>' +
        '<h2 class="tl-titre">' + esc(a.titre) + '</h2>' +
        (a.chapeau ? '<p class="tl-dek">' + esc(a.chapeau) + '</p>' : '') +
        '<p class="tl-sign">Par <b>' + esc(a.auteur) + '</b> · Publié le ' + esc(a.date) + '</p>' +
      '</div>' +
      '<div class="tl-grid"><div class="tl-main">' +
        (a.image ? '<div class="tl-img"><img src="' + attr(a.image) + '" width="' + attr(a.image_l) + '" height="' + attr(a.image_h) + '" alt="' + attr(a.alt) + '" loading="lazy" decoding="async"></div>' : '') +
        '<div class="tl-corps">' + a.contenu + '</div>' +
        '<a class="tl-saut" href="#pied">Aller au pied de page</a><div class="tl-sentinelle"></div>' +
      '</div>' +
      '<aside class="tl-pub" aria-label="Publicité"><div class="tl-pubbox"><span class="tl-publbl">Publicité</span><div class="tl-pubslot">Exemple d’emplacement<br>300 × 250</div></div></aside>' +
      '</div>';
    tl.insertBefore(s, annonce);
    arts.push({ url: a.url, titre: a.titre_onglet || a.titre, el: s.querySelector('.tl-head'), it: a.it, lu: false });
  }

  function fin() {
    fini = true;
    if (tl.querySelector('.tl-finale') || !donnees || !donnees.fin) return;
    var f = document.createElement('div');
    f.className = 'tl-finale';
    f.innerHTML = '<a class="tl-bouton" href="' + attr(donnees.fin.url) + '">' + esc(donnees.fin.label) + '</a>';
    tl.insertBefore(f, annonce);
  }

  var tic = false;
  function suivreLecture() {
    tic = false;
    var seuil = innerHeight / 3, idx = 0;
    for (var i = 0; i < arts.length; i++) if (arts[i].el && arts[i].el.getBoundingClientRect().top <= seuil) idx = i;
    if (idx !== courant) {
      courant = idx;
      var a = arts[idx];
      history.replaceState(history.state, '', a.url + location.hash);
      document.title = a.titre;
      liensIt.forEach(function (l, k) { l.setAttribute('href', idx === 0 ? itOrig[k] : (a.it || itOrig[k])); });
      window.__asDefilement.adresses.push(a.url);
    }
    for (var j = 1; j < arts.length; j++) {
      if (arts[j].lu) continue;
      var bloc = arts[j].el.parentNode.getBoundingClientRect();
      if (bloc.top + bloc.height / 2 < innerHeight) {
        arts[j].lu = true;
        window.__asDefilement.lus.push(arts[j].url);
        document.dispatchEvent(new CustomEvent('as:article-lu', { detail: { url: arts[j].url } }));
      }
    }
  }
  addEventListener('scroll', function () {
    guetter();
    if (!tic) { tic = true; requestAnimationFrame(suivreLecture); }
  }, { passive: true });

  guetter();
})();
