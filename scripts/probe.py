#!/usr/bin/env python3
"""Probe provider APIs for model changes and auto-fill metadata.

Fetches model lists from providers that expose a /v1/models (or similar)
endpoint, compares with the local provider JSONs, and reports:
  - New models not in the local registry
  - Models removed from the API (still local, may need pruning)
  - Models missing attachment info (auto-filled from OpenRouter or rules)
  - Context window / max output / thinking when OpenRouter provides them
  - Models that need manual review (no rule, no OpenRouter data)

Usage:
  python scripts/probe.py                    # probe + report, no changes
  python scripts/probe.py --apply            # apply auto-fills
  python scripts/probe.py --provider openai  # probe a single provider
  python scripts/probe.py --report-only      # just generate the report

Pure Python — no external dependencies required.

Writes modern attachments objects (not legacy supports_* fields).
Never invents context_window_tokens without an API/OpenRouter value.
"""

from __future__ import annotations

import fnmatch
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROVIDERS_DIR = ROOT / "providers"
RULES_PATH = ROOT / "scripts" / "model_rules.json"
REPORT_PATH = ROOT / "probe_report.md"
MODELS_DIR = ROOT / "models"
BASES_DIR = ROOT / "bases"

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
OPENROUTER_SOURCE_URL = "https://openrouter.ai/api/v1/models"

# Providers with a /v1/models endpoint (OpenAI-compatible).
# Maps provider id -> endpoint URL (None = local-only, skip in CI).
PROVIDER_ENDPOINTS = {
    "openai": "https://api.openai.com/v1/models",
    "deepseek": "https://api.deepseek.com/models",
    "groq": "https://api.groq.com/openai/v1/models",
    "mistral": "https://api.mistral.ai/v1/models",
    "moonshot": "https://api.moonshot.cn/v1/models",
    "nvidia": "https://integrate.api.nvidia.com/v1/models",
    "openrouter": "https://openrouter.ai/api/v1/models",
    "ollama": "http://localhost:11434/v1/models",
    "lmstudio": "http://localhost:1234/v1/models",
    "llamacpp": "http://localhost:8080/v1/models",
}

# Providers that need API keys (read from env or GitHub Secrets).
API_KEY_ENV = {
    "openai": "OPENAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "groq": "GROQ_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "moonshot": "MOONSHOT_API_KEY",
    "nvidia": "NVIDIA_API_KEY",
}

LEGACY_ATTACHMENT_KEYS = (
    "supports_attachments",
    "supports_images",
    "supports_audio",
    "supports_video",
    "supports_documents",
)

MODALITY_MAP = {
    "supports_images": "images",
    "supports_audio": "audio",
    "supports_video": "video",
    "supports_documents": "documents",
}


class ProbeResult:
    def __init__(self):
        self.updated = []            # (provider, model, fields_filled)
        self.new_models = []         # (provider, model_name)
        self.removed = []            # (provider, model_name)
        self.needs_review = []       # (provider, model_name, reason)
        self.errors = []             # (provider, error)
        self.unprobed_review = []    # (provider, model_name, reason)
        self.default_ctx = []        # (provider, model_name, ctx)
        self.needs_pricing = []      # (provider, model_name, reason)
        self.ctx_filled = []         # (provider, model_name, ctx)
        self.max_out_filled = []     # (provider, model_name, max_out)


def today_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def load_catalog() -> dict[str, dict]:
    catalog = {}
    if not MODELS_DIR.is_dir():
        return catalog
    for path in MODELS_DIR.glob("*.json"):
        data = json.loads(path.read_text())
        if isinstance(data, dict) and data.get("id"):
            catalog[data["id"]] = data
    return catalog


def save_canonical(model_id: str, data: dict) -> None:
    MODELS_DIR.mkdir(exist_ok=True)
    path = MODELS_DIR / f"{model_id.replace('/', '__')}.json"
    path.write_text(json.dumps(data, indent=2) + "\n")


def resolve_entry_for_read(entry: dict, catalog: dict) -> dict:
    """Return a view of the model with name + merged fields for probing logic."""
    if "ref" in entry and entry["ref"] in catalog:
        base = dict(catalog[entry["ref"]])
        # drop catalog-only
        for k in ("family", "vendor", "description", "aliases", "id"):
            base.pop(k, None)
        merged = {**base, **{k: v for k, v in entry.items() if k not in ("ref",)}}
        merged["name"] = entry.get("api_name") or entry.get("name") or entry["ref"]
        merged["ref"] = entry["ref"]
        return merged
    return entry


