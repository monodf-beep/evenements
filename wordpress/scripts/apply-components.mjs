#!/usr/bin/env node
/**
 * apply-components.mjs — Applique le CSS des composants (carte, header, footer,
 * homepage) sur agendasabauda.eu via Code Snippets (scope site-css).
 * Source : wordpress/design-system/components.css (extrait des build-recipes).
 * Idempotent (crée/maj le snippet « CS · Composants (styles) »). Réversible.
 * Auth : Application Password via .env (WP_AS_*). Zéro dépendance.
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
const API = env.WP_AS_URL.replace(/\/$/, '') + '/wp-json/code-snippets/v1/snippets';
const NAME = 'CS · Composants (styles)';

async function api(path, opts = {}) {
  const res = await fetch(path, { ...opts, headers: { Authorization: AUTH, 'Content-Type': 'application/json', ...(opts.headers || {}) } });
  const t = await res.text(); let d; try { d = JSON.parse(t); } catch { d = t; }
  if (!res.ok) throw new Error(`HTTP ${res.status} :: ${typeof d === 'string' ? d.slice(0, 200) : JSON.stringify(d).slice(0, 300)}`);
  return d;
}

async function main() {
  const css = readFileSync(join(REPO, 'wordpress', 'design-system', 'components.css'), 'utf8');
  const list = await api(`${API}?_fields=id,name`);
  const existing = Array.isArray(list) ? list.find((s) => s.name === NAME) : null;
  const payload = { name: NAME, code: css, scope: 'site-css', active: true };
  const snip = existing
    ? await api(`${API}/${existing.id}`, { method: 'POST', body: JSON.stringify(payload) })
    : await api(API, { method: 'POST', body: JSON.stringify(payload) });
  const id = snip.id || existing.id;
  const chk = await api(`${API}/${id}?_fields=id,name,scope,active`);
  if (!chk.active) await api(`${API}/${id}/activate`, { method: 'POST' });
  console.log('✅', JSON.stringify(await api(`${API}/${id}?_fields=id,name,scope,active`)), `(${css.length} octets)`);
}
main().catch((e) => { console.error('❌', e.message); process.exit(1); });
