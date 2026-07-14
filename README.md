# NAVI Registry

A community-supported database of LLM inference providers and models for [NAVI](https://github.com/navi-ai-org/navi).

## How it works

NAVI ships with a snapshot of this registry embedded in its binary. On startup, NAVI checks if a newer version of the registry is available here and pulls it automatically — so you get new providers and models without upgrading NAVI itself.

```
Embedded snapshot (offline)  →  SQLite cache  →  Remote pull (this repo)
```

## Architecture: canonical models + thin providers

Model **capabilities** live once under `models/`. Providers only **reference** them and add endpoint-specific overrides (usually pricing and API name).

```
models/gpt-5.4.json          ← context, attachments, thinking, sources
providers/openai.json        ← { "ref": "gpt-5.4", "pricing": {...} }
providers/opencode.json      ← { "ref": "gpt-5.4", "context_window_tokens": 400000, "pricing": {...} }
```

`validate.py` flattens refs so NAVI still sees a resolved model list with `name` + capabilities.

## Adding a model

1. Create `models/<id>.json` with verified intrinsic fields (never invent `context_window_tokens`).
2. Reference it from one or more providers:

```json
{
  "ref": "gpt-5.4",
  "pricing": {
    "input_per_1m": 2.5,
    "output_per_1m": 15.0,
    "currency": "USD"
  }
}
```

3. Run `python scripts/validate.py` and commit `models/`, provider files, and `manifest.json`.

### Canonical model example

```json
{
  "id": "gpt-5.4",
  "vendor": "openai",
  "family": "gpt",
  "context_window_tokens": 1050000,
  "max_output_tokens": 128000,
  "supports_thinking": true,
  "attachments": { "images": true, "documents": true },
  "aliases": ["openai/gpt-5.4"],
  "sources": {
    "context_window_tokens": {
      "url": "https://platform.openai.com/docs/models",
      "verified_at": "2026-07-14"
    }
  }
}
```

### Provider example

```json
{
  "id": "my-provider",
  "label": "My Provider",
  "kind": "openai-chat-completions",
  "api_key_env": "MY_PROVIDER_API_KEY",
  "base_url": "https://api.my-provider.com/v1",
  "models": [
    { "ref": "gpt-5.4", "pricing": { "input_per_1m": 2.5, "output_per_1m": 15.0, "currency": "USD" } },
    { "ref": "claude-sonnet-4", "api_name": "anthropic/claude-sonnet-4" }
  ]
}
```

Legacy inline models (`{ "name": "...", "context_window_tokens": ... }`) still validate during the transition, but new entries should use `ref`.

### Provider inheritance (`extends`)

Shared regional catalogs can live under `bases/`:

```json
{
  "id": "mimo-anthropic-ams",
  "label": "MiMo Europe",
  "extends": "mimo-anthropic",
  "kind": "anthropic-messages",
  "api_key_env": "MIMO_API_KEY",
  "base_url": "https://token-plan-ams.xiaomimimo.com/anthropic"
}
```

### Supported `kind` values

| Kind | Protocol |
|---|---|
| `openai-responses` | OpenAI Responses API |
| `openai-chat-completions` | OpenAI Chat Completions (most providers) |
| `anthropic-messages` | Anthropic Messages API |
| `gemini-generate-content` | Google Gemini Generate Content |

## What belongs where

| Field | Canonical `models/` | Provider override |
|---|---|---|
| context window (true max) | ✅ | only if gateway caps lower |
| attachments / thinking | ✅ | rare |
| pricing | ❌ | ✅ always |
| api name (`openai/gpt-4o`) | aliases | `api_name` |
| status | ✅ lifecycle | if this endpoint removed it |

## Validation

```bash
python scripts/validate.py
```

Pure Python — no pip install. Loads schemas, resolves `extends` + model `ref`s, regenerates `manifest.json` (hashes, coverage, catalog index).

Rebuild the catalog from current providers (maintenance):

```bash
python scripts/build_model_catalog.py --apply
python scripts/validate.py
```

## Probe

```bash
python scripts/probe.py
python scripts/probe.py --apply
```

Probe is ref-aware: pricing lands on provider rows; missing attachments/context update the canonical model when absent. Daily CI opens a PR (does not push to main).

## License

[Apache-2.0](LICENSE)
