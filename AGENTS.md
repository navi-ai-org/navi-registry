# AGENTS.md

Guide for agents working in the NAVI Registry repository.

## What this repo is

A **data registry**, not a software project. It holds JSON definitions of LLM inference providers/models consumed by [NAVI](https://github.com/navi-ai-org/navi). NAVI embeds a snapshot at build time and pulls this repo at runtime for updates. There is no application code, no build step, and no test suite — only data files, a JSON Schema, and a Python validator.

## Repository layout

```
providers/*.json           One provider definition per file (27 providers, 332 models)
schemas/provider.schema.json   JSON Schema for a provider file
scripts/validate.py        Validator + manifest generator (pure Python, no deps)
manifest.json              AUTO-GENERATED index — never hand-edit
README.md                  User-facing docs
```

## Essential command

```bash
python scripts/validate.py
```

This single script does **two things**: validates every `providers/*.json` against its rules AND regenerates `manifest.json`. Run it after any provider change and commit the regenerated `manifest.json` together with the provider edits.

The README mentions `pip install jsonschema`, but `validate.py` is **pure Python** and does not import `jsonschema`. No dependency installation is needed. (The README line is stale.)

## Critical gotchas

### 1. Schema file and validator can drift — keep them in sync

`schemas/provider.schema.json` and `scripts/validate.py` are **independently maintained**. The validator does not load the schema file; it hardcodes its own `known_keys`, `known_model_keys`, enum sets, and type checks. When adding a new field you must update **both** files or validation will reject entries that the schema permits (or vice versa). The validator's key sets are the actual source of truth for what passes CI.

### 2. `manifest.json` is auto-generated

Never edit `manifest.json` by hand. `validate.py` rewrites it with:
- SHA-256 of each provider file's raw bytes
- Per-provider `model_count`
- A `version` integer that **auto-bumps** when provider entries change and is **preserved** when they don't
- An `updated_at` timestamp that is similarly preserved on no-op runs (so re-running the validator doesn't drift the timestamp)

Providers are sorted alphabetically by `id` in the output.

### 3. Duplicate provider IDs are rejected

The validator fails on duplicate `id` values across files. The filename does not have to equal the `id`, but the manifest references `providers/<filename>`, so in practice every file is named `<id>.json`.

## Provider file conventions

### Required fields

`id`, `label`, `kind`, `api_key_env`, `models` are required. Everything else is optional.

### `id`

Must match `^[a-z0-9][a-z0-9-]*$` — lowercase, hyphen-separated, alphanumeric. Filename should match the id.

### `kind` (protocol)

One of exactly four values:
| Kind | Protocol |
|---|---|
| `openai-responses` | OpenAI Responses API |
| `openai-chat-completions` | OpenAI Chat Completions (most providers) |
| `anthropic-messages` | Anthropic Messages API |
| `gemini-generate-content` | Google Gemini Generate Content |

### `api_key_env`

The environment variable name NAVI reads for the API key. Convention is `<PROVIDER>_API_KEY`, but there are exceptions (e.g. `GITHUB_COPILOT_TOKEN`). Multi-region variants of the same provider reuse the same env var (e.g. the three `mimo-anthropic-*` files all use `MIMO_API_KEY`; `zai` and `zai-coding` both use `ZAI_API_KEY`).

### `base_url`

API base URL. The schema permits `null` for providers resolved at runtime, but **every current provider has a concrete `base_url`**. Don't omit it unless you have a runtime-resolution reason.

### `task_size` (model-level, required)

Only `"small"` or `"large"`. This is a **harness routing hint**, not a model-size description — NAVI uses it to pick which model handles which tasks. Large = flagship/heavy; small = fast/cheap.

### `tool_calling_mode`

Optional. One of `native`, `text-extracted`, `manifest-only`, `disabled`. Currently only `commandcode.json` sets it (`native`).

### Attachment metadata

Two layers with inheritance:
- `defaults.attachments` at provider level — inherited by all models
- `attachments` at model level — **overrides** only the specific keys that differ

Keys: `images`, `audio`, `video`, `documents` (all booleans). Prefer this over the legacy per-modality booleans (`supports_attachments`, `supports_images`, `supports_audio`, `supports_video`, `supports_documents`), which the schema keeps for backward compatibility but marks as legacy.

`documents: true` means the provider accepts documents as native attachments — it does **not** mean NAVI can extract local document text into the prompt.

### `request_options`

Free-form object for provider-specific request tweaks (e.g. Anthropic's `anthropic_cache_control`, OpenAI's `prompt_cache_key`/`prompt_cache_retention`). Several providers set it to `{}` explicitly.

### `pricing` (model-level)

Object with `input_per_1m`, `output_per_1m`, `cached_input_per_1m`, `cached_output_per_1m` (numbers, per 1M tokens) and `currency` (string, default `USD`). Currently **no provider populates `pricing`** — the field exists in the schema/validator but is unused. Same for `reasoning_levels`, `default_reasoning_effort`, `capabilities`, `default_large_model`, and `default_small_model`: defined and validated, but not yet used by any provider file. Don't assume these are populated when reading data.

## Formatting styles

Two coexisting styles in `providers/`:
- **Compact single-line models** — `{ "name": ..., "task_size": ..., "context_window_tokens": ... }` (used by `ollama`, `llamacpp`, `commandcode`)
- **Expanded multi-line models** — one field per line (used by most others: `anthropic`, `openai`, `openrouter`, `google-gemini`, `mistral`, etc.)

Match the style of nearby entries within the same file. There is no enforced formatter.

## Adding a new provider

1. Create `providers/<id>.json`. See `README.md` for a minimal example and `schemas/provider.schema.json` for the full field list.
2. Run `python scripts/validate.py`. It must exit 0 and print `OK` for your file.
3. Commit the new provider file **and** the regenerated `manifest.json`.

## What not to expect

- No test suite, no CI workflows, no linter, no Makefile.
- No `jsonschema` dependency despite the README — the validator is self-contained.
- No code that imports or executes the provider JSON; NAVI (a separate repo/binary) is the consumer.
