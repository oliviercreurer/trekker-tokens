#!/usr/bin/env python3
"""Build tokens.json from Figma plugin runtime extraction data.

Usage:
    python3 build_tokens.py <variables_json> <styles_json> <output_json>

Arguments:
    variables_json  Path to JSON file with extracted variable collections (from figma_execute)
    styles_json     Path to JSON file with extracted text styles (from figma_execute)
    output_json     Path to write the final tokens.json
"""
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

def rgb_to_hex(r: float, g: float, b: float) -> str:
    """Convert normalized RGB (0-1) to uppercase hex without #."""
    r_int = round(r * 255)
    g_int = round(g * 255)
    b_int = round(b * 255)
    return f"{r_int:02X}{g_int:02X}{b_int:02X}"

def get_alias_suffix(alias: str) -> str:
    """Extract last segment after '/' from alias name."""
    if "/" in alias:
        return alias.split("/")[-1]
    return alias

def load_figma_data(filepath: str) -> List[Dict[str, Any]]:
    """Load Figma variable collections."""
    with open(filepath, 'r') as f:
        return json.load(f)

def find_collection(collections: List[Dict], name: str) -> Optional[Dict]:
    """Find collection by name."""
    for col in collections:
        if col.get("name") == name:
            return col
    return None

def get_collection_meta(collection: Dict) -> Dict:
    """Extract _meta block with collection ID and mode IDs for restore."""
    return {
        "collectionId": collection.get("id", ""),
        "modes": {m["name"]: m["id"] for m in collection.get("modes", [])},
    }

def get_figma_ids(var: Dict) -> Dict:
    """Extract _figmaId and _aliasIds from a variable for restore."""
    ids = {"_figmaId": var.get("id", "")}
    alias_ids = {}
    for mode_name, mode_data in var.get("values", {}).items():
        if "aliasId" in mode_data:
            alias_ids[mode_name] = mode_data["aliasId"]
    if alias_ids:
        ids["_aliasIds"] = alias_ids
    return ids

def get_mode_id_by_name(collection: Dict, mode_name: str) -> Optional[str]:
    """Get mode ID by mode name."""
    for mode in collection.get("modes", []):
        if mode.get("name") == mode_name:
            return mode.get("id")
    return None

def build_color_collection(figma_data: List[Dict]) -> Dict:
    """Build color collection from Figma Color collection."""
    color_col = find_collection(figma_data, "Color")
    if not color_col:
        return {"name": "Color", "modes": ["Light", "Dark"], "groups": {}}

    meta = get_collection_meta(color_col)

    modes_list = [m["name"] for m in color_col.get("modes", [])]
    groups = {
        "background": {"label": "Background", "tokens": []},
        "border": {"label": "Border", "tokens": []},
        "icon": {"label": "Icon", "tokens": []},
        "link": {"label": "Link", "tokens": []},
        "skeleton": {"label": "Skeleton", "tokens": []},
        "text": {"label": "Text", "tokens": []},
        "opacity": {"label": "Opacity", "tokens": []},
    }

    for var in color_col.get("variables", []):
        var_name = var["name"]
        var_type = var["type"]
        description = var.get("description", "")

        # Get first segment for grouping
        first_segment = var_name.split("/")[0] if "/" in var_name else var_name

        if first_segment not in groups:
            continue

        figma_ids = get_figma_ids(var)

        if var_type == "COLOR":
            token = {"name": var_name, "description": description, **figma_ids}

            # Get Light and Dark values (use mode names, not IDs)
            if "Light" in var.get("values", {}):
                light_data = var["values"]["Light"]
                light_resolved = light_data.get("resolved")
                light_val = {}
                if light_resolved and "r" in light_resolved:
                    light_val["hex"] = rgb_to_hex(
                        light_resolved["r"],
                        light_resolved["g"],
                        light_resolved["b"]
                    )
                if "alias" in light_data:
                    light_val["alias"] = get_alias_suffix(light_data["alias"])
                token["light"] = light_val

            if "Dark" in var.get("values", {}):
                dark_data = var["values"]["Dark"]
                dark_resolved = dark_data.get("resolved")
                dark_val = {}
                if dark_resolved and "r" in dark_resolved:
                    dark_val["hex"] = rgb_to_hex(
                        dark_resolved["r"],
                        dark_resolved["g"],
                        dark_resolved["b"]
                    )
                if "alias" in dark_data:
                    dark_val["alias"] = get_alias_suffix(dark_data["alias"])
                token["dark"] = dark_val

            groups[first_segment]["tokens"].append(token)

        elif var_type == "FLOAT":
            token = {"name": var_name, "description": description, **figma_ids}

            if "Light" in var.get("values", {}):
                light_resolved = var["values"]["Light"].get("resolved")
                token["light"] = {"value": light_resolved} if light_resolved is not None else {}

            if "Dark" in var.get("values", {}):
                dark_resolved = var["values"]["Dark"].get("resolved")
                token["dark"] = {"value": dark_resolved} if dark_resolved is not None else {}

            groups[first_segment]["tokens"].append(token)

    # Filter out empty groups
    groups = {k: v for k, v in groups.items() if v["tokens"]}

    return {
        "name": "Color",
        "modes": ["Light", "Dark"],
        "_meta": meta,
        "groups": groups
    }

