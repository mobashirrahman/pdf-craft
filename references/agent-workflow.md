# Agent workflow operations

Reconfigured 2026-09-08. Policy lives in AGENTS.md. Claude Code roles live in
.claude/agents/; OpenCode roles live in .opencode/agents/. This is a
coordinator-driven workflow, not an unattended scheduler.

## Roles and cost basis

| Role | Surface | Model | Cost |
| --- | --- | --- | --- |
| coordinator | Claude Code | Sonnet 5 | plan allowance, largest share |
| architect | Claude Code subagent | Opus 5 | plan allowance, one shot |
| reviewer | Claude Code subagent | Sonnet 5 | plan allowance, one shot |
| coder | OpenCode `muse-coder` | muse-spark-1.3-contributor-free | free |
| coder (parallel backend) | OpenCode `glm-coder` | tokenrouter/z-ai/glm-5.3-free | free |
| coder (parallel backend) | OpenCode `orca-coder` | orcarouter/z-ai/glm-5.3-flash-free | free |
| coder (parallel backend) | OpenCode `nemo-coder` | opencode/nemotron-3-ultra-free | free, Zen login, limited time |
| coder (parallel backend) | OpenCode `mimo-coder` | opencode/mimo-v2.5-free | free, Zen login, limited time |
| coder (parallel backend) | OpenCode `gem-coder` | google/gemini-3.5-flash | free tier |
| coder (parallel backend) | OpenCode `groq-coder` | groq/openai/gpt-oss-120b | free developer tier |
| coder (parallel backend) | OpenCode `zai-coder` | zai/glm-4.5-flash | free ($0) |
| coder (parallel backend) | OpenCode `lag-coder` | openrouter-free/poolside/laguna-s-2.1:free | free coding agent, shared 50/day |
| coder (parallel backend) | OpenCode `north-coder` | openrouter-free/cohere/north-mini-code:free | free coding agent, shared 50/day |
| coder (parallel backend, metered) | OpenCode `tium-coder` | tium/glm-5.3-flash | metered, weighted-token balance |
| coder (parallel backend, metered) | OpenCode `sail-coder` | sail/zai-org/GLM-5.3-Flash | metered, paygo, zero retention |
| coder (parallel backend, metered) | OpenCode `above-coder` | above/glm-5.3-flash-modal | $10 credit, $2/day cap |
| coder (parallel backend, metered) | OpenCode `tiyuvta-coder` | tiyuvta/ornith-ai/ornith-1.5-35b-a3b | metered |
| coder (parallel backend, metered) | OpenCode `nv-coder` | nvidia/nvidia/nemotron-3-ultra-550b-a55b | metered, paygo |
| coder (16th parallel backend, metered) | OpenCode `bai-coder` | bai/glm-5.3-flash | metered, prepaid |
| investigator, tests, lint | OpenCode `muse-investigator` | muse-spark-1.3-contributor-free | free |
| investigator (parallel backend) | OpenCode `glm-investigator` | tokenrouter/z-ai/glm-5.3-free | free |
| investigator (parallel backend) | OpenCode `orca-investigator` | orcarouter/z-ai/glm-5.3-flash-free | free |
| investigator (parallel backend) | OpenCode `nemo-investigator` | opencode/nemotron-3-ultra-free | free, Zen login, limited time |
| investigator (parallel backend) | OpenCode `mimo-investigator` | opencode/mimo-v2.5-free | free, Zen login, limited time |
| investigator (parallel backend) | OpenCode `gem-investigator` | google/gemini-3.5-flash | free tier |
| investigator (parallel backend) | OpenCode `groq-investigator` | groq/openai/gpt-oss-120b | free developer tier |
| investigator (parallel backend) | OpenCode `zai-investigator` | zai/glm-4.5-flash | free ($0) |
| investigator (parallel backend) | OpenCode `lag-investigator` | openrouter-free/poolside/laguna-s-2.1:free | free coding agent, shared 50/day |
| investigator (parallel backend) | OpenCode `north-investigator` | openrouter-free/cohere/north-mini-code:free | free coding agent, shared 50/day |
| investigator (parallel backend, metered) | OpenCode `tium-investigator` | tium/glm-5.3-flash | metered, weighted-token balance |
| investigator (parallel backend, metered) | OpenCode `sail-investigator` | sail/zai-org/GLM-5.3-Flash | metered, paygo, zero retention |
| investigator (parallel backend, metered) | OpenCode `above-investigator` | above/glm-5.3-flash-modal | $10 credit, $2/day cap |
| investigator (parallel backend, metered) | OpenCode `tiyuvta-investigator` | tiyuvta/ornith-ai/ornith-1.5-35b-a3b | metered |
| investigator (parallel backend, metered) | OpenCode `nv-investigator` | nvidia/nvidia/nemotron-3-ultra-550b-a55b | metered, paygo |
| investigator (16th parallel backend, metered) | OpenCode `bai-investigator` | bai/glm-5.3-flash | metered, prepaid |
| extra review pass | OpenCode `muse-reviewer` | muse-spark-1.3-contributor-free | free |
| extra review pass (parallel backend) | OpenCode `glm-reviewer` | tokenrouter/z-ai/glm-5.3-free | free |
| extra review pass (parallel backend) | OpenCode `orca-reviewer` | orcarouter/z-ai/glm-5.3-flash-free | free |
| extra review pass (parallel backend) | OpenCode `nemo-reviewer` | opencode/nemotron-3-ultra-free | free, Zen login, limited time |
| extra review pass (parallel backend) | OpenCode `mimo-reviewer` | opencode/mimo-v2.5-free | free, Zen login, limited time |
| extra review pass (parallel backend) | OpenCode `gem-reviewer` | google/gemini-3.5-flash | free tier |
| extra review pass (parallel backend) | OpenCode `groq-reviewer` | groq/openai/gpt-oss-120b | free developer tier |
| extra review pass (parallel backend) | OpenCode `zai-reviewer` | zai/glm-4.5-flash | free ($0) |
| extra review pass (parallel backend) | OpenCode `lag-reviewer` | openrouter-free/poolside/laguna-s-2.1:free | free coding agent, shared 50/day |
| extra review pass (parallel backend) | OpenCode `north-reviewer` | openrouter-free/cohere/north-mini-code:free | free coding agent, shared 50/day |
| extra review pass (parallel backend, metered) | OpenCode `tium-reviewer` | tium/glm-5.3-flash | metered, weighted-token balance |
| extra review pass (parallel backend, metered) | OpenCode `sail-reviewer` | sail/zai-org/GLM-5.3-Flash | metered, paygo, zero retention |
| extra review pass (parallel backend, metered) | OpenCode `above-reviewer` | above/glm-5.3-flash-modal | $10 credit, $2/day cap |
| extra review pass (parallel backend, metered) | OpenCode `tiyuvta-reviewer` | tiyuvta/ornith-ai/ornith-1.5-35b-a3b | metered |
| extra review pass (parallel backend, metered) | OpenCode `nv-reviewer` | nvidia/nvidia/nemotron-3-ultra-550b-a55b | metered, paygo |
| extra review pass (16th parallel backend, metered) | OpenCode `bai-reviewer` | bai/glm-5.3-flash | metered, prepaid |

