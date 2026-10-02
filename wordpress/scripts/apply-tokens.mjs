#!/usr/bin/env node
/**
 * apply-tokens.mjs — Applique les design tokens de la charte Cultura Sabauda
 * sur agendasabauda.eu via le plugin Code Snippets.
 *
 * IMPORTANT (découvert le 2026-07-12) : le scope CSS natif "site-css" de Code
 * Snippets est une fonctionnalité PRO — en version gratuite (celle installée,
 * v3.9.6) le snippet s'enregistre et s'active SANS ERREUR mais son code n'est
 * JAMAIS émis côté front (vérifié : absent du HTML public, avec ou sans cache).
 * Contournement : un snippet PHP (scope "front-end", 100% gratuit, déjà utilisé
 * ailleurs sur ce site) qui échote la CSS dans <head> via wp_head. Le CSS est
 * embarqué en base64 dans le code PHP généré pour éviter tout problème
 * d'échappement de guillemets/backslashes.
 *
 * Idempotent : crée le snippet « CS · Design Tokens (charte) » s'il n'existe
 * pas, le met à jour sinon, puis l'active. Réversible (désactivable/supprimable
 * depuis Réglages → Snippets).
 *
 * Auth : Application Password (Basic) lu depuis .env (WP_AS_USER / WP_AS_APP_PASSWORD).
 * Aucune dépendance : fetch natif Node ≥ 18.
 *
 * Usage :  node wordpress/scripts/apply-tokens.mjs
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = join(__dirname, '..', '..');

// ── charge .env (valeurs pouvant contenir des espaces) ──
function loadEnv() {
  const env = {};
  const raw = readFileSync(join(REPO, '.env'), 'utf8');
  for (const line of raw.split('\n')) {
    const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/);
    if (m && !line.trim().startsWith('#')) env[m[1]] = m[2];
  }
  return env;
}

const env = loadEnv();
const BASE = env.WP_AS_URL?.replace(/\/$/, '');
const USER = env.WP_AS_USER;
const PASS = (env.WP_AS_APP_PASSWORD || '').replace(/\s+/g, ''); // app password sans espaces
if (!BASE || !USER || !PASS) {
  console.error('❌ .env incomplet (WP_AS_URL / WP_AS_USER / WP_AS_APP_PASSWORD).');
  process.exit(1);
}
const AUTH = 'Basic ' + Buffer.from(`${USER}:${PASS}`).toString('base64');
const API = `${BASE}/wp-json/code-snippets/v1/snippets`;
const SNIPPET_NAME = 'CS · Design Tokens (charte)';

async function api(path, opts = {}) {
  const res = await fetch(path, {
    ...opts,
    headers: { Authorization: AUTH, 'Content-Type': 'application/json', ...(opts.headers || {}) },
  });
  const text = await res.text();
  let data; try { data = JSON.parse(text); } catch { data = text; }
  if (!res.ok) throw new Error(`HTTP ${res.status} ${path}\n${typeof data === 'string' ? data : JSON.stringify(data)}`);
  return data;
}

function cssAsPhpSnippet(css, styleId) {
  const b64 = Buffer.from(css, 'utf8').toString('base64');
  return `add_action('wp_head', function () {\n    echo '<style id="${styleId}">' . base64_decode('${b64}') . '</style>';\n}, 5);`;
}

async function main() {
  const css = readFileSync(join(REPO, 'wordpress', 'design-system', 'tokens.css'), 'utf8');
  const code = cssAsPhpSnippet(css, 'cs-design-tokens');

  // 1. Le snippet existe-t-il déjà ?
  const list = await api(`${API}?_fields=id,name,scope,active`);
  const existing = Array.isArray(list) ? list.find((s) => s.name === SNIPPET_NAME) : null;

  const payload = { name: SNIPPET_NAME, code, scope: 'front-end', active: true };

  let snippet;
  if (existing) {
    console.log(`↻ Mise à jour du snippet existant [${existing.id}]…`);
    snippet = await api(`${API}/${existing.id}`, { method: 'POST', body: JSON.stringify(payload) });
  } else {
    console.log('＋ Création du snippet…');
    snippet = await api(API, { method: 'POST', body: JSON.stringify(payload) });
  }

  // 2. S'assurer qu'il est actif
  const id = snippet.id || existing?.id;
  const check = await api(`${API}/${id}?_fields=id,name,scope,active`);
  if (!check.active) {
    console.log('▶ Activation…');
    await api(`${API}/${id}/activate`, { method: 'POST' });
  }

  const final = await api(`${API}/${id}?_fields=id,name,scope,active`);
  console.log('✅ OK :', JSON.stringify(final));
  console.log(`   → ${css.length} octets de tokens CSS appliqués site-wide sur ${BASE}`);
}

main().catch((e) => { console.error('❌', e.message); process.exit(1); });