def build_typography_collection(figma_data: List[Dict]) -> Dict:
    """Build typography collection from Figma Typography collection."""
    typo_col = find_collection(figma_data, "Typography")
    if not typo_col:
        return {"name": "Typography", "groups": {}}

    meta = get_collection_meta(typo_col)
    groups = {
        "family": {"label": "Family", "tokens": []},
        "weight": {"label": "Weight", "tokens": []},
        "size": {"label": "Size", "tokens": []},
        "height": {"label": "Height", "tokens": []},
        "spacing": {"label": "Spacing", "tokens": []},
    }

    for var in typo_col.get("variables", []):
        var_name = var["name"]
        var_type = var["type"]
        description = var.get("description", "")
        figma_ids = get_figma_ids(var)

        # Get second segment for grouping (after "font/")
        parts = var_name.split("/")
        if len(parts) < 2:
            continue

        second_segment = parts[1]
        if second_segment not in groups:
            continue

        # Use "Default" mode name to look up values (not ID)
        if "Default" in var.get("values", {}):
            resolved = var["values"]["Default"].get("resolved")

            token = {
                "name": var_name,
                "description": description,
                **figma_ids,
            }
            if var_type == "STRING":
                token["value"] = resolved
            elif var_type == "FLOAT":
                token["value"] = resolved

            groups[second_segment]["tokens"].append(token)

    # Filter out empty groups
    groups = {k: v for k, v in groups.items() if v["tokens"]}

    return {
        "name": "Typography",
        "_meta": meta,
        "groups": groups
    }

def build_size_collection(figma_data: List[Dict]) -> Dict:
    """Build size collection from Figma Size collection."""
    size_col = find_collection(figma_data, "Size")
    if not size_col:
        return {"name": "Size", "groups": {}}

    meta = get_collection_meta(size_col)
    groups = {
        "spacing": {"label": "Spacing", "tokens": []},
        "radius": {"label": "Radius", "tokens": []},
        "stroke": {"label": "Stroke", "tokens": []},
    }

    for var in size_col.get("variables", []):
        var_name = var["name"]
        description = var.get("description", "")
        figma_ids = get_figma_ids(var)

        first_segment = var_name.split("/")[0] if "/" in var_name else var_name

        if first_segment not in groups:
            continue

        # Use "Mode 1" mode name to look up values (not ID)
        if "Mode 1" in var.get("values", {}):
            resolved = var["values"]["Mode 1"].get("resolved")
            token = {
                "name": var_name,
                "value": resolved,
                "description": description,
                **figma_ids,
            }
            groups[first_segment]["tokens"].append(token)

    # Also check Color collection for stroke/* variables
    color_col = find_collection(figma_data, "Color")
    if color_col:
        for var in color_col.get("variables", []):
            var_name = var["name"]
            if var_name.startswith("stroke/"):
                description = var.get("description", "")
                figma_ids = get_figma_ids(var)
                # Use Color collection's Light mode for stroke values
                if "Light" in var.get("values", {}):
                    resolved = var["values"]["Light"].get("resolved")
                    token = {
                        "name": var_name,
                        "value": resolved,
                        "description": description,
                        **figma_ids,
                    }
                    groups["stroke"]["tokens"].append(token)

    # Filter out empty groups
    groups = {k: v for k, v in groups.items() if v["tokens"]}

    return {
        "name": "Size",
        "_meta": meta,
        "groups": groups
    }

