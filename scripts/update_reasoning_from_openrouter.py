#!/usr/bin/env python3
"""Update canonical model reasoning_levels/default_reasoning_effort from OpenRouter /models.

Usage:
  python scripts/update_reasoning_from_openrouter.py /path/to/openrouter_models.json [--dry-run]

Pure Python, no dependencies.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "models"

# Order matters: preferred match keys.
BUDGET_ORDER = ["low", "medium", "high", "xhigh", "max"]


def normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def bare_id(value: str) -> str:
    # strip leading ~, provider prefix, and :free/:whatever suffix
    v = value.lstrip("~")
    if "/" in v:
        v = v.split("/")[-1]
    return v.split(":")[0]


def normalize_effort(e: str | None) -> str | None:
    if not e:
        return None
    e = e.strip().lower()
    if e == "none":
        return "off"
    if e == "minimal":
        return "low"
    if e in ("low", "medium", "high", "xhigh", "max"):
        return e
    return None


def effort_sort_key(level: str) -> int:
    try:
        return BUDGET_ORDER.index(level)
    except ValueError:
        return 99


def build_lookup(openrouter_data: dict) -> dict[str, dict]:
    """Map bare id and normalized bare id to the richest (non-:free, non-~) entry."""
    by_bare: dict[str, dict] = {}
    by_norm: dict[str, dict] = {}

    for m in openrouter_data.get("data", []):
        mid = m.get("id", "")
        if not mid:
            continue
        # Prefer non-~ and non-:free entries by key overwrite
        base = bare_id(mid)
        if base not in by_bare or (not mid.startswith("~") and ":" not in mid):
            by_bare[base] = m
        n = normalize(base)
        if n not in by_norm or (not mid.startswith("~") and ":" not in mid):
            by_norm[n] = m

    return {"by_bare": by_bare, "by_norm": by_norm}


def find_match(model: dict, lookup: dict) -> dict | None:
    by_bare = lookup["by_bare"]
    by_norm = lookup["by_norm"]

    candidates = [model.get("id", "")] + list(model.get("aliases", []))
    for c in candidates:
        b = bare_id(c)
        if b in by_bare:
            return by_bare[b]
        n = normalize(b)
        if n in by_norm:
            return by_norm[n]

    # For aggregator vendors without aliases, derive a family prefix and try fuzzy
    vendor = model.get("vendor", "")
    if vendor == "aggregator":
        family = model.get("family", "")
        # common OpenRouter vendor slugs by family
        family_to_vendor = {
            "claude": "anthropic",
            "gpt": "openai",
            "gemini": "google",
            "grok": "x-ai",
            "kimi": "moonshotai",
            "deepseek": "deepseek",
            "minimax": "minimax",
            "glm": "z-ai",
            "qwen": "qwen",
            "step": "stepfun",
            "nemotron": "nvidia",
            "muse": "meta",
            "mimo": "xiaomi",
        }
        if family in family_to_vendor:
            slug = f"{family_to_vendor[family]}/{model['id']}"
            b = bare_id(slug)
            if b in by_bare:
                return by_bare[b]
            n = normalize(b)
            if n in by_norm:
                return by_norm[n]

    return None


def compute_reasoning(or_model: dict) -> dict | None:
    """Return desired reasoning fields or None if no OpenRouter reasoning data."""
    reasoning = or_model.get("reasoning")
    if not reasoning:
        return None

    supported = reasoning.get("supported_efforts") or []
    if not isinstance(supported, list):
        supported = []

    mandatory = reasoning.get("mandatory", False)
    default_enabled = reasoning.get("default_enabled", False)
    default_effort_raw = reasoning.get("default_effort")

    normalized_levels: list[str] = []
    for e in supported:
        ne = normalize_effort(e)
        if ne and ne not in normalized_levels:
            normalized_levels.append(ne)

    # Determine if off/no-thinking is selectable.
    # OpenRouter supported_efforts may include "none"; if not, off is still allowed
    # when reasoning is not mandatory.
    off_allowed = ("none" in (str(x).lower() for x in supported)) or not mandatory

    # If only off is present, the model does not actually support thinking.
    real_levels = [l for l in normalized_levels if l != "off"]
    if not real_levels:
        if supported:
            return {"supports_thinking": False}
        # reasoning object present but no supported_efforts -> binary, no levels
        return {"supports_thinking": True}

    levels = [l for l in normalized_levels if l != "off"]
    if off_allowed and "off" not in levels:
        levels.insert(0, "off")

    # Sort from low to high for consistent output (off already first if present)
    if "off" in levels:
        rest = sorted([l for l in levels if l != "off"], key=effort_sort_key)
        levels = ["off"] + rest
    else:
        levels = sorted(levels, key=effort_sort_key)

    # Default effort
    default = normalize_effort(default_effort_raw)
    if default == "off" and not off_allowed:
        default = None

    if default is None:
        if default_enabled:
            # Pick the lowest non-off level
            default = next((l for l in levels if l != "off"), levels[0])
        else:
            default = "off" if off_allowed else levels[0]

    if default not in levels:
        # Fall back to lowest non-off, or first level
        default = next((l for l in levels if l != "off"), levels[0])

    return {
        "supports_thinking": True,
        "reasoning_levels": levels,
        "default_reasoning_effort": default,
    }


def apply_to_model(model: dict, desired: dict, source_url: str, today: str) -> bool:
    """Apply desired reasoning fields to a canonical model. Returns True if changed."""
    changed = False

    if desired.get("supports_thinking") is False:
        if model.get("supports_thinking") is not False:
            model["supports_thinking"] = False
            changed = True
        for k in ("reasoning_levels", "default_reasoning_effort"):
            if k in model:
                del model[k]
                changed = True
        return changed

    if desired.get("supports_thinking") is True:
        if model.get("supports_thinking") is not True:
            model["supports_thinking"] = True
            changed = True

        levels = desired.get("reasoning_levels")
        if levels is None:
            # OpenRouter does not list supported efforts; remove any stale levels.
            for k in ("reasoning_levels", "default_reasoning_effort"):
                if k in model:
                    del model[k]
                    changed = True
        else:
            if model.get("reasoning_levels") != levels:
                model["reasoning_levels"] = levels
                changed = True

            default = desired.get("default_reasoning_effort")
            if default is not None:
                if model.get("default_reasoning_effort") != default:
                    model["default_reasoning_effort"] = default
                    changed = True

        if changed:
            sources = model.setdefault("sources", {})
            note = "auto-filled from OpenRouter /api/v1/models"
            for field in ("reasoning_levels", "default_reasoning_effort"):
                if field not in sources:
                    sources[field] = {
                        "url": source_url,
                        "verified_at": today,
                        "note": note,
                    }

    return changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("openrouter_json", help="Path to OpenRouter /api/v1/models JSON")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    or_path = Path(args.openrouter_json)
    with open(or_path) as f:
        or_data = json.load(f)

    lookup = build_lookup(or_data)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    updated = 0
    unchanged = 0
    unmatched = 0
    for path in sorted(MODELS_DIR.glob("*.json")):
        with open(path) as f:
            model = json.load(f)

        match = find_match(model, lookup)
        if not match:
            unmatched += 1
            continue

        source_url = f"https://openrouter.ai/api/v1/models/{match['id']}"
        desired = compute_reasoning(match)
        if desired is None:
            unmatched += 1
            continue

        if apply_to_model(model, desired, source_url, today):
            updated += 1
            if args.dry_run:
                print(f"[DRY-RUN] would update {path.name}: {desired}")
            else:
                with open(path, "w") as f:
                    json.dump(model, f, indent=2)
                    f.write("\n")
                print(f"updated {path.name}: {desired}")
        else:
            unchanged += 1

    print(f"\nSummary: updated={updated}, unchanged={unchanged}, unmatched={unmatched}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