Published per-million token rates, used here as a proxy for how fast each model
consumes the plan allowance: Fable 5.1 $10/$50, Opus 5 $5/$25, Sonnet 4.5 $3/$15,
Sonnet 5 $2/$10, Haiku 4.5 $1/$5, Muse free, GLM-5.3 via TokenRouter free (this
one model only — see below), GLM-5.3 Flash via OrcaRouter free (rate-limited
rather than billed — see below), GLM-5.3 Flash via B.AI $0.075/$0.25 (metered,
prepaid balance — see below, not free despite the same underlying model family),
Gemini 3.5 Flash via Google AI Studio free (free-tier rate limits),
GPT-OSS 120B via Groq free (developer-tier rate limits), GLM-4.5 Flash via
Z.ai $0/$0, Laguna S 2.1 and North Mini Code via OpenRouter free (one shared
50-request/day pool across both). Metered: B.AI GLM-5.3 Flash $0.075/$0.25,
Tium GLM-5.3 Flash on a weighted-token balance (31 for a hello-world probe),
Sail paygo (~$0.80/$3.00 class), above.dev GLM-5.3 Flash on a $10 credit
($0.165/$0.55, $0.032 cached, $2/day cap), tiyuvta Ornith $0.22/$1.20 and
GLM-5.3 Flash $0.075/$0.25, NVIDIA Nemotron paygo (rates per model).
Fable is the most expensive model available, not a cheap tier; do not use it
for routine work. Sonnet 5 is both newer and cheaper than Sonnet 4.5, so there
is no reason to pin 4.5.

