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
| coder (3rd parallel backend) | OpenCode `bai-coder` | bai/glm-5.3-flash | metered, prepaid |
| investigator, tests, lint | OpenCode `muse-investigator` | muse-spark-1.3-contributor-free | free |
| investigator (parallel backend) | OpenCode `glm-investigator` | tokenrouter/z-ai/glm-5.3-free | free |
| investigator (3rd parallel backend) | OpenCode `bai-investigator` | bai/glm-5.3-flash | metered, prepaid |
| extra review pass | OpenCode `muse-reviewer` | muse-spark-1.3-contributor-free | free |
| extra review pass (parallel backend) | OpenCode `glm-reviewer` | tokenrouter/z-ai/glm-5.3-free | free |
| extra review pass (3rd parallel backend) | OpenCode `bai-reviewer` | bai/glm-5.3-flash | metered, prepaid |

Published per-million token rates, used here as a proxy for how fast each model
consumes the plan allowance: Fable 5.1 $10/$50, Opus 5 $5/$25, Sonnet 4.5 $3/$15,
Sonnet 5 $2/$10, Haiku 4.5 $1/$5, Muse free, GLM-5.3 via TokenRouter free (this
one model only — see below), GLM-5.3 Flash via B.AI $0.075/$0.25 (metered,
prepaid balance — see below, not free despite the same underlying model family).
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

B.AI (b.ai, `provider.bai` in `opencode.json`) is a third backend, added
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

Three independent backends means three independent rate limits: split
genuinely independent packets across `muse-coder`+`glm-coder`(+`bai-coder`),
or the investigator/reviewer equivalents, to run in parallel — never to shard
one task's file scope across backends. Prefer the two free backends before
reaching for the metered one.

Budget shape for one medium task: the coordinator is roughly three quarters of
the cost, because its context is re-sent every turn. Architect and reviewer are
bounded single shots and together are about a quarter. Reducing coordinator
context is therefore worth more than downgrading a specialist.

## Routing rule

Give a delegate backend (Muse, GLM/TokenRouter, or GLM/B.AI) anything with a
machine-checkable acceptance criterion: codebase investigation, targeted
tests, lint, mechanical refactors, draft tests against a supplied spec. Keep
on Claude anything whose check is judgment: architecture, security, final
validation before a commit, and review of a delegate's own output —
same-model review shares that model's blind spots no matter which backend
wrote the change.

Delegating investigation matters most: a 400-word report replaces tens of
thousands of tokens of source that would otherwise sit in coordinator context
for the rest of the session. When two investigations are independent, run one
on `muse-investigator` and one on `glm-investigator` at the same time; add
`bai-investigator` as a third lane for a third independent question.

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

# B.AI backend (metered, not free -- see above): same shape, requires
# BAI_API_KEY in the environment the same way.
opencode run --pure --agent bai-coder --model bai/glm-5.3-flash "Implement the attached task" --file /absolute/path/to/handoff.md
opencode run --pure --agent bai-investigator --model bai/glm-5.3-flash "Answer the attached question" --file /absolute/path/to/question.md
opencode run --pure --agent bai-reviewer --model bai/glm-5.3-flash "Review the attached changes" --file /absolute/path/to/review.md
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

Both OpenCode role definitions are recognized, and the free Muse route was
confirmed live on 2026-09-08 with a `--pure` round trip. The `glm-*` roles and
the `tokenrouter` custom provider (`opencode.json` → `@ai-sdk/openai-compatible`,
`baseURL: https://api.tokenrouter.com/v1`) were confirmed live on 2026-09-09:
a `--pure` round trip through `glm-investigator` ran a real shell command
against this repository and reported a correct, verified answer. The `bai-*`
roles and the `bai` provider were confirmed live the same day the same way
(first call took ~90s — cold start, not a fault; a 40s timeout is too tight
for this backend's first request in a session).

The first live check stalled in OpenCode's internal Git snapshot `add --all`.
Project opencode.json disables snapshots to avoid indexing the large collection.
OpenCode file undo is therefore unavailable; preserve existing changes and use
scoped Git commits. See [snapshot configuration](https://dev.opencode.ai/docs/config).

Coder and investigator shell access is broad: prompt constraints are operating
instructions, not a security sandbox. Reviewer edit/bash/task denial is enforced
by OpenCode permissions. No role should be treated as an OS isolation boundary.
Same-model review provides separate context but shares the coder's blind spots,
which is why the gating review runs on Claude.

The local model catalogue also lists OpenCode MiMo V2.5 Free, Nemotron free
variants and OpenRouter `openrouter/free`, `cohere/north-mini-code:free`, and
`poolside/laguna-s-2.1:free`. Discovery is not an authenticated inference test.
These are optional alternatives, not enabled fallbacks. Free availability and
limits can change. Contributor/free routes have provider-specific data terms.

## Official references

- [OpenCode agents and permissions](https://opencode.ai/docs/agents/)
- [OpenCode custom providers](https://opencode.ai/docs/providers/)
- [OpenCode Zen model IDs, pricing and data terms](https://opencode.ai/docs/zen/)
- [OpenRouter limits](https://openrouter.ai/docs/api-reference/limits)
- [TokenRouter GLM-5.3-free pricing](https://www.tokenrouter.com/models/z-ai/glm-5.3-free/)
- [B.AI pricing and usage](https://docs.b.ai/llmservice/pricing-and-usage/)
- [Codex pricing and usage-saving guidance](https://developers.openai.com/codex/pricing/)
