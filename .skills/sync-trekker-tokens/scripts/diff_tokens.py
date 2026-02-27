#!/usr/bin/env python3
"""Diff two tokens.json files and append a changelog entry to the new one.

Usage:
    python3 diff_tokens.py <old_tokens_json> <new_tokens_json> [--notes "Optional description"]

The script compares old vs new, detects added/changed/removed tokens,
and appends a changelog entry to the new tokens.json file in-place.

Changelog entries store flat hex strings for before/after values
(not full token objects) so the React UI can render them directly.
"""
import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


def flatten_tokens(data: Dict) -> Dict[str, Dict]:
    """Build a flat map of key -> token data from a tokens.json structure."""
    tokens = {}
    for coll_key, coll in data.get("collections", {}).items():
        for grp_key, grp in coll.get("groups", {}).items():
            items = grp.get("tokens", grp.get("styles", []))
            for t in items:
                name = t["name"]
                key = f"{coll_key}/{grp_key}/{name}"
                tokens[key] = {
                    "raw": t,
                    "collection": coll_key,
                    "group": grp_key,
                    "name": name,
                }
    return tokens


def extract_hex(mode_val: Any) -> Optional[str]:
    """Extract a flat hex string from a token mode value.

    Handles both formats:
      - Simple string: "E6E4D9"
      - Dict with hex: {"hex": "E6E4D9", "alias": "base-100"}
    """
    if isinstance(mode_val, dict):
        return mode_val.get("hex")
    if isinstance(mode_val, str):
        return mode_val
    return None


def token_display(token: Dict) -> Dict:
    """Extract a flat display representation of a token for changelog storage.

    Returns only the fields useful for rendering diffs: light/dark hex values,
    or a scalar value for non-color tokens.
    """
    result = {}
    if "light" in token:
        result["light"] = extract_hex(token["light"])
    if "dark" in token:
        result["dark"] = extract_hex(token["dark"])
    if "value" in token and "light" not in token:
        val = token["value"]
        result["value"] = val if not isinstance(val, dict) else str(val)
    return result


def comparable(token: Dict) -> Dict:
    """Create a comparable representation of a token, ignoring metadata fields."""
    return {k: v for k, v in token.items() if not k.startswith("_")}


def diff(old_data: Dict, new_data: Dict) -> List[Dict]:
    """Compute the list of changes between two tokens.json structures."""
    old_tokens = flatten_tokens(old_data)
    new_tokens = flatten_tokens(new_data)

    old_keys = set(old_tokens.keys())
    new_keys = set(new_tokens.keys())

    changes = []

    # Added tokens
    for k in sorted(new_keys - old_keys):
        t = new_tokens[k]
        entry = {
            "type": "added",
            "collection": t["collection"],
            "group": t["group"],
            "name": t["name"],
        }
        display = token_display(t["raw"])
        if display:
            entry["value"] = display
        changes.append(entry)

    # Removed tokens
    for k in sorted(old_keys - new_keys):
        t = old_tokens[k]
        changes.append({
            "type": "removed",
            "collection": t["collection"],
            "group": t["group"],
            "name": t["name"],
        })

    # Changed tokens
    for k in sorted(old_keys & new_keys):
        old_cmp = comparable(old_tokens[k]["raw"])
        new_cmp = comparable(new_tokens[k]["raw"])
        if old_cmp != new_cmp:
            t = new_tokens[k]
            entry = {
                "type": "changed",
                "collection": t["collection"],
                "group": t["group"],
                "name": t["name"],
                "before": token_display(old_tokens[k]["raw"]),
                "after": token_display(new_tokens[k]["raw"]),
            }
            changes.append(entry)

    return changes


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 diff_tokens.py <old_tokens> <new_tokens> [--notes 'description']")
        sys.exit(1)

    old_path = sys.argv[1]
    new_path = sys.argv[2]

    # Parse optional --notes flag
    notes = None
    if "--notes" in sys.argv:
        idx = sys.argv.index("--notes")
        if idx + 1 < len(sys.argv):
            notes = sys.argv[idx + 1]

    with open(old_path) as f:
        old_data = json.load(f)
    with open(new_path) as f:
        new_data = json.load(f)

    changes = diff(old_data, new_data)

    added = len([c for c in changes if c["type"] == "added"])
    changed = len([c for c in changes if c["type"] == "changed"])
    removed = len([c for c in changes if c["type"] == "removed"])

    print(f"Added: {added}, Changed: {changed}, Removed: {removed}")

    if not changes:
        print("No changes detected — skipping changelog entry.")
        return

    now = datetime.now(timezone.utc).isoformat()
    entry = {
        "date": now,
        "changes": changes,
        "summary": {"added": added, "changed": changed, "removed": removed},
        "notes": notes or f"Sync: +{added} added, ~{changed} changed, -{removed} removed.",
    }

    changelog = new_data.get("changelog", [])
    changelog.append(entry)
    new_data["changelog"] = changelog

    with open(new_path, "w") as f:
        json.dump(new_data, f, indent=2)

    print(f"Appended changelog entry #{len(changelog)} to {new_path}")


if __name__ == "__main__":
    main()
