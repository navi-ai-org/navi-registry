# Registry Probe Report

## Summary
- Auto-filled attachments: **67**
- New models (not in registry): **355**
- Removed models (local only): **33**
- Needs manual review (probed): **30**
- Needs manual review (unprobed): **110**
- Default context window (200k, likely unset): **48**
- Errors: **7**

## Auto-filled Attachments

| Provider | Model | Fields |
|---|---|---|
| anthropic | claude-3-5-haiku-20241022 | images, documents |
| anthropic | claude-3-5-sonnet-20240620 | images, documents |
| anthropic | claude-3-5-sonnet-20241022 | images, documents |
| anthropic | claude-3-7-sonnet-20250219 | images, documents |
| anthropic | claude-3-haiku-20240307 | images, documents |
| anthropic | claude-3-opus-20240229 | images, documents |
| anthropic | claude-3-sonnet-20240229 | images, documents |
| anthropic | claude-3.5-haiku | images, documents |
| anthropic | claude-3.5-sonnet | images, documents |
| anthropic | claude-3.7-sonnet | images, documents |
| anthropic | claude-haiku-4 | images, documents |
| anthropic | claude-opus-4 | images, documents |
| anthropic | claude-opus-4-1-20250805 | images, documents |
| anthropic | claude-opus-4-20250514 | images, documents |
| anthropic | claude-sonnet-4 | images, documents |
| anthropic | claude-sonnet-4-20250514 | images, documents |
| charm-hyper | gpt-oss-120b | images |
| charm-hyper | gpt-oss-20b | images |
| commandcode | claude-fable-5 | images, documents |
| commandcode | claude-haiku-4-5-20251001 | images, documents |
| commandcode | claude-opus-4-7 | images, documents |
| commandcode | claude-opus-4-8 | images, documents |
| commandcode | claude-sonnet-4-6 | images, documents |
| commandcode | google/gemini-3.1-flash-lite | images, audio, video, documents |
| commandcode | google/gemini-3.5-flash | images, audio, video, documents |
| commandcode | gpt-5.3-codex | images, documents |
| commandcode | gpt-5.4 | images, documents |
| commandcode | gpt-5.4-mini | images, documents |
| commandcode | gpt-5.5 | images, documents |
| commandcode | xiaomi/mimo-v2.5 | images, audio, video |
| github-copilot | claude-haiku-4.5 | images, documents |
| github-copilot | claude-sonnet-4.5 | images, documents |
| github-copilot | gpt-5-mini | images, documents |
| github-copilot | gpt-5.1 | images, documents |
| github-copilot | gpt-5.1-codex | images |
| gitlawb | google/gemini-3.1-flash-lite-preview | images, audio, video, documents |
| gitlawb | mimo-v2.5 | images, audio, video |
| google-gemini | gemini-1.5-flash | images, audio, video, documents |
| google-gemini | gemini-1.5-pro | images, audio, video, documents |
| google-gemini | gemini-2.0-flash | images, audio, video, documents |
| google-gemini | gemini-2.0-flash-001 | images, audio, video, documents |
| google-gemini | gemini-2.0-flash-lite | images, audio, video, documents |
| google-gemini | gemini-2.5-flash | images, audio, video, documents |
| google-gemini | gemini-2.5-flash-lite | images, audio, video, documents |
| google-gemini | gemini-2.5-flash-preview-05-20 | images, audio, video, documents |
| google-gemini | gemini-2.5-pro | images, audio, video, documents |
| google-gemini | gemini-2.5-pro-preview-06-05 | images, audio, video, documents |
| groq | meta-llama/llama-guard-4-12b | images |
| mimo-anthropic-ams | mimo-v2.5 | images, audio, video |
| mimo-anthropic-cn | mimo-v2.5 | images, audio, video |
| mimo-anthropic-sgp | mimo-v2.5 | images, audio, video |
| opencode | claude-opus-4.5 | images, documents |
| opencode | claude-sonnet-4.5 | images, documents |
| opencode | gpt-5.1-codex | images |
| opencode | gpt-5.2 | images, documents |
| opencode | grok-build-0.1 | images |
| opencode | kimi-k2.5 | images |
| opencode | kimi-k2.6 | images |
| opencode | qwen3.6-plus | images, video |
| opencode-go | kimi-k2.5 | images |
| opencode-go | qwen3.6-plus | images, video |
| xai | grok-2-vision-1212 | images |
| xai | grok-3 | images |
| xai | grok-4 | images, documents |
| xai | grok-4.3 | images, documents |
| xai | grok-build-0.1 | images |
| xiaomi | mimo-v2.5 | images, audio, video |

## New Models (not in local registry)

