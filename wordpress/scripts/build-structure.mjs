#!/usr/bin/env node
/**
 * build-structure.mjs — Crée la structure de navigation d'agendasabauda.eu :
 *   1. Pages piliers (FR) — idempotent par slug.
 *   2. Menu principal « Principal FR » + items (temporel, Catégories▾, Territoires▾,
 *      Agenda▾, À propos, Proposer). Idempotent : si le menu existe déjà, on ne
 *      recrée PAS les items (évite les doublons) — supprimer le menu pour rebâtir.
 *
 * Ne touche PAS au réglage front-page (la home se règlera avec son contenu).
 * Auth : Application Password via .env (WP_AS_*). Zéro dépendance (fetch natif).
 * Usage : node wordpress/scripts/build-structure.mjs
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const REPO = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const env = {};
for (const line of readFileSync(join(REPO, '.env'), 'utf8').split('\n')) {
  const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/);
  if (m && !line.trim().startsWith('#')) env[m[1]] = m[2];
}
const BASE = env.WP_AS_URL.replace(/\/$/, '') + '/wp-json/wp/v2';
const AUTH = 'Basic ' + Buffer.from(`${env.WP_AS_USER}:${(env.WP_AS_APP_PASSWORD || '').replace(/\s+/g, '')}`).toString('base64');

async function api(path, opts = {}) {
  const res = await fetch(BASE + path, {
    ...opts,
    headers: { Authorization: AUTH, 'Content-Type': 'application/json', ...(opts.headers || {}) },
  });
  const text = await res.text();
  let data; try { data = JSON.parse(text); } catch { data = text; }
  if (!res.ok) throw new Error(`HTTP ${res.status} ${path} :: ${typeof data === 'string' ? data.slice(0, 200) : JSON.stringify(data).slice(0, 300)}`);
  return data;
}

// ── 1. Pages piliers ──────────────────────────────────────────────
const PAGES = [
  { slug: 'accueil', title: 'Accueil', content: '<!-- Home construite ensuite (JetEngine Listing Grids). --><p>Que faire dans les Alpes, de Chambéry à Turin.</p>' },
  { slug: 'aujourdhui', title: "Aujourd'hui", content: "<p>Les événements du jour dans les Alpes franco-italiennes.</p>" },
  { slug: 'ce-week-end', title: 'Ce week-end', content: '<p>La sélection du week-end : expositions, concerts, marchés, festivals — de la Savoie au Piémont.</p>' },
  { slug: 'cette-semaine', title: 'Cette semaine', content: '<p>Tout ce qui se passe cette semaine dans les territoires sabaudes.</p>' },
  { slug: 'tout-l-agenda', title: "Tout l'agenda", content: "<p>L'agenda complet, filtrable par date, ville, catégorie et territoire.</p>" },
  { slug: 'a-propos', title: 'À propos', content: '<p>Agenda Sabauda, l’agenda culturel des Alpes franco-italiennes, édité par Cultura Sabauda.</p>' },
  { slug: 'proposer-un-evenement', title: 'Proposer un événement', content: '<p>Vous organisez un événement culturel en Savoie, Piémont ou Vallée d’Aoste ? Proposez-le (soumission modérée).</p>' },
];

async function ensurePage(p) {
  const existing = await api(`/pages?slug=${p.slug}&status=publish,draft&_fields=id,slug`);
  if (Array.isArray(existing) && existing.length) {
    console.log(`  = page « ${p.title} » existe déjà [${existing[0].id}]`);
    return existing[0].id;
  }
  const created = await api('/pages', { method: 'POST', body: JSON.stringify({ title: p.title, slug: p.slug, content: p.content, status: 'publish' }) });
  console.log(`  + page « ${p.title} » créée [${created.id}]`);
  return created.id;
}

// ── 2. Données menu ───────────────────────────────────────────────
const CATS = [
  ['Cinéma', 'cinema'], ['Concerts & Musique', 'concerts-musique'], ['Conférences & Rencontres', 'conferences-rencontres'],
  ['Expositions & Patrimoine', 'expositions-patrimoine'], ['Festivals', 'festivals'], ['Fêtes & Traditions populaires', 'fetes-traditions'],
  ['Gastronomie & Sagre', 'gastronomie-sagre'], ['Jeune public & Famille', 'jeune-public-famille'], ['Marchés & Foires', 'marches-foires'],
  ['Spectacle vivant', 'spectacle-vivant'], ['Sport', 'sport'],
].map(([name, slug]) => ({ name, url: `https://agendasabauda.eu/evenements/categorie/${slug}/` }));

const TERRS = [
  ['Savoie / Haute-Savoie', 'savoie-haute-savoie'], ['Piémont', 'piemont'],
  ["Vallée d'Aoste", 'vallee-d-aoste'], ['Comté de Nice', 'nice-alpes-maritimes'],
].map(([name, slug]) => ({ name, url: `https://agendasabauda.eu/territoire/${slug}/` }));

let order = 0;
async function addItem(menuId, { title, pageId, url, parent }) {
  const body = { title, menus: menuId, status: 'publish', menu_order: ++order };
  if (parent) body.parent = parent;
  if (pageId) { body.type = 'post_type'; body.object = 'page'; body.object_id = pageId; }
  else { body.type = 'custom'; body.url = url || '#'; }
  const it = await api('/menu-items', { method: 'POST', body: JSON.stringify(body) });
  return it.id;
}

async function main() {
  console.log('── 1. Pages piliers ──');
  const pid = {};
  for (const p of PAGES) pid[p.slug] = await ensurePage(p);

  console.log('── 2. Menu principal ──');
  const menus = await api('/menus?slug=principal-fr&_fields=id,slug');
  if (Array.isArray(menus) && menus.length) {
    console.log(`  = menu « Principal FR » existe déjà [${menus[0].id}] — items non recréés (supprimer le menu pour rebâtir).`);
    console.log('✅ Terminé (pages ok, menu déjà en place).');
    return;
  }
  const menu = await api('/menus', { method: 'POST', body: JSON.stringify({ name: 'Principal FR', slug: 'principal-fr' }) });
  console.log(`  + menu « Principal FR » créé [${menu.id}]`);

  await addItem(menu.id, { title: "Aujourd'hui", pageId: pid['aujourdhui'] });
  await addItem(menu.id, { title: 'Ce week-end', pageId: pid['ce-week-end'] });

  const cat = await addItem(menu.id, { title: 'Catégories', url: '#' });
  for (const c of CATS) await addItem(menu.id, { title: c.name, url: c.url, parent: cat });

  const terr = await addItem(menu.id, { title: 'Territoires', url: '#' });
  for (const t of TERRS) await addItem(menu.id, { title: t.name, url: t.url, parent: terr });

  const ag = await addItem(menu.id, { title: 'Agenda', url: '#' });
  await addItem(menu.id, { title: "Tout l'agenda", pageId: pid['tout-l-agenda'], parent: ag });
  await addItem(menu.id, { title: 'Cette semaine', pageId: pid['cette-semaine'], parent: ag });

  await addItem(menu.id, { title: 'À propos', pageId: pid['a-propos'] });
  await addItem(menu.id, { title: 'Proposer un événement', pageId: pid['proposer-un-evenement'] });

  console.log(`✅ Menu « Principal FR » construit (${order} items) + ${PAGES.length} pages. Menu ID = ${menu.id}`);
}

main().catch((e) => { console.error('❌', e.message); process.exit(1); });
