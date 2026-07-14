# AGENTS.md

Guide for agents working in the NAVI Registry repository.

## What this repo is

A **data registry**, not a software project. It holds JSON definitions of LLM inference providers/models consumed by [NAVI](https://github.com/navi-ai-org/navi). NAVI embeds a snapshot at build time and pulls this repo at runtime for updates. There is no application runtime code — only data files, JSON Schemas, pure-Python tooling, and CI workflows.

## Repository layout

```
models/*.json                                 Canonical model catalog (capabilities once)
providers/*.json                              Thin providers: ref + pricing/overrides
bases/*.json                                  Shared base catalogs for extends
transcription-providers/*.json                Remote STT / dictation providers
schemas/model.schema.json                     JSON Schema for canonical models
schemas/provider.schema.json                  JSON Schema for LLM providers (ref or legacy)
schemas/transcription-provider.schema.json    JSON Schema for STT providers
scripts/validate.py                           Validator + ref flatten + manifest generator
scripts/probe.py                              API probe + metadata auto-fill (ref-aware)
scripts/build_model_catalog.py                Build/rebuild models/ and rewrite providers to refs
scripts/model_rules.json                      Attachment/metadata rules for probe
scripts/migrate_attachments.py                One-shot legacy → modern attachments migrator
manifest.json                                 AUTO-GENERATED index — never hand-edit
probe_report.md                               Last probe report (also uploaded as CI artifact)
.github/workflows/validate.yml                PR/push validation
.github/workflows/probe.yml                   Daily probe → PR + review issue
README.md                                     User-facing docs
```

## Essential command

```bash
python scripts/validate.py
```

This script validates every provider (after resolving `extends`), prints coverage stats, and regenerates `manifest.json`. Run it after any provider change and commit the regenerated `manifest.json` together with the provider edits.

No dependency installation is needed (`validate.py` is pure Python and loads field sets from the schema files).

## Canonical models (`models/`) + provider `ref`

**This is the primary data model.** Intrinsic model metadata lives under `models/<id>.json`. Providers list:

```json
{ "ref": "gpt-5.4", "pricing": { "input_per_1m": 2.5, "output_per_1m": 15.0, "currency": "USD" } }
```

Optional provider fields: `api_name` (if API id ≠ ref), plus overrides for context/max_output/status when the *endpoint* differs from the canonical model.

`validate.py` merges `models/<ref>.json` + overrides into a resolved entry with `name` for NAVI compatibility.

Rules:
- **Never invent** `context_window_tokens` on the canonical model.
- **Pricing is provider-level** (gateways differ).
- Prefer official vendor values when building the catalog (`scripts/build_model_catalog.py`).
- Aggregators (opencode, openrouter, commandcode, …) should almost always only set `ref` + `pricing` (+ `api_name`).
- Legacy inline `{ "name": ... }` still validates but new work must use `ref`.


## Critical gotchas

### 1. Schema is the structural source of truth

`scripts/validate.py` **loads** `schemas/*.schema.json` for known keys, required fields, and enums. Domain rules (200k suspicion, inheritance flattening, coverage) live only in the validator. When adding a new field:

1. Update the schema first.
2. Re-run `python scripts/validate.py` — key sets are derived automatically.
3. Add any extra type/domain checks in the validator if needed.

### 2. `manifest.json` is auto-generated

Never edit `manifest.json` by hand. `validate.py` rewrites it with:
- SHA-256 of each provider file's raw bytes
- Per-provider `model_count` and optional `extends`
- A top-level `coverage` health summary
- A `version` integer that **auto-bumps** when provider entries change and is **preserved** when they don't
- An `updated_at` timestamp that is similarly preserved on no-op runs

Providers are sorted alphabetically by `id` in the output.

### 3. Duplicate provider IDs are rejected

The validator fails on duplicate `id` values across files. The filename does not have to equal the `id`, but the manifest references `providers/<filename>`, so in practice every file is named `<id>.json`.

### 4. Prefer modern `attachments`

Use `defaults.attachments` / model `attachments`. Legacy `supports_images` etc. still parse for compatibility but emit warnings when used without a modern `attachments` object. Probe writes modern attachments only.

## Provider file conventions

### Required fields

`id`, `label`, `kind`, `api_key_env` are required. `models` is required on the **flattened** document (after `extends` resolution). Each models[] item should be `{ "ref": "..." }` (preferred) or a legacy inline model. Raw files that set `extends` may omit `models` if the base supplies them.

### `id`

Must match `^[a-z0-9][a-z0-9-]*$` — lowercase, hyphen-separated, alphanumeric. Filename should match the id.

### `extends`

Optional string pointing at a base id under `bases/` (or another provider id). Deep-merged with the child overlay; lists are replaced, not concatenated. Example: `mimo-anthropic-{ams,cn,sgp}` extend `bases/mimo-anthropic.json`.

### `kind` (protocol)

One of exactly four values for **LLM** providers:
| Kind | Protocol |
|---|---|
| `openai-responses` | OpenAI Responses API |
| `openai-chat-completions` | OpenAI Chat Completions (most providers) |
| `anthropic-messages` | Anthropic Messages API |
| `gemini-generate-content` | Google Gemini Generate Content |

**Transcription / dictation** providers live under `transcription-providers/` with their own kinds:
| Kind | Protocol |
|---|---|
| `openai-audio-transcriptions` | OpenAI-compatible `POST /audio/transcriptions` (OpenAI Whisper, Groq Whisper) |
| `wispr-flow` | Wispr Flow `POST /api` (base64 WAV) |

Required STT fields: `id`, `label`, `kind`, `api_key_env`, `base_url`, and `models` after flatten. Optional: `transcription_path`, `default_model`, `supports_streaming`, model `pricing.per_minute`.

### `api_key_env`

The environment variable name NAVI reads for the API key. Convention is `<PROVIDER>_API_KEY`, but there are exceptions (e.g. `GITHUB_COPILOT_TOKEN`). Multi-region variants of the same provider reuse the same env var (e.g. the three `mimo-anthropic-*` files all use `MIMO_API_KEY`; `zai` and `zai-coding` both use `ZAI_API_KEY`).

### `base_url`

API base URL. The schema permits `null` for providers resolved at runtime, but **every current provider has a concrete `base_url`**. Don't omit it unless you have a runtime-resolution reason.

### `tool_calling_mode`

Optional. One of `native`, `text-extracted`, `manifest-only`, `disabled`. Currently only `commandcode.json` sets it (`native`).

### Attachment metadata

Two layers with inheritance:
- `defaults.attachments` at provider level — inherited by all models
- `attachments` at model level — **overrides** only the specific keys that differ

Keys: `images`, `audio`, `video`, `documents` (all booleans). Prefer this over the legacy per-modality booleans (`supports_attachments`, `supports_images`, `supports_audio`, `supports_video`, `supports_documents`), which the schema keeps for backward compatibility but marks as legacy.

`documents: true` means the provider accepts documents as native attachments — it does **not** mean NAVI can extract local document text into the prompt.

### `sources` (provenance)

Optional map on each model: field name → `{ "url", "verified_at"?, "note"? }`. Prefer recording sources for `context_window_tokens`, `pricing`, and `attachments`. When `context_window_tokens` is exactly `200000` and a source is present, the suspicion warning is suppressed.

### `status` (lifecycle)

Optional model field: `active` (default if omitted), `deprecated`, `removed`, `preview`. Probe `--apply` may set `status: removed` for models that disappeared from a provider `/models` API.

### `request_options`

Free-form object for provider-specific request tweaks (e.g. Anthropic's `anthropic_cache_control`, OpenAI's `prompt_cache_key`/`prompt_cache_retention`). Several providers set it to `{}` explicitly.

### `pricing` (model-level)

Object with `input_per_1m`, `output_per_1m`, `cached_input_per_1m`, `cached_output_per_1m` (numbers, per 1M tokens) and `currency` (string, default `USD`). Many models already include pricing; coverage is tracked in `manifest.json` → `coverage.models_with_pricing`. Optional fields like `reasoning_levels`, `default_reasoning_effort`, `capabilities`, `default_large_model`, and `default_small_model` are validated when present but still sparsely used.

## Formatting styles

Two coexisting styles in `providers/`:
- **Compact single-line models** — `{ "name": ..., "context_window_tokens": ... }` (used by some local providers)
- **Expanded multi-line models** — one field per line (used by most others)

Match the style of nearby entries within the same file. There is no enforced formatter. Note: `migrate_attachments.py` and `probe.py --apply` rewrite files with `json.dump(indent=2)`.

## Adding a new provider

1. Create `providers/<id>.json`. See `README.md` for a minimal example and `schemas/provider.schema.json` for the full field list.
2. Run `python scripts/validate.py`. It must exit 0 and print `OK` for your file.
3. Commit the new provider file **and** the regenerated `manifest.json`.

## CI

- `validate.yml` — runs on every PR/push; fails if validation fails or `manifest.json` is stale.
- `probe.yml` — daily schedule; runs probe `--apply`, opens/updates a PR on `chore/probe-auto-update`, and creates/updates a `registry-needs-review` issue (body refreshed each run). Probe report is also uploaded as an artifact.

## What not to expect

- No application test suite / linter / Makefile.
- No `jsonschema` pip dependency — the validator is self-contained and schema-driven.
- No code that imports or executes the provider JSON; NAVI (a separate repo/binary) is the consumer.

## Model Data Integrity Rules

**This section is mandatory.** Any agent adding or editing model entries MUST follow these rules. The validator (`scripts/validate.py`) enforces some of them at runtime.

### The Problem

Agents have been inventing `context_window_tokens` values — typically defaulting to `200000` when they don't know the real value. This is **forbidden**. An incorrect context window misleads users and the NAVI harness into thinking a model has more or less capacity than it actually does.

### State Machine for Model Metadata

Every model entry MUST go through this pipeline before it can be committed. No skipping steps.

#### State 1: `research`

For each model field that should have a value (`context_window_tokens`, `max_output_tokens`, `recommended_temperature`, `supports_thinking`, `pricing`, attachment capabilities):

1. **Search the web** for the official provider documentation, model card, or API docs.
2. Find the exact value from a **primary source** (the provider's own website, HuggingFace model card, or official API docs).
3. Record the source URL and the exact value found — prefer writing it into `sources.<field>`.
4. If no primary source exists, search for the model name on the provider's `/models` API endpoint or community-verified sources (e.g. OpenRouter model pages).
5. If no source can be found after diligent search, proceed to State 2.

**Sources that are NOT acceptable:**
- Other registry repos (e.g. LiteLLM) unless they cite a primary source
- AI-generated guesses or "common knowledge"
- Defaulting to a round number like 200000 because "it's probably fine"

#### State 2: `null_if_unknown`

If you could not find a verified value:

- Set the field to `null` (omit it from JSON — the schema allows missing optional fields).
- **Do NOT invent a value.** A missing field is always better than a wrong field.
- NAVI falls back to a conservative default at runtime when `context_window_tokens` is missing.

```json
// CORRECT — omit when unknown
{ "name": "mystery-model" }

// WRONG — invented value
{ "name": "mystery-model", "context_window_tokens": 200000 }
```

#### State 3: `populate`

Only fill in a field if you found a verified value from a primary source in State 1.

- `context_window_tokens`: exact integer from the provider's documentation (e.g. `128000`, `1048576`, `200000`). Never round or approximate.
- `max_output_tokens`: exact integer from the provider's documentation.
- `recommended_temperature`: from the provider's recommended value, not a guess.
- `supports_thinking`: `true` only if the provider explicitly documents reasoning/thinking support.
- `pricing`: from the provider's pricing page. Use `input_per_1m` and `output_per_1m` as exact numbers.
- `attachments`: set modality booleans only if the provider's docs explicitly mention image/audio/video/document support.
- `sources`: record the URL (and ideally `verified_at`) for critical fields.

#### State 4: `verify`

Before committing, run the validator:

```bash
python scripts/validate.py
```

The validator will **warn** (not error) if `context_window_tokens` is exactly `200000` and there is no `sources.context_window_tokens` (and the model is not on the known-good allowlist). This is a flag for human review — it's not always wrong (some Claude models genuinely have 200k), but it's the most commonly invented value, so it gets extra scrutiny.

Review every warning. If the value is correct, add a source entry. If the value was invented, fix it or remove it.

### Forbidden Practices

| Practice | Why it's wrong |
|---|---|
| Defaulting `context_window_tokens` to `200000` | 200000 is not a universal default — it's Claude's context window. Other models have wildly different values. |
| Copying values from a different model | Each model has its own context window. Even models in the same family can differ. |
| Using "common knowledge" without a source | "Common knowledge" is often wrong or outdated. Always verify. |
| Rounding approximate values | `128K` should be `128000`, not `131072` (which is 128 KiB). Use the exact number the provider documents. |
| Filling all optional fields just because they exist | Empty is better than wrong. Only fill what you can verify. |

### Checklist for Adding or Updating a Model

Before committing a model entry, verify each item:

- [ ] Canonical entry in `models/<id>.json` (or reuse existing)
- [ ] Provider row uses `{ "ref": "<id>" }` (+ `api_name` if needed)
- [ ] `context_window_tokens` on canonical — verified, or omitted if unknown
- [ ] `sources.context_window_tokens` — present when context is set (recommended)
- [ ] `max_output_tokens` / `supports_thinking` / `attachments` on canonical when verified
- [ ] `pricing` on the **provider** row, not the canonical model
- [ ] `status` — set if not active (deprecated/removed/preview)
- [ ] Validator passes with no unexpected warnings
- [ ] `manifest.json` regenerated via `python scripts/validate.py`

### Aggregator Providers (OpenRouter, charm-hyper)

Aggregator providers that expose a `/models` API endpoint get their model lists synced dynamically by NAVI at runtime. The JSON in this repo serves as the **fallback/base** set. For aggregator providers:

- Include only the most important models in the JSON (5-20 entries)
- Focus on models that need metadata the API doesn't return (e.g. pricing, attachment support)
- Models returned by the API at runtime are merged with these entries
- Do NOT try to list all 300+ OpenRouter models — NAVI fetches them dynamically
