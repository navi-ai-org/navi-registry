#!/usr/bin/env python3
"""Validate provider JSONs and regenerate manifest.json with correct SHA-256s.

Pure Python — no external dependencies required.
"""

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROVIDERS_DIR = ROOT / "providers"
TRANSCRIPTION_PROVIDERS_DIR = ROOT / "transcription-providers"
MANIFEST_PATH = ROOT / "manifest.json"

VALID_KINDS = {
    "openai-responses",
    "openai-chat-completions",
    "anthropic-messages",
    "gemini-generate-content",
}
VALID_TRANSCRIPTION_KINDS = {
    "openai-audio-transcriptions",
    "wispr-flow",
}
VALID_TOOL_CALLING_MODES = {"native", "text-extracted", "manifest-only", "disabled"}


class ValidationError(Exception):
    pass


def require_keys(data: dict, required: set, pid: str) -> None:
    missing = required - set(data.keys())
    if missing:
        raise ValidationError(f"missing required fields: {sorted(missing)}")


def check_type(value, expected_type, field: str) -> None:
    if value is not None and not isinstance(value, expected_type):
        raise ValidationError(
            f"{field}: expected {expected_type.__name__}, got {type(value).__name__}"
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


def validate_provider(data: dict, filename: str) -> None:
    pid = data.get("id", filename)

    require_keys(data, {"id", "label", "kind", "api_key_env", "models"}, pid)

    # Unknown keys — allow forward-compatible optional fields but catch typos.
    known_keys = {
        "id", "label", "description", "kind", "api_key_env", "base_url",
        "tool_calling_mode", "default_large_model", "default_small_model",
        "request_options", "defaults", "models", "aggregator",
    }
    unknown = set(data.keys()) - known_keys
    if unknown:
        raise ValidationError(f"unknown fields: {sorted(unknown)}")

    # Field-level checks.
    check_type(data["id"], str, "id")
    check_type(data["label"], str, "label")
    check_type(data.get("description", ""), str, "description")
    check_type(data["kind"], str, "kind")
    check_type(data["api_key_env"], str, "api_key_env")

    if data["kind"] not in VALID_KINDS:
        raise ValidationError(
            f"kind: '{data['kind']}' is not valid. Must be one of {sorted(VALID_KINDS)}"
        )

    base_url = data.get("base_url")
    if base_url is not None:
        check_type(base_url, str, "base_url")

    tcm = data.get("tool_calling_mode")
    if tcm is not None:
        check_type(tcm, str, "tool_calling_mode")
        if tcm not in VALID_TOOL_CALLING_MODES:
            raise ValidationError(
                f"tool_calling_mode: '{tcm}' is not valid. "
                f"Must be one of {sorted(VALID_TOOL_CALLING_MODES)}"
            )

    check_type(data.get("default_large_model"), str, "default_large_model")
    check_type(data.get("default_small_model"), str, "default_small_model")
    check_type(data.get("request_options"), dict, "request_options")
    check_type(data.get("aggregator"), bool, "aggregator")
    check_type(data.get("defaults"), dict, "defaults")
    defaults = data.get("defaults") or {}
    unknown_defaults = set(defaults.keys()) - {"attachments"}
    if unknown_defaults:
        raise ValidationError(f"defaults: unknown fields: {sorted(unknown_defaults)}")
    validate_attachments(defaults.get("attachments"), "defaults.attachments")

    models = data["models"]
    if not isinstance(models, list) or len(models) == 0:
        raise ValidationError("models: must be a non-empty array")

    for i, model in enumerate(models):
        if not isinstance(model, dict):
            raise ValidationError(f"models[{i}]: must be an object")
        require_keys(model, {"name"}, f"{pid}/models[{i}]")

        known_model_keys = {
            "name", "label", "context_window_tokens",
            "max_output_tokens", "recommended_temperature", "supports_thinking",
            "supports_attachments", "supports_images", "supports_audio",
            "supports_video", "supports_documents", "attachments",
            "reasoning_levels", "default_reasoning_effort", "pricing", "capabilities",
        }
        unknown_m = set(model.keys()) - known_model_keys
        if unknown_m:
            raise ValidationError(
                f"models[{i}] ({model.get('name', '?')}): unknown fields: {sorted(unknown_m)}"
            )

        check_type(model["name"], str, f"models[{i}].name")

        check_type(model.get("label"), str, f"models[{i}].label")
        check_type(model.get("context_window_tokens"), int, f"models[{i}].context_window_tokens")

        # Warn on suspicious context_window_tokens values.
        # 200000 is the most commonly invented default — it's Claude's real
        # context window, but agents copy it to other models incorrectly.
        ctx = model.get("context_window_tokens")
        if ctx == 200000:
            model_name = model.get("name", "?")
            # Known models that genuinely have 200k context — won't warn for these.
            KNOWN_200K = {
                # Anthropic Claude family (200k is correct for all Claude 3/3.5/4 models)
                "claude-opus-4", "claude-opus-4-1", "claude-opus-4-5",
                "claude-opus-4-6", "claude-opus-4-7", "claude-opus-4-8",
                "claude-sonnet-4", "claude-sonnet-4-5", "claude-sonnet-4-6",
                "claude-sonnet-5", "claude-haiku-4-5", "claude-fable-5",
                "claude-3-5-sonnet", "claude-3-5-haiku", "claude-3-opus",
                "claude-3-sonnet", "claude-3-haiku", "claude-3.5-sonnet",
                "claude-3.5-haiku", "claude-3.7-sonnet",
                # OpenAI o-series (200k is correct for o1/o3)
                "o1", "o1-pro", "o1-mini", "o3", "o3-pro", "o3-mini", "o4-mini",
                # Charm Hyper / GLM
                "GLM-5", "GLM-5.1",
                # GitHub Copilot
                "gpt-5.1-codex", "gpt-5.1", "gpt-5-mini",
                # CommandCode / ZAI
                "zai-org/GLM-5", "zai-org/GLM-5.1",
                "MiniMaxAI/MiniMax-M2.7", "MiniMaxAI/MiniMax-M2.5",
                "Qwen/Qwen3.6-Max-Preview", "Qwen/Qwen3.6-Plus",
                # MiniMax abab6.5
                "abab6.5-chat", "abab6.5g-chat", "abab6.5s-chat", "abab6.5t-chat",
                # OpenCode free models
                "big-pickle", "mimo-v2.5-free", "hy3-free", "north-mini-code-free",
                # Anthropic dated versions
                "claude-opus-4-1-20250805", "claude-opus-4-20250514",
                "claude-sonnet-4-20250514", "claude-haiku-4",
                "claude-3-7-sonnet-20250219",
                "claude-3-5-sonnet-20241022", "claude-3-5-sonnet-20240620",
                "claude-3-5-haiku-20241022",
                "claude-3-opus-20240229", "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307",
                # CommandCode dated versions
                "claude-haiku-4-5-20251001", "claude-sonnet-4.5",
                "claude-haiku-4.5", "gpt-5.5",
            }
            if model_name not in KNOWN_200K:
                print(
                    f"  WARN  {pid}/models[{i}] ({model_name}): "
                    f"context_window_tokens=200000 — verify this is correct "
                    f"and not an invented default. See AGENTS.md § Model Data Integrity.",
                    file=sys.stderr,
                )

        check_type(model.get("max_output_tokens"), int, f"models[{i}].max_output_tokens")
        check_type(model.get("recommended_temperature"), (int, float),
                   f"models[{i}].recommended_temperature")
        check_type(model.get("supports_thinking"), bool, f"models[{i}].supports_thinking")
        check_type(model.get("supports_attachments"), bool, f"models[{i}].supports_attachments")
        check_type(model.get("supports_images"), bool, f"models[{i}].supports_images")
        check_type(model.get("supports_audio"), bool, f"models[{i}].supports_audio")
        check_type(model.get("supports_video"), bool, f"models[{i}].supports_video")
        check_type(model.get("supports_documents"), bool, f"models[{i}].supports_documents")
        validate_attachments(model.get("attachments"), f"models[{i}].attachments")
        check_type(model.get("reasoning_levels"), list, f"models[{i}].reasoning_levels")
        check_type(model.get("default_reasoning_effort"), str,
                   f"models[{i}].default_reasoning_effort")
        check_type(model.get("capabilities"), list, f"models[{i}].capabilities")

        pricing = model.get("pricing")
        if pricing is not None:
            if not isinstance(pricing, dict):
                raise ValidationError(f"models[{i}].pricing: must be an object")
            known_pricing_keys = {
                "input_per_1m", "output_per_1m",
                "cached_input_per_1m", "cached_output_per_1m", "currency",
            }
            unknown_p = set(pricing.keys()) - known_pricing_keys
            if unknown_p:
                raise ValidationError(
                    f"models[{i}].pricing: unknown fields: {sorted(unknown_p)}"
                )
            for pk in ("input_per_1m", "output_per_1m",
                        "cached_input_per_1m", "cached_output_per_1m"):
                check_type(pricing.get(pk), (int, float), f"models[{i}].pricing.{pk}")
            check_type(pricing.get("currency"), str, f"models[{i}].pricing.currency")


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_transcription_provider(data: dict, filename: str) -> None:
    """Validate a remote speech-to-text / dictation provider file."""
    pid = data.get("id", filename)

    require_keys(
        data,
        {"id", "label", "kind", "api_key_env", "base_url", "models"},
        pid,
    )

    known_keys = {
        "id",
        "label",
        "description",
        "kind",
        "api_key_env",
        "base_url",
        "transcription_path",
        "default_model",
        "supports_streaming",
        "models",
    }
    unknown = set(data.keys()) - known_keys
    if unknown:
        raise ValidationError(f"unknown fields: {sorted(unknown)}")

    check_type(data["id"], str, "id")
    check_type(data["label"], str, "label")
    check_type(data.get("description", ""), str, "description")
    check_type(data["kind"], str, "kind")
    check_type(data["api_key_env"], str, "api_key_env")
    check_type(data["base_url"], str, "base_url")

    if data["kind"] not in VALID_TRANSCRIPTION_KINDS:
        raise ValidationError(
            f"kind: '{data['kind']}' is not valid. "
            f"Must be one of {sorted(VALID_TRANSCRIPTION_KINDS)}"
        )

    check_type(data.get("transcription_path"), str, "transcription_path")
    check_type(data.get("default_model"), str, "default_model")
    check_type(data.get("supports_streaming"), bool, "supports_streaming")

    models = data["models"]
    if not isinstance(models, list) or len(models) == 0:
        raise ValidationError("models: must be a non-empty array")

    for i, model in enumerate(models):
        if not isinstance(model, dict):
            raise ValidationError(f"models[{i}]: must be an object")
        require_keys(model, {"name"}, f"{pid}/models[{i}]")

        known_model_keys = {
            "name",
            "label",
            "description",
            "languages",
            "sample_rate_hz",
            "max_duration_seconds",
            "max_file_bytes",
            "pricing",
        }
        unknown_m = set(model.keys()) - known_model_keys
        if unknown_m:
            raise ValidationError(
                f"models[{i}] ({model.get('name', '?')}): unknown fields: {sorted(unknown_m)}"
            )

        check_type(model["name"], str, f"models[{i}].name")
        check_type(model.get("label"), str, f"models[{i}].label")
        check_type(model.get("description"), str, f"models[{i}].description")
        check_type(model.get("languages"), list, f"models[{i}].languages")
        check_type(model.get("sample_rate_hz"), int, f"models[{i}].sample_rate_hz")
        check_type(
            model.get("max_duration_seconds"), int, f"models[{i}].max_duration_seconds"
        )
        check_type(model.get("max_file_bytes"), int, f"models[{i}].max_file_bytes")

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


def main() -> int:
    provider_files = sorted(PROVIDERS_DIR.glob("*.json"))

    if not provider_files:
        print("ERROR: no provider files found", file=sys.stderr)
        return 1

    entries = {}
    total_models = 0
    errors = 0

    print("LLM providers:")
    for pf in provider_files:
        try:
            with open(pf) as f:
                data = json.load(f)
            validate_provider(data, pf.name)
            pid = data["id"]
            model_count = len(data.get("models", []))
            total_models += model_count
            sha = compute_sha256(pf)
            if pid in entries:
                print(f"  FAIL duplicate id '{pid}' in {pf.name}", file=sys.stderr)
                errors += 1
                continue
            entries[pid] = {
                "file": f"providers/{pf.name}",
                "sha256": sha,
                "model_count": model_count,
            }
            print(f"  OK   {pid:30s}  models={model_count:3d}  sha256={sha[:12]}...")
        except (ValidationError, json.JSONDecodeError, KeyError) as e:
            print(f"  FAIL {pf.name}: {e}", file=sys.stderr)
            errors += 1

    transcription_entries = {}
    transcription_models = 0
    transcription_files = sorted(TRANSCRIPTION_PROVIDERS_DIR.glob("*.json")) if TRANSCRIPTION_PROVIDERS_DIR.is_dir() else []

    print("\nTranscription providers:")
    if not transcription_files:
        print("  (none)")
    for pf in transcription_files:
        try:
            with open(pf) as f:
                data = json.load(f)
            validate_transcription_provider(data, pf.name)
            pid = data["id"]
            model_count = len(data.get("models", []))
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

    new_providers = dict(sorted(entries.items()))
    new_transcription = dict(sorted(transcription_entries.items()))

    # Preserve version if content is unchanged; bump if changed.
    version = 1
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH) as f:
            old = json.load(f)
        old_providers = old.get("providers", {})
        old_transcription = old.get("transcription_providers", {})
        if old_providers == new_providers and old_transcription == new_transcription:
            version = old.get("version", 1)
            now = old.get("updated_at", now)
        else:
            version = old.get("version", 1) + 1

    manifest = {
        "version": version,
        "updated_at": now,
        "providers": new_providers,
        "transcription_providers": new_transcription,
    }

    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")

    print(
        f"\nmanifest.json: version={version} "
        f"providers={len(entries)} models={total_models} "
        f"transcription_providers={len(transcription_entries)} "
        f"transcription_models={transcription_models}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
