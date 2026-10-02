/*
 * Test navigateur du défilement continu (article suivant chargé en bas de page).
 *
 * POURQUOI ICI ET PAS DANS run_all.py. Ce test pilote un vrai Chromium contre le site
 * en ligne : il ne tourne ni sur le VPS ni sur une fixture, il se lance depuis une
 * session qui a Playwright (conteneur Claude Code). Il vise les pages de test
 * « test-lecture-corps-* » (noindex), jamais une fiche publiée.
 *
 * ÉCRIT AVANT LE PROTOTYPE (2026-10-01) et passé d'abord sur les pages SANS défilement :
 * « la suite apparaît » devait y échouer, « le pied de page reste atteignable » y
 * réussir. Un témoin qui n'a jamais été rouge ne prouve rien (ERREURS_2026-09-14).
 *
 * Lancer :
 *   PLAYWRIGHT=/opt/node22/lib/node_modules/playwright \
 *   CHROMIUM=/opt/pw-browsers/chromium-1194/chrome-linux/chrome \
 *   node tests/navigateur/defilement_continu.js [URL]
 * Dans le conteneur Claude Code, ajouter PW_SPKI=<empreinte du CA du proxy>
 * (voir /root/.ccr/README.md) : Chromium ne lit pas le magasin NSS du proxy.
 *
 * Ce que le test NE couvre PAS, et qui reste à faire à la main sur un vrai téléphone :
 * l'élan du défilement au doigt (c'est lui qui décide si « s'attarder en bas » marche),
 * un vrai lecteur d'écran, et la police (Nunito Sans ne charge pas dans le conteneur).
 */
'use strict';
const { chromium } = require(process.env.PLAYWRIGHT || 'playwright');

const URL0 = process.argv[2] || 'https://agendasabauda.eu/test-lecture-corps-19/';
const ATTENTE = 1000; // marge d'attente du test (le prototype ne temporise plus que 200 ms)
const PIED = ['.as-footer-mobile', '.site-footer', 'footer'];

const resultats = [];
// Apostrophes et espaces typographiques : la page affiche « ’ » et des insécables là où
// les données gardent « ' » (vu le 02/10 sur « Huit violoncelles… l’Opéra »).
const norm = t => String(t).replace(/[\u2019\u02bc]/g, "'").replace(/[\u00a0\u202f]/g, ' ').replace(/\s+/g, ' ').trim();
function verdict(nom, ok, detail) {
  resultats.push({ nom, ok });
  console.log(`${ok ? 'PASSE ' : 'ÉCHOUE'}  ${nom}${detail ? '  — ' + detail : ''}`);
}

async function ouvrir(navig, vue, opts = {}) {
  const ctx = await navig.newContext({ viewport: vue.taille, isMobile: vue.mobile, hasTouch: vue.mobile, javaScriptEnabled: opts.js !== false });
  const pg = await ctx.newPage();
  const requetes = [];
  pg.on('request', r => { if (/cs-tests\/.*\.json/.test(r.url())) requetes.push(r.url()); });
  const rep = await pg.goto(URL0 + (opts.suffixe || ''), { waitUntil: 'load', timeout: 90000 });
  await pg.waitForTimeout(800);
  // Le bandeau de consentement masque le bas de l'écran ; il n'est pas l'objet du test.
  await pg.evaluate(() => document.querySelectorAll('.cmplz-cookiebanner,#cmplz-cookiebanner-container').forEach(e => e.style.display = 'none')).catch(() => {});
  return { ctx, pg, requetes, statut: rep && rep.status() };
}

// Amène le bas de l'article (sentinelle, ou à défaut fin du corps) au bas de l'écran
// COMME UN LECTEUR : par pas de 150 px toutes les 150 ms (1 000 px/s), jamais d'un bond. Un saut direct
// ressemble à la touche Fin, que le prototype doit justement ignorer : un test qui saute
// ne mesure pas la lecture lente.
//
// LEÇON DU 01/10 : un échec « lecture lente » intermittent a été pris pour un défaut du
// prototype ; c'était un 502 du serveur (page jamais servie). D'où le statut HTTP affiché
// à chaque ouverture : un échec sans « statut 200 » ne dit rien du prototype.
// `avance` (en écrans) arrête la lecture AVANT la fin : 0,5 = la fin de l'article est
// encore une demi-hauteur d'écran sous le bas de l'écran.
async function allerFinArticle(pg, rang, avance = 0) {
  const cible = await pg.evaluate(([rang, avance]) => {
    const s = document.querySelectorAll('.tl-sentinelle')[rang] || document.querySelectorAll('.tl-corps')[rang];
    if (!s) return null;
    return Math.max(0, s.getBoundingClientRect().bottom + scrollY - innerHeight + 60 - avance * innerHeight);
  }, [rang, avance]);
  if (cible === null) return;
  for (let i = 0; i < 200; i++) {
    const y = await pg.evaluate(() => scrollY);
    if (Math.abs(cible - y) < 5) break;
    const pas = Math.sign(cible - y) * Math.min(150, Math.abs(cible - y));
    const avant = y;
    await pg.evaluate(p => scrollBy(0, p), pas);
    await pg.waitForTimeout(150);
    if (Math.abs((await pg.evaluate(() => scrollY)) - avant) < 1) break; // bas de page atteint
  }
}