def apply_to_ref_entry(entry: dict, filled: dict, catalog: dict) -> bool:
    """Apply filled fields onto a ref-style provider entry (overrides only).

    Intrinsic fields that match catalog are not duplicated.
    Pricing always goes on the provider entry.
    Returns True if entry changed.
    """
    changed = False
    ref = entry.get("ref")
    canon = catalog.get(ref, {}) if ref else {}

    if "attachments" in filled and isinstance(filled["attachments"], dict):
        # Prefer writing to canonical if provider has no override and canon lacks it
        if not entry.get("attachments") and not canon.get("attachments"):
            if ref and ref in catalog:
                catalog[ref].setdefault("attachments", {})
                for k, v in filled["attachments"].items():
                    catalog[ref]["attachments"].setdefault(k, v)
                # mark catalog dirty via special key
                catalog[ref]["_dirty"] = True
                changed = True
        elif not entry.get("attachments"):
            # only override if different from canon
            if filled["attachments"] != canon.get("attachments"):
                entry["attachments"] = filled["attachments"]
                changed = True

    if filled.get("pricing") and not entry.get("pricing"):
        # pricing value may be True flag from older path; skip if not dict
        pass

    return changed


def load_rules() -> dict:
    if not RULES_PATH.exists():
        return {}
    with open(RULES_PATH) as f:
        data = json.load(f)
    return data.get("rules", {})


def match_rule(model_name: str, rules: dict) -> dict | None:
    """Match a model name against rules (exact first, then glob)."""
    if model_name in rules:
        return rules[model_name]
    for pattern, fields in rules.items():
        if "*" in pattern and fnmatch.fnmatch(model_name, pattern):
            return fields
    return None


def fetch_json(url: str, api_key: str | None = None, timeout: int = 10) -> dict | None:
    """Fetch JSON from a URL with optional Bearer auth."""
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "navi-registry-probe/1.1")
    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError) as e:
        print(f"  FETCH FAIL {url}: {e}", file=sys.stderr)
        return None


def parse_models_response(data: dict, provider_id: str) -> list[str]:
    """Extract model names from a /v1/models response."""
    models = data.get("data", data.get("models", []))
    if not isinstance(models, list):
        return []

    names = []
    for m in models:
        if isinstance(m, dict):
            mid = m.get("id", m.get("name", ""))
            if "/" in mid and provider_id == "openrouter":
                names.append(mid)
            elif "/" in mid:
                names.append(mid.split("/")[-1])
            else:
                names.append(mid)
        elif isinstance(m, str):
            names.append(m)
    return names


def normalize_rule_fields(fields: dict | None) -> dict:
    """Convert legacy rule shape to modern attachments + other fields."""
    if not fields:
        return {}
    out: dict = {}
    attachments: dict = {}

    # Already modern?
    if isinstance(fields.get("attachments"), dict):
        attachments.update(fields["attachments"])

    for legacy, modern in MODALITY_MAP.items():
        if legacy in fields and isinstance(fields[legacy], bool):
            attachments.setdefault(modern, fields[legacy])
        if modern in fields and isinstance(fields[modern], bool):
            attachments.setdefault(modern, fields[modern])

    if attachments:
        out["attachments"] = attachments

    for key in (
        "pricing",
        "context_window_tokens",
        "max_output_tokens",
        "supports_thinking",
    ):
        if key in fields and fields[key] is not None:
            out[key] = fields[key]

    return out