- `groq/allam-2-7b`
- `groq/compound`
- `groq/compound-mini`
- `groq/gpt-oss-120b`
- `groq/gpt-oss-20b`
- `groq/gpt-oss-safeguard-20b`
- `groq/llama-4-scout-17b-16e-instruct`
- `groq/llama-prompt-guard-2-22m`
- `groq/llama-prompt-guard-2-86m`
- `groq/orpheus-arabic-saudi`
- `groq/orpheus-v1-english`
- `groq/qwen3-32b`
- `groq/qwen3.6-27b`
- `groq/whisper-large-v3`
- `groq/whisper-large-v3-turbo`
- `ollama/deepseek-v4-flash:cloud`
- `ollama/deepseek-v4-pro:cloud`
- `ollama/gemma4:31b-cloud`
- `ollama/glm-5.1:cloud`
- `ollama/glm-5.2:cloud`
- `ollama/glm-5:cloud`
- `ollama/gpt-oss:20b-cloud`
- `ollama/kimi-k2.5:cloud`
- `ollama/kimi-k2.7-code:cloud`
- `ollama/minimax-m2.7:cloud`
- `ollama/minimax-m3:cloud`
- `ollama/nemotron-3-super:cloud`
- `ollama/qwen3.5:397b-cloud`
- `ollama/rnj-1:8b-cloud`
- `openrouter/ai21/jamba-large-1.7`
- `openrouter/aion-labs/aion-1.0`
- `openrouter/aion-labs/aion-1.0-mini`
- `openrouter/aion-labs/aion-2.0`
- `openrouter/aion-labs/aion-rp-llama-3.1-8b`
- `openrouter/allenai/olmo-3-32b-think`
- `openrouter/amazon/nova-2-lite-v1`
- `openrouter/amazon/nova-lite-v1`
- `openrouter/amazon/nova-micro-v1`
- `openrouter/amazon/nova-premier-v1`
- `openrouter/amazon/nova-pro-v1`
- `openrouter/anthracite-org/magnum-v4-72b`
- `openrouter/anthropic/claude-3-haiku`
- `openrouter/anthropic/claude-fable-5`
- `openrouter/anthropic/claude-haiku-4.5`
- `openrouter/anthropic/claude-opus-4.1`
- `openrouter/anthropic/claude-opus-4.5`
- `openrouter/anthropic/claude-opus-4.6`
- `openrouter/anthropic/claude-opus-4.7`
- `openrouter/anthropic/claude-opus-4.7-fast`
- `openrouter/anthropic/claude-opus-4.8`
- `openrouter/anthropic/claude-opus-4.8-fast`
- `openrouter/anthropic/claude-sonnet-4.5`
- `openrouter/anthropic/claude-sonnet-4.6`
- `openrouter/anthropic/claude-sonnet-5`
- `openrouter/arcee-ai/coder-large`
- `openrouter/arcee-ai/trinity-large-thinking`
- `openrouter/arcee-ai/trinity-mini`
- `openrouter/arcee-ai/virtuoso-large`
- `openrouter/baidu/ernie-4.5-vl-424b-a47b`
- `openrouter/bytedance-seed/seed-1.6`
- `openrouter/bytedance-seed/seed-1.6-flash`
- `openrouter/bytedance-seed/seed-2.0-lite`
- `openrouter/bytedance-seed/seed-2.0-mini`
- `openrouter/bytedance/ui-tars-1.5-7b`
- `openrouter/cognitivecomputations/dolphin-mistral-24b-venice-edition:free`
- `openrouter/cohere/command-a`
- `openrouter/cohere/command-r-08-2024`
- `openrouter/cohere/command-r-plus-08-2024`
- `openrouter/cohere/command-r7b-12-2024`
- `openrouter/cohere/north-mini-code:free`
- `openrouter/deepcogito/cogito-v2.1-671b`
- `openrouter/deepseek/deepseek-chat-v3-0324`
- `openrouter/deepseek/deepseek-chat-v3.1`
- `openrouter/deepseek/deepseek-r1`
- `openrouter/deepseek/deepseek-r1-0528`
- `openrouter/deepseek/deepseek-r1-distill-llama-70b`
- `openrouter/deepseek/deepseek-v3.1-terminus`
- `openrouter/deepseek/deepseek-v3.2`
- `openrouter/deepseek/deepseek-v3.2-exp`
- `openrouter/deepseek/deepseek-v4-flash`
- `openrouter/google/gemini-2.5-flash-image`
- `openrouter/google/gemini-2.5-flash-lite`
- `openrouter/google/gemini-2.5-flash-lite-preview-09-2025`
- `openrouter/google/gemini-2.5-pro-preview`
- `openrouter/google/gemini-2.5-pro-preview-05-06`
- `openrouter/google/gemini-3-flash-preview`
- `openrouter/google/gemini-3-pro-image`
- `openrouter/google/gemini-3-pro-image-preview`
- `openrouter/google/gemini-3.1-flash-image`
- `openrouter/google/gemini-3.1-flash-image-preview`
- `openrouter/google/gemini-3.1-flash-lite`
- `openrouter/google/gemini-3.1-flash-lite-image`
- `openrouter/google/gemini-3.1-flash-lite-preview`
- `openrouter/google/gemini-3.1-pro-preview`
- `openrouter/google/gemini-3.1-pro-preview-customtools`
- `openrouter/google/gemini-3.5-flash`
- `openrouter/google/gemma-2-27b-it`
- `openrouter/google/gemma-3-12b-it`
- `openrouter/google/gemma-3-27b-it`
- `openrouter/google/gemma-3-4b-it`
- `openrouter/google/gemma-3n-e4b-it`
- `openrouter/google/gemma-4-26b-a4b-it`
- `openrouter/google/gemma-4-26b-a4b-it:free`
- `openrouter/google/gemma-4-31b-it`
- `openrouter/google/gemma-4-31b-it:free`
- `openrouter/google/lyria-3-clip-preview`
- `openrouter/google/lyria-3-pro-preview`
- `openrouter/gryphe/mythomax-l2-13b`
- `openrouter/ibm-granite/granite-4.0-h-micro`
- `openrouter/ibm-granite/granite-4.1-8b`
- `openrouter/inception/mercury-2`
- `openrouter/inclusionai/ling-2.6-1t`
- `openrouter/inclusionai/ling-2.6-flash`
- `openrouter/inclusionai/ring-2.6-1t`
- `openrouter/inflection/inflection-3-pi`
- `openrouter/inflection/inflection-3-productivity`
- `openrouter/kwaipilot/kat-coder-pro-v2`
- `openrouter/liquid/lfm-2-24b-a2b`
- `openrouter/liquid/lfm-2.5-1.2b-instruct:free`
- `openrouter/liquid/lfm-2.5-1.2b-thinking:free`
- `openrouter/mancer/weaver`
- `openrouter/meta-llama/llama-3-8b-instruct`
- `openrouter/meta-llama/llama-3.1-70b-instruct`
- `openrouter/meta-llama/llama-3.1-8b-instruct`
- `openrouter/meta-llama/llama-3.2-11b-vision-instruct`
- `openrouter/meta-llama/llama-3.2-1b-instruct`
- `openrouter/meta-llama/llama-3.2-3b-instruct`
- `openrouter/meta-llama/llama-3.2-3b-instruct:free`
- `openrouter/meta-llama/llama-3.3-70b-instruct`
- `openrouter/meta-llama/llama-3.3-70b-instruct:free`
- `openrouter/meta-llama/llama-guard-4-12b`
- `openrouter/microsoft/phi-4`
- `openrouter/microsoft/wizardlm-2-8x22b`
- `openrouter/minimax/minimax-01`
- `openrouter/minimax/minimax-m1`
- `openrouter/minimax/minimax-m2`
- `openrouter/minimax/minimax-m2-her`
- `openrouter/minimax/minimax-m2.1`
- `openrouter/minimax/minimax-m2.5`
- `openrouter/minimax/minimax-m2.7`
- `openrouter/minimax/minimax-m3`
- `openrouter/mistralai/codestral-2508`
- `openrouter/mistralai/devstral-2512`
- `openrouter/mistralai/ministral-14b-2512`
- `openrouter/mistralai/ministral-3b-2512`
- `openrouter/mistralai/ministral-8b-2512`
- `openrouter/mistralai/mistral-large-2407`
- `openrouter/mistralai/mistral-large-2512`
- `openrouter/mistralai/mistral-medium-3`
- `openrouter/mistralai/mistral-medium-3-5`
- `openrouter/mistralai/mistral-medium-3.1`
- `openrouter/mistralai/mistral-nemo`
- `openrouter/mistralai/mistral-saba`
- `openrouter/mistralai/mistral-small-24b-instruct-2501`
- `openrouter/mistralai/mistral-small-2603`
- `openrouter/mistralai/mistral-small-3.1-24b-instruct`
- `openrouter/mistralai/mistral-small-3.2-24b-instruct`
- `openrouter/mistralai/mixtral-8x22b-instruct`
- `openrouter/mistralai/voxtral-small-24b-2507`
- `openrouter/moonshotai/kimi-k2-0905`
- `openrouter/moonshotai/kimi-k2-thinking`
- `openrouter/moonshotai/kimi-k2.5`
- `openrouter/moonshotai/kimi-k2.6`
- `openrouter/moonshotai/kimi-k2.7-code`
- `openrouter/morph/morph-v3-fast`
- `openrouter/morph/morph-v3-large`
- `openrouter/nex-agi/nex-n2-mini`
- `openrouter/nex-agi/nex-n2-pro`
- `openrouter/nousresearch/hermes-3-llama-3.1-405b`
- `openrouter/nousresearch/hermes-3-llama-3.1-405b:free`
- `openrouter/nousresearch/hermes-3-llama-3.1-70b`
- `openrouter/nousresearch/hermes-4-405b`
- `openrouter/nousresearch/hermes-4-70b`
- `openrouter/nvidia/llama-3.3-nemotron-super-49b-v1.5`
- `openrouter/nvidia/nemotron-3-nano-30b-a3b`
- `openrouter/nvidia/nemotron-3-nano-30b-a3b:free`
- `openrouter/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free`
- `openrouter/nvidia/nemotron-3-super-120b-a12b`
- `openrouter/nvidia/nemotron-3-super-120b-a12b:free`
- `openrouter/nvidia/nemotron-3-ultra-550b-a55b`
- `openrouter/nvidia/nemotron-3-ultra-550b-a55b:free`
- `openrouter/nvidia/nemotron-3.5-content-safety:free`
- `openrouter/nvidia/nemotron-nano-12b-v2-vl:free`
- `openrouter/nvidia/nemotron-nano-9b-v2:free`
- `openrouter/openai/gpt-3.5-turbo`
- `openrouter/openai/gpt-3.5-turbo-0613`
- `openrouter/openai/gpt-3.5-turbo-16k`
- `openrouter/openai/gpt-3.5-turbo-instruct`
- `openrouter/openai/gpt-4`
- `openrouter/openai/gpt-4-turbo`
- `openrouter/openai/gpt-4-turbo-preview`
- `openrouter/openai/gpt-4.1-mini`
- `openrouter/openai/gpt-4.1-nano`
- `openrouter/openai/gpt-4o`
- `openrouter/openai/gpt-4o-2024-05-13`
- `openrouter/openai/gpt-4o-2024-08-06`
- `openrouter/openai/gpt-4o-2024-11-20`
- `openrouter/openai/gpt-4o-mini`
- `openrouter/openai/gpt-4o-mini-2024-07-18`
- `openrouter/openai/gpt-4o-mini-search-preview`
- `openrouter/openai/gpt-4o-search-preview`
- `openrouter/openai/gpt-5`
- `openrouter/openai/gpt-5-chat`
- `openrouter/openai/gpt-5-codex`
- `openrouter/openai/gpt-5-image`
- `openrouter/openai/gpt-5-image-mini`
- `openrouter/openai/gpt-5-mini`
- `openrouter/openai/gpt-5-nano`
- `openrouter/openai/gpt-5-pro`
- `openrouter/openai/gpt-5.1`
- `openrouter/openai/gpt-5.1-chat`
- `openrouter/openai/gpt-5.1-codex`
- `openrouter/openai/gpt-5.1-codex-max`
- `openrouter/openai/gpt-5.1-codex-mini`
- `openrouter/openai/gpt-5.2`
- `openrouter/openai/gpt-5.2-chat`
- `openrouter/openai/gpt-5.2-codex`
- `openrouter/openai/gpt-5.2-pro`
- `openrouter/openai/gpt-5.3-chat`
- `openrouter/openai/gpt-5.3-codex`
- `openrouter/openai/gpt-5.4-image-2`
- `openrouter/openai/gpt-5.4-mini`
- `openrouter/openai/gpt-5.4-nano`
- `openrouter/openai/gpt-5.4-pro`
- `openrouter/openai/gpt-5.5-pro`
- `openrouter/openai/gpt-audio`
- `openrouter/openai/gpt-audio-mini`
- `openrouter/openai/gpt-chat-latest`
- `openrouter/openai/gpt-oss-120b`
- `openrouter/openai/gpt-oss-120b:free`
- `openrouter/openai/gpt-oss-20b`
- `openrouter/openai/gpt-oss-20b:free`
- `openrouter/openai/gpt-oss-safeguard-20b`
- `openrouter/openai/o1`
- `openrouter/openai/o1-pro`
- `openrouter/openai/o3`
- `openrouter/openai/o3-deep-research`
- `openrouter/openai/o3-mini`
- `openrouter/openai/o3-mini-high`
- `openrouter/openai/o3-pro`
- `openrouter/openai/o4-mini`
- `openrouter/openai/o4-mini-deep-research`
- `openrouter/openai/o4-mini-high`
- `openrouter/openrouter/auto`
- `openrouter/openrouter/bodybuilder`
- `openrouter/openrouter/free`
- `openrouter/openrouter/fusion`
- `openrouter/openrouter/pareto-code`
- `openrouter/perceptron/perceptron-mk1`
- `openrouter/perplexity/sonar`
- `openrouter/perplexity/sonar-deep-research`
- `openrouter/perplexity/sonar-pro`
- `openrouter/perplexity/sonar-pro-search`
- `openrouter/perplexity/sonar-reasoning-pro`
- `openrouter/poolside/laguna-m.1`
- `openrouter/poolside/laguna-m.1:free`
- `openrouter/poolside/laguna-xs-2.1`
- `openrouter/poolside/laguna-xs-2.1:free`
- `openrouter/poolside/laguna-xs.2`
- `openrouter/poolside/laguna-xs.2:free`
- `openrouter/qwen/qwen-2.5-72b-instruct`
- `openrouter/qwen/qwen-2.5-7b-instruct`
- `openrouter/qwen/qwen-2.5-coder-32b-instruct`
- `openrouter/qwen/qwen-plus`
- `openrouter/qwen/qwen-plus-2025-07-28`
- `openrouter/qwen/qwen-plus-2025-07-28:thinking`
- `openrouter/qwen/qwen2.5-vl-72b-instruct`
- `openrouter/qwen/qwen3-14b`
- `openrouter/qwen/qwen3-235b-a22b-2507`
- `openrouter/qwen/qwen3-235b-a22b-thinking-2507`
- `openrouter/qwen/qwen3-30b-a3b`
- `openrouter/qwen/qwen3-30b-a3b-instruct-2507`
- `openrouter/qwen/qwen3-30b-a3b-thinking-2507`
- `openrouter/qwen/qwen3-8b`
- `openrouter/qwen/qwen3-coder-30b-a3b-instruct`
- `openrouter/qwen/qwen3-coder-flash`
- `openrouter/qwen/qwen3-coder-next`
- `openrouter/qwen/qwen3-coder-plus`
- `openrouter/qwen/qwen3-coder:free`
- `openrouter/qwen/qwen3-max`
- `openrouter/qwen/qwen3-max-thinking`
- `openrouter/qwen/qwen3-next-80b-a3b-instruct`
- `openrouter/qwen/qwen3-next-80b-a3b-instruct:free`
- `openrouter/qwen/qwen3-next-80b-a3b-thinking`
- `openrouter/qwen/qwen3-vl-235b-a22b-instruct`
- `openrouter/qwen/qwen3-vl-235b-a22b-thinking`
- `openrouter/qwen/qwen3-vl-30b-a3b-instruct`
- `openrouter/qwen/qwen3-vl-30b-a3b-thinking`
- `openrouter/qwen/qwen3-vl-32b-instruct`
- `openrouter/qwen/qwen3-vl-8b-instruct`
- `openrouter/qwen/qwen3-vl-8b-thinking`
- `openrouter/qwen/qwen3.5-122b-a10b`
- `openrouter/qwen/qwen3.5-27b`
- `openrouter/qwen/qwen3.5-35b-a3b`
- `openrouter/qwen/qwen3.5-397b-a17b`
- `openrouter/qwen/qwen3.5-9b`
- `openrouter/qwen/qwen3.5-flash-02-23`
- `openrouter/qwen/qwen3.5-plus-02-15`
- `openrouter/qwen/qwen3.5-plus-20260420`
- `openrouter/qwen/qwen3.6-27b`
- `openrouter/qwen/qwen3.6-35b-a3b`
- `openrouter/qwen/qwen3.6-flash`
- `openrouter/qwen/qwen3.6-max-preview`
- `openrouter/qwen/qwen3.6-plus`
- `openrouter/qwen/qwen3.7-max`
- `openrouter/qwen/qwen3.7-plus`
- `openrouter/rekaai/reka-edge`
- `openrouter/rekaai/reka-flash-3`
- `openrouter/relace/relace-apply-3`
- `openrouter/relace/relace-search`
- `openrouter/sakana/fugu-ultra`
- `openrouter/sao10k/l3-lunaris-8b`
- `openrouter/sao10k/l3.1-70b-hanami-x1`
- `openrouter/sao10k/l3.1-euryale-70b`
- `openrouter/sao10k/l3.3-euryale-70b`
- `openrouter/stepfun/step-3.5-flash`
- `openrouter/stepfun/step-3.7-flash`
- `openrouter/switchpoint/router`
- `openrouter/tencent/hunyuan-a13b-instruct`
- `openrouter/tencent/hy3`
- `openrouter/tencent/hy3-preview`
- `openrouter/tencent/hy3:free`
- `openrouter/thedrummer/cydonia-24b-v4.1`
- `openrouter/thedrummer/rocinante-12b`
- `openrouter/thedrummer/skyfall-36b-v2`
- `openrouter/thedrummer/unslopnemo-12b`
- `openrouter/undi95/remm-slerp-l2-13b`
- `openrouter/upstage/solar-pro-3`
- `openrouter/writer/palmyra-x5`
- `openrouter/x-ai/grok-4.20`
- `openrouter/x-ai/grok-4.20-multi-agent`
- `openrouter/x-ai/grok-4.3`
- `openrouter/x-ai/grok-build-0.1`
- `openrouter/xiaomi/mimo-v2.5`
- `openrouter/xiaomi/mimo-v2.5-pro`
- `openrouter/z-ai/glm-4.5-air`
- `openrouter/z-ai/glm-4.5v`
- `openrouter/z-ai/glm-4.6`
- `openrouter/z-ai/glm-4.6v`
- `openrouter/z-ai/glm-4.7`
- `openrouter/z-ai/glm-4.7-flash`
- `openrouter/z-ai/glm-5`
- `openrouter/z-ai/glm-5-turbo`
- `openrouter/z-ai/glm-5.1`
- `openrouter/z-ai/glm-5.2`
- `openrouter/z-ai/glm-5v-turbo`
- `openrouter/~anthropic/claude-fable-latest`
- `openrouter/~anthropic/claude-haiku-latest`
- `openrouter/~anthropic/claude-opus-latest`
- `openrouter/~anthropic/claude-sonnet-latest`
- `openrouter/~google/gemini-flash-latest`
- `openrouter/~google/gemini-pro-latest`
- `openrouter/~moonshotai/kimi-latest`
- `openrouter/~openai/gpt-latest`
- `openrouter/~openai/gpt-mini-latest`