const nbSuites = pg => pg.evaluate(() => document.querySelectorAll('.tl-art').length);
const chemin = pg => pg.evaluate(() => location.pathname);
const piedVisible = pg => pg.evaluate(sel => sel.some(s => {
  const e = document.querySelector(s); if (!e || e.offsetParent === null) return false;
  const r = e.getBoundingClientRect(); return r.top < innerHeight && r.bottom > 0;
}), PIED);

async function scenarios(navig, vue) {
  const tag = `[${vue.nom}]`;

  // 1. Lecture : la suite doit être LÀ avant qu'on ait fini le premier article (remarque de
  //    Franck, 01/10 : avec « s'arrêter une seconde en bas », il fallait savoir qu'elle
  //    viendrait). La page est ouverte avec #l2c pour vérifier que ce suffixe de test ne
  //    fuit pas sur l'adresse de l'article suivant (vu par Franck le 01/10).
  let { ctx, pg, requetes, statut } = await ouvrir(navig, vue, { suffixe: '#l2c' });
  verdict(`${tag} page de test en ligne`, statut === 200, `statut ${statut}`);
  const cheminDepart = await chemin(pg);
  const titreDepart = await pg.title();
  await pg.waitForTimeout(500);
  verdict(`${tag} aucune requête au chargement`, requetes.length === 0, `${requetes.length} requête(s)`);
  await allerFinArticle(pg, 0, 0.5);
  await pg.waitForTimeout(600);
  const n0 = await nbSuites(pg);
  verdict(`${tag} la suite est là avant la fin du premier article`, n0 === 1, `${n0} article(s) ajouté(s), fin de l'article encore ½ écran plus bas`);
  await allerFinArticle(pg, 0);
  await pg.waitForTimeout(ATTENTE + 1200);
  const n1 = await nbSuites(pg);
  verdict(`${tag} lecture lente : la suite apparaît`, n1 === 1, `${n1} article(s) ajouté(s)`);
  verdict(`${tag} une seule requête pour la suite`, requetes.length === 1, `${requetes.length} requête(s)`);

  if (n1 >= 1) {
    // 2. L'adresse ne change pas tant que le titre suivant est sous le tiers de l'écran...
    const placer = f => pg.evaluate(f => { const h = document.querySelector('.tl-art .tl-head'); scrollTo(0, h.getBoundingClientRect().top + scrollY - innerHeight * f); }, f);
    await placer(0.6); await pg.waitForTimeout(400);
    const cheminAvant = await chemin(pg);
    verdict(`${tag} titre suivant aux 6/10 : adresse inchangée`, cheminAvant === cheminDepart, cheminAvant);
    // ... et change quand il passe au-dessus.
    await placer(0.2); await pg.waitForTimeout(400);
    const urlSuite = await pg.evaluate(() => document.querySelector('.tl-art').getAttribute('data-url'));
    const cheminApres = await chemin(pg);
    verdict(`${tag} titre suivant aux 2/10 : adresse de l'article suivant`, cheminApres === new URL(urlSuite).pathname, cheminApres);
    const hashApres = await pg.evaluate(() => location.hash);
    verdict(`${tag} pas de suffixe de test (#l2c) sur l'adresse suivante`, hashApres === '', hashApres || '(aucun)');
    const titreApres = await pg.title();
    verdict(`${tag} titre de l'onglet suit`, titreApres !== titreDepart, titreApres.slice(0, 60));
    // 3. On remonte : retour à l'article de départ.
    await pg.evaluate(() => scrollTo(0, 0)); await pg.waitForTimeout(400);
    verdict(`${tag} on remonte : adresse de départ`, (await chemin(pg)) === cheminDepart, await chemin(pg));
    verdict(`${tag} on remonte : titre de départ`, (await pg.title()) === titreDepart);

    // 4. Limite : on s'attarde aussi en bas du dernier article -> plus rien, bouton de fin.
    await allerFinArticle(pg, 1);
    await pg.waitForTimeout(ATTENTE + 1200);
    const n2 = await nbSuites(pg);
    const finale = await pg.evaluate(() => !!document.querySelector('.tl-finale'));
    verdict(`${tag} limite : pas plus de 2 articles ajoutés`, n2 <= 2, `${n2}`);
    verdict(`${tag} limite : bouton de fin présent`, finale);
    // Mesure de stabilité (CLS) cumulée pendant tout le scénario.
    const cls = await pg.evaluate(() => (window.__cls || 0));
    verdict(`${tag} stabilité de la page (CLS < 0,1)`, cls < 0.1, `CLS ${cls.toFixed(3)}`);
  }
  await ctx.close();

  // 5. Défilement rapide / touche Fin : le pied de page est atteint, rien ne se charge.
  ({ ctx, pg, requetes, statut } = await ouvrir(navig, vue));
  if (statut !== 200) verdict(`${tag} touche Fin : page servie`, false, `statut ${statut}`);
  await pg.keyboard.press('End');
  await pg.waitForTimeout(300);
  verdict(`${tag} touche Fin : pied de page visible`, await piedVisible(pg));
  await pg.waitForTimeout(ATTENTE + 1200);
  const nFin = await nbSuites(pg);
  verdict(`${tag} touche Fin : rien ne se charge`, nFin === 0, `${nFin} article(s) ajouté(s)`);
  verdict(`${tag} touche Fin : pied de page toujours visible après attente`, await piedVisible(pg));
  await ctx.close();

  // 6. Clavier : « Aller au pied de page » existe, précède la sentinelle, et y amène le focus.
  ({ ctx, pg, statut } = await ouvrir(navig, vue));
  if (statut !== 200) verdict(`${tag} clavier : page servie`, false, `statut ${statut}`);
  const ordre = await pg.evaluate(() => {
    const a = document.querySelector('.tl-saut'), s = document.querySelector('.tl-sentinelle');
    return !!a && !!s && !!(a.compareDocumentPosition(s) & Node.DOCUMENT_POSITION_FOLLOWING);
  });
  const etat = await pg.evaluate(() => `saut=${document.querySelectorAll('.tl-saut').length} sentinelle=${document.querySelectorAll('.tl-sentinelle').length} titre=${document.title.slice(0, 30)}`);
  verdict(`${tag} clavier : lien « Aller au pied de page » avant le chargement`, ordre, ordre ? '' : etat);
  if (ordre) {
    await pg.focus('.tl-saut');
    await pg.keyboard.press('Enter');
    await pg.waitForTimeout(500);
    const focusPied = await pg.evaluate(sel => sel.some(s => { const e = document.querySelector(s); return e && e.contains(document.activeElement); }), PIED);
    verdict(`${tag} clavier : Entrée met le focus dans le pied de page`, focusPied);
  }
  await ctx.close();
}

