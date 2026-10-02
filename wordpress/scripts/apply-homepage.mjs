#!/usr/bin/env node
/**
 * apply-homepage.mjs — Pousse wordpress/design-system/homepage-mobile.gutenberg.html
 * comme content de la page Accueil (928).
 *
 * Usage : node wordpress/scripts/apply-homepage.mjs [post_id]
 *   défaut post_id = 928
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

const postId = process.argv[2] || '928';

async function main() {
  const content = readFileSync(join(REPO, 'wordpress', 'design-system', 'homepage-mobile.gutenberg.html'), 'utf8');
  const res = await fetch(`${BASE}/${postId}`, {
    method: 'POST',
    headers: { Authorization: AUTH, 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  });
  const data = await res.json();
  if (!res.ok) { console.error('❌', JSON.stringify(data)); process.exit(1); }
  console.log(`✅ Page ${postId} mise à jour — content.raw = ${data.content.raw.length} octets`);
}
main().catch((e) => { console.error('❌', e.message); process.exit(1); });