The account is Claude Pro with extra usage disabled: hitting the cap stops work
rather than billing overage. An OpenRouter API key is configured in OpenCode and
spends real money; the Anthropic models it lists are a paid duplicate of models
already reachable through Claude Code. Do not route roles through it.

TokenRouter (tokenrouter.com — unrelated to the similarly-named tokenrouter.io)
is configured the same way: a paid marketplace billed against a wallet balance.
`opencode.json`'s `provider.tokenrouter.models` block declares exactly one
model, `z-ai/glm-5.3-free` ($0.00/$0.00, confirmed 2026-09-09), and the
`glm-*` agents pin that model explicitly. Never add another TokenRouter model
to that block, and never pass a different TokenRouter model ID on the command
line, without checking its price on the TokenRouter console first — everything
else there costs real money from the configured `TOKENROUTER_API_KEY` (stored
in the gitignored project `.env`, never in `opencode.json` or committed
config). TokenRouter also offers to become Claude Code's own
`ANTHROPIC_BASE_URL` (proxying Sonnet/Opus/Haiku through their marketplace
instead of the Claude plan) — deliberately not configured; the coordinator
stays on direct Anthropic billing.

OrcaRouter (orcarouter.ai, `provider.orcarouter` in `opencode.json`) is a
third backend, added 2026-09-09. Like TokenRouter it is otherwise a paid
marketplace (200+ models, zero markup on each provider's own rate, plus paid
Team/Enterprise tiers) fronting a specific pinned free model:
`z-ai/glm-5.3-flash-free`, confirmed via its own model page as "never charged
to your balance" — free but rate-limited (HTTP 429 on excess) rather than
free but capped by dollar amount. `opencode.json`'s `provider.orcarouter.models`
block declares only that one slug. OrcaRouter also offers an adaptive
"auto"-routing model (`orcarouter/auto`, the form the user's initial example
used) that can land on any of its 200+ models including expensive paid ones —
deliberately not configured; only the pinned free slug is reachable. Like
TokenRouter, OrcaRouter also offers to become Claude Code's own
`ANTHROPIC_BASE_URL` — not configured, same reasoning as TokenRouter.

B.AI (b.ai, `provider.bai` in `opencode.json`) is a fourth backend, added
2026-09-09. It is a prepaid-credit marketplace (1 USD = 1,000,000 credits,
crypto top-ups) fronting 40+ models under codenames — notably `gpt-5.6-luna`,
`gpt-5.6-terra`, `gpt-5.6-sol` and `gpt-6-astra`, the exact names already used
by this repo's Codex `luna-orchestrator` setup, strongly suggesting that setup
already runs through B.AI or an identical white-label reseller rather than
raw OpenAI billing — unconfirmed, not changed, just noted. Only
`glm-5.3-flash` is declared in the provider's `models` block; per B.AI's own
pricing page it costs $0.075/$0.25 per million input/output tokens, unlike
TokenRouter's pinned model. The user has confirmed using it for routine work
regardless — it is currently funded — but it must never be described as free
in a report or commit message, and its console balance is worth checking
before a large batch.