(async () => {
  const args = process.env.PW_SPKI ? ['--ignore-certificate-errors-spki-list=' + process.env.PW_SPKI] : [];
  const navig = await chromium.launch({ executablePath: process.env.CHROMIUM || undefined, args, proxy: process.env.HTTPS_PROXY ? { server: process.env.HTTPS_PROXY } : undefined });
  // Cumul du CLS dès le chargement de chaque page.
  const initCls = 'window.__cls=0;new PerformanceObserver(l=>{for(const e of l.getEntries()){if(!e.hadRecentInput)window.__cls+=e.value}}).observe({type:"layout-shift",buffered:true});';
  navig.contexts; // (contextes créés par ouvrir())
  const orig = navig.newContext.bind(navig);
  navig.newContext = async o => { const c = await orig(o); await c.addInitScript(initCls); return c; };

  for (const vue of [
    { nom: 'ordinateur', taille: { width: 1900, height: 1000 }, mobile: false },
    // Grand écran : la fin de l'article et le bas de la page y sont à moins d'un écran
    // l'un de l'autre. C'est là qu'une règle « tout en bas = veut le pied de page »
    // bloquerait aussi la lecture lente.
    { nom: 'grand écran', taille: { width: 2560, height: 1440 }, mobile: false },
    { nom: 'téléphone', taille: { width: 390, height: 844 }, mobile: true },
  ]) await scenarios(navig, vue);

  // 7. Ce que voit Google : sans JavaScript, un seul article.
  const vue = { nom: 'sans JS', taille: { width: 1280, height: 900 }, mobile: false };
  const { ctx, pg } = await ouvrir(navig, vue, { js: false });
  const html = await pg.content();
  const titres = (html.match(/class="tl-titre"/g) || []).length;
  verdict('[sans JS] un seul article dans le HTML', titres === 1, `${titres} titre(s) d'article`);
  await ctx.close();

  // 8. L'adresse de l'article suivant est une vraie page.
  const ctx2 = await navig.newContext({ viewport: { width: 1280, height: 900 } });
  const p2 = await ctx2.newPage();
  await p2.goto(URL0, { waitUntil: 'load', timeout: 90000 });
  const suite = await p2.evaluate(async () => { const t = document.querySelector('.tl[data-suite]'); if (!t) return null; const d = await (await fetch(t.getAttribute('data-suite'))).json(); return d.articles[0]; }).catch(() => null);
  if (suite) {
    const rep = await p2.goto(suite.url, { waitUntil: 'load', timeout: 90000 });
    const h1 = await p2.evaluate(() => (document.querySelector('h1') || {}).textContent || '');
    verdict('[rechargement] l\'adresse de la suite est une vraie page', rep.status() === 200 && norm(h1) === norm(suite.titre), `${rep.status()} « ${h1.trim().slice(0, 50)} »`);
  } else verdict('[rechargement] l\'adresse de la suite est une vraie page', false, 'pas de données de suite');
  await ctx2.close();

  await navig.close();
  const ko = resultats.filter(r => !r.ok).length;
  console.log(`\n${resultats.length - ko} passent, ${ko} échouent, sur ${resultats.length} vérifications.`);
  process.exit(ko ? 1 : 0);
})();
