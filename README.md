# NAVI Registry

A community-supported database of LLM inference providers and models for [NAVI](https://github.com/navi-ai-org/navi).

## How it works

NAVI ships with a snapshot of this registry embedded in its binary. On startup, NAVI checks if a newer version of the registry is available here and pulls it automatically — so you get new providers and models without upgrading NAVI itself.

```
Embedded snapshot (offline)  →  SQLite cache  →  Remote pull (this repo)
```

## Adding a provider

1. Create `providers/<your-provider>.json` (see `schemas/provider.schema.json` for the full schema).
2. Run `python scripts/validate.py` to validate and regenerate `manifest.json`.
3. Commit both files and open a pull request.

### Minimal example

```json
{
  "id": "my-provider",
  "label": "My Provider",
  "description": "Short description for the model picker",
  "kind": "openai-chat-completions",
  "api_key_env": "MY_PROVIDER_API_KEY",
  "base_url": "https://api.my-provider.com/v1",
  "models": [
    {
      "name": "my-model",
      "task_size": "large",
      "context_window_tokens": 128000
    }
  ]
}
```

### Supported `kind` values

| Kind | Protocol |
|---|---|
| `openai-responses` | OpenAI Responses API |
| `openai-chat-completions` | OpenAI Chat Completions (most providers) |
| `anthropic-messages` | Anthropic Messages API |
| `gemini-generate-content` | Google Gemini Generate Content |

## Attachment metadata

Use `attachments` to describe which attachment modalities a model accepts directly. Provider-level defaults keep large provider files compact, and model-level values override only the differences:

```json
{
  "defaults": {
    "attachments": {
      "images": false,
      "audio": false,
      "video": false,
      "documents": false
    }
  },
  "models": [
    {
      "name": "some-vision-model",
      "task_size": "large",
      "attachments": {
        "images": true
      }
    }
  ]
}
```

`documents: true` means the provider/model accepts documents as native attachments. It does not mean NAVI can extract local document text and paste it into the prompt.

## Validation

```bash
pip install jsonschema
python scripts/validate.py
```

This validates every provider file against the JSON Schema and regenerates `manifest.json` with correct SHA-256 hashes and model counts.

## License

[Apache-2.0](LICENSE)
