#!/usr/bin/env node
/**
 * Trekker Design Token Export Pipeline
 *
 * Reads the current token data JSON, merges it into the HTML template,
 * and writes index.html.
 *
 * The token data itself is extracted from Figma via the Desktop Bridge
 * plugin (see the companion Cowork shortcut "Sync Trekker Tokens").
 * This script handles the second half: stamping the data into the HTML.
 *
 * Usage:
 *   node scripts/export-tokens.mjs [--data tokens.json] [--template index.html] [--out index.html]
 */

import { readFileSync, writeFileSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = resolve(__dirname, '..');

// Parse args
const args = process.argv.slice(2);
function flag(name, fallback) {
  const i = args.indexOf(`--${name}`);
  return i >= 0 && args[i + 1] ? args[i + 1] : fallback;
}

const dataPath = resolve(root, flag('data', 'tokens.json'));
const templatePath = resolve(root, flag('template', 'index.html'));
const outPath = resolve(root, flag('out', 'index.html'));

// Read
const tokenData = JSON.parse(readFileSync(dataPath, 'utf-8'));

// Stamp export date
tokenData.exportedAt = new Date().toISOString();

const html = readFileSync(templatePath, 'utf-8');

// Replace the JSON blob inside <script id="token-data">...</script>
const updated = html.replace(
  /(<script id="token-data" type="application\/json">)([\s\S]*?)(<\/script>)/,
  `$1\n${JSON.stringify(tokenData, null, 2)}\n$3`
);

writeFileSync(outPath, updated, 'utf-8');

const count = Object.values(tokenData.collections).reduce((n, col) =>
  n + Object.values(col.groups).reduce((m, g) => m + g.tokens.length, 0), 0);

console.log(`✓ Wrote ${outPath}`);
console.log(`  ${count} tokens across ${Object.keys(tokenData.collections).length} collections`);
console.log(`  Exported at ${tokenData.exportedAt}`);