## Removed Models (local only, may need pruning)

- `groq/deepseek-r1-distill-llama-70b`
- `groq/gemma2-9b-it`
- `groq/meta-llama/llama-4-maverick-17b-128e-instruct`
- `groq/meta-llama/llama-4-scout-17b-16e-instruct`
- `groq/meta-llama/llama-guard-4-12b`
- `groq/mistral-saba-24b`
- `groq/moonshotai/kimi-k2-instruct`
- `groq/openai/gpt-oss-120b`
- `groq/openai/gpt-oss-20b`
- `groq/qwen/qwen3-32b`
- `ollama/codellama`
- `ollama/deepseek-r1`
- `ollama/devstral`
- `ollama/gemma3`
- `ollama/gemma3:12b`
- `ollama/gemma3:27b`
- `ollama/granite-code`
- `ollama/llama3.1`
- `ollama/llama3.2`
- `ollama/llama3.3`
- `ollama/mistral`
- `ollama/phi4`
- `ollama/phi4-mini`
- `ollama/qwen2.5-coder`
- `ollama/qwen2.5-coder:14b`
- `ollama/qwen2.5-coder:32b`
- `ollama/qwen2.5-coder:7b`
- `ollama/qwen3`
- `ollama/starcoder2`
- `openrouter/meta-llama/llama-3.3-70b`
- `openrouter/mistralai/codestral`
- `openrouter/x-ai/grok-3`
- `openrouter/x-ai/grok-4`