def build_styles_collection(figma_data: List[Dict], text_styles: List[Dict]) -> Dict:
    """Build styles collection from text styles extracted via figma_execute."""
    groups = {
        "heading": {"label": "Heading", "styles": []},
        "body": {"label": "Body", "styles": []},
        "technical": {"label": "Technical", "styles": []},
    }

    # Build value lookup for typography variables
    typo_col = find_collection(figma_data, "Typography")

    # Create mappings: value -> variable name
    font_family_map = {}  # "Outfit" -> "font/family/body"
    font_weight_map = {}  # "SemiBold" -> "font/weight/semibold"
    font_size_map = {}    # 48 -> "font/size/1000"
    font_height_map = {}  # 60 -> "font/height/1000"

    if typo_col:
        for var in typo_col.get("variables", []):
            var_name = var["name"]
            resolved = var.get("values", {}).get("Default", {}).get("resolved")

            if resolved is None:
                continue

            if "family" in var_name and var.get("type") == "STRING":
                font_family_map[resolved] = var_name
            elif "weight" in var_name and var.get("type") == "STRING":
                font_weight_map[resolved] = var_name
            elif "size" in var_name and var.get("type") == "FLOAT":
                font_size_map[resolved] = var_name
            elif "height" in var_name and var.get("type") == "FLOAT":
                font_height_map[resolved] = var_name

    # Specimen text
    headings_specimen = "Fire"
    body_specimen = "Through the darkness of future's past, the magician longs to see. One chants out between two worlds...Fire walk with me."

    for style in text_styles:
        style_name = style["name"]
        first_segment = style_name.split("/")[0]

        if first_segment not in groups:
            continue

        # Convert name format: "heading/xxlarge" -> "text.heading.xxlarge"
        text_name = "text." + style_name.replace("/", ".")

        # Select specimen
        if first_segment == "heading":
            specimen = headings_specimen
        elif first_segment == "body":
            specimen = body_specimen
        elif first_segment == "technical":
            if "code" in style_name:
                specimen = "const greeting = 'Fire walk with me';"
            else:
                specimen = "0123456789"
        else:
            specimen = ""

        # Build recipe
        recipe = {}

        # fontFamily
        font_family = style.get("fontFamily")
        if font_family in font_family_map:
            recipe["fontFamily"] = font_family_map[font_family]

        # fontWeight
        font_style = style.get("fontStyle")
        weight_lower = font_style.lower() if font_style else "regular"
        weight_var = f"font/weight/{weight_lower}"
        recipe["fontWeight"] = weight_var

        # fontSize
        font_size = style.get("fontSize")
        if font_size in font_size_map:
            recipe["fontSize"] = font_size_map[font_size]

        # lineHeight
        line_height = style.get("lineHeight")
        if line_height in font_height_map:
            recipe["lineHeight"] = font_height_map[line_height]

        # letterSpacing
        letter_spacing = style.get("letterSpacing")
        if letter_spacing == -0.5:
            recipe["letterSpacing"] = "font/spacing/tight"
        elif letter_spacing == 0:
            recipe["letterSpacing"] = "font/spacing/normal"
        else:
            recipe["letterSpacing"] = f"font/spacing/{letter_spacing}"

        style_token = {
            "name": text_name,
            "specimen": specimen,
            "resolved": {
                "fontFamily": style.get("fontFamily"),
                "fontStyle": style.get("fontStyle"),
                "fontSize": style.get("fontSize"),
                "lineHeight": style.get("lineHeight"),
                "letterSpacing": style.get("letterSpacing"),
            },
            "recipe": recipe,
        }

        groups[first_segment]["styles"].append(style_token)

    return {
        "name": "Styles",
        "groups": groups
    }

