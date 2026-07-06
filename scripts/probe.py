#!/usr/bin/env python3
"""Probe provider APIs for model changes and auto-fill attachment capabilities.

Fetches model lists from providers that expose a /v1/models (or similar)
endpoint, compares with the local provider JSONs, and reports:
  - New models not in the local registry
  - Models removed from the API (still local, may need pruning)
  - Models missing attachment info (auto-filled from OpenRouter or rules)
  - Models that need manual review (no rule, no OpenRouter data)

Usage:
  python scripts/probe.py                    # probe + report, no changes
  python scripts/probe.py --apply            # apply attachment auto-fills
  python scripts/probe.py --provider openai  # probe a single provider
  python scripts/probe.py --report-only      # just generate the report

Pure Python — no external dependencies required.
"""

import fnmatch
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROVIDERS_DIR = ROOT / "providers"
RULES_PATH = ROOT / "scripts" / "model_rules.json"
REPORT_PATH = ROOT / "probe_report.md"

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"

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

ATTACHMENT_FIELDS = [
    "supports_images",
    "supports_audio",
    "supports_video",
    "supports_documents",
]


class ProbeResult:
    def __init__(self):
        self.updated = []       # (provider, model, fields_filled)
        self.new_models = []    # (provider, model_name)
        self.removed = []       # (provider, model_name)
        self.needs_review = []  # (provider, model_name, reason)
        self.errors = []        # (provider, error)


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
    req.add_header("User-Agent", "navi-registry-probe/1.0")
    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError) as e:
        print(f"  FETCH FAIL {url}: {e}", file=sys.stderr)
        return None


def parse_models_response(data: dict, provider_id: str) -> list[str]:
    """Extract model names from a /v1/models response.

    Different providers have slightly different shapes.
    """
    models = data.get("data", data.get("models", []))
    if not isinstance(models, list):
        return []

    names = []
    for m in models:
        if isinstance(m, dict):
            # OpenRouter uses "id" like "openai/gpt-4o", strip provider prefix.
            mid = m.get("id", m.get("name", ""))
            if "/" in mid and provider_id == "openrouter":
                # Keep full id for OpenRouter (includes provider prefix).
                names.append(mid)
            elif "/" in mid:
                # Other providers may include a prefix; strip it.
                names.append(mid.split("/")[-1])
            else:
                names.append(mid)
        elif isinstance(m, str):
            names.append(m)
    return names


def fetch_openrouter_capabilities() -> dict:
    """Fetch OpenRouter /api/v1/models and extract attachment capabilities.

    Returns a dict mapping model_id -> {supports_images, supports_audio, ...}.
    """
    data = fetch_json(OPENROUTER_MODELS_URL)
    if not data:
        return {}

    caps = {}
    for m in data.get("data", []):
        mid = m.get("id", "")
        arch = m.get("architecture", {})
        inputs = arch.get("input_modalities", [])
        fields = {}
        if "image" in inputs:
            fields["supports_images"] = True
        if "audio" in inputs:
            fields["supports_audio"] = True
        if "video" in inputs:
            fields["supports_video"] = True
        if "file" in inputs or "document" in inputs:
            fields["supports_documents"] = True
        if fields:
            caps[mid] = fields
        # Also store by bare model name (without provider prefix).
        if "/" in mid:
            bare = mid.split("/", 1)[1]
            if fields:
                caps[bare] = fields
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


def has_attachment_info(model: dict) -> bool:
    return any(k in model for k in ATTACHMENT_FIELDS)


