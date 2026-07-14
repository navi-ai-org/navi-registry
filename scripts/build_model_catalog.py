#!/usr/bin/env python3
"""Build models/ catalog and rewrite providers to use {ref, overrides}.

Strategy:
1. Collect all model entries across providers (after extends flatten).
2. Group by bare model name (strip provider prefix after '/').
3. Pick canonical source by vendor priority (official providers first).
4. Write models/<id>.json with intrinsic fields (no pricing).
5. Rewrite each provider models[] entry to {ref, api_name?, overrides}.

Usage:
  python scripts/build_model_catalog.py           # dry-run summary
  python scripts/build_model_catalog.py --apply   # write models/ + rewrite providers
  python scripts/build_model_catalog.py --apply --providers-only  # only rewrite providers (catalog exists)

Never invents context windows. Pricing stays on the provider entry.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.validate import (  # noqa: E402
    MODELS_DIR,
    PROVIDERS_DIR,
    BASES_DIR,
    deep_merge,
    load_json,
    model_filename_for_id,
    resolve_extends,
)

# Official / primary vendors first — their metadata wins for the canonical entry.
VENDOR_PRIORITY = [
    "openai",
    "anthropic",
    "google-gemini",
    "deepseek",
    "mistral",
    "moonshot",
    "xai",
    "groq",
    "minimax",
    "nvidia",
    "xiaomi",
    "zai",
    "stepfun",
    "ollama",
    "lmstudio",
    "llamacpp",
    # secondary / plans
    "zai-coding",
    "mimo-anthropic-ams",
    "mimo-anthropic-cn",
    "mimo-anthropic-sgp",
    "github-copilot",
    # aggregators last
    "charm-hyper",
    "commandcode",
    "gitlawb",
    "opencode",
    "opencode-go",
    "openrouter",
]

# Map provider id → vendor tag for the canonical model.
PROVIDER_VENDOR = {
    "openai": "openai",
    "anthropic": "anthropic",
    "google-gemini": "google",
    "deepseek": "deepseek",
    "mistral": "mistral",
    "moonshot": "moonshot",
    "xai": "xai",
    "groq": "groq",
    "minimax": "minimax",
    "nvidia": "nvidia",
    "xiaomi": "xiaomi",
    "zai": "zhipu",
    "zai-coding": "zhipu",
    "stepfun": "stepfun",
    "mimo-anthropic-ams": "xiaomi",
    "mimo-anthropic-cn": "xiaomi",
    "mimo-anthropic-sgp": "xiaomi",
    "ollama": "local",
    "lmstudio": "local",
    "llamacpp": "local",
    "github-copilot": "github",
    "charm-hyper": "aggregator",
    "commandcode": "aggregator",
    "gitlawb": "aggregator",
    "opencode": "aggregator",
    "opencode-go": "aggregator",
    "openrouter": "aggregator",
}

INTRINSIC_KEYS = [
    "label",
    "context_window_tokens",
    "max_output_tokens",
    "recommended_temperature",
    "supports_thinking",
    "attachments",
    "reasoning_levels",
    "default_reasoning_effort",
    "capabilities",
    "status",
    "sources",
]

# Provider override keys compared against canonical (pricing always stays on provider).
OVERRIDE_COMPARE_KEYS = [
    "context_window_tokens",
    "max_output_tokens",
    "recommended_temperature",
    "supports_thinking",
    "attachments",
    "status",
    "label",
    "reasoning_levels",
    "default_reasoning_effort",
    "capabilities",
]


def bare_name(name: str) -> str:
    return name.split("/")[-1] if "/" in name else name


def safe_model_id(name: str) -> str:
    """Canonical id = bare name; keep case as used by majority/vendor."""
    return bare_name(name)


def priority(pid: str) -> int:
    try:
        return VENDOR_PRIORITY.index(pid)
    except ValueError:
        return 999


def collect_entries() -> dict[str, list[tuple[str, str, dict]]]:
    """bare_id -> list of (provider_id, api_name, model_dict)"""
    by_bare: dict[str, list[tuple[str, str, dict]]] = defaultdict(list)

    # Include bases as sources of truth for shared catalogs
    for directory in (PROVIDERS_DIR, BASES_DIR):
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.json")):
            raw = load_json(path)
            # For bases, no extends usually; for providers resolve
            try:
                data = resolve_extends(raw) if raw.get("extends") else raw
            except Exception:
                data = raw
            pid = data.get("id") or path.stem
            # Skip thin extends-only providers (models come from base)
            models = data.get("models") or []
            if not models:
                continue
            # If this is a base, tag as base-<id> only for provenance, still use id
            for m in models:
                if not isinstance(m, dict) or "name" not in m:
                    # already a ref? skip in collect from raw files pre-migration
                    if isinstance(m, dict) and "ref" in m:
                        continue
                    continue
                api_name = m["name"]
                bid = safe_model_id(api_name)
                by_bare[bid].append((pid, api_name, m))

    return by_bare


def pick_canonical(
    bare: str, entries: list[tuple[str, str, dict]]
) -> tuple[str, str, dict]:
    """Return (provider_id, api_name, model) for canonical source."""
    ranked = sorted(entries, key=lambda e: (priority(e[0]), e[1]))
    return ranked[0]


def build_canonical(bare: str, entries: list[tuple[str, str, dict]]) -> dict:
    src_pid, src_api, src_model = pick_canonical(bare, entries)
    canon: dict = {"id": bare}

    vendor = PROVIDER_VENDOR.get(src_pid)
    if vendor:
        canon["vendor"] = vendor

    # Family heuristic
    family = None
    low = bare.lower()
    for prefix in (
        "claude-",
        "gpt-",
        "o1",
        "o3",
        "o4",
        "gemini-",
        "glm-",
        "mimo-",
        "kimi-",
        "deepseek-",
        "grok-",
        "qwen",
        "llama-",
        "mistral",
        "codestral",
        "pixtral",
        "ministral",
        "nemotron",
        "abab",
        "step-",
    ):
        if low.startswith(prefix) or prefix.rstrip("-") in low[: len(prefix) + 2]:
            family = prefix.rstrip("-")
            break
    if family:
        canon["family"] = family

    for key in INTRINSIC_KEYS:
        if key in src_model and src_model[key] is not None:
            canon[key] = copy.deepcopy(src_model[key])

    # Aliases: all distinct api names + full names seen
    aliases = sorted({api for _, api, _ in entries if api != bare})
    if aliases:
        canon["aliases"] = aliases

    # Prefer largest verified context among primary vendors if src missing? NO — never invent.
    # But if source has lower priority weird value and a higher-priority vendor has different,
    # we already picked highest priority.

    # status default omit if active
    if canon.get("status") == "active":
        del canon["status"]

    return canon, src_pid


def values_equal(a, b) -> bool:
    return a == b


def build_provider_entry(
    api_name: str, model: dict, canon: dict
) -> dict:
    """Build {ref, api_name?, overrides, pricing?} for a provider row."""
    entry: dict = {"ref": canon["id"]}

    if api_name != canon["id"]:
        entry["api_name"] = api_name

    for key in OVERRIDE_COMPARE_KEYS:
        if key not in model:
            continue
        cval = canon.get(key)
        mval = model[key]
        if key == "status" and (mval or "active") == (cval or "active"):
            continue
        if not values_equal(mval, cval):
            entry[key] = copy.deepcopy(mval)

    # Pricing always provider-side if present
    if "pricing" in model and model["pricing"]:
        entry["pricing"] = copy.deepcopy(model["pricing"])

    # sources on provider only if override-specific (skip — keep on canonical)
    return entry


def rewrite_provider_file(
    path: Path,
    catalog: dict[str, dict],
    alias_to_id: dict[str, str],
) -> tuple[bool, int, int]:
    """Rewrite models in a provider/base file. Returns (changed, ref_count, inline_left)."""
    raw = load_json(path)
    if not isinstance(raw.get("models"), list) or not raw["models"]:
        return False, 0, 0

    new_models = []
    refs = 0
    inline = 0
    for m in raw["models"]:
        if not isinstance(m, dict):
            new_models.append(m)
            inline += 1
            continue
        if "ref" in m and "name" not in m:
            # already ref form
            new_models.append(m)
            refs += 1
            continue
        if "name" not in m:
            new_models.append(m)
            inline += 1
            continue

        api_name = m["name"]
        bare = safe_model_id(api_name)
        # Find catalog id
        cid = None
        if bare in catalog:
            cid = bare
        elif api_name in alias_to_id:
            cid = alias_to_id[api_name]
        elif bare in alias_to_id:
            cid = alias_to_id[bare]

        if not cid or cid not in catalog:
            # keep inline
            new_models.append(m)
            inline += 1
            continue

        entry = build_provider_entry(api_name, m, catalog[cid])
        new_models.append(entry)
        refs += 1

    if new_models == raw["models"]:
        return False, refs, inline

    raw["models"] = new_models
    with open(path, "w") as f:
        json.dump(raw, f, indent=2)
        f.write("\n")
    return True, refs, inline


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--providers-only",
        action="store_true",
        help="Do not rebuild models/; only rewrite providers using existing catalog",
    )
    args = parser.parse_args()

    by_bare = collect_entries()
    print(f"Collected {len(by_bare)} unique bare model ids from providers/bases")

    catalog: dict[str, dict] = {}
    provenance: dict[str, str] = {}

    if args.providers_only and MODELS_DIR.is_dir():
        for path in MODELS_DIR.glob("*.json"):
            data = load_json(path)
            catalog[data["id"]] = data
        print(f"Loaded existing catalog: {len(catalog)} models")
    else:
        for bare, entries in sorted(by_bare.items()):
            canon, src_pid = build_canonical(bare, entries)
            catalog[bare] = canon
            provenance[bare] = src_pid

        print(f"Built {len(catalog)} canonical models")
        # Show sample conflicts
        multi = {k: v for k, v in by_bare.items() if len({e[0] for e in v}) > 1}
        print(f"Models used by multiple providers: {len(multi)}")
        for bare in list(sorted(multi, key=lambda b: -len(multi[b])))[:10]:
            providers = sorted({e[0] for e in multi[bare]})
            print(f"  {bare}: from {provenance[bare]} also in {providers}")

        if args.apply:
            MODELS_DIR.mkdir(exist_ok=True)
            # Clear old catalog files? only overwrite known
            written = 0
            for mid, data in sorted(catalog.items()):
                path = MODELS_DIR / model_filename_for_id(mid)
                with open(path, "w") as f:
                    json.dump(data, f, indent=2)
                    f.write("\n")
                written += 1
            print(f"Wrote {written} files under models/")

    # Alias index
    alias_to_id: dict[str, str] = {}
    for mid, data in catalog.items():
        alias_to_id[mid] = mid
        for a in data.get("aliases") or []:
            alias_to_id[a] = mid
        alias_to_id.setdefault(bare_name(mid), mid)

    if not args.apply:
        print("\nDry-run only. Re-run with --apply to write files.")
        return 0

    # Rewrite providers + bases that have models
    changed_files = 0
    total_refs = 0
    total_inline = 0
    for directory in (PROVIDERS_DIR, BASES_DIR):
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.json")):
            changed, refs, inline = rewrite_provider_file(path, catalog, alias_to_id)
            total_refs += refs
            total_inline += inline
            if changed:
                changed_files += 1
                print(f"  rewrote {path.relative_to(ROOT)} (refs={refs}, inline_left={inline})")

    print(
        f"\nDone. files_changed={changed_files} ref_entries={total_refs} "
        f"inline_left={total_inline}"
    )
    print("Next: python scripts/validate.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