def fetch_openrouter_capabilities() -> dict:
    """Fetch OpenRouter models and extract capabilities, pricing, context.

    Returns dict mapping model_id (and bare name) -> fields.
    """
    data = fetch_json(OPENROUTER_MODELS_URL)
    if not data:
        return {}

    caps = {}
    for m in data.get("data", []):
        mid = m.get("id", "")
        arch = m.get("architecture", {}) or {}
        inputs = arch.get("input_modalities", []) or []
        fields: dict = {}

        attachments = {}
        if "image" in inputs:
            attachments["images"] = True
        if "audio" in inputs:
            attachments["audio"] = True
        if "video" in inputs:
            attachments["video"] = True
        if "file" in inputs or "document" in inputs:
            attachments["documents"] = True
        if attachments:
            fields["attachments"] = attachments

        # Context window from OpenRouter (authoritative for their catalog).
        ctx = m.get("context_length")
        if isinstance(ctx, int) and ctx > 0:
            fields["context_window_tokens"] = ctx
        elif isinstance(ctx, float) and ctx > 0:
            fields["context_window_tokens"] = int(ctx)

        # Max output if present (field name varies).
        top = m.get("top_provider") or {}
        max_out = top.get("max_completion_tokens") or m.get("max_completion_tokens")
        if isinstance(max_out, int) and max_out > 0:
            fields["max_output_tokens"] = max_out

        # Thinking / reasoning hints.
        supported = m.get("supported_parameters") or []
        if isinstance(supported, list) and (
            "reasoning" in supported
            or "include_reasoning" in supported
            or m.get("reasoning") is not None
        ):
            fields["supports_thinking"] = True

        # Pricing: OpenRouter is per-token; convert to per-1M.
        pricing = m.get("pricing", {}) or {}
        prompt_price = pricing.get("prompt")
        completion_price = pricing.get("completion")
        if prompt_price is not None and completion_price is not None:
            try:
                p = float(prompt_price)
                c = float(completion_price)
                if p >= 0 and c >= 0 and (p > 0 or c > 0):
                    price_obj = {
                        "input_per_1m": round(p * 1_000_000, 6),
                        "output_per_1m": round(c * 1_000_000, 6),
                        "currency": "USD",
                    }
                    cached = pricing.get("input_cache_read")
                    if cached is not None:
                        try:
                            price_obj["cached_input_per_1m"] = round(
                                float(cached) * 1_000_000, 6
                            )
                        except ValueError:
                            pass
                    fields["pricing"] = price_obj
            except ValueError:
                pass

        if fields:
            fields["_source"] = {
                "url": f"https://openrouter.ai/api/v1/models/{mid}"
                if mid
                else OPENROUTER_SOURCE_URL,
                "verified_at": today_iso(),
                "note": "auto-filled by probe from OpenRouter /api/v1/models",
            }
            caps[mid] = fields
            if "/" in mid:
                bare = mid.split("/", 1)[1]
                # Prefer longer/more specific keys; only set bare if missing.
                caps.setdefault(bare, fields)
    return caps


def load_provider_json(provider_id: str) -> dict | None:
    path = PROVIDERS_DIR / f"{provider_id}.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def save_provider_json(provider_id: str, data: dict) -> None:
    path = PROVIDERS_DIR / f"{provider_id}.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def has_attachment_info(model: dict, provider_defaults: dict | None = None) -> bool:
    if isinstance(model.get("attachments"), dict) and model["attachments"]:
        return True
    if any(k in model for k in LEGACY_ATTACHMENT_KEYS):
        return True
    defaults = (provider_defaults or {}).get("attachments")
    return isinstance(defaults, dict) and any(
        isinstance(defaults.get(k), bool)
        for k in ("images", "audio", "video", "documents")
    )


def has_pricing_info(model: dict) -> bool:
    return "pricing" in model and isinstance(model["pricing"], dict) and model["pricing"]


def set_source(model: dict, field: str, source: dict | None) -> None:
    if not source:
        return
    sources = model.setdefault("sources", {})
    if field not in sources:
        sources[field] = {
            k: source[k]
            for k in ("url", "verified_at", "note")
            if k in source
        }


