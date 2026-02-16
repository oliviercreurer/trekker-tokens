# Token Schema Reference

## Top-level structure

```json
{
  "exportedAt": "<ISO 8601 UTC timestamp>",
  "collections": {
    "color": { ... },
    "typography": { ... },
    "size": { ... },
    "styles": { ... },
    "state": { ... }
  }
}
```

## Color collection

Source: Figma "Color" variable collection (209 variables).

```json
{
  "name": "Color",
  "modes": ["Light", "Dark"],
  "groups": {
    "background": { "label": "Background", "tokens": [...] },
    "border":     { "label": "Border",     "tokens": [...] },
    "icon":       { "label": "Icon",       "tokens": [...] },
    "link":       { "label": "Link",       "tokens": [...] },
    "skeleton":   { "label": "Skeleton",   "tokens": [...] },
    "text":       { "label": "Text",       "tokens": [...] },
    "opacity":    { "label": "Opacity",    "tokens": [...] }
  }
}
```

### COLOR-type token format

```json
{
  "name": "text/default",
  "description": "Use for headings...",
  "light": { "alias": "base-1000", "hex": "100F0F" },
  "dark":  { "alias": "base-200",  "hex": "CECDC3" }
}
```

Rules:
- **alias**: Strip the prefix group from the alias path. `"base/base-1000"` becomes `"base-1000"`, `"red/red-600"` becomes `"red-600"`. Split on `/`, take the last segment.
- **hex**: Uppercase, 6-character hex, no `#` prefix. Convert from Figma RGBA `{r, g, b, a}` where each channel is 0..1: `round(r * 255)` → hex.
- If no alias (direct value), omit the `alias` field.

### FLOAT-type token format (opacity group)

```json
{
  "name": "opacity/subtle",
  "description": "",
  "light": { "value": 60 },
  "dark":  { "value": 60 }
}
```

### Grouping rule

Group by the **first path segment** of the variable name: `"background/input/default"` → group `"background"`.

## Typography collection

Source: Figma "Typography" variable collection (27 variables, single "Default" mode).

```json
{
  "name": "Typography",
  "groups": {
    "family":  { "label": "Family",  "tokens": [...] },
    "weight":  { "label": "Weight",  "tokens": [...] },
    "size":    { "label": "Size",    "tokens": [...] },
    "height":  { "label": "Height",  "tokens": [...] },
    "spacing": { "label": "Spacing", "tokens": [...] }
  }
}
```

No `modes` field. Group by the **second** path segment (after `font/`): `"font/family/body"` → group `"family"`.

### Token format

```json
{ "name": "font/family/body", "value": "Outfit", "description": "Primary app font" }
```

- STRING type: value is the string
- FLOAT type: value is the number

## Size collection

Source: Figma "Size" variable collection (26 variables, single mode).

```json
{
  "name": "Size",
  "groups": {
    "spacing": { "label": "Spacing", "tokens": [...] },
    "radius":  { "label": "Radius",  "tokens": [...] },
    "stroke":  { "label": "Stroke",  "tokens": [...] }
  }
}
```

No `modes` field. Group by first path segment.

### Token format

```json
{ "name": "spacing/25", "value": 2, "description": "Use for small and compact pieces of UI." }
```

Note: "stroke" variables (stroke/default, stroke/bold, stroke/focused, stroke/selected) live in the Figma **Color** variable collection but belong in the Size/stroke group in the output. Filter them out of the Color output and into Size.

## Styles collection

Source: Figma local text styles (not variables).

```json
{
  "name": "Styles",
  "groups": {
    "heading":   { "label": "Heading",   "styles": [...] },
    "body":      { "label": "Body",      "styles": [...] },
    "technical": { "label": "Technical", "styles": [...] }
  }
}
```

Note: uses `"styles"` key, not `"tokens"`.

### Style format

```json
{
  "name": "text.heading.xxlarge",
  "specimen": "Fire",
  "resolved": {
    "fontFamily": "Outfit",
    "fontStyle": "SemiBold",
    "fontSize": 48,
    "lineHeight": 60,
    "letterSpacing": -0.5
  },
  "recipe": {
    "fontFamily": "font/family/body",
    "fontWeight": "font/weight/semibold",
    "fontSize": "font/size/1000",
    "lineHeight": "font/height/1000",
    "letterSpacing": "font/spacing/tight"
  }
}
```

Rules:
- **name**: Convert `"heading/xxlarge"` → `"text.heading.xxlarge"` (prepend `text.`, replace `/` with `.`)
- **specimen**: `"Fire"` for headings. For body styles, use the Twin Peaks quote: `"Through the darkness of future's past, the magician longs to see. One chants out between two worlds...Fire walk with me."`. For technical styles: `"const greeting = 'Fire walk with me';"` for code, descriptive text for others.
- **recipe**: Map resolved values back to Typography variable names. Use lookups:
  - fontFamily: "Outfit" → "font/family/body", "JetBrains Mono" → "font/family/code"
  - fontWeight: "SemiBold" → "font/weight/semibold", "Medium" → "font/weight/medium", "Regular" → "font/weight/regular", "Bold" → "font/weight/bold"
  - fontSize: reverse-lookup the Typography size variable whose value matches
  - lineHeight: reverse-lookup the Typography height variable whose value matches
  - letterSpacing: -0.5 → "font/spacing/tight", 0 → "font/spacing/normal"

## State collection

Source: Figma "State" variable collection (1 variable).

```json
{
  "name": "State",
  "modes": ["default"],
  "groups": {
    "interaction": {
      "label": "Interaction",
      "tokens": [
        { "name": "Dark mode", "type": "BOOLEAN", "value": false, "description": "" }
      ]
    }
  }
}
```

Mode name is lowercase `"default"`.
