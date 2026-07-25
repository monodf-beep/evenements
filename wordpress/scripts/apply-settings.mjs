#!/usr/bin/env node
/**
 * apply-settings.mjs — Règle l'identité de base d'agendasabauda.eu.
 *
 * Titre du site, accroche (baseline de marque), fuseau horaire, début de semaine.
 * Idempotent (rejouable sans effet de bord). Réversible depuis Réglages → Général.
 *
 * Auth : Application Password (Basic) via .env (WP_AS_*). Zéro dépendance.
 * Usage : node wordpress/scripts/apply-settings.mjs
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const REPO = join(dirname(fileURLToPath(import.meta.url)), '..', '..');

function loadEnv() {
  const env = {};
  for (const line of readFileSync(join(REPO, '.env'), 'utf8').split('\n')) {
    const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/);
    if (m && !line.trim().startsWith('#')) env[m[1]] = m[2];
  }
  return env;
}

const env = loadEnv();
const BASE = env.WP_AS_URL?.replace(/\/$/, '');
const AUTH = 'Basic ' + Buffer.from(`${env.WP_AS_USER}:${(env.WP_AS_APP_PASSWORD || '').replace(/\s+/g, '')}`).toString('base64');

// Réglages cibles (accroche = baseline documentée dans docs/BRIEF_DESIGN_AGENDA_SABAUDA.md)
const SETTINGS = {
  title: 'Agenda Sabauda',
  description: 'Que faire dans les Alpes, de Chambéry à Turin',
  timezone: 'Europe/Paris',
  start_of_week: 1, // lundi
};

async function main() {
  const url = `${BASE}/wp-json/wp/v2/settings`;
  const before = await (await fetch(url, { headers: { Authorization: AUTH } })).json();
  console.log('Avant :', JSON.stringify({ title: before.title, description: before.description, timezone: before.timezone }));

  const res = await fetch(url, {
    method: 'POST',
    headers: { Authorization: AUTH, 'Content-Type': 'application/json' },
    body: JSON.stringify(SETTINGS),
  });
  const after = await res.json();
  if (!res.ok) { console.error('❌', JSON.stringify(after)); process.exit(1); }
  console.log('Après :', JSON.stringify({ title: after.title, description: after.description, timezone: after.timezone, start_of_week: after.start_of_week }));
  console.log('✅ Identité du site appliquée.');
}

main().catch((e) => { console.error('❌', e.message); process.exit(1); });