def apply_fields_to_model(model: dict, fields: dict, filled: dict) -> bool:
    """Apply modern fields to a model. Returns True if changed.

    filled is updated with a summary of what was applied.
    """
    changed = False
    source = fields.get("_source")

    # Attachments (modern only)
    att = fields.get("attachments")
    if isinstance(att, dict) and att:
        current = dict(model.get("attachments") or {})
        before = dict(current)
        for k, v in att.items():
            if k not in current and isinstance(v, bool):
                current[k] = v
        if current != before:
            model["attachments"] = current
            filled["attachments"] = current
            set_source(model, "attachments", source)
            changed = True

    # Pricing
    pricing = fields.get("pricing")
    if pricing and not has_pricing_info(model):
        model["pricing"] = pricing
        filled["pricing"] = True
        set_source(model, "pricing", source)
        changed = True

    # Context window — only fill if missing (never overwrite, never invent)
    ctx = fields.get("context_window_tokens")
    if isinstance(ctx, int) and ctx > 0 and "context_window_tokens" not in model:
        model["context_window_tokens"] = ctx
        filled["context_window_tokens"] = ctx
        set_source(model, "context_window_tokens", source)
        changed = True

    # Max output
    max_out = fields.get("max_output_tokens")
    if isinstance(max_out, int) and max_out > 0 and "max_output_tokens" not in model:
        model["max_output_tokens"] = max_out
        filled["max_output_tokens"] = max_out
        set_source(model, "max_output_tokens", source)
        changed = True

    # Thinking
    if (
        "supports_thinking" in fields
        and isinstance(fields["supports_thinking"], bool)
        and "supports_thinking" not in model
    ):
        model["supports_thinking"] = fields["supports_thinking"]
        filled["supports_thinking"] = fields["supports_thinking"]
        set_source(model, "supports_thinking", source)
        changed = True

    # Drop legacy attachment keys if modern attachments present
    if isinstance(model.get("attachments"), dict) and model["attachments"]:
        for k in LEGACY_ATTACHMENT_KEYS:
            if k in model:
                del model[k]
                changed = True

    return changed


def resolve_fields(provider_id: str, name: str, rules: dict, openrouter_caps: dict) -> dict:
    or_key = f"{provider_id}/{name}"
    fields = openrouter_caps.get(or_key) or openrouter_caps.get(name)
    if fields:
        return dict(fields)
    rule = match_rule(name, rules)
    if rule:
        normalized = normalize_rule_fields(rule)
        if normalized:
            normalized["_source"] = {
                "url": "scripts/model_rules.json",
                "verified_at": today_iso(),
                "note": f"matched model_rules entry for {name}",
            }
        return normalized
    return {}


def enrich_models(
    provider_id: str,
    data: dict,
    rules: dict,
    openrouter_caps: dict,
    result: ProbeResult,
    review_list: list,
    catalog: dict | None = None,
) -> bool:
    """Enrich models for a provider. Returns True if any model changed.

    Supports both legacy inline models and {ref,...} entries. For refs:
    - pricing overrides land on the provider entry
    - missing attachments may update the canonical model when absent
    - context is only filled when missing (never invent)
    """
    changed = False
    defaults = data.get("defaults") or {}
    catalog = catalog if catalog is not None else load_catalog()

    for idx, entry in enumerate(data.get("models", [])):
        view = resolve_entry_for_read(entry, catalog)
        name = view.get("name") or entry.get("ref") or "?"
        fields = resolve_fields(provider_id, name, rules, openrouter_caps)
        # also try bare ref
        if not fields and entry.get("ref"):
            fields = resolve_fields(provider_id, entry["ref"], rules, openrouter_caps)
        filled: dict = {}

        ctx = view.get("context_window_tokens")
        if ctx == 200000:
            sources = view.get("sources") or {}
            if "context_window_tokens" not in sources:
                result.default_ctx.append((provider_id, name, ctx))

        needs_attach = not has_attachment_info(view, defaults)
        is_ref = "ref" in entry

        if fields:
            if is_ref:
                # Apply pricing onto provider entry
                pricing = fields.get("pricing")
                if pricing and not entry.get("pricing"):
                    entry["pricing"] = pricing
                    filled["pricing"] = True
                    changed = True
                # Attachments: update canonical if missing
                att = fields.get("attachments")
                if isinstance(att, dict) and att:
                    ref = entry["ref"]
                    if ref in catalog and not catalog[ref].get("attachments"):
                        catalog[ref]["attachments"] = att
                        catalog[ref]["_dirty"] = True
                        filled["attachments"] = att
                        changed = True
                    elif not entry.get("attachments") and att != (catalog.get(ref) or {}).get("attachments"):
                        # only set override if differs and still missing on view
                        if not has_attachment_info(view, defaults):
                            entry["attachments"] = att
                            filled["attachments"] = att
                            changed = True
                # Context on canonical only if missing
                ctx_new = fields.get("context_window_tokens")
                ref = entry.get("ref")
                if (
                    isinstance(ctx_new, int)
                    and ctx_new > 0
                    and ref in catalog
                    and "context_window_tokens" not in catalog[ref]
                ):
                    catalog[ref]["context_window_tokens"] = ctx_new
                    catalog[ref]["_dirty"] = True
                    filled["context_window_tokens"] = ctx_new
                    changed = True
                # supports_thinking on canonical if missing
                if (
                    "supports_thinking" in fields
                    and ref in catalog
                    and "supports_thinking" not in catalog[ref]
                ):
                    catalog[ref]["supports_thinking"] = fields["supports_thinking"]
                    catalog[ref]["_dirty"] = True
                    filled["supports_thinking"] = fields["supports_thinking"]
                    changed = True
                if filled:
                    result.updated.append((provider_id, name, filled))
                    if "context_window_tokens" in filled:
                        result.ctx_filled.append(
                            (provider_id, name, filled["context_window_tokens"])
                        )
            else:
                if apply_fields_to_model(entry, fields, filled):
                    result.updated.append((provider_id, name, filled))
                    changed = True
                    if "context_window_tokens" in filled:
                        result.ctx_filled.append(
                            (provider_id, name, filled["context_window_tokens"])
                        )
                    if "max_output_tokens" in filled:
                        result.max_out_filled.append(
                            (provider_id, name, filled["max_output_tokens"])
                        )

        # Re-check using updated view
        view2 = resolve_entry_for_read(entry, catalog)
        if not has_attachment_info(view2, defaults):
            if needs_attach:
                review_list.append(
                    (provider_id, name, "no attachment rule or OpenRouter data")
                )

        if not has_pricing_info(entry) and not has_pricing_info(view2):
            if not (fields and "pricing" in fields):
                result.needs_pricing.append(
                    (provider_id, name, "no pricing data from OpenRouter or rules")
                )

    # Persist dirty canonicals
    for mid, cdata in list(catalog.items()):
        if cdata.pop("_dirty", False):
            save_canonical(mid, cdata)
            changed = True

    return changed