## Needs Manual Review (probed providers, no attachment info)

- `groq/deepseek-r1-distill-llama-70b` — no attachment rule or OpenRouter data
- `groq/gemma2-9b-it` — no attachment rule or OpenRouter data
- `groq/llama-3.1-8b-instant` — no attachment rule or OpenRouter data
- `groq/llama-3.3-70b-versatile` — no attachment rule or OpenRouter data
- `groq/meta-llama/llama-4-maverick-17b-128e-instruct` — no attachment rule or OpenRouter data
- `groq/meta-llama/llama-4-scout-17b-16e-instruct` — no attachment rule or OpenRouter data
- `groq/mistral-saba-24b` — no attachment rule or OpenRouter data
- `groq/moonshotai/kimi-k2-instruct` — no attachment rule or OpenRouter data
- `groq/openai/gpt-oss-120b` — no attachment rule or OpenRouter data
- `groq/openai/gpt-oss-20b` — no attachment rule or OpenRouter data
- `groq/qwen/qwen3-32b` — no attachment rule or OpenRouter data
- `ollama/codellama` — no attachment rule or OpenRouter data
- `ollama/deepseek-r1` — no attachment rule or OpenRouter data
- `ollama/devstral` — no attachment rule or OpenRouter data
- `ollama/gemma3` — no attachment rule or OpenRouter data
- `ollama/gemma3:12b` — no attachment rule or OpenRouter data
- `ollama/gemma3:27b` — no attachment rule or OpenRouter data
- `ollama/granite-code` — no attachment rule or OpenRouter data
- `ollama/llama3.1` — no attachment rule or OpenRouter data
- `ollama/llama3.2` — no attachment rule or OpenRouter data
- `ollama/llama3.3` — no attachment rule or OpenRouter data
- `ollama/mistral` — no attachment rule or OpenRouter data
- `ollama/phi4` — no attachment rule or OpenRouter data
- `ollama/phi4-mini` — no attachment rule or OpenRouter data
- `ollama/qwen2.5-coder` — no attachment rule or OpenRouter data
- `ollama/qwen2.5-coder:14b` — no attachment rule or OpenRouter data
- `ollama/qwen2.5-coder:32b` — no attachment rule or OpenRouter data
- `ollama/qwen2.5-coder:7b` — no attachment rule or OpenRouter data
- `ollama/qwen3` — no attachment rule or OpenRouter data
- `ollama/starcoder2` — no attachment rule or OpenRouter data