def build_state_collection(figma_data: List[Dict]) -> Dict:
    """Build state collection from Figma State collection."""
    state_col = find_collection(figma_data, "State")
    if not state_col:
        return {"name": "State", "modes": ["default"], "groups": {"interaction": {"label": "Interaction", "tokens": []}}}

    meta = get_collection_meta(state_col)
    groups = {
        "interaction": {"label": "Interaction", "tokens": []},
    }

    for var in state_col.get("variables", []):
        var_name = var["name"]
        var_type = var["type"]
        description = var.get("description", "")
        figma_ids = get_figma_ids(var)

        # Use "Mode 1" mode name to look up values (not ID)
        if "Mode 1" in var.get("values", {}):
            resolved = var["values"]["Mode 1"].get("resolved")
            token = {
                "name": var_name,
                "type": var_type,
                "value": resolved,
                "description": description,
                **figma_ids,
            }
            groups["interaction"]["tokens"].append(token)

    return {
        "name": "State",
        "modes": ["default"],
        "_meta": meta,
        "groups": groups
    }

def main():
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)

    input_file = sys.argv[1]
    styles_file = sys.argv[2]
    output_file = sys.argv[3]

    # Load Figma variable collections
    print(f"Loading variable data from {input_file}...")
    figma_data = load_figma_data(input_file)
    print(f"Loaded {len(figma_data)} collections")

    # Load text styles
    print(f"Loading text styles from {styles_file}...")
    with open(styles_file, 'r') as f:
        text_styles = json.load(f)
    print(f"Loaded {len(text_styles)} text styles")

    # Build collections
    print("Building collections...")
    collections = {
        "color": build_color_collection(figma_data),
        "typography": build_typography_collection(figma_data),
        "size": build_size_collection(figma_data),
        "styles": build_styles_collection(figma_data, text_styles),
        "state": build_state_collection(figma_data),
    }

    # Build output
    output = {
        "exportedAt": datetime.now(timezone.utc).isoformat(),
        "collections": collections,
    }

    # Back up existing tokens.json before overwriting
    output_path = Path(output_file)
    if output_path.exists():
        backup_dir = output_path.parent / ".backups"
        backup_dir.mkdir(exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        backup_path = backup_dir / f"tokens-{stamp}.json"
        shutil.copy2(output_path, backup_path)
        print(f"Backed up previous tokens to {backup_path}")

        # Keep only the 10 most recent backups
        backups = sorted(backup_dir.glob("tokens-*.json"), key=lambda p: p.stat().st_mtime)
        if len(backups) > 10:
            for old_backup in backups[:-10]:
                old_backup.unlink()
            print(f"Pruned {len(backups) - 10} old backup(s)")

    # Preserve existing changelog from previous tokens.json
    if output_path.exists():
        try:
            with open(output_path, 'r') as f:
                existing = json.load(f)
            if "changelog" in existing:
                output["changelog"] = existing["changelog"]
                print(f"Preserved {len(output['changelog'])} changelog entries")
        except (json.JSONDecodeError, KeyError):
            pass

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Writing output to {output_file}...")
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)

    # Print summary
    print("\nSummary:")
    for col_key, col in collections.items():
        if "groups" in col:
            total_tokens = sum(
                len(g.get("tokens", [])) + len(g.get("styles", []))
                for g in col["groups"].values()
            )
            print(f"  {col['name']}: {len(col['groups'])} groups, {total_tokens} tokens")
        else:
            print(f"  {col['name']}: 0 tokens")

    print(f"\nExported to {output_file}")

if __name__ == "__main__":
    main()