def apply_attachment_fields(model: dict, fields: dict) -> bool:
    """Apply attachment fields to a model if not already set. Returns True if changed."""
    changed = False
    for k, v in fields.items():
        if k not in model or model[k] is None:
            model[k] = v
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

    local_models = {m["name"] for m in data.get("models", [])}
    api_key_env = API_KEY_ENV.get(provider_id)
    api_key = os.environ.get(api_key_env) if api_key_env else None

    # Skip remote endpoints in CI if no API key and endpoint requires auth.
    is_local = endpoint.startswith("http://localhost")
    if not is_local and api_key_env and not api_key:
        result.errors.append(
            (provider_id, f"no API key in env ${api_key_env}, skipping remote probe")
        )
        return

    # For local endpoints, try but gracefully fail if not running.
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

    # For OpenRouter, model ids include the provider prefix (e.g. "openai/gpt-4o").
    # Filter to only models from this provider.
    if provider_id == "openrouter":
        api_model_names = {n for n in api_model_names}
    else:
        # Strip any provider prefix from API model names.
        api_model_names = {n.split("/")[-1] if "/" in n else n for n in api_model_names}

    # Detect new and removed models.
    for name in sorted(api_model_names - local_models):
        result.new_models.append((provider_id, name))
    for name in sorted(local_models - api_model_names):
        result.removed.append((provider_id, name))

    # Auto-fill attachment capabilities.
    changed = False
    for model in data.get("models", []):
        name = model["name"]

        # Skip if already has attachment info.
        if has_attachment_info(model):
            continue

        # Try OpenRouter capabilities first (most reliable).
        or_key = f"{provider_id}/{name}"
        fields = openrouter_caps.get(or_key) or openrouter_caps.get(name)

        # Fall back to rules.
        if not fields:
            fields = match_rule(name, rules)

        if fields:
            if apply_attachment_fields(model, fields):
                result.updated.append((provider_id, name, fields))
                changed = True
        else:
            result.needs_review.append((provider_id, name, "no attachment rule or OpenRouter data"))

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
        if only_provider not in providers:
            print(f"ERROR: unknown provider '{only_provider}'", file=sys.stderr)
            print(f"Available: {', '.join(providers)}", file=sys.stderr)
            sys.exit(1)
        providers = [only_provider]

    for pid in providers:
        print(f"  probing {pid}...")
        probe_provider(pid, rules, openrouter_caps, result, apply)


def generate_report(result: ProbeResult) -> str:
    lines = ["# Registry Probe Report", ""]
    lines.append(f"## Summary")
    lines.append(f"- Auto-filled attachments: **{len(result.updated)}**")
    lines.append(f"- New models (not in registry): **{len(result.new_models)}**")
    lines.append(f"- Removed models (local only): **{len(result.removed)}**")
    lines.append(f"- Needs manual review: **{len(result.needs_review)}**")
    lines.append(f"- Errors: **{len(result.errors)}**")
    lines.append("")

    if result.updated:
        lines.append("## Auto-filled Attachments")
        lines.append("")
        lines.append("| Provider | Model | Fields |")
        lines.append("|---|---|---|")
        for pid, name, fields in sorted(result.updated):
            fstr = ", ".join(k.replace("supports_", "") for k, v in fields.items() if v)
            lines.append(f"| {pid} | {name} | {fstr} |")
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
        for pid, name in sorted(result.removed):
            lines.append(f"- `{pid}/{name}`")
        lines.append("")

    if result.needs_review:
        lines.append("## Needs Manual Review (no attachment info)")
        lines.append("")
        for pid, name, reason in sorted(result.needs_review):
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
    parser.add_argument("--apply", action="store_true", help="apply attachment auto-fills to JSON files")
    parser.add_argument("--provider", type=str, default=None, help="probe only this provider")
    parser.add_argument("--report-only", action="store_true", help="only generate report, skip probing")
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
    print(f"  Auto-filled: {len(result.updated)}")
    print(f"  New models:  {len(result.new_models)}")
    print(f"  Removed:     {len(result.removed)}")
    print(f"  Needs review: {len(result.needs_review)}")
    print(f"  Errors:      {len(result.errors)}")

    if result.needs_review:
        print("\n--- Needs Manual Review ---")
        for pid, name, reason in sorted(result.needs_review):
            print(f"  {pid}/{name}: {reason}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