def probe_provider(
    provider_id: str,
    rules: dict,
    openrouter_caps: dict,
    result: ProbeResult,
    apply: bool,
) -> None:
    """Probe a single provider and update the result."""
    endpoint = PROVIDER_ENDPOINTS.get(provider_id)
    if not endpoint:
        return

    data = load_provider_json(provider_id)
    if not data:
        result.errors.append((provider_id, "provider JSON not found"))
        return

    catalog = load_catalog()
    local_models = set()
    for m in data.get("models", []):
        if "ref" in m:
            local_models.add(m.get("api_name") or m.get("name") or m["ref"])
        elif "name" in m:
            local_models.add(m["name"])
    api_key_env = API_KEY_ENV.get(provider_id)
    api_key = os.environ.get(api_key_env) if api_key_env else None

    is_local = endpoint.startswith("http://localhost")
    if not is_local and api_key_env and not api_key:
        result.errors.append(
            (provider_id, f"no API key in env ${api_key_env}, skipping remote probe")
        )
        # Still enrich from rules/OpenRouter without API list.
        catalog = load_catalog()
        if enrich_models(
            provider_id, data, rules, openrouter_caps, result, result.needs_review, catalog
        ):
            if apply:
                save_provider_json(provider_id, data)
        return

    if is_local:
        try:
            urllib.request.urlopen(endpoint, timeout=2)
        except Exception:
            result.errors.append((provider_id, "local server not running, skipping"))
            return

    resp = fetch_json(endpoint, api_key)
    if not resp:
        result.errors.append((provider_id, "failed to fetch /models"))
        return

    api_model_names = set(parse_models_response(resp, provider_id))
    if provider_id != "openrouter":
        api_model_names = {
            n.split("/")[-1] if "/" in n else n for n in api_model_names
        }

    for name in sorted(api_model_names - local_models):
        result.new_models.append((provider_id, name))
    for name in sorted(local_models - api_model_names):
        # Mark removed as lifecycle hint only in report; do not rewrite status unless apply+flag.
        result.removed.append((provider_id, name))

    changed = enrich_models(
        provider_id, data, rules, openrouter_caps, result, result.needs_review, catalog
    )

    # Optionally tag removed models with status=removed when applying.
    if apply:
        for model in data.get("models", []):
            mname = model.get("api_name") or model.get("name") or model.get("ref")
            if mname in (local_models - api_model_names):
                if model.get("status") != "removed":
                    model["status"] = "removed"
                    changed = True

    if changed and apply:
        save_provider_json(provider_id, data)


