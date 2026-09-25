#!/usr/bin/env node
/**
 * apply-carte-evenement.mjs — Crée/maintient le Listing Item JetEngine
 * "carte-evenement-blocks" (post_type=jet-engine, vue Blocks/Gutenberg) et y écrit
 * le markup de wordpress/design-system/carte-evenement.gutenberg.html.
 *
 * IMPORTANT : le Listing Item lui-même (source=Posts, from post type=Events, vue=Blocks)
 * doit exister au préalable — créé une fois via l'admin JetEngine (Listings/Components →
 * Add New Item). Ce script NE PEUT PAS le créer (l'API générique ne pose pas les méta
 * requises par JetEngine — leçon apprise avec les Theme Parts). Il ne fait que mettre à
 * jour le CONTENU (content.raw) d'un Listing Item existant, via son ID.
 *
 * Usage : node wordpress/scripts/apply-carte-evenement.mjs <post_id_du_listing>
 *   ex.  node wordpress/scripts/apply-carte-evenement.mjs 969
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
const BASE = env.WP_AS_URL.replace(/\/$/, '') + '/wp-json/wp/v2/jet-engine';

const postId = process.argv[2];
if (!postId) {
  console.error('❌ Usage: node apply-carte-evenement.mjs <post_id>');
  process.exit(1);
}

async function main() {
  const content = readFileSync(join(REPO, 'wordpress', 'design-system', 'carte-evenement.gutenberg.html'), 'utf8');
  const res = await fetch(`${BASE}/${postId}`, {
    method: 'POST',
    headers: { Authorization: AUTH, 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  });
  const data = await res.json();
  if (!res.ok) { console.error('❌', JSON.stringify(data)); process.exit(1); }
  console.log(`✅ Listing ${postId} mis à jour — content.raw = ${data.content.raw.length} octets`);
}
main().catch((e) => { console.error('❌', e.message); process.exit(1); });
