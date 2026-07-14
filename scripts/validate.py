#!/usr/bin/env python3
"""Validate registry data and regenerate manifest.json.

Pure Python — no external dependencies.

Features:
- Loads structural field sets from schemas/*.schema.json
- Canonical model catalog under models/
- Provider model entries may be legacy inline {name,...} OR {ref, overrides...}
- Provider extends inheritance under bases/
- Coverage health stats in manifest
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PROVIDERS_DIR = ROOT / "providers"
BASES_DIR = ROOT / "bases"
MODELS_DIR = ROOT / "models"
TRANSCRIPTION_PROVIDERS_DIR = ROOT / "transcription-providers"
MANIFEST_PATH = ROOT / "manifest.json"
PROVIDER_SCHEMA_PATH = ROOT / "schemas" / "provider.schema.json"
MODEL_SCHEMA_PATH = ROOT / "schemas" / "model.schema.json"
TRANSCRIPTION_SCHEMA_PATH = ROOT / "schemas" / "transcription-provider.schema.json"

ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
# Canonical model ids may include dots, slashes is NOT allowed in filename id;
# slashes appear only as api_name / aliases.
MODEL_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")
VALID_MODEL_STATUS = {"active", "deprecated", "removed", "preview"}
LEGACY_ATTACHMENT_KEYS = (
    "supports_attachments",
    "supports_images",
    "supports_audio",
    "supports_video",
    "supports_documents",
)

# Intrinsic fields that live on the canonical model (not pricing).
CANONICAL_MODEL_FIELDS = {
    "label",
    "description",
    "family",
    "vendor",
    "status",
    "context_window_tokens",
    "max_output_tokens",
    "recommended_temperature",
    "supports_thinking",
    "attachments",
    "reasoning_levels",
    "default_reasoning_effort",
    "capabilities",
    "sources",
}

# Fields allowed on a provider model entry (legacy or ref override).
PROVIDER_MODEL_OVERRIDE_FIELDS = {
    "ref",
    "api_name",
    "name",
    "label",
    "status",
    "context_window_tokens",
    "max_output_tokens",
    "recommended_temperature",
    "supports_thinking",
    "supports_attachments",
    "supports_images",
    "supports_audio",
    "supports_video",
    "supports_documents",
    "attachments",
    "reasoning_levels",
    "default_reasoning_effort",
    "pricing",
    "capabilities",
    "sources",
}

KNOWN_200K = {
    "claude-opus-4", "claude-opus-4-1", "claude-opus-4-5",
    "claude-opus-4-6", "claude-opus-4-7", "claude-opus-4-8",
    "claude-sonnet-4", "claude-sonnet-4-5", "claude-sonnet-4-6",
    "claude-sonnet-5", "claude-haiku-4-5", "claude-fable-5",
    "claude-3-5-sonnet", "claude-3-5-haiku", "claude-3-opus",
    "claude-3-sonnet", "claude-3-haiku", "claude-3.5-sonnet",
    "claude-3.5-haiku", "claude-3.7-sonnet",
    "o1", "o1-pro", "o1-mini", "o3", "o3-pro", "o3-mini", "o4-mini",
    "GLM-5", "GLM-5.1",
    "gpt-5.1-codex", "gpt-5.1", "gpt-5-mini",
    "zai-org/GLM-5", "zai-org/GLM-5.1",
    "MiniMaxAI/MiniMax-M2.7", "MiniMaxAI/MiniMax-M2.5",
    "Qwen/Qwen3.6-Max-Preview", "Qwen/Qwen3.6-Plus",
    "abab6.5-chat", "abab6.5g-chat", "abab6.5s-chat", "abab6.5t-chat",
    "big-pickle", "mimo-v2.5-free", "hy3-free", "north-mini-code-free",
    "claude-opus-4-1-20250805", "claude-opus-4-20250514",
    "claude-sonnet-4-20250514", "claude-haiku-4",
    "claude-3-7-sonnet-20250219",
    "claude-3-5-sonnet-20241022", "claude-3-5-sonnet-20240620",
    "claude-3-5-haiku-20241022",
    "claude-3-opus-20240229", "claude-3-sonnet-20240229",
    "claude-3-haiku-20240307",
    "claude-haiku-4-5-20251001", "claude-sonnet-4.5",
    "claude-haiku-4.5", "gpt-5.5",
    "glm-5.1", "glm-5", "glm-5-turbo", "glm-4.7", "glm-4.6",
}


class ValidationError(Exception):
    pass


def load_json(path: Path) -> Any:
    with open(path) as f:
        return json.load(f)


def schema_property_keys(schema: dict, def_name: str | None = None) -> set[str]:
    if def_name:
        node = schema.get("$defs", {}).get(def_name, {})
    else:
        node = schema
    return set((node.get("properties") or {}).keys())


def schema_required(schema: dict, def_name: str | None = None) -> set[str]:
    if def_name:
        node = schema.get("$defs", {}).get(def_name, {})
    else:
        node = schema
    return set(node.get("required") or [])


def schema_enum(schema: dict, prop: str, def_name: str | None = None) -> set[str] | None:
    if def_name:
        node = schema.get("$defs", {}).get(def_name, {})
    else:
        node = schema
    prop_schema = (node.get("properties") or {}).get(prop) or {}
    enum = prop_schema.get("enum")
    return set(enum) if enum else None


PROVIDER_SCHEMA = load_json(PROVIDER_SCHEMA_PATH)
TRANSCRIPTION_SCHEMA = load_json(TRANSCRIPTION_SCHEMA_PATH)
MODEL_SCHEMA = load_json(MODEL_SCHEMA_PATH) if MODEL_SCHEMA_PATH.exists() else {}

KNOWN_PROVIDER_KEYS = schema_property_keys(PROVIDER_SCHEMA)
REQUIRED_PROVIDER_KEYS = schema_required(PROVIDER_SCHEMA)
# Union of legacy model + ref entry keys for provider model rows.
KNOWN_MODEL_KEYS = (
    schema_property_keys(PROVIDER_SCHEMA, "model")
    | schema_property_keys(PROVIDER_SCHEMA, "model_ref")
    | {"ref", "api_name"}
)
VALID_KINDS = schema_enum(PROVIDER_SCHEMA, "kind") or set()
VALID_TOOL_CALLING_MODES = schema_enum(PROVIDER_SCHEMA, "tool_calling_mode") or set()
VALID_MODEL_STATUS_SCHEMA = (
    schema_enum(PROVIDER_SCHEMA, "status", "model") or VALID_MODEL_STATUS
)

KNOWN_CANONICAL_KEYS = schema_property_keys(MODEL_SCHEMA) if MODEL_SCHEMA else set()
REQUIRED_CANONICAL_KEYS = schema_required(MODEL_SCHEMA) if MODEL_SCHEMA else {"id"}

KNOWN_TRANSCRIPTION_KEYS = schema_property_keys(TRANSCRIPTION_SCHEMA)
REQUIRED_TRANSCRIPTION_KEYS = schema_required(TRANSCRIPTION_SCHEMA)
KNOWN_TRANSCRIPTION_MODEL_KEYS = schema_property_keys(
    TRANSCRIPTION_SCHEMA, "transcription_model"
)
VALID_TRANSCRIPTION_KINDS = schema_enum(TRANSCRIPTION_SCHEMA, "kind") or set()


def require_keys(data: dict, required: set, pid: str) -> None:
    missing = required - set(data.keys())
    if missing:
        raise ValidationError(f"missing required fields: {sorted(missing)}")


def check_type(value, expected_type, field: str) -> None:
    if value is not None and not isinstance(value, expected_type):
        type_name = (
            " or ".join(t.__name__ for t in expected_type)
            if isinstance(expected_type, tuple)
            else expected_type.__name__
        )
        raise ValidationError(
            f"{field}: expected {type_name}, got {type(value).__name__}"
        )


def deep_merge(base: dict, overlay: dict) -> dict:
    result = copy.deepcopy(base)
    for key, value in overlay.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def load_base_definition(base_id: str, stack: list[str] | None = None) -> dict:
    stack = stack or []
    if base_id in stack:
        raise ValidationError(
            f"extends cycle detected: {' -> '.join(stack + [base_id])}"
        )

    candidates = [
        BASES_DIR / f"{base_id}.json",
        PROVIDERS_DIR / f"{base_id}.json",
        TRANSCRIPTION_PROVIDERS_DIR / f"{base_id}.json",
    ]
    path = next((p for p in candidates if p.exists()), None)
    if path is None:
        raise ValidationError(
            f"extends: base '{base_id}' not found in bases/ or providers/"
        )

    data = load_json(path)
    if not isinstance(data, dict):
        raise ValidationError(f"extends: base '{base_id}' must be an object")

    parent = data.get("extends")
    if parent:
        parent_data = load_base_definition(parent, stack + [base_id])
        return deep_merge(
            parent_data, {k: v for k, v in data.items() if k != "extends"}
        )
    return {k: v for k, v in data.items() if k != "extends"}


def resolve_extends(data: dict) -> dict:
    extends = data.get("extends")
    if not extends:
        return copy.deepcopy(data)
    if not isinstance(extends, str) or not extends:
        raise ValidationError("extends: must be a non-empty string")
    base = load_base_definition(extends, stack=[data.get("id", "?")])
    overlay = {k: v for k, v in data.items() if k != "extends"}
    return deep_merge(base, overlay)


# ── Canonical model catalog ──────────────────────────────────────────────────


def model_filename_for_id(model_id: str) -> str:
    """Map model id to a safe filename (no path separators)."""
    safe = model_id.replace("/", "__")
    return f"{safe}.json"


def load_canonical_catalog() -> dict[str, dict]:
    """Load models/*.json → {id: data}. Also index aliases."""
    catalog: dict[str, dict] = {}
    if not MODELS_DIR.is_dir():
        return catalog

    for path in sorted(MODELS_DIR.glob("*.json")):
        data = load_json(path)
        if not isinstance(data, dict):
            raise ValidationError(f"{path.name}: canonical model must be an object")
        mid = data.get("id")
        if not mid or not isinstance(mid, str):
            raise ValidationError(f"{path.name}: missing string id")
        if mid in catalog:
            raise ValidationError(f"duplicate canonical model id '{mid}'")
        catalog[mid] = data
    return catalog


def build_alias_index(catalog: dict[str, dict]) -> dict[str, str]:
    """Map alias/api name → canonical id."""
    index: dict[str, str] = {}
    for mid, data in catalog.items():
        index[mid] = mid
        # bare self
        bare = mid.split("/")[-1]
        index.setdefault(bare, mid)
        for alias in data.get("aliases") or []:
            if not isinstance(alias, str) or not alias:
                continue
            if alias in index and index[alias] != mid:
                raise ValidationError(
                    f"alias '{alias}' maps to both '{index[alias]}' and '{mid}'"
                )
            index[alias] = mid
    return index


def validate_canonical_model(data: dict, filename: str) -> None:
    require_keys(data, REQUIRED_CANONICAL_KEYS or {"id"}, filename)
    unknown = set(data.keys()) - KNOWN_CANONICAL_KEYS if KNOWN_CANONICAL_KEYS else set()
    # Allow only known keys when schema present
    if KNOWN_CANONICAL_KEYS and unknown:
        raise ValidationError(f"{filename}: unknown fields: {sorted(unknown)}")

    check_type(data["id"], str, "id")
    if not data["id"]:
        raise ValidationError("id: must be non-empty")

    check_type(data.get("label"), str, "label")
    check_type(data.get("description"), str, "description")
    check_type(data.get("family"), str, "family")
    check_type(data.get("vendor"), str, "vendor")

    status = data.get("status")
    if status is not None:
        check_type(status, str, "status")
        if status not in VALID_MODEL_STATUS:
            raise ValidationError(
                f"status: '{status}' invalid; must be one of {sorted(VALID_MODEL_STATUS)}"
            )

    check_type(data.get("context_window_tokens"), int, "context_window_tokens")
    check_type(data.get("max_output_tokens"), int, "max_output_tokens")
    check_type(
        data.get("recommended_temperature"), (int, float), "recommended_temperature"
    )
    check_type(data.get("supports_thinking"), bool, "supports_thinking")
    validate_attachments(data.get("attachments"), "attachments")
    check_type(data.get("reasoning_levels"), list, "reasoning_levels")
    check_type(data.get("default_reasoning_effort"), str, "default_reasoning_effort")
    check_type(data.get("capabilities"), list, "capabilities")
    check_type(data.get("aliases"), list, "aliases")
    if data.get("aliases"):
        for i, a in enumerate(data["aliases"]):
            check_type(a, str, f"aliases[{i}]")
    validate_sources(data.get("sources"), "sources")

    # 200k warning on canonical too
    if data.get("context_window_tokens") == 200000:
        sources = data.get("sources") or {}
        if "context_window_tokens" not in sources and data["id"] not in KNOWN_200K:
            print(
                f"  WARN  models/{filename} ({data['id']}): "
                f"context_window_tokens=200000 — verify + add sources.",
                file=sys.stderr,
            )


def validate_attachments(value, field: str) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        raise ValidationError(f"{field}: must be an object")
    known = {"images", "audio", "video", "documents"}
    unknown = set(value.keys()) - known
    if unknown:
        raise ValidationError(f"{field}: unknown fields: {sorted(unknown)}")
    for key in known:
        check_type(value.get(key), bool, f"{field}.{key}")


def validate_sources(value, field: str) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        raise ValidationError(f"{field}: must be an object")
    for key, src in value.items():
        if not isinstance(key, str) or not key:
            raise ValidationError(f"{field}: keys must be non-empty strings")
        if not isinstance(src, dict):
            raise ValidationError(f"{field}.{key}: must be an object")
        if "url" not in src or not isinstance(src["url"], str) or not src["url"]:
            raise ValidationError(f"{field}.{key}: missing required string 'url'")
        unknown = set(src.keys()) - {"url", "verified_at", "note"}
        if unknown:
            raise ValidationError(f"{field}.{key}: unknown fields: {sorted(unknown)}")
        check_type(src.get("verified_at"), str, f"{field}.{key}.verified_at")
        check_type(src.get("note"), str, f"{field}.{key}.note")


def has_modern_attachments(model: dict) -> bool:
    return isinstance(model.get("attachments"), dict) and bool(model["attachments"])


def has_legacy_attachments(model: dict) -> bool:
    return any(k in model for k in LEGACY_ATTACHMENT_KEYS)


def has_any_attachments(model: dict, provider_defaults: dict | None = None) -> bool:
    if has_modern_attachments(model) or has_legacy_attachments(model):
        return True
    defaults = (provider_defaults or {}).get("attachments")
    return isinstance(defaults, dict) and any(
        isinstance(defaults.get(k), bool)
        for k in ("images", "audio", "video", "documents")
    )


def has_pricing_info(model: dict) -> bool:
    pricing = model.get("pricing")
    return isinstance(pricing, dict) and bool(pricing)


def model_status(model: dict) -> str:
    return model.get("status") or "active"


def warn_200k(pid: str, index: int, model: dict) -> None:
    ctx = model.get("context_window_tokens")
    if ctx != 200000:
        return
    name = model.get("name", model.get("ref", "?"))
    sources = model.get("sources") or {}
    if "context_window_tokens" in sources:
        return
    if name in KNOWN_200K or model.get("ref") in KNOWN_200K:
        return
    print(
        f"  WARN  {pid}/models[{index}] ({name}): "
        f"context_window_tokens=200000 — verify this is correct "
        f"and not an invented default. Add sources.context_window_tokens when verified.",
        file=sys.stderr,
    )


def warn_legacy_attachments(pid: str, index: int, model: dict) -> None:
    if has_legacy_attachments(model) and not has_modern_attachments(model):
        name = model.get("name", model.get("ref", "?"))
        print(
            f"  WARN  {pid}/models[{index}] ({name}): "
            f"legacy supports_* without attachments object.",
            file=sys.stderr,
        )


def resolve_model_entry(
    entry: dict,
    catalog: dict[str, dict],
    alias_index: dict[str, str],
    pid: str,
    index: int,
) -> dict:
    """Resolve a provider model entry to a full NAVI-compatible model dict.

    Output always has ``name`` (API id) and merged capabilities.
    """
    if not isinstance(entry, dict):
        raise ValidationError(f"models[{index}]: must be an object")

    unknown = set(entry.keys()) - KNOWN_MODEL_KEYS
    if unknown:
        raise ValidationError(
            f"models[{index}]: unknown fields: {sorted(unknown)}"
        )

    ref = entry.get("ref")
    if ref is not None:
        check_type(ref, str, f"models[{index}].ref")
        if not ref:
            raise ValidationError(f"models[{index}].ref: must be non-empty")

        # Resolve ref via direct id or alias index
        canon_id = ref if ref in catalog else alias_index.get(ref)
        if not canon_id or canon_id not in catalog:
            raise ValidationError(
                f"models[{index}].ref: unknown canonical model '{ref}' "
                f"(expected models/{model_filename_for_id(ref)})"
            )
        canonical = catalog[canon_id]

        # Build base from canonical (drop catalog-only fields)
        resolved = {
            k: copy.deepcopy(v)
            for k, v in canonical.items()
            if k in CANONICAL_MODEL_FIELDS and k not in ("family", "vendor", "description")
        }
        # Keep family/vendor out of provider-facing model unless useful later.
        # Attach label from canonical if present.
        if "label" in canonical:
            resolved["label"] = canonical["label"]
        if "status" in canonical:
            resolved["status"] = canonical["status"]

        # Apply provider overrides (anything except ref)
        overlay = {
            k: v
            for k, v in entry.items()
            if k not in ("ref",) and v is not None
        }
        # Map api_name → name
        api_name = overlay.pop("api_name", None) or overlay.pop("name", None)
        resolved = deep_merge(resolved, overlay)
        resolved["name"] = api_name or canon_id
        resolved["ref"] = canon_id  # keep ref for coverage/debug (stripped for NAVI export if needed)
        return resolved

    # Legacy inline model — requires name
    if "name" not in entry:
        raise ValidationError(
            f"models[{index}]: legacy model requires 'name' (or use 'ref')"
        )
    check_type(entry["name"], str, f"models[{index}].name")
    if not entry["name"]:
        raise ValidationError(f"models[{index}].name: must be non-empty")
    return copy.deepcopy(entry)


def validate_resolved_model(
    model: dict, pid: str, index: int, provider_defaults: dict | None
) -> None:
    """Type-check a fully resolved model entry."""
    check_type(model.get("name"), str, f"models[{index}].name")
    check_type(model.get("label"), str, f"models[{index}].label")

    status = model.get("status")
    if status is not None:
        check_type(status, str, f"models[{index}].status")
        if status not in VALID_MODEL_STATUS_SCHEMA:
            raise ValidationError(
                f"models[{index}].status: '{status}' invalid; "
                f"must be one of {sorted(VALID_MODEL_STATUS_SCHEMA)}"
            )

    check_type(
        model.get("context_window_tokens"), int, f"models[{index}].context_window_tokens"
    )
    warn_200k(pid, index, model)
    check_type(model.get("max_output_tokens"), int, f"models[{index}].max_output_tokens")
    check_type(
        model.get("recommended_temperature"),
        (int, float),
        f"models[{index}].recommended_temperature",
    )
    check_type(model.get("supports_thinking"), bool, f"models[{index}].supports_thinking")
    for k in LEGACY_ATTACHMENT_KEYS:
        check_type(model.get(k), bool, f"models[{index}].{k}")
    validate_attachments(model.get("attachments"), f"models[{index}].attachments")
    warn_legacy_attachments(pid, index, model)
    check_type(model.get("reasoning_levels"), list, f"models[{index}].reasoning_levels")
    check_type(
        model.get("default_reasoning_effort"),
        str,
        f"models[{index}].default_reasoning_effort",
    )
    check_type(model.get("capabilities"), list, f"models[{index}].capabilities")
    validate_sources(model.get("sources"), f"models[{index}].sources")

    pricing = model.get("pricing")
    if pricing is not None:
        if not isinstance(pricing, dict):
            raise ValidationError(f"models[{index}].pricing: must be an object")
        known_pricing_keys = {
            "input_per_1m",
            "output_per_1m",
            "cached_input_per_1m",
            "cached_output_per_1m",
            "currency",
        }
        unknown_p = set(pricing.keys()) - known_pricing_keys
        if unknown_p:
            raise ValidationError(
                f"models[{index}].pricing: unknown fields: {sorted(unknown_p)}"
            )
        for pk in (
            "input_per_1m",
            "output_per_1m",
            "cached_input_per_1m",
            "cached_output_per_1m",
        ):
            check_type(pricing.get(pk), (int, float), f"models[{index}].pricing.{pk}")
        check_type(pricing.get("currency"), str, f"models[{index}].pricing.currency")


def validate_provider(
    data: dict,
    filename: str,
    catalog: dict[str, dict],
    alias_index: dict[str, str],
) -> dict:
    """Validate and return flattened provider with resolved models."""
    if not isinstance(data, dict):
        raise ValidationError("provider root must be an object")

    flat = resolve_extends(data)
    pid = flat.get("id", filename)

    required = set(REQUIRED_PROVIDER_KEYS) | {"models"}
    require_keys(flat, required, pid)

    unknown = set(flat.keys()) - KNOWN_PROVIDER_KEYS
    if unknown:
        raise ValidationError(f"unknown fields: {sorted(unknown)}")

    check_type(flat["id"], str, "id")
    if not ID_RE.match(flat["id"]):
        raise ValidationError(f"id: '{flat['id']}' must match ^[a-z0-9][a-z0-9-]*$")
    check_type(flat["label"], str, "label")
    check_type(flat.get("description", ""), str, "description")
    check_type(flat["kind"], str, "kind")
    check_type(flat["api_key_env"], str, "api_key_env")

    if flat["kind"] not in VALID_KINDS:
        raise ValidationError(
            f"kind: '{flat['kind']}' is not valid. Must be one of {sorted(VALID_KINDS)}"
        )

    base_url = flat.get("base_url")
    if base_url is not None:
        check_type(base_url, str, "base_url")

    tcm = flat.get("tool_calling_mode")
    if tcm is not None:
        check_type(tcm, str, "tool_calling_mode")
        if tcm not in VALID_TOOL_CALLING_MODES:
            raise ValidationError(
                f"tool_calling_mode: '{tcm}' is not valid. "
                f"Must be one of {sorted(VALID_TOOL_CALLING_MODES)}"
            )

    check_type(flat.get("default_large_model"), str, "default_large_model")
    check_type(flat.get("default_small_model"), str, "default_small_model")
    check_type(flat.get("request_options"), dict, "request_options")
    check_type(flat.get("aggregator"), bool, "aggregator")
    check_type(flat.get("defaults"), dict, "defaults")

    defaults = flat.get("defaults") or {}
    unknown_defaults = set(defaults.keys()) - {"attachments"}
    if unknown_defaults:
        raise ValidationError(f"defaults: unknown fields: {sorted(unknown_defaults)}")
    validate_attachments(defaults.get("attachments"), "defaults.attachments")

    models = flat["models"]
    if not isinstance(models, list) or len(models) == 0:
        raise ValidationError("models: must be a non-empty array")

    resolved_models = []
    seen_names: set[str] = set()
    for i, entry in enumerate(models):
        resolved = resolve_model_entry(entry, catalog, alias_index, pid, i)
        validate_resolved_model(resolved, pid, i, defaults)
        name = resolved["name"]
        if name in seen_names:
            raise ValidationError(f"models[{i}].name: duplicate model name '{name}'")
        seen_names.add(name)
        resolved_models.append(resolved)

    flat["models"] = resolved_models
    return flat


def validate_transcription_provider(data: dict, filename: str) -> dict:
    if not isinstance(data, dict):
        raise ValidationError("provider root must be an object")

    flat = resolve_extends(data)
    pid = flat.get("id", filename)

    required = set(REQUIRED_TRANSCRIPTION_KEYS) | {"models"}
    require_keys(flat, required, pid)

    unknown = set(flat.keys()) - KNOWN_TRANSCRIPTION_KEYS
    if unknown:
        raise ValidationError(f"unknown fields: {sorted(unknown)}")

    check_type(flat["id"], str, "id")
    if not ID_RE.match(flat["id"]):
        raise ValidationError(f"id: '{flat['id']}' must match ^[a-z0-9][a-z0-9-]*$")
    check_type(flat["label"], str, "label")
    check_type(flat.get("description", ""), str, "description")
    check_type(flat["kind"], str, "kind")
    check_type(flat["api_key_env"], str, "api_key_env")
    check_type(flat["base_url"], str, "base_url")

    if flat["kind"] not in VALID_TRANSCRIPTION_KINDS:
        raise ValidationError(
            f"kind: '{flat['kind']}' is not valid. "
            f"Must be one of {sorted(VALID_TRANSCRIPTION_KINDS)}"
        )

    check_type(flat.get("transcription_path"), str, "transcription_path")
    check_type(flat.get("default_model"), str, "default_model")
    check_type(flat.get("supports_streaming"), bool, "supports_streaming")

    models = flat["models"]
    if not isinstance(models, list) or len(models) == 0:
        raise ValidationError("models: must be a non-empty array")

    seen_names: set[str] = set()
    for i, model in enumerate(models):
        if not isinstance(model, dict):
            raise ValidationError(f"models[{i}]: must be an object")
        require_keys(model, {"name"}, f"{pid}/models[{i}]")

        unknown_m = set(model.keys()) - KNOWN_TRANSCRIPTION_MODEL_KEYS
        if unknown_m:
            raise ValidationError(
                f"models[{i}] ({model.get('name', '?')}): unknown fields: {sorted(unknown_m)}"
            )

        check_type(model["name"], str, f"models[{i}].name")
        if model["name"] in seen_names:
            raise ValidationError(
                f"models[{i}].name: duplicate model name '{model['name']}'"
            )
        seen_names.add(model["name"])

        check_type(model.get("label"), str, f"models[{i}].label")
        check_type(model.get("description"), str, f"models[{i}].description")

        status = model.get("status")
        if status is not None:
            check_type(status, str, f"models[{i}].status")
            if status not in VALID_MODEL_STATUS:
                raise ValidationError(
                    f"models[{i}].status: '{status}' is not valid. "
                    f"Must be one of {sorted(VALID_MODEL_STATUS)}"
                )

        check_type(model.get("languages"), list, f"models[{i}].languages")
        check_type(model.get("sample_rate_hz"), int, f"models[{i}].sample_rate_hz")
        check_type(
            model.get("max_duration_seconds"), int, f"models[{i}].max_duration_seconds"
        )
        check_type(model.get("max_file_bytes"), int, f"models[{i}].max_file_bytes")
        validate_sources(model.get("sources"), f"models[{i}].sources")

        pricing = model.get("pricing")
        if pricing is not None:
            if not isinstance(pricing, dict):
                raise ValidationError(f"models[{i}].pricing: must be an object")
            known_pricing_keys = {"per_minute", "currency"}
            unknown_p = set(pricing.keys()) - known_pricing_keys
            if unknown_p:
                raise ValidationError(
                    f"models[{i}].pricing: unknown fields: {sorted(unknown_p)}"
                )
            check_type(
                pricing.get("per_minute"),
                (int, float),
                f"models[{i}].pricing.per_minute",
            )
            check_type(pricing.get("currency"), str, f"models[{i}].pricing.currency")

    return flat


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_coverage(providers: list[dict], catalog: dict[str, dict]) -> dict:
    total = 0
    with_pricing = 0
    with_attachments = 0
    with_modern_attachments = 0
    with_legacy_only = 0
    missing_ctx = 0
    unverified_200k = 0
    with_sources = 0
    with_thinking = 0
    with_ref = 0
    by_status: dict[str, int] = {
        "active": 0,
        "deprecated": 0,
        "removed": 0,
        "preview": 0,
    }

    for data in providers:
        defaults = data.get("defaults") or {}
        for model in data.get("models", []):
            total += 1
            status = model_status(model)
            by_status[status] = by_status.get(status, 0) + 1
            if model.get("ref"):
                with_ref += 1
            if has_pricing_info(model):
                with_pricing += 1
            if has_any_attachments(model, defaults):
                with_attachments += 1
            if has_modern_attachments(model) or isinstance(
                defaults.get("attachments"), dict
            ):
                if has_modern_attachments(model) or has_any_attachments(model, defaults):
                    with_modern_attachments += 1
            if has_legacy_attachments(model) and not has_modern_attachments(model):
                with_legacy_only += 1
            if "context_window_tokens" not in model:
                missing_ctx += 1
            if model.get("context_window_tokens") == 200000:
                sources = model.get("sources") or {}
                if (
                    "context_window_tokens" not in sources
                    and model.get("name") not in KNOWN_200K
                    and model.get("ref") not in KNOWN_200K
                ):
                    unverified_200k += 1
            if model.get("sources"):
                with_sources += 1
            if model.get("supports_thinking") is True:
                with_thinking += 1

    return {
        "models_total": total,
        "models_with_pricing": with_pricing,
        "models_with_attachments": with_attachments,
        "models_with_modern_attachments": with_modern_attachments,
        "models_legacy_attachments_only": with_legacy_only,
        "models_missing_context_window": missing_ctx,
        "models_unverified_200k": unverified_200k,
        "models_with_sources": with_sources,
        "models_with_thinking": with_thinking,
        "models_with_ref": with_ref,
        "canonical_models": len(catalog),
        "models_by_status": by_status,
    }


def main() -> int:
    # ── Canonical catalog ────────────────────────────────────────────────
    catalog: dict[str, dict] = {}
    alias_index: dict[str, str] = {}
    catalog_errors = 0

    print("Canonical models:")
    if MODELS_DIR.is_dir():
        model_files = sorted(MODELS_DIR.glob("*.json"))
        if not model_files:
            print("  (none)")
        for mf in model_files:
            try:
                data = load_json(mf)
                validate_canonical_model(data, mf.name)
                mid = data["id"]
                if mid in catalog:
                    print(f"  FAIL duplicate id '{mid}' in {mf.name}", file=sys.stderr)
                    catalog_errors += 1
                    continue
                catalog[mid] = data
                print(f"  OK   {mid}")
            except (ValidationError, json.JSONDecodeError, KeyError) as e:
                print(f"  FAIL {mf.name}: {e}", file=sys.stderr)
                catalog_errors += 1
        try:
            alias_index = build_alias_index(catalog)
        except ValidationError as e:
            print(f"  FAIL alias index: {e}", file=sys.stderr)
            catalog_errors += 1
        print(f"  total={len(catalog)} aliases={len(alias_index) - len(catalog)}")
    else:
        print("  (models/ directory not present — legacy inline models only)")

    if catalog_errors:
        print(f"\n{catalog_errors} canonical model error(s)", file=sys.stderr)
        return 1

    # ── LLM providers ────────────────────────────────────────────────────
    provider_files = sorted(PROVIDERS_DIR.glob("*.json"))
    if not provider_files:
        print("ERROR: no provider files found", file=sys.stderr)
        return 1

    entries = {}
    flattened_providers: list[dict] = []
    total_models = 0
    errors = 0
    ref_count = 0
    inline_count = 0

    print("\nLLM providers:")
    for pf in provider_files:
        try:
            data = load_json(pf)
            # Count raw entry styles before resolve
            raw_flat = resolve_extends(data)
            for m in raw_flat.get("models") or []:
                if isinstance(m, dict) and "ref" in m:
                    ref_count += 1
                else:
                    inline_count += 1

            flat = validate_provider(data, pf.name, catalog, alias_index)
            pid = flat["id"]
            model_count = len(flat.get("models", []))
            total_models += model_count
            sha = compute_sha256(pf)
            if pid in entries:
                print(f"  FAIL duplicate id '{pid}' in {pf.name}", file=sys.stderr)
                errors += 1
                continue
            entry = {
                "file": f"providers/{pf.name}",
                "sha256": sha,
                "model_count": model_count,
            }
            if data.get("extends"):
                entry["extends"] = data["extends"]
            entries[pid] = entry
            flattened_providers.append(flat)
            print(f"  OK   {pid:30s}  models={model_count:3d}  sha256={sha[:12]}...")
        except (ValidationError, json.JSONDecodeError, KeyError) as e:
            print(f"  FAIL {pf.name}: {e}", file=sys.stderr)
            errors += 1

    # ── Transcription ────────────────────────────────────────────────────
    transcription_entries = {}
    transcription_models = 0
    transcription_files = (
        sorted(TRANSCRIPTION_PROVIDERS_DIR.glob("*.json"))
        if TRANSCRIPTION_PROVIDERS_DIR.is_dir()
        else []
    )

    print("\nTranscription providers:")
    if not transcription_files:
        print("  (none)")
    for pf in transcription_files:
        try:
            data = load_json(pf)
            flat = validate_transcription_provider(data, pf.name)
            pid = flat["id"]
            model_count = len(flat.get("models", []))
            transcription_models += model_count
            sha = compute_sha256(pf)
            if pid in transcription_entries:
                print(f"  FAIL duplicate id '{pid}' in {pf.name}", file=sys.stderr)
                errors += 1
                continue
            transcription_entries[pid] = {
                "file": f"transcription-providers/{pf.name}",
                "sha256": sha,
                "model_count": model_count,
            }
            print(f"  OK   {pid:30s}  models={model_count:3d}  sha256={sha[:12]}...")
        except (ValidationError, json.JSONDecodeError, KeyError) as e:
            print(f"  FAIL {pf.name}: {e}", file=sys.stderr)
            errors += 1

    if errors:
        print(f"\n{errors} validation error(s)", file=sys.stderr)
        return 1

    coverage = compute_coverage(flattened_providers, catalog)
    new_providers = dict(sorted(entries.items()))
    new_transcription = dict(sorted(transcription_entries.items()))

    # Catalog fingerprint for version bump
    catalog_index = {
        mid: {
            "file": f"models/{model_filename_for_id(mid)}",
            "sha256": compute_sha256(MODELS_DIR / model_filename_for_id(mid))
            if (MODELS_DIR / model_filename_for_id(mid)).exists()
            else None,
        }
        for mid in sorted(catalog)
    }

    version = 1
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH) as f:
            old = json.load(f)
        old_providers = old.get("providers", {})
        old_transcription = old.get("transcription_providers", {})
        old_catalog = old.get("models", {})
        if (
            old_providers == new_providers
            and old_transcription == new_transcription
            and old_catalog == catalog_index
        ):
            version = old.get("version", 1)
            now = old.get("updated_at", now)
        else:
            version = old.get("version", 1) + 1

    manifest = {
        "version": version,
        "updated_at": now,
        "coverage": coverage,
        "models": catalog_index,
        "providers": new_providers,
        "transcription_providers": new_transcription,
    }

    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")

    print(
        f"\nmanifest.json: version={version} "
        f"providers={len(entries)} models={total_models} "
        f"canonical={len(catalog)} "
        f"transcription_providers={len(transcription_entries)} "
        f"transcription_models={transcription_models}"
    )
    print(
        "coverage: "
        f"pricing={coverage['models_with_pricing']}/{coverage['models_total']} "
        f"attachments={coverage['models_with_attachments']}/{coverage['models_total']} "
        f"refs={coverage['models_with_ref']}/{coverage['models_total']} "
        f"inline_raw={inline_count} ref_raw={ref_count} "
        f"unverified_200k={coverage['models_unverified_200k']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