def probe_all(
    rules: dict,
    openrouter_caps: dict,
    result: ProbeResult,
    apply: bool,
    only_provider: str | None,
) -> None:
    providers = sorted(PROVIDER_ENDPOINTS.keys())
    if only_provider:
        if only_provider not in providers and only_provider not in {
            p.stem for p in PROVIDERS_DIR.glob("*.json")
        }:
            print(f"ERROR: unknown provider '{only_provider}'", file=sys.stderr)
            print(f"Available: {', '.join(providers)}", file=sys.stderr)
            sys.exit(1)
        providers = [only_provider] if only_provider in PROVIDER_ENDPOINTS else []

    for pid in providers:
        print(f"  probing {pid}...")
        probe_provider(pid, rules, openrouter_caps, result, apply)

    if not only_provider:
        scan_unprobed_providers(rules, openrouter_caps, result, apply)
    elif only_provider and only_provider not in PROVIDER_ENDPOINTS:
        # Single unprobed provider
        scan_one_unprobed(only_provider, rules, openrouter_caps, result, apply)


def scan_one_unprobed(
    pid: str,
    rules: dict,
    openrouter_caps: dict,
    result: ProbeResult,
    apply: bool,
) -> None:
    data = load_provider_json(pid)
    if not data:
        result.errors.append((pid, "provider JSON not found"))
        return
    # Skip thin extends-only files without local models list (enriched via base at validate).
    if not data.get("models") and data.get("extends"):
        print(f"  skipping {pid} (extends base; edit bases/{data['extends']}.json)")
        return
    print(f"  scanning {pid} (no API endpoint)...")
    changed = enrich_models(
        pid, data, rules, openrouter_caps, result, result.unprobed_review, load_catalog()
    )
    if changed and apply:
        save_provider_json(pid, data)


def scan_unprobed_providers(
    rules: dict,
    openrouter_caps: dict,
    result: ProbeResult,
    apply: bool,
) -> None:
    """Scan providers without API endpoints — auto-fill via rules + OpenRouter.

    Also scans bases/*.json so shared catalogs (used via extends) get enriched.
    """
    all_providers = sorted(p.stem for p in PROVIDERS_DIR.glob("*.json"))
    unprobed = [p for p in all_providers if p not in PROVIDER_ENDPOINTS]

    for pid in unprobed:
        scan_one_unprobed(pid, rules, openrouter_caps, result, apply)

    bases_dir = ROOT / "bases"
    if bases_dir.is_dir():
        for base_path in sorted(bases_dir.glob("*.json")):
            print(f"  scanning base {base_path.stem}...")
            data = json.loads(base_path.read_text())
            if not data.get("models"):
                continue
            changed = enrich_models(
                base_path.stem, data, rules, openrouter_caps, result, result.unprobed_review, load_catalog()
            )
            if changed and apply:
                base_path.write_text(json.dumps(data, indent=2) + "\n")


def format_filled(fields: dict) -> str:
    parts = []
    if "attachments" in fields:
        att = fields["attachments"]
        if isinstance(att, dict):
            parts.extend(k for k, v in att.items() if v)
        else:
            parts.append("attachments")
    for key in (
        "pricing",
        "context_window_tokens",
        "max_output_tokens",
        "supports_thinking",
    ):
        if key in fields:
            parts.append(key.replace("supports_", "").replace("_tokens", ""))
    return ", ".join(parts) if parts else str(fields)


