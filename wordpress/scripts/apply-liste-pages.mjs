#!/usr/bin/env node
/**
 * apply-liste-pages.mjs — Pousse le contenu Gutenberg des pages "Tout l'agenda"
 * (932) et "Ce week-end" (930) : titre + Listing Grid (carte-evenement-blocks,
 * post 969, liste dense). Filtre par date ("ce week-end") pas encore câblé
 * (nécessite JetEngine Query Builder) — les deux pages affichent pour l'instant
 * tous les événements publiés.
 *
 * Usage : node wordpress/scripts/apply-liste-pages.mjs
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
const AUTH = 'Basic ' + Buffer.from(`${env.WP_AS_USER}:${(env.WP_AS_APP_PASSWORD || '').replace(/\s+/g, '')}`).toString('base64');
const BASE = env.WP_AS_URL.replace(/\/$/, '') + '/wp-json/wp/v2/pages';

const PAGES = [
  { id: 932, file: 'liste-tout-agenda.gutenberg.html' },
  { id: 930, file: 'liste-ce-week-end.gutenberg.html' },
];

async function main() {
  for (const { id, file } of PAGES) {
    const content = readFileSync(join(REPO, 'wordpress', 'design-system', file), 'utf8');
    const res = await fetch(`${BASE}/${id}`, {
      method: 'POST',
      headers: { Authorization: AUTH, 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    });
    const data = await res.json();
    if (!res.ok) { console.error(`❌ page ${id}`, JSON.stringify(data)); process.exit(1); }
    console.log(`✅ Page ${id} mise à jour — content.raw = ${data.content.raw.length} octets`);
  }
}
main().catch((e) => { console.error('❌', e.message); process.exit(1); });
