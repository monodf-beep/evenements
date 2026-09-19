add_filter('body_class', function ($c) {
    $home_ids = function_exists('cs_agenda_home_page_ids') ? cs_agenda_home_page_ids() : array(928, 1717);
    if (is_page($home_ids)) { $c[] = 'cs-home'; }
    return $c;
});
add_action('wp_head', function () { ?>
<style id="cs-hdr-compact">
.as-site-header__inner{ padding-top:9px !important; padding-bottom:9px !important; }
.as-site-header__wordmark img{ max-height:30px !important; width:auto !important; transition:max-height .15s ease; }
/* 2026-08-06 (Franck) : au scroll (body.cs-hdr-min), le monogramme aS cede la
   place a la Mole (icone dessinee, cf. Cultura Sabauda Design System). Repos =
   monogramme seul (comportement inchange) ; scroll = Mole seule, coloree en
   corail comme dans la maquette validee, meme gabarit de taille que l'ancien
   monogramme au meme etat (24px). */
.as-site-header__mole{ display:none; height:30px; width:auto; color:#DC5D45; transition:height .15s ease; }
body.cs-hdr-min .as-site-header__monogram{ display:none !important; }
body.cs-hdr-min .as-site-header__mole,body.cs-hdr-min .as-site-header__wordmark img.as-site-header__mole,body.cs-hdr-min .as-home-minilogo img.as-site-header__mole,body.cs-hdr-min .as-home-desktop__nav-logo img.as-site-header__mole{ display:inline-block !important; height:32px !important; max-height:32px !important; width:auto !important; }
body.cs-hdr-min .as-site-header__wordmark-text{ display:none !important; }
.as-site-header__wordmark-text{ font-size:14px !important; transition:font-size .15s ease; }
/* 2026-08-01 (Franck) : revient sur la decision du 2026-07-22 -- au scroll on bascule sur le monogramme aS + texte (lockup compact), plus lisible que le masthead complet retreci. */
body.cs-hdr-min .as-site-header__wordmark img{ max-height:24px !important; }
body.cs-hdr-min .as-site-header__wordmark-text{ font-size:12.5px !important; }
body.cs-hdr-min .as-site-header__inner{ padding-top:5px !important; padding-bottom:5px !important; flex-wrap:nowrap !important; align-items:center !important; } body.cs-hdr-min .as-site-header__lang{ margin-left:auto !important; }
/* 2026-08-02 (Franck) : le panneau home (.as-home-sticky-panel, bake dans le
   contenu, cf. snippet 12 + pages 928/1717) remplace ENTIEREMENT .as-site-header
   sur la home, mobile et desktop -- plus de systeme cache/revele a un seuil ni
   de distinction mobile/desktop, l'ancien doublon desktop n'existe plus. */
body.cs-home .as-site-header{ display:none !important; }
/* 2026-09-07 (Franck, capture mobile) : « il y a un espace en trop en haut de page ».
   MESURE sur la page rendue (Chromium, viewport 412x915), pas une impression : le panneau
   home commencait a 25,5 px du haut au lieu de 0, et le logo a 41,5 px au lieu de 16.
   CAUSE : wpautop enveloppe dans un <p> les commentaires HTML isoles du contenu des pages
   928/1717, et un <p> sans texte garde sa marge basse (1.5em = 25,5 px a 17 px de fonte).
   Six sur la home FR, trois cote IT -- et le contenu STOCKE de 1717 n'en contient AUCUN :
   ils sont fabriques au RENDU, donc les retirer du contenu ne tiendrait pas, la prochaine
   edition de la page les ramenerait. On neutralise donc l'effet la ou il se produit.
   :empty matche bien un <p> ne contenant qu'un commentaire (verifie en direct : 6 sur 6).
   Remesure apres correctif : panneau a 0, logo a 16 px, soit le seul padding du masthead. */
.as-home-root p:empty{ display:none !important; }
/* 2026-08-02 (Franck) : position:sticky testee en direct et abandonnee -- bloquee
   par body{overflow-x:hidden} (regle site-wide, hors scope pour la modifier). Le
   panneau passe donc en position:fixed uniquement une fois le seuil de scroll
   franchi (meme mecanisme que l'ancien .as-site-header), reste en flux normal
   au repos -- pas de contenu duplique a cacher cette fois, un seul panneau. */
body.cs-hdr-min .as-home-sticky-panel{ position:fixed !important; top:0; left:0; right:0; max-width:480px !important; margin:0 auto !important; }
body.cs-hdr-min .as-masthead-block{ max-height:0 !important; opacity:0 !important; padding-top:0 !important; padding-bottom:0 !important; }
/* 2026-08-02 (Franck) : UNE seule taille de lockup compact pour tout le site --
   les pages internes affichaient un monogramme 30px + texte 14px, la home scrollee
   24px + 12.5px, et le nav desktop de la home 26px : trois hauteurs de header
   differentes selon ou l'on se trouvait. Reference retenue = celle des pages
   internes (la plus lisible, et de loin la plus frequente sur le site). */
body.cs-hdr-min .as-home-minilogo{ max-width:200px !important; opacity:1 !important; }
body.cs-hdr-min .as-home-minilogo img{ height:30px !important; }
body.cs-hdr-min .as-home-minilogo span{ font-size:14px !important; }
body.cs-hdr-min .as-home-sticky-panel > div:nth-child(2){ padding-top:9px !important; padding-bottom:9px !important; }
.as-home-desktop__nav-logo img{ height:30px !important; }
.as-home-desktop__nav-logo span{ font-size:14px !important; }
/* 2026-08-02 (Franck) : DESKTOP home -- .as-home-desktop__nav est sticky DANS son
   conteneur .as-home-desktop (~1100px de haut), donc il disparaissait une fois
   scrolle au-dela. Passe en fixed des le seuil cs-hdr-min pour rester visible sur
   toute la page, comme le panneau mobile. Padding compensatoire = hauteur nav. */
@media (min-width:900px){
  /* 2026-08-02 (Franck) : la barre territoire de la home desktop etait un encart
     ARRONDI, detache du nav (margin-top:20px), et non sticky -- alors que sur tout
     le reste du site c'est une barre pleine largeur collee sous le header. On la
     rend identique : meme pleine largeur, meme alignement de contenu (910px), meme
     comportement au scroll (elle suit le nav en 2e ligne). */
  .as-home-desktop .as-terr-bar-inline{
    margin-top:0 !important; border-radius:0 !important;
    margin-left:calc(50% - 50vw); margin-right:calc(50% - 50vw);
    padding-left:calc(50vw - 455px) !important; padding-right:calc(50vw - 455px) !important;
    box-sizing:border-box;
  }
  body.cs-home.cs-hdr-min .as-home-desktop__nav{ position:fixed; top:0; left:0; right:0; z-index:42; margin:0 !important; }
  body.cs-home.cs-hdr-min .as-home-desktop .as-terr-bar-inline{ position:fixed; top:49px; left:0; right:0; z-index:41; margin:0 !important; }
  /* (la compensation de hauteur est desormais assuree par une cale inseree en JS,
     a l'emplacement exact du bloc qui passe en fixed -- un padding sur le conteneur
     decalait le masthead vers le bas au lieu de combler le trou laisse par le nav.) */
}
/* 2026-08-02 (Franck) : la bordure superieure de la barre FR/IT separait a l'origine
   le masthead (au-dessus) de cette barre -- une fois le masthead reduit a 0 en
   scroll, cette bordure devient le tout premier pixel du panneau fixe, lue comme
   une barre noire parasite en haut d'ecran. On la retire uniquement en mode compact. */
.as-home-sticky-panel > div:nth-child(2){ transition: border-top-color .15s ease; }
body.cs-hdr-min .as-home-sticky-panel > div:nth-child(2){ border-top-color: transparent !important; }
/* 2026-08-02 (Franck) : obsolete -- as-terr-bar-inline fait maintenant partie
   du flux normal DANS .as-home-sticky-panel (position:sticky sur le parent),
   elle n'a plus besoin d'un position:fixed independant ni d'un top calcule. */
.site-footer .footer-widgets{ max-width:900px; margin-left:auto !important; margin-right:auto !important; padding-top:22px !important; padding-bottom:22px !important; } .site-footer .site-info{ max-width:900px; margin-left:auto !important; margin-right:auto !important; } .site-footer li{ line-height:1.45 !important; margin-bottom:2px !important; } .site-footer .widget, .site-footer .footer-widget{ margin-bottom:0 !important; } .site-footer .footer-widgets-container .widget_nav_menu ul.menu{ padding:0 !important; margin:0 !important; } .site-footer .footer-widgets-container .widget_nav_menu ul.menu > li{ margin:0 0 4px !important; padding:0 !important; line-height:1.3 !important; } .site-footer .footer-widgets-container .widget_nav_menu ul.menu > li > a{ padding:0 !important; display:inline-block !important; line-height:1.3 !important; } .site-footer .widget_nav_menu .sub-menu{ list-style:none; margin:2px 0 6px 12px !important; padding:0 !important; } .site-footer .widget_nav_menu .sub-menu li{ margin:0 0 2px !important; padding:0 !important; line-height:1.3 !important; } .site-footer .widget_nav_menu .sub-menu a{ font-size:12.5px; color:#6F6B62; padding:0 !important; display:inline-block !important; line-height:1.3 !important; }body.home .as-site-header__wordmark img{ max-height:30px !important; } .as-menu-overlay .as-site-header__menu{ display:block !important; } .as-menu-overlay .as-site-header__menu li{ border-bottom:1px solid #E3DCCE; } .as-menu-overlay .as-site-header__menu a{ display:block; padding:15px 0; } .as-menu-overlay .as-site-header__menu .sub-menu{ display:block !important; position:static; border:0; min-width:0; padding:0 0 10px 14px; } .as-menu-overlay .as-site-header__menu .sub-menu a{ padding:8px 0; text-transform:none; letter-spacing:0; } </style>
<?php }, 30);
add_action('wp_footer', function () { ?>
<script>
(function(){
 var b=document.body, hdr=document.querySelector('.as-site-header'), terr=document.querySelector('.as-terr-bar');
 var isHome = b.classList.contains('cs-home');
 var cachedHomeThreshold = null;
 function homeThreshold(){
   if (cachedHomeThreshold !== null) { return cachedHomeThreshold; }
   var taglines = document.querySelectorAll('.as-masthead-tagline');
   for (var i=0;i<taglines.length;i++){
     var el = taglines[i];
     if (el.offsetParent !== null){
       var bar = el.parentElement.nextElementSibling;
       var target = bar || el;
       var rect = target.getBoundingClientRect();
       cachedHomeThreshold = (window.scrollY||document.documentElement.scrollTop) + rect.bottom;
       return cachedHomeThreshold;
     }
   }
   return 80;
 }
 function sync(){
  if(!hdr||!terr){ return; }
  if (terr.classList.contains('as-terr-bar-inline')) { return; }
  terr.style.top = hdr.offsetHeight + 'px';
 }
 // 2026-08-02 (Franck) : CALES DE COMPENSATION. Les blocs qui passent en
 // position:fixed au scroll sortent du flux : sans remplacer leur hauteur
 // exacte, tout le contenu en dessous remonte d'un coup au franchissement du
 // seuil et redescend au retour (229px mesures sur la home mobile). Au
 // voisinage du seuil, le moindre mouvement de doigt faisait donc sauter la
 // page entiere -- bug signale le 2026-08-01 ("tout saute", video a l'appui).
 // La hauteur est mesuree JUSTE AVANT le passage en fixed, donc a l'etat
 // deploye, et rendue au flux par une cale de meme hauteur.
 var groups = [];
 if (isHome) {
   var mobPanel = document.querySelector('.as-home-sticky-panel');
   if (mobPanel) { groups.push({ els: [mobPanel], anchor: mobPanel }); }
   var dNav = document.querySelector('.as-home-desktop__nav');
   var dTerr = document.querySelector('.as-home-desktop .as-terr-bar-inline');
   if (dNav && dTerr) { groups.push({ els: [dNav, dTerr], anchor: dTerr }); }
   groups.forEach(function (g) {
     var sp = document.createElement('div');
     sp.setAttribute('aria-hidden', 'true');
     sp.style.display = 'none';
     g.anchor.parentNode.insertBefore(sp, g.anchor.nextSibling);
     g.spacer = sp;
   });
 }
 var compact = null;
 function setCompact(on){
   if (on === compact) { return; }
   if (on) {
     groups.forEach(function (g) {
       var h = 0;
       g.els.forEach(function (e) { if (e.offsetParent !== null) { h += e.getBoundingClientRect().height; } });
       g.spacer.style.height = h + 'px';
       g.spacer.style.display = h > 0 ? 'block' : 'none';
     });
     b.classList.add('cs-hdr-min');
   } else {
     b.classList.remove('cs-hdr-min');
     groups.forEach(function (g) { g.spacer.style.display = 'none'; });
   }
   compact = on;
 }
 function onScroll(){
   var y=window.scrollY||document.documentElement.scrollTop;
   var limit = isHome ? homeThreshold() : 80;
   setCompact(y > limit);
   sync();
 }
 window.addEventListener('scroll', onScroll, {passive:true});
 window.addEventListener('resize', sync);
 sync(); onScroll();
})();
</script>
<?php }, 30);