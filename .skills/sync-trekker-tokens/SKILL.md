---
name: sync-trekker-tokens
description: "Sync design tokens from the Trekker V2 Figma file to tokens.json. Use this skill whenever the user says 'sync tokens', 'update tokens', 'export tokens', 'pull from Figma', or mentions refreshing design tokens. Also trigger when the user asks about token values and wants the latest data from Figma."
---

# Sync Trekker Tokens

Extracts all design tokens and text styles from the Trekker V2 Figma file using the **plugin runtime** (figma_execute), then writes them to `tokens.json` and stamps them into `index.html` via the export pipeline.

## Why plugin runtime matters

The Figma REST API and variable cache can serve stale data. The plugin runtime (`figma_execute`) reads directly from the open document in Figma Desktop, so it always reflects the user's latest edits. Every extraction in this skill MUST use `figma_execute` — never `figma_get_variables` or other cached endpoints.

## Prerequisites

- Figma Desktop must be open with the Trekker V2 file
- The Desktop Bridge plugin must be connected (verify with `figma_get_status`)
- The workspace folder must be the `trekker-tokens` directory

## Workflow

### Step 1: Verify connection

Call `figma_get_status` and confirm WebSocket connection to "Trekker V2".

### Step 2: Extract all variable collections

Run this single `figma_execute` call (timeout 30000ms) to pull every variable collection with fully resolved values:

```javascript
const collections = await figma.variables.getLocalVariableCollectionsAsync();
const result = [];

for (const coll of collections) {
  const collData = {
    id: coll.id, name: coll.name,
    modes: coll.modes.map(m => ({ id: m.modeId, name: m.name })),
    variables: []
  };

  for (const varId of coll.variableIds) {
    const v = await figma.variables.getVariableByIdAsync(varId);
    const modeValues = {};

    for (const mode of coll.modes) {
      const raw = v.valuesByMode[mode.modeId];
      if (raw && raw.type === 'VARIABLE_ALIAS') {
        const alias = await figma.variables.getVariableByIdAsync(raw.id);
        const aliasColl = await figma.variables.getVariableCollectionByIdAsync(alias.variableCollectionId);
        let finalVal = alias.valuesByMode[aliasColl.defaultModeId];
        while (finalVal && finalVal.type === 'VARIABLE_ALIAS') {
          const next = await figma.variables.getVariableByIdAsync(finalVal.id);
          const nc = await figma.variables.getVariableCollectionByIdAsync(next.variableCollectionId);
          finalVal = next.valuesByMode[nc.defaultModeId];
        }
        modeValues[mode.name] = { alias: alias.name, resolved: finalVal };
      } else {
        modeValues[mode.name] = { resolved: raw };
      }
    }

    collData.variables.push({
      name: v.name, type: v.resolvedType,
      description: v.description || '', values: modeValues
    });
  }
  result.push(collData);
}
return result;
```

The result will be large. Save it to a temp file for processing.

### Step 3: Extract text styles

Run a second `figma_execute` call:

```javascript
const styles = await figma.getLocalTextStylesAsync();
return styles.map(s => ({
  name: s.name, description: s.description || '',
  fontFamily: s.fontName.family, fontStyle: s.fontName.style,
  fontSize: s.fontSize,
  lineHeight: s.lineHeight.unit === 'PIXELS' ? s.lineHeight.value : 'AUTO',
  letterSpacing: s.letterSpacing.value
}));
```

### Step 4: Build tokens.json

Save the variable collections from Step 2 to a temp file (e.g. `/tmp/figma_variables.json`) and the text styles from Step 3 to another temp file (e.g. `/tmp/figma_styles.json`). Then run:

```bash
python3 <workspace>/.skills/sync-trekker-tokens/scripts/build_tokens.py \
  /tmp/figma_variables.json \
  /tmp/figma_styles.json \
  <workspace>/tokens.json
```

The script takes three positional arguments: variables input, styles input, and output path. It produces `tokens.json` following the schema documented in `references/token-schema.md`.

### Step 5: Stamp into HTML

Run the export pipeline to inject the updated tokens into `index.html`:

```bash
cd <workspace> && node scripts/export-tokens.mjs
```

This replaces the JSON blob inside `<script id="token-data">` in `index.html` with the freshly built `tokens.json`. This step is **mandatory** — `index.html` is the actual site and must always reflect the latest token data.

### Step 6: Verify

Spot-check a few tokens by comparing the generated JSON against plugin runtime values. Report a summary to the user: total token count per collection, and flag any tokens that couldn't be resolved.

## Token schema

Read `references/token-schema.md` for the full output format specification.

## Important rules

1. **Always use figma_execute** — never rely on figma_get_variables or cached data
2. **Resolve aliases fully** — chase VARIABLE_ALIAS chains to the primitive value
3. **Preserve all 5 collections** — color, typography, size, styles, state
4. **Don't clobber** — if only syncing one collection, merge it into the existing tokens.json rather than overwriting