An `OPENROUTER_FREE_API_KEY` is stored in `.env` but **not** wired into
`opencode.json`: on 2026-09-09 OpenRouter's own API rejected the free slug the
user asked for (`z-ai/glm-5.3-flash:free` → "This model is unavailable for
free... use this slug instead: z-ai/glm-5.3-flash", the paid one), most likely
a lapsed promotion (a limited-time 50% discount on this model was documented
as ending 2026-09-09 16:00 UTC). Re-check before wiring this one up; do not
silently fall back to the paid slug.

Sixteen independent backends means sixteen independent rate limits: split genuinely
independent packets across `muse-coder`+`glm-coder`+`orca-coder`+`nemo-coder`+`mimo-coder`+`gem-coder`+`groq-coder`+`zai-coder`+`lag-coder`+`north-coder`(+`bai-coder`+`tium-coder`+`sail-coder`+`above-coder`+`tiyuvta-coder`+`nv-coder`),
or the investigator/reviewer equivalents, to run in parallel — never to shard
one task's file scope across backends. Prefer the ten free backends before
reaching for a metered one. Note the two OpenRouter backends share one
50-request/day pool, so spend them on coding tasks only.

Budget shape for one medium task: the coordinator is roughly three quarters of
the cost, because its context is re-sent every turn. Architect and reviewer are
bounded single shots and together are about a quarter. Reducing coordinator
context is therefore worth more than downgrading a specialist.

## Routing rule

Give a delegate backend (Muse, GLM/TokenRouter, GLM/OrcaRouter, GLM/B.AI,
Nemotron/Zen, or MiMo/Zen)
anything with a machine-checkable acceptance criterion: codebase
investigation, targeted tests, lint, mechanical refactors, draft tests
against a supplied spec. Keep on Claude anything whose check is judgment:
architecture, security, final validation before a commit, and review of a
delegate's own output — same-model review shares that model's blind spots no
matter which backend wrote the change (this applies to `nemo-reviewer` on
`nemo-coder` output and `mimo-reviewer` on `mimo-coder` output as well).

Delegating investigation matters most: a 400-word report replaces tens of
thousands of tokens of source that would otherwise sit in coordinator context
for the rest of the session. When two investigations are independent, run one
on `muse-investigator` and one on `glm-investigator` at the same time; add
`orca-investigator` for a third independent question, `nemo-investigator` for
a fourth, `mimo-investigator` for a fifth, `gem-investigator` for a sixth,
`groq-investigator` for a seventh, `zai-investigator` for an eighth,
`lag-investigator` for a ninth and `north-investigator` for a tenth;
`tium-`, `sail-`, `above-` and `tiyuvta-investigator` are the metered
eleventh through fourteenth (`bai-investigator` remains the metered
fifteenth); `nv-investigator` is the metered sixteenth.

## Commands

```bash
opencode run --pure --agent muse-coder --model opencode/muse-spark-1.3-contributor-free "Implement the attached task" --file /absolute/path/to/handoff.md
opencode run --pure --agent muse-investigator --model opencode/muse-spark-1.3-contributor-free "Answer the attached question" --file /absolute/path/to/question.md
opencode run --pure --agent muse-reviewer --model opencode/muse-spark-1.3-contributor-free "Review the attached changes" --file /absolute/path/to/review.md

# GLM backend: same shape, requires TOKENROUTER_API_KEY in the environment
# (set -a; source .env; set +a   -- before the opencode call, since OpenCode
# does not load the project .env itself).
opencode run --pure --agent glm-coder --model tokenrouter/z-ai/glm-5.3-free "Implement the attached task" --file /absolute/path/to/handoff.md
opencode run --pure --agent glm-investigator --model tokenrouter/z-ai/glm-5.3-free "Answer the attached question" --file /absolute/path/to/question.md
opencode run --pure --agent glm-reviewer --model tokenrouter/z-ai/glm-5.3-free "Review the attached changes" --file /absolute/path/to/review.md

# OrcaRouter backend: same shape, requires ORCAROUTER_API_KEY in the
# environment the same way. Free (rate-limited), not tokenrouter/orcarouter's
# "auto" adaptive route -- always pin the -free slug explicitly.
opencode run --pure --agent orca-coder --model orcarouter/z-ai/glm-5.3-flash-free "Implement the attached task" --file /absolute/path/to/handoff.md
opencode run --pure --agent orca-investigator --model orcarouter/z-ai/glm-5.3-flash-free "Answer the attached question" --file /absolute/path/to/question.md
opencode run --pure --agent orca-reviewer --model orcarouter/z-ai/glm-5.3-flash-free "Review the attached changes" --file /absolute/path/to/review.md

# B.AI backend (metered, not free -- see above): same shape, requires
# BAI_API_KEY in the environment the same way.
opencode run --pure --agent bai-coder --model bai/glm-5.3-flash "Implement the attached task" --file /absolute/path/to/handoff.md
opencode run --pure --agent bai-investigator --model bai/glm-5.3-flash "Answer the attached question" --file /absolute/path/to/question.md
opencode run --pure --agent bai-reviewer --model bai/glm-5.3-flash "Review the attached changes" --file /absolute/path/to/review.md

# Nemotron / MiMo backends (free via the existing OpenCode Zen login, no new
# key; limited-time free): same shape, no extra env needed.
opencode run --pure --agent nemo-coder --model opencode/nemotron-3-ultra-free "Implement the attached task" --file /absolute/path/to/handoff.md
opencode run --pure --agent nemo-investigator --model opencode/nemotron-3-ultra-free "Answer the attached question" --file /absolute/path/to/question.md
opencode run --pure --agent nemo-reviewer --model opencode/nemotron-3-ultra-free "Review the attached changes" --file /absolute/path/to/review.md
opencode run --pure --agent mimo-coder --model opencode/mimo-v2.5-free "Implement the attached task" --file /absolute/path/to/handoff.md
opencode run --pure --agent mimo-investigator --model opencode/mimo-v2.5-free "Answer the attached question" --file /absolute/path/to/question.md
opencode run --pure --agent mimo-reviewer --model opencode/mimo-v2.5-free "Review the attached changes" --file /absolute/path/to/review.md

# Gemini backend (free tier): built-in `google` provider, requires
# GOOGLE_GENERATIVE_AI_API_KEY in the environment the same way. Do NOT route
# Gemini through a generic OpenAI-compatible block: multi-step tool use fails
# (missing thought_signature, verified 2026-09-09).
opencode run --pure --agent gem-coder --model google/gemini-3.5-flash "Implement the attached task" --file /absolute/path/to/handoff.md
opencode run --pure --agent gem-investigator --model google/gemini-3.5-flash "Answer the attached question" --file /absolute/path/to/question.md
opencode run --pure --agent gem-reviewer --model google/gemini-3.5-flash "Review the attached changes" --file /absolute/path/to/review.md

# Groq backend (free developer tier): built-in `groq` provider, requires
# GROQ_API_KEY in the environment the same way. Do NOT route Groq through a
# generic OpenAI-compatible block: follow-up calls fail (reasoning_content
# rejected, verified 2026-09-09).
opencode run --pure --agent groq-coder --model groq/openai/gpt-oss-120b "Implement the attached task" --file /absolute/path/to/handoff.md
opencode run --pure --agent groq-investigator --model groq/openai/gpt-oss-120b "Answer the attached question" --file /absolute/path/to/question.md
opencode run --pure --agent groq-reviewer --model groq/openai/gpt-oss-120b "Review the attached changes" --file /absolute/path/to/review.md

# Z.ai backend (GLM-4.5 Flash $0/$0): custom `zai` provider in opencode.json,
# requires ZAI_API_KEY in the environment the same way. Only glm-4.5-flash is
# declared; never add a paid GLM model without asking.
opencode run --pure --agent zai-coder --model zai/glm-4.5-flash "Implement the attached task" --file /absolute/path/to/handoff.md
opencode run --pure --agent zai-investigator --model zai/glm-4.5-flash "Answer the attached question" --file /absolute/path/to/question.md
opencode run --pure --agent zai-reviewer --model zai/glm-4.5-flash "Review the attached changes" --file /absolute/path/to/review.md

# OpenRouter-free backends (coding agents, user-approved exception): custom
# `openrouter-free` provider in opencode.json on OPENROUTER_FREE_API_KEY, two
# pinned :free slugs only. The free pool is ONE shared 50-request/day
# allowance across both — spend on coding tasks, never add paid slugs.
opencode run --pure --agent lag-coder --model openrouter-free/poolside/laguna-s-2.1:free "Implement the attached task" --file /absolute/path/to/handoff.md
opencode run --pure --agent lag-investigator --model openrouter-free/poolside/laguna-s-2.1:free "Answer the attached question" --file /absolute/path/to/question.md
opencode run --pure --agent lag-reviewer --model openrouter-free/poolside/laguna-s-2.1:free "Review the attached changes" --file /absolute/path/to/review.md
opencode run --pure --agent north-coder --model openrouter-free/cohere/north-mini-code:free "Implement the attached task" --file /absolute/path/to/handoff.md
opencode run --pure --agent north-investigator --model openrouter-free/cohere/north-mini-code:free "Answer the attached question" --file /absolute/path/to/question.md
opencode run --pure --agent north-reviewer --model openrouter-free/cohere/north-mini-code:free "Review the attached changes" --file /absolute/path/to/review.md

# Metered backends (funded, not free — prefer the ten free ones first).
# Tium (weighted-token balance, cost headers per call):
opencode run --pure --agent tium-coder --model tium/glm-5.3-flash "Implement the attached task" --file /absolute/path/to/handoff.md
opencode run --pure --agent tium-investigator --model tium/glm-5.3-flash "Answer the attached question" --file /absolute/path/to/question.md
opencode run --pure --agent tium-reviewer --model tium/glm-5.3-flash "Review the attached changes" --file /absolute/path/to/review.md
# Sail (paygo, zero data retention — prefer for anything sensitive):
opencode run --pure --agent sail-coder --model sail/zai-org/GLM-5.3-Flash "Implement the attached task" --file /absolute/path/to/handoff.md
opencode run --pure --agent sail-investigator --model sail/zai-org/GLM-5.3-Flash "Answer the attached question" --file /absolute/path/to/question.md
opencode run --pure --agent sail-reviewer --model sail/zai-org/GLM-5.3-Flash "Review the attached changes" --file /absolute/path/to/review.md
# above.dev ($10 credit, $2/day cap on the free key):
opencode run --pure --agent above-coder --model above/glm-5.3-flash-modal "Implement the attached task" --file /absolute/path/to/handoff.md
opencode run --pure --agent above-investigator --model above/glm-5.3-flash-modal "Answer the attached question" --file /absolute/path/to/question.md
opencode run --pure --agent above-reviewer --model above/glm-5.3-flash-modal "Review the attached changes" --file /absolute/path/to/review.md
# tiyuvta (metered; Ornith is the only non-GLM-family model in the swarm):
opencode run --pure --agent tiyuvta-coder --model tiyuvta/ornith-ai/ornith-1.5-35b-a3b "Implement the attached task" --file /absolute/path/to/handoff.md
opencode run --pure --agent tiyuvta-investigator --model tiyuvta/ornith-ai/ornith-1.5-35b-a3b "Answer the attached question" --file /absolute/path/to/question.md
opencode run --pure --agent tiyuvta-reviewer --model tiyuvta/ornith-ai/ornith-1.5-35b-a3b "Review the attached changes" --file /absolute/path/to/review.md
# NVIDIA NIM (metered paygo; note the stutter — provider id `nvidia` plus
# NVIDIA's own org-prefixed model id):
opencode run --pure --agent nv-coder --model nvidia/nvidia/nemotron-3-ultra-550b-a55b "Implement the attached task" --file /absolute/path/to/handoff.md
opencode run --pure --agent nv-investigator --model nvidia/nvidia/nemotron-3-ultra-550b-a55b "Answer the attached question" --file /absolute/path/to/question.md
opencode run --pure --agent nv-reviewer --model nvidia/nvidia/nemotron-3-ultra-550b-a55b "Review the attached changes" --file /absolute/path/to/review.md
```

`--file` is a yargs array option: placed before the message it greedily
consumes the message text as a filename ("File not found: Say hello") and
the run then silently ignores the attachment. The message positional must
come first. Confirmed 2026-09-09.

Save the returned session ID. Use `--session ID` for coder repairs; never reuse
the coder's session for review. Keep packets and complete logs in
pdf-craft-output/agents/. Supply owned paths, acceptance checks and constraints;
review actual diffs and test evidence.

The Claude `architect` and `reviewer` subagents are invoked from the coordinator
by name. Both are limited to Read, Grep and Glob, so the coordinator captures the
diff and test evidence for the reviewer.

## Fallback

The Codex `luna-orchestrator` profile and `~/.codex/agents/architect.toml`
(gpt-6-astra) remain configured and draw on a separate allowance. Use them when
the Claude plan limit is tight; start with `codex --profile luna-orchestrator`.
A profile does not change an already-running chat. Note that
`~/.codex/config.toml` sets `model_reasoning_effort = "xhigh"` globally, which is
expensive for any Codex thread; lower it to medium before routine fallback use.
Never silently fall back to a paid model. Stop on authentication/quota failures.

## Local validation

All sixteen OpenCode role families are recognized, and the free Muse route was
confirmed live on 2026-09-08 with a `--pure` round trip. The `glm-*` roles and
the `tokenrouter` custom provider (`opencode.json` → `@ai-sdk/openai-compatible`,
`baseURL: https://api.tokenrouter.com/v1`) were confirmed live on 2026-09-09:
a `--pure` round trip through `glm-investigator` ran a real shell command
against this repository and reported a correct, verified answer. The `orca-*`
roles and the `orcarouter` provider, and the `bai-*` roles and the `bai`
provider, were confirmed live the same day the same way (the B.AI first call
took ~90s — cold start, not a fault; a 40s timeout is too tight for that
backend's first request in a session). The `nemo-*` roles
(`opencode/nemotron-3-ultra-free`) and `mimo-*` roles
(`opencode/mimo-v2.5-free`) run on the existing OpenCode Zen login with no
`opencode.json` change and were confirmed live on 2026-09-09 the same way:
each investigator ran a real shell command against this repository and
reported a correct, verified answer. The `gem-*` roles
(`google/gemini-3.5-flash`, built-in `google` provider), `groq-*` roles
(`groq/openai/gpt-oss-120b`, built-in `groq` provider) and `zai-*` roles
(`zai/glm-4.5-flash`, custom `zai` provider) were confirmed live on 2026-09-09
the same way, each running two shell commands and returning a correct final
report. Key setup evidence, kept here so nobody repeats the dead ends: the
Gemini key lists `gemini-3.5-flash` via the models endpoint; the Groq key
drives `openai/gpt-oss-120b` (its `/models` endpoint 403s on this key, which
is a permissions quirk, not a bad key); the Z.ai key drives `glm-4.5-flash`
(`glm-4.7-flash` 429'd as temporarily overloaded at setup time, so the older
Flash is pinned). The `lag-*` roles
(`openrouter-free/poolside/laguna-s-2.1:free`) and `north-*` roles
(`openrouter-free/cohere/north-mini-code:free`) were confirmed live on
2026-09-09 the same way, after direct-API verification first (laguna-s
returned the exact probe token; north-mini-code 200; `laguna-xs-2.1:free`
429'd upstream twice and was left unwired). The `tium-*` roles
(`tium/glm-5.3-flash`, 250k weighted-token balance, per-call cost headers),
`sail-*` roles (`sail/zai-org/GLM-5.3-Flash`, paygo, zero retention),
`above-*` roles (`above/glm-5.3-flash-modal`, $10 credit verified live at
$10.0000 with per-call cost headers) and `tiyuvta-*` roles
(`tiyuvta/ornith-ai/ornith-1.5-35b-a3b`) were each confirmed live on
2026-09-09 with two sequential shell commands and a correct final report,
after direct-REST verification first. The `nv-*` roles
(`nvidia/nvidia/nemotron-3-ultra-550b-a55b`, paygo) were confirmed live on
2026-09-09 the same way, after an account-entitlement survey (5 of 81
catalogued models callable on this key; kimi-k3 504'd repeatedly).

The first live check stalled in OpenCode's internal Git snapshot `add --all`.
Project opencode.json disables snapshots to avoid indexing the large collection.
OpenCode file undo is therefore unavailable; preserve existing changes and use
scoped Git commits. See [snapshot configuration](https://dev.opencode.ai/docs/config).

Coder and investigator shell access is broad: prompt constraints are operating
instructions, not a security sandbox. Reviewer edit/bash/task denial is enforced
by OpenCode permissions. No role should be treated as an OS isolation boundary.
Same-model review provides separate context but shares the coder's blind spots,
which is why the gating review runs on Claude.

The local model catalogue also lists OpenRouter `openrouter/free`,
`cohere/north-mini-code:free`, and `poolside/laguna-s-2.1:free`. Discovery is
not an authenticated inference test. The `openrouter-free` block is a
user-approved exception limited to two pinned `:free` slugs on the free key
(see AGENTS.md); the paid OpenRouter route stays banned. Free availability and
limits can change. Contributor/free routes have provider-specific data terms.

## Official references

- [OpenCode agents and permissions](https://opencode.ai/docs/agents/)
- [OpenCode custom providers](https://opencode.ai/docs/providers/)
- [OpenCode Zen model IDs, pricing and data terms](https://opencode.ai/docs/zen/)
- [OpenRouter limits](https://openrouter.ai/docs/api-reference/limits)
- [TokenRouter GLM-5.3-free pricing](https://www.tokenrouter.com/models/z-ai/glm-5.3-free/)
- [OrcaRouter GLM-5.3 Flash (Free) pricing](https://www.orcarouter.ai/models/z-ai/glm-5.3-flash-free)
- [B.AI pricing and usage](https://docs.b.ai/llmservice/pricing-and-usage/)
- [Codex pricing and usage-saving guidance](https://developers.openai.com/codex/pricing/)
