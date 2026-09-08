# Agent workflow operations

Configured 2026-09-08. Project policy lives in AGENTS.md; OpenCode roles live in
.opencode/agents/. The local Codex architect definition uses gpt-6-astra with
medium reasoning. The local luna-orchestrator profile selects gpt-5.6-luna,
medium reasoning; start a new coordinator with `codex --profile luna-orchestrator`.
A profile does not change an already-running chat. This is a coordinator-driven
workflow, not an unattended scheduler.

Use one architect plan, a bounded coder task, and a fresh review session.
Keep packets and complete logs in pdf-craft-output/agents/. Supply owned paths,
acceptance checks and constraints; review actual diffs and test evidence.

```bash
opencode run --pure --agent muse-coder --model opencode/muse-spark-1.3-contributor-free --file /absolute/path/to/handoff.md "Implement the attached task"
opencode run --pure --agent muse-reviewer --model opencode/muse-spark-1.3-contributor-free --file /absolute/path/to/review.md "Review the attached changes"
```

Save the returned session ID. Use `--session ID` for coder repairs; never reuse
the coder's session for review. Reviewer shell and edit permissions are denied.
Same-model review provides separate context but can share the coder's blind spots.
If the current Codex surface cannot invoke the architect, report that limitation;
do not substitute an OpenRouter paid model.

## Usage controls

- Begin a new Luna thread with a short handoff when this conversation grows large.
- Keep architecture to one compact plan; skip that phase for trivial fixes.
- Let Muse do bounded investigation, implementation and targeted tests.
- Keep reports around 400 words and full logs out of coordinator context.
- Use one worker, reuse its session for a focused repair, avoid recursive teams.
- Disable unused connectors; avoid Fast mode when preserving allowance matters.
- Check Codex `/status` or the usage dashboard. Offloading work does not remove
  Codex costs for Luna coordination and Astra planning, or guarantee a five-hour
  window will last. OpenCode/OpenRouter quotas are separate.
- Never silently fall back to a paid model. Stop on authentication/quota failures.

The local model catalogue also lists OpenCode MiMo V2.5 Free, Nemotron free
variants and OpenRouter `openrouter/free`, `cohere/north-mini-code:free`, and
`poolside/laguna-s-2.1:free`. Discovery is not an authenticated inference test.
These are optional alternatives, not enabled fallbacks. Free availability and
limits can change. Contributor/free routes have provider-specific data terms.

## Official references

- [OpenCode agents and permissions](https://opencode.ai/docs/agents/)
- [OpenCode Zen model IDs, pricing and data terms](https://opencode.ai/docs/zen/)
- [OpenRouter limits](https://openrouter.ai/docs/api-reference/limits)
- [Codex pricing and usage-saving guidance](https://developers.openai.com/codex/pricing/)

## Local validation

OpenCode recognizes both role definitions; the Luna profile parses as TOML.
The first live check stalled in OpenCode's internal Git snapshot `add --all`.
Project opencode.json disables snapshots to avoid indexing the large collection.
OpenCode file undo is therefore unavailable; preserve existing changes and use
scoped Git commits. See [snapshot configuration](https://dev.opencode.ai/docs/config).

The free Muse reviewer completed a live read-only configuration review. Its
suggestions about removing deployment instructions or requiring duplicate model
defaults were not adopted: deployment is explicitly authorized, and named agents
plus explicit CLI model selection are intentional. The fresh-review rule was
made explicit. Coder shell access is broad: prompt constraints are operating
instructions, not a security sandbox. Reviewer edit/bash/task denial is enforced
by OpenCode permissions. Neither role should be treated as an OS isolation boundary.
