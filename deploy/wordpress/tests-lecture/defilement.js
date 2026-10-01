/*
 * Prototype de défilement continu — pages de test « test-lecture-corps-* » (noindex) SEULEMENT.
 * Déposé dans wp-content/uploads/cs-tests/, appelé depuis le contenu de ces pages.
 * Écrit le 2026-10-01. Test : tests/navigateur/defilement_continu.js.
 *
 * Principe (choisi avec Franck, sur le modèle d'ItaliaOggi) :
 *  - Google ne fait pas défiler : il ne voit que le premier article, qui a sa propre adresse.
 *    L'article suivant n'est JAMAIS dans le HTML, il n'arrive qu'en JavaScript.
 *  - La suite se charge pendant la lecture, quand la fin de l'article approche, pour être
 *    déjà là quand on finit. Un défilement rapide ou la touche Fin traversent la zone et
 *    atteignent le pied de page (voir « Déclencheur » plus bas).
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

  var MAX = 2;        // articles ajoutés au plus
  var donnees = null, ajoutes = 0, enCours = false, fini = false, minuteur = null;
  var base = location.href.split('#')[0], hashDepart = location.hash;
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

  // Déclencheur. Première version : « s'arrêter une seconde en bas de l'article ». Franck
  // (01/10) : il fallait presque SAVOIR qu'un article allait venir ; la suite doit déjà être
  // là quand on finit de lire. Donc on charge PENDANT la lecture, dès que la fin de
  // l'article arrive à moins d'APPROCHE écran sous le bas de l'écran. Deux exceptions :
  //  - on défile vite (plus de VITESSE_MAX écrans par seconde) : on survole, on ne lit pas.
  //    On réévalue PAUSE ms après le dernier mouvement, au repos ;
  //  - on est tout en bas de la page : touche Fin, ou coup de doigt fini sur le pied de
  //    page. C'est le pied de page qu'on veut (test rouge du 01/10 sur un écran de
  //    1 000 px : la suite chassait le pied de page).
  var APPROCHE = 1, VITESSE_MAX = 3, PAUSE = 200, traces = [];
  function noter() {
    var t = Date.now();
    traces.push({ t: t, y: scrollY });
    while (traces.length && t - traces[0].t > 300) traces.shift();
  }
  function vitesse() { // écrans par seconde sur les 300 dernières ms
    if (traces.length < 2) return 0;
    var a = traces[0], b = traces[traces.length - 1], dt = (b.t - a.t) / 1000;
    return dt > 0 ? Math.abs(b.y - a.y) / innerHeight / dt : 0;
  }
  function sentinelle() { var s = tl.querySelectorAll('.tl-sentinelle'); return s.length ? s[s.length - 1] : null; }
  function enBasAbsolu() { return scrollY + innerHeight >= document.documentElement.scrollHeight - 4; }
  function proche(s) { return s.getBoundingClientRect().top < innerHeight * (1 + APPROCHE); }
  function evaluer(auRepos) {
    if (enCours || fini) return;
    var s = sentinelle();
    if (!s || !proche(s) || enBasAbsolu()) return;
    if (!auRepos && vitesse() > VITESSE_MAX) return;
    charger();
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
      '<div class="tl-sep" role="separator"><span class="tl-sr">Article suivant</span></div>' +
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
      // Le suffixe (#l2c…) n'appartient qu'à la page de départ : sur l'adresse d'un autre
      // article il ne veut rien dire (vu par Franck le 01/10 sur /concerts-nice-2026/#l2c).
      history.replaceState(history.state, '', a.url + (idx === 0 ? hashDepart : ''));
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
    noter();
    evaluer(false);
    clearTimeout(minuteur);
    minuteur = setTimeout(function () { traces = []; evaluer(true); }, PAUSE);
    if (!tic) { tic = true; requestAnimationFrame(suivreLecture); }
  }, { passive: true });

  evaluer(true);
})();