## Needs Manual Review (unprobed providers, no attachment info)

- `charm-hyper/DeepSeek V4 Flash` — no attachment rule or OpenRouter data — needs manual review
- `charm-hyper/DeepSeek V4 Pro` — no attachment rule or OpenRouter data — needs manual review
- `charm-hyper/GLM-5` — no attachment rule or OpenRouter data — needs manual review
- `charm-hyper/GLM-5.1` — no attachment rule or OpenRouter data — needs manual review
- `charm-hyper/Gemma 4 26B A4B` — no attachment rule or OpenRouter data — needs manual review
- `charm-hyper/Kimi K2.5` — no attachment rule or OpenRouter data — needs manual review
- `charm-hyper/Kimi K2.6` — no attachment rule or OpenRouter data — needs manual review
- `charm-hyper/MiniMax M2.1` — no attachment rule or OpenRouter data — needs manual review
- `charm-hyper/Qwen 3 32B` — no attachment rule or OpenRouter data — needs manual review
- `commandcode/MiniMaxAI/MiniMax-M2.5` — no attachment rule or OpenRouter data — needs manual review
- `commandcode/MiniMaxAI/MiniMax-M2.7` — no attachment rule or OpenRouter data — needs manual review
- `commandcode/MiniMaxAI/MiniMax-M3` — no attachment rule or OpenRouter data — needs manual review
- `commandcode/Qwen/Qwen3.6-Max-Preview` — no attachment rule or OpenRouter data — needs manual review
- `commandcode/Qwen/Qwen3.6-Plus` — no attachment rule or OpenRouter data — needs manual review
- `commandcode/Qwen/Qwen3.7-Max` — no attachment rule or OpenRouter data — needs manual review
- `commandcode/Qwen/Qwen3.7-Plus` — no attachment rule or OpenRouter data — needs manual review
- `commandcode/deepseek/deepseek-v4-flash` — no attachment rule or OpenRouter data — needs manual review
- `commandcode/deepseek/deepseek-v4-pro` — no attachment rule or OpenRouter data — needs manual review
- `commandcode/moonshotai/Kimi-K2.5` — no attachment rule or OpenRouter data — needs manual review
- `commandcode/moonshotai/Kimi-K2.6` — no attachment rule or OpenRouter data — needs manual review
- `commandcode/moonshotai/Kimi-K2.7-Code` — no attachment rule or OpenRouter data — needs manual review
- `commandcode/nvidia/nemotron-3-ultra-550b-a55b` — no attachment rule or OpenRouter data — needs manual review
- `commandcode/stepfun/Step-3.5-Flash` — no attachment rule or OpenRouter data — needs manual review
- `commandcode/stepfun/Step-3.7-Flash` — no attachment rule or OpenRouter data — needs manual review
- `commandcode/xiaomi/mimo-v2.5-pro` — no attachment rule or OpenRouter data — needs manual review
- `commandcode/zai-org/GLM-5` — no attachment rule or OpenRouter data — needs manual review
- `commandcode/zai-org/GLM-5.1` — no attachment rule or OpenRouter data — needs manual review
- `gitlawb/mimo-v2.5-pro` — no attachment rule or OpenRouter data — needs manual review
- `google-gemini/gemini-1.5-flash-002` — no attachment rule or OpenRouter data — needs manual review
- `google-gemini/gemini-1.5-flash-8b` — no attachment rule or OpenRouter data — needs manual review
- `google-gemini/gemini-1.5-pro-002` — no attachment rule or OpenRouter data — needs manual review
- `mimo-anthropic-ams/mimo-v2-flash` — no attachment rule or OpenRouter data — needs manual review
- `mimo-anthropic-ams/mimo-v2-omni` — no attachment rule or OpenRouter data — needs manual review
- `mimo-anthropic-ams/mimo-v2-pro` — no attachment rule or OpenRouter data — needs manual review
- `mimo-anthropic-ams/mimo-v2.5-pro` — no attachment rule or OpenRouter data — needs manual review
- `mimo-anthropic-cn/mimo-v2-flash` — no attachment rule or OpenRouter data — needs manual review
- `mimo-anthropic-cn/mimo-v2-omni` — no attachment rule or OpenRouter data — needs manual review
- `mimo-anthropic-cn/mimo-v2-pro` — no attachment rule or OpenRouter data — needs manual review
- `mimo-anthropic-cn/mimo-v2.5-pro` — no attachment rule or OpenRouter data — needs manual review
- `mimo-anthropic-sgp/mimo-v2-flash` — no attachment rule or OpenRouter data — needs manual review
- `mimo-anthropic-sgp/mimo-v2-omni` — no attachment rule or OpenRouter data — needs manual review
- `mimo-anthropic-sgp/mimo-v2-pro` — no attachment rule or OpenRouter data — needs manual review
- `mimo-anthropic-sgp/mimo-v2.5-pro` — no attachment rule or OpenRouter data — needs manual review
- `minimax/MiniMax-M2` — no attachment rule or OpenRouter data — needs manual review
- `minimax/MiniMax-M2.1` — no attachment rule or OpenRouter data — needs manual review
- `minimax/MiniMax-M2.1-highspeed` — no attachment rule or OpenRouter data — needs manual review
- `minimax/MiniMax-M2.5` — no attachment rule or OpenRouter data — needs manual review
- `minimax/MiniMax-M2.5-highspeed` — no attachment rule or OpenRouter data — needs manual review
- `minimax/MiniMax-M2.7` — no attachment rule or OpenRouter data — needs manual review
- `minimax/MiniMax-M2.7-highspeed` — no attachment rule or OpenRouter data — needs manual review
- `minimax/MiniMax-M3` — no attachment rule or OpenRouter data — needs manual review
- `minimax/MiniMax-Text-01` — no attachment rule or OpenRouter data — needs manual review
- `minimax/MiniMax-Text-01-456B` — no attachment rule or OpenRouter data — needs manual review
- `minimax/abab6.5-chat` — no attachment rule or OpenRouter data — needs manual review
- `minimax/abab6.5g-chat` — no attachment rule or OpenRouter data — needs manual review
- `minimax/abab6.5s-chat` — no attachment rule or OpenRouter data — needs manual review
- `minimax/abab6.5t-chat` — no attachment rule or OpenRouter data — needs manual review
- `opencode/big-pickle` — no attachment rule or OpenRouter data — needs manual review
- `opencode/deepseek-v4-flash-free` — no attachment rule or OpenRouter data — needs manual review
- `opencode/gemini-3-pro` — no attachment rule or OpenRouter data — needs manual review
- `opencode/glm-5` — no attachment rule or OpenRouter data — needs manual review
- `opencode/glm-5.1` — no attachment rule or OpenRouter data — needs manual review
- `opencode/minimax-m2.1` — no attachment rule or OpenRouter data — needs manual review
- `opencode/minimax-m2.5` — no attachment rule or OpenRouter data — needs manual review
- `opencode/minimax-m2.7` — no attachment rule or OpenRouter data — needs manual review
- `opencode/nemotron-3-super-free` — no attachment rule or OpenRouter data — needs manual review
- `opencode/qwen3.5-plus` — no attachment rule or OpenRouter data — needs manual review
- `opencode-go/deepseek-v4-flash` — no attachment rule or OpenRouter data — needs manual review
- `opencode-go/deepseek-v4-pro` — no attachment rule or OpenRouter data — needs manual review
- `opencode-go/glm-5` — no attachment rule or OpenRouter data — needs manual review
- `opencode-go/minimax-m2.5` — no attachment rule or OpenRouter data — needs manual review
- `stepfun/step-1` — no attachment rule or OpenRouter data — needs manual review
- `stepfun/step-1-128k` — no attachment rule or OpenRouter data — needs manual review
- `stepfun/step-1-256k` — no attachment rule or OpenRouter data — needs manual review
- `stepfun/step-1-32k` — no attachment rule or OpenRouter data — needs manual review
- `stepfun/step-1-8k` — no attachment rule or OpenRouter data — needs manual review
- `stepfun/step-1v` — no attachment rule or OpenRouter data — needs manual review
- `stepfun/step-2` — no attachment rule or OpenRouter data — needs manual review
- `stepfun/step-2-16k` — no attachment rule or OpenRouter data — needs manual review
- `stepfun/step-3` — no attachment rule or OpenRouter data — needs manual review
- `stepfun/step-3.5-flash` — no attachment rule or OpenRouter data — needs manual review
- `xai/grok-2-1212` — no attachment rule or OpenRouter data — needs manual review
- `xai/grok-3-fast` — no attachment rule or OpenRouter data — needs manual review
- `xai/grok-3-mini` — no attachment rule or OpenRouter data — needs manual review
- `xai/grok-3-mini-fast` — no attachment rule or OpenRouter data — needs manual review
- `xai/grok-4-fast` — no attachment rule or OpenRouter data — needs manual review
- `xai/grok-4-fast-non-reasoning` — no attachment rule or OpenRouter data — needs manual review
- `xai/grok-4-fast-reasoning` — no attachment rule or OpenRouter data — needs manual review
- `xiaomi/mimo-v2-flash` — no attachment rule or OpenRouter data — needs manual review
- `xiaomi/mimo-v2-omni` — no attachment rule or OpenRouter data — needs manual review
- `xiaomi/mimo-v2-pro` — no attachment rule or OpenRouter data — needs manual review
- `xiaomi/mimo-v2.5-pro` — no attachment rule or OpenRouter data — needs manual review
- `zai/glm-4-0520` — no attachment rule or OpenRouter data — needs manual review
- `zai/glm-4-air` — no attachment rule or OpenRouter data — needs manual review
- `zai/glm-4-airx` — no attachment rule or OpenRouter data — needs manual review
- `zai/glm-4-flash` — no attachment rule or OpenRouter data — needs manual review
- `zai/glm-4-long` — no attachment rule or OpenRouter data — needs manual review
- `zai/glm-4-plus` — no attachment rule or OpenRouter data — needs manual review
- `zai/glm-4.5` — no attachment rule or OpenRouter data — needs manual review
- `zai/glm-4.5-air` — no attachment rule or OpenRouter data — needs manual review
- `zai/glm-4.5-flash` — no attachment rule or OpenRouter data — needs manual review
- `zai/glm-4.5-x` — no attachment rule or OpenRouter data — needs manual review
- `zai/glm-4.6` — no attachment rule or OpenRouter data — needs manual review
- `zai/glm-4.7` — no attachment rule or OpenRouter data — needs manual review
- `zai/glm-5` — no attachment rule or OpenRouter data — needs manual review
- `zai/glm-5-turbo` — no attachment rule or OpenRouter data — needs manual review
- `zai/glm-5.1` — no attachment rule or OpenRouter data — needs manual review
- `zai-coding/glm-5` — no attachment rule or OpenRouter data — needs manual review
- `zai-coding/glm-5-turbo` — no attachment rule or OpenRouter data — needs manual review
- `zai-coding/glm-5.1` — no attachment rule or OpenRouter data — needs manual review