def generate_report(result: ProbeResult) -> str:
    lines = ["# Registry Probe Report", ""]
    lines.append("## Summary")
    lines.append(f"- Auto-filled fields: **{len(result.updated)}**")
    lines.append(f"- Context windows filled: **{len(result.ctx_filled)}**")
    lines.append(f"- Max output filled: **{len(result.max_out_filled)}**")
    lines.append(f"- New models (not in registry): **{len(result.new_models)}**")
    lines.append(f"- Removed models (local only): **{len(result.removed)}**")
    lines.append(f"- Needs manual review (probed): **{len(result.needs_review)}**")
    lines.append(f"- Needs manual review (unprobed): **{len(result.unprobed_review)}**")
    lines.append(
        f"- Default context window (200k, likely unset): **{len(result.default_ctx)}**"
    )
    lines.append(f"- Needs pricing: **{len(result.needs_pricing)}**")
    lines.append(f"- Errors: **{len(result.errors)}**")
    lines.append("")

    if result.updated:
        lines.append("## Auto-filled Fields")
        lines.append("")
        lines.append("| Provider | Model | Fields |")
        lines.append("|---|---|---|")
        for pid, name, fields in sorted(result.updated):
            lines.append(f"| {pid} | {name} | {format_filled(fields)} |")
        lines.append("")

    if result.ctx_filled:
        lines.append("## Context Windows Filled")
        lines.append("")
        for pid, name, ctx in sorted(result.ctx_filled):
            lines.append(f"- `{pid}/{name}` → {ctx}")
        lines.append("")

    if result.new_models:
        lines.append("## New Models (not in local registry)")
        lines.append("")
        for pid, name in sorted(result.new_models):
            lines.append(f"- `{pid}/{name}`")
        lines.append("")

    if result.removed:
        lines.append("## Removed Models (local only, may need pruning)")
        lines.append("")
        lines.append(
            "When `--apply` is used, these models are tagged `status: removed`."
        )
        lines.append("")
        for pid, name in sorted(result.removed):
            lines.append(f"- `{pid}/{name}`")
        lines.append("")

    if result.needs_review:
        lines.append("## Needs Manual Review (probed providers, no attachment info)")
        lines.append("")
        for pid, name, reason in sorted(result.needs_review):
            lines.append(f"- `{pid}/{name}` — {reason}")
        lines.append("")

    if result.unprobed_review:
        lines.append("## Needs Manual Review (unprobed providers, no attachment info)")
        lines.append("")
        for pid, name, reason in sorted(result.unprobed_review):
            lines.append(f"- `{pid}/{name}` — {reason}")
        lines.append("")

    if result.default_ctx:
        lines.append("## Default Context Window (200k — likely unset)")
        lines.append("")
        for pid, name, ctx in sorted(result.default_ctx):
            lines.append(f"- `{pid}/{name}` — context_window_tokens={ctx}")
        lines.append("")

    if result.needs_pricing:
        lines.append("## Needs Pricing (no pricing data available)")
        lines.append("")
        for pid, name, reason in sorted(result.needs_pricing):
            lines.append(f"- `{pid}/{name}` — {reason}")
        lines.append("")

    if result.errors:
        lines.append("## Errors")
        lines.append("")
        for pid, err in sorted(result.errors):
            lines.append(f"- `{pid}`: {err}")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Probe provider APIs for model changes")
    parser.add_argument(
        "--apply", action="store_true", help="apply auto-fills to JSON files"
    )
    parser.add_argument(
        "--provider", type=str, default=None, help="probe only this provider"
    )
    parser.add_argument(
        "--report-only", action="store_true", help="only generate report, skip probing"
    )
    args = parser.parse_args()

    print("Loading attachment rules...")
    rules = load_rules()
    print(f"  {len(rules)} rules loaded")

    print("Fetching OpenRouter capabilities (no auth needed)...")
    openrouter_caps = fetch_openrouter_capabilities()
    print(f"  {len(openrouter_caps)} models with capability data")

    result = ProbeResult()

    if not args.report_only:
        probe_all(rules, openrouter_caps, result, args.apply, args.provider)

    report = generate_report(result)
    with open(REPORT_PATH, "w") as f:
        f.write(report)

    print(f"\nReport written to {REPORT_PATH.relative_to(ROOT)}")
    print("\n--- Summary ---")
    print(f"  Auto-filled:       {len(result.updated)}")
    print(f"  Ctx filled:        {len(result.ctx_filled)}")
    print(f"  New models:        {len(result.new_models)}")
    print(f"  Removed:           {len(result.removed)}")
    print(f"  Needs review (probed):   {len(result.needs_review)}")
    print(f"  Needs review (unprobed): {len(result.unprobed_review)}")
    print(f"  Default ctx (200k): {len(result.default_ctx)}")
    print(f"  Needs pricing:      {len(result.needs_pricing)}")
    print(f"  Errors:            {len(result.errors)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
