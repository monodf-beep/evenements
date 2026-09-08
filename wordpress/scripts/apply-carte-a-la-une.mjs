#!/usr/bin/env node
/**
 * apply-carte-a-la-une.mjs — Met à jour le contenu Gutenberg du Listing Item
 * "carte-a-la-une-blocks" (post_type=jet-engine, vue Blocks/Gutenberg, post 976)
 * avec wordpress/design-system/carte-a-la-une.gutenberg.html.
 *
 * Le Listing Item lui-même a été créé au préalable via l'admin JetEngine
 * (Listings/Components → Add New Item ; source=Posts, from post type=Events,
 * vue=Blocks (Gutenberg)). Ce script ne fait que pousser le content.raw.
 *
 * Usage : node wordpress/scripts/apply-carte-a-la-une.mjs [post_id]
 *   défaut post_id = 976
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

const postId = process.argv[2] || '976';

async function main() {
  const content = readFileSync(join(REPO, 'wordpress', 'design-system', 'carte-a-la-une.gutenberg.html'), 'utf8');
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