## Default Context Window (200k — likely unset)

- `anthropic/claude-3-5-haiku-20241022` — context_window_tokens=200000
- `anthropic/claude-3-5-sonnet-20240620` — context_window_tokens=200000
- `anthropic/claude-3-5-sonnet-20241022` — context_window_tokens=200000
- `anthropic/claude-3-7-sonnet-20250219` — context_window_tokens=200000
- `anthropic/claude-3-haiku-20240307` — context_window_tokens=200000
- `anthropic/claude-3-opus-20240229` — context_window_tokens=200000
- `anthropic/claude-3-sonnet-20240229` — context_window_tokens=200000
- `anthropic/claude-3.5-haiku` — context_window_tokens=200000
- `anthropic/claude-3.5-sonnet` — context_window_tokens=200000
- `anthropic/claude-3.7-sonnet` — context_window_tokens=200000
- `anthropic/claude-haiku-4` — context_window_tokens=200000
- `anthropic/claude-opus-4` — context_window_tokens=200000
- `anthropic/claude-opus-4-1-20250805` — context_window_tokens=200000
- `anthropic/claude-opus-4-20250514` — context_window_tokens=200000
- `anthropic/claude-sonnet-4` — context_window_tokens=200000
- `anthropic/claude-sonnet-4-20250514` — context_window_tokens=200000
- `charm-hyper/GLM-5` — context_window_tokens=200000
- `charm-hyper/GLM-5.1` — context_window_tokens=200000
- `commandcode/MiniMaxAI/MiniMax-M2.5` — context_window_tokens=200000
- `commandcode/MiniMaxAI/MiniMax-M2.7` — context_window_tokens=200000
- `commandcode/Qwen/Qwen3.6-Max-Preview` — context_window_tokens=200000
- `commandcode/Qwen/Qwen3.6-Plus` — context_window_tokens=200000
- `commandcode/claude-haiku-4-5-20251001` — context_window_tokens=200000
- `commandcode/gpt-5.5` — context_window_tokens=200000
- `commandcode/zai-org/GLM-5` — context_window_tokens=200000
- `commandcode/zai-org/GLM-5.1` — context_window_tokens=200000
- `github-copilot/claude-haiku-4.5` — context_window_tokens=200000
- `github-copilot/claude-sonnet-4.5` — context_window_tokens=200000
- `github-copilot/gpt-5-mini` — context_window_tokens=200000
- `github-copilot/gpt-5.1` — context_window_tokens=200000
- `github-copilot/gpt-5.1-codex` — context_window_tokens=200000
- `minimax/abab6.5-chat` — context_window_tokens=200000
- `minimax/abab6.5g-chat` — context_window_tokens=200000
- `minimax/abab6.5s-chat` — context_window_tokens=200000
- `minimax/abab6.5t-chat` — context_window_tokens=200000
- `opencode/big-pickle` — context_window_tokens=200000
- `opencode/claude-opus-4.5` — context_window_tokens=200000
- `opencode/claude-sonnet-4.5` — context_window_tokens=200000
- `opencode/glm-5` — context_window_tokens=200000
- `opencode/glm-5.1` — context_window_tokens=200000
- `zai/glm-4.6` — context_window_tokens=200000
- `zai/glm-4.7` — context_window_tokens=200000
- `zai/glm-5` — context_window_tokens=200000
- `zai/glm-5-turbo` — context_window_tokens=200000
- `zai/glm-5.1` — context_window_tokens=200000
- `zai-coding/glm-5` — context_window_tokens=200000
- `zai-coding/glm-5-turbo` — context_window_tokens=200000
- `zai-coding/glm-5.1` — context_window_tokens=200000

## Errors

- `deepseek`: no API key in env $DEEPSEEK_API_KEY, skipping remote probe
- `llamacpp`: local server not running, skipping
- `lmstudio`: local server not running, skipping
- `mistral`: no API key in env $MISTRAL_API_KEY, skipping remote probe
- `moonshot`: no API key in env $MOONSHOT_API_KEY, skipping remote probe
- `nvidia`: no API key in env $NVIDIA_API_KEY, skipping remote probe
- `openai`: no API key in env $OPENAI_API_KEY, skipping remote probe
