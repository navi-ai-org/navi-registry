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
3. Record the source URL and the exact value found.
4. If no primary source exists, search for the model name on the provider's `/models` API endpoint or community-verified sources (e.g. OpenRouter model pages).
5. If no source can be found after diligent search, proceed to State 2.

**Sources that are NOT acceptable:**
- Other registry repos (e.g. LiteLLM, OpenRouter's internal JSON) unless they cite a primary source
- AI-generated guesses or "common knowledge"
- Defaulting to a round number like 200000 because "it's probably fine"

#### State 2: `null_if_unknown`

If you could not find a verified value:

- Set the field to `null` (omit it from JSON — the schema allows missing optional fields).
- **Do NOT invent a value.** A missing field is always better than a wrong field.
- NAVI falls back to a conservative default at runtime when `context_window_tokens` is missing.

```json
// CORRECT — omit when unknown
{ "name": "mystery-model", "task_size": "small" }

// WRONG — invented value
{ "name": "mystery-model", "task_size": "small", "context_window_tokens": 200000 }
```

#### State 3: `populate`

Only fill in a field if you found a verified value from a primary source in State 1.

- `context_window_tokens`: exact integer from the provider's documentation (e.g. `128000`, `1048576`, `200000`). Never round or approximate.
- `max_output_tokens`: exact integer from the provider's documentation.
- `recommended_temperature`: from the provider's recommended value, not a guess.
- `supports_thinking`: `true` only if the provider explicitly documents reasoning/thinking support.
- `pricing`: from the provider's pricing page. Use `input_per_1m` and `output_per_1m` as exact numbers.
- `attachments`: `true` only if the provider's docs explicitly mention image/audio/video/document support.

#### State 4: `verify`

Before committing, run the validator:

```bash
python scripts/validate.py
```

The validator will **warn** (not error) if `context_window_tokens` is exactly `200000`. This is a flag for human review — it's not always wrong (some Claude models genuinely have 200k), but it's the most commonly invented value, so it gets extra scrutiny.

Review every warning. If the value is correct, the warning can be ignored. If the value was invented, fix it or remove it.

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

- [ ] `name` — exact model name as returned by the provider's `/models` API
- [ ] `task_size` — `"small"` for fast/cheap models, `"large"` for flagship/heavy (harness routing hint)
- [ ] `context_window_tokens` — verified from provider docs, or omitted if unknown
- [ ] `max_output_tokens` — verified from provider docs, or omitted if unknown
- [ ] `recommended_temperature` — verified from provider docs, or omitted if unknown
- [ ] `supports_thinking` — `true` only if provider docs mention reasoning/thinking
- [ ] `pricing` — verified from provider's pricing page, or omitted if unknown
- [ ] `attachments` — `true` only if provider docs mention the modality
- [ ] Validator passes with no unexpected warnings
- [ ] `manifest.json` regenerated via `python scripts/validate.py`

### Aggregator Providers (OpenRouter, charm-hyper)

Aggregator providers that expose a `/models` API endpoint get their model lists synced dynamically by NAVI at runtime. The JSON in this repo serves as the **fallback/base** set. For aggregator providers:

- Include only the most important models in the JSON (5-20 entries)
- Focus on models that need metadata the API doesn't return (e.g. pricing, attachment support)
- Models returned by the API at runtime are merged with these entries
- Do NOT try to list all 300+ OpenRouter models — NAVI fetches them dynamically
