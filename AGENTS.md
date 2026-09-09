<!-- BEGIN PROJECT AGENT WORKFLOW -->
## Agent workflow

Claude Code is the coordinator. Run it on Sonnet (`/model sonnet`); the
coordinator replays its context on every turn and is the largest share of the
budget, so keep Opus for coordination only when a task genuinely needs it.
Roles: `architect` and `reviewer` are Claude Code subagents in `.claude/agents/`;
`muse-*`, `glm-*`, `bai-*`, `orca-*`, `nemo-*`, `mimo-*`, `gem-*`, `groq-*`,
`zai-*`, `lag-*`, `north-*`, `tium-*`, `sail-*`, `above-*`, `tiyuvta-*`
and `nv-*` (coder/investigator/reviewer each) are
OpenCode roles in `.opencode/agents/` — sixteen independent backends, same role
split, same guardrails. Muse Spark, GLM-5.3 via TokenRouter, GLM-5.3 Flash
via OrcaRouter (`orca-*`), Nemotron 3 Ultra (`nemo-*`) and MiMo-V2.5
(`mimo-*`) — the last two via the existing OpenCode Zen login, no new key —
Gemini 3.5 Flash (`gem-*`, free tier via Google AI Studio), GPT-OSS 120B
(`groq-*`, free developer tier), GLM-4.5 Flash (`zai-*`, $0 via Z.ai),
Laguna S 2.1 (`lag-*`, free coding agent via OpenRouter) and North Mini Code
(`north-*`, free coding agent via OpenRouter)
are genuinely free (pinned models, rate-limited rather than billed, the
Zen ones for a limited time). GLM-5.3 Flash via B.AI (`bai-*`), GLM-5.3 Flash
via Tium (`tium-*`), GLM-5.3 Flash via Sail (`sail-*`), GLM-5.3 Flash via
above.dev (`above-*`, $10 credit, $2/day cap) and Ornith 1.5 35B via tiyuvta
(`tiyuvta-*`) are metered — currently funded and
approved for routine use per the user, but they are not free; do not describe
them as free in a report or commit message, and check
balances before a large batch. Nemotron 3 Ultra 550B via NVIDIA NIM (`nv-*`,
paygo) is metered too — and note the stutter in its model ref
(`nvidia/nvidia/...`): the first segment is our provider-block id, the rest
is NVIDIA's own org-prefixed model id. These instructions apply only
to the coordinator; delegated roles never spawn teams.

1. Gather a compact evidence packet: objective, relevant files, current behavior,
   constraints, acceptance checks. Reuse existing plans where applicable.
   Delegate the codebase investigation to `muse-investigator` so source files
   stay out of coordinator context; it returns paths, symbols and behavior.
2. Ask the `architect` subagent for one concise plan whose tasks each name owned
   files and a machine-checkable acceptance check. Save the plan before coding.
   Skip architecture for trivial unambiguous fixes. Architect runs on Sonnet
   by default; request Opus explicitly only when the design judgment genuinely
   needs it.
3. Run OpenCode `muse-coder` using exactly
   `opencode/muse-spark-1.3-contributor-free`. Supply the plan, owned files and checks.
   Let the bounded task finish; do not edit its files concurrently or interrupt
   merely because output is quiet. Save its session ID and full output on disk.
   When a plan has two or more genuinely independent tasks (disjoint owned
   files, no shared state), dispatch across backends in parallel rather than
   serially. `muse-coder`, `glm-coder` (`tokenrouter/z-ai/glm-5.3-free`),
   `orca-coder` (`orcarouter/z-ai/glm-5.3-flash-free`), `nemo-coder`
   (`opencode/nemotron-3-ultra-free`), `mimo-coder`
   (`opencode/mimo-v2.5-free`), `gem-coder` (`google/gemini-3.5-flash`),
   `groq-coder` (`groq/openai/gpt-oss-120b`) and `zai-coder`
   (`zai/glm-4.5-flash`), plus `lag-coder`
   (`openrouter-free/poolside/laguna-s-2.1:free`) and `north-coder`
   (`openrouter-free/cohere/north-mini-code:free`), cost only wall-clock
   time, not money — use all ten free ones before reaching for a metered
   backend (`bai-*`, `tium-*`, `sail-*`, `above-*`, `tiyuvta-*` or `nv-*`).
   Never split one task's file scope
   across backends. The two OpenRouter backends share one 50-request/day free
   allowance on `OPENROUTER_FREE_API_KEY`, so spend it on coding tasks only.
4. Run tests and lint through `muse-investigator`, which reports pass/fail and
   failing assertions rather than full logs. Validate anything that gates a
   commit yourself: a free model attesting to its own work is not evidence.
5. Run the `reviewer` subagent with the actual scoped diff, relevant source and
   test evidence. Reviewer cannot edit or run commands; the coordinator captures
   the diff and    test evidence for it. Use `muse-reviewer` only as a free extra
   pass, never as the sole review of `muse-coder` output — same model, same
   blind spots. The same applies to every other backend's reviewer on its own
   backend's output.
6. Return concrete defects to the SAME coder session for one focused repair;
   ask the reviewer to recheck affected changes. Coordinator validates, documents,
   stages only intended paths and commits on the feature branch. Report remaining gaps.

Use `opencode run --pure --agent muse-coder --model
opencode/muse-spark-1.3-contributor-free --file /absolute/path/to/handoff.md
"Implement the attached task"` (one shell command). Use `--session ID` only for
coder repairs. Replace agent with `muse-investigator` or `muse-reviewer` and
attach the matching packet. Never reuse a coder session for review. Do not use
`--continue` for reviews. Store packets/logs under pdf-craft-output/agents/.

Routing rule: give a delegate backend (Muse, GLM/TokenRouter, GLM/OrcaRouter,
GLM/B.AI, Nemotron/Zen, MiMo/Zen, Gemini/Google, Groq, GLM/Z.ai,
Laguna/OpenRouter-free, North/OpenRouter-free, GLM/Tium, GLM/Sail,
GLM/above.dev, Ornith/tiyuvta, or Nemotron/NVIDIA) anything with a machine-checkable acceptance criterion
(investigation, tests, lint, mechanical refactors, draft tests); split
independent packets across backends to run in parallel, preferring the ten
free ones before reaching for a metered one. Keep on Claude anything whose
check is judgment: architecture, security, final pre-commit validation, and
review of a delegate's own code — same-model review shares that model's blind
spots regardless of which backend produced the change.

Cost controls: at most one active worker per backend (so at most sixteen workers
total, on disjoint file scopes); bounded handoffs and reports (roughly 400
words); logs on disk, not whole transcripts in chat; targeted tests once,
repeat only after changes/failures; reuse plans; no competing solutions or
recursive delegation.
Quota discipline (mandatory): batch questions per turn — every turn replays
full context, so three questions in one turn costs ~1/3 of three turns;
/compact before context balloons, /clear between tasks with a 5-line handoff
note (objective, files, pending, session IDs); utility subagents on Haiku;
start heavy sessions right after the 5h reset, no parallel Claude sessions
in one window.
Never silently substitute paid models. Do not route roles through OpenRouter
except on the two pinned `:free` slugs below: a paid OpenRouter key is also
configured and spends real money, while Claude subagents
and the free backends do not. The TokenRouter key configured for `glm-coder`/
`glm-investigator`/`glm-reviewer` is scoped to exactly one model,
`z-ai/glm-5.3-free` ($0/$0); the OrcaRouter key configured for `orca-coder`/
`orca-investigator`/`orca-reviewer` is scoped to exactly one model,
`z-ai/glm-5.3-flash-free` (free, rate-limited rather than billed — "never
charged to your balance" per OrcaRouter's own model page); the B.AI key
configured for `bai-coder`/`bai-investigator`/`bai-reviewer` is scoped to
exactly one model, `glm-5.3-flash` (metered, ~$0.075/$0.25 per million tokens,
prepaid). All three services are otherwise paid marketplaces (OrcaRouter:
200+ models, zero markup on provider rates but still billed; B.AI: prepaid
credit balance), so never add another model to any of their `opencode.json`
provider blocks, or pass one on the command line — including OrcaRouter's
`orcarouter/auto` adaptive-routing alias, which can land on any of its 200+
models including paid ones — without confirming its price first. The `zai`
custom provider block (`https://api.z.ai/api/paas/v4`, `ZAI_API_KEY`) declares
exactly one model, `glm-4.5-flash` ($0/$0, verified live 2026-09-09); never
add a paid GLM model there without asking. A separate
`OPENROUTER_FREE_API_KEY` is wired ONLY through the `openrouter-free` block in
`opencode.json`, which declares exactly two slugs —
`poolside/laguna-s-2.1:free` and `cohere/north-mini-code:free` (both $0/$0,
verified live 2026-09-09; the earlier `z-ai/glm-5.3-flash:free` slug was
rejected by OpenRouter's own API as a lapsed promotion and stays unwired).
This is an explicit user-approved exception: never point any role at a paid
OpenRouter slug, never add another slug to that block without verifying it is
`:free` first, and never substitute the paid key. The free allowance is one
shared 50-request/day pool across both backends (1,000/day only after a $10
credit purchase — not approved, do not buy). Free endpoints may log prompts:
bounded technical packets only. (`laguna-xs-2.1:free` was left out: Poolside
rate-limited it upstream at setup time; re-check before adding.) The `tium`
(`https://api.tium.ai/v1`, `TIUM_API_KEY`), `sail`
(`https://api.sailresearch.com/v1`, `SAIL_API_KEY`), `above`
(`https://api.above.dev/v1`, `ABOVE_API_KEY`) and `tiyuvta`
(`https://api.tiyuvta.ai/v1`, `TIYUVTA_API_KEY`) blocks each declare exactly
one pinned model (`tium/glm-5.3-flash`, `sail/zai-org/GLM-5.3-Flash`,
`above/glm-5.3-flash-modal`, `tiyuvta/ornith-ai/ornith-1.5-35b-a3b` — all
verified live 2026-09-09); never add another model to any of them without
confirming its price first. Sail has zero data retention by default — prefer
it for anything sensitive. Gemini (`gem-*`, `google/gemini-3.5-flash`) and Groq (`groq-*`,
`groq/openai/gpt-oss-120b`) run through OpenCode's built-in `google`/`groq`
providers, not custom `opencode.json` blocks: routing either through a generic
OpenAI-compatible block breaks multi-step tool use (Gemini rejects calls
missing `thought_signature`; Groq rejects returned `reasoning_content` — both
verified 2026-09-09). `.env` holds `GEMINI_API_KEY` (direct REST reference)
and `GOOGLE_GENERATIVE_AI_API_KEY` (same key, the name the built-in provider
reads) plus `GROQ_API_KEY`. Google's free tier may use prompts for training
outside the EU/UK/EEA — delegates already receive only bounded technical
packets, never credentials or bulk book content; keep it that way. Prefer Sonnet over Opus, and never Fable, for routine work — Fable 5.1
bills at 2x Opus and 5x Sonnet. On auth/quota failures pause that route; honor
retry hints, avoid repeated model switches. Model listings are not proof of
account access or unlimited free usage. Do not change the selected model
mid-turn.
The Codex `luna-orchestrator` profile and `architect.toml` remain available as a
fallback on a separate allowance when the Claude plan limit is tight.
Operational commands and cost notes: [agent workflow](references/agent-workflow.md).
<!-- END PROJECT AGENT WORKFLOW -->

# Agent 工作流

pdf-craft 是一个把扫描书籍 PDF 转换为 Markdown 或 EPUB 的 Python 库。本仓库使用 `~/.agents/skills/vibecoding` 作为通用维护工作法。本文件只记录 pdf-craft 特有的边界和按需阅读路由。

## 工作区边界

- `pdf_craft/` 是包源码。公共导入从 `pdf_craft/__init__.py` 暴露，便利入口在 `pdf_craft/functions.py`。
- `tests/` 包含轻量单元测试和小型 PDF fixture。普通代码改动默认以这些测试作为验证面。
- `docs/`、`README.md` 和 `README_zh-CN.md` 是读者/贡献者阅读的文档。不要把这些说明复制到 Agent 文档里。
- `references/` 是 Agent 面向的引用文档。只阅读当前任务需要的引用文档。
- `pdf_craft_tool/` 是未发布的本地 CLI，承载手动转换、翻译和冒烟矩阵；`scripts/` 只保留依赖源码同步辅助脚本。不要把它们当作默认开发流程。
- `analysing/`、`pdf-craft-output/`、`models-cache/`、`.venv/`、`dist/`、`build/` 和 `*.egg-info` 是生成产物或本地运行产物。

## 仅在需要时阅读

- 当需要判断模块归属、公共 API 边界或新代码应放在哪里时，阅读[架构与模块边界](references/architecture.md)。
- 当修改 PDF 提取、OCR 归一化、缓存 XML 产物、目录生成、章节生成、Markdown 渲染或 EPUB 渲染时，阅读[转换流水线](references/conversion-pipeline.md)。
- 当选择 setup、验证、worktree 行为、发布或外部依赖处理方式时，阅读[开发与 Worktree](references/development-and-worktrees.md)。
- 当准备发版、更新版本号、编写 changelog 或调整发布流程时，阅读[发版流程](references/release-workflow.md)。
- 当处理 bio01–bio24 分布式 OCR、持续发现新书、Qwen 视觉校对或运行中的任务时，先阅读 [Cluster pipeline handoff](references/cluster-pipeline.md)。
- For publication-only fleet updates, metadata sidecars or cover revisions, read the publication service notes in [Cluster pipeline handoff](references/cluster-pipeline.md); keep OCR and publication queues independent.
- Bengali OCR dataset creation and Tesseract fine-tuning are explicitly deferred; see [Future plans](docs/en/FUTURE_PLANS.md) only if revisiting that topic. Do not start this work without a new user request.

## 项目特有默认规则

- 这是库项目。除非未来任务引入长期服务，否则不要启动常驻开发服务器。
- 普通验证应避免 CUDA、模型下载、网络请求和完整 PDF 转换，除非任务明确触及这些行为。
- 模型缓存和转换输出不得进入提交内容。`pdf_craft_tool` 的产物默认写入每个 worktree 自己的 `pdf-craft-output/`；只有任务明确需要 OCR 时，才考虑共享外部模型缓存。
- 纯文档任务不得修改包代码或依赖版本。

## Active book-processing deployment

- The user authorized continuous OCR and proofreading across bio01–bio24. This task explicitly introduces a background coordinator; it is an exception to the no-long-running-service default above.
- `data/` is the user's continuously updated input collection. Deleting, moving or renaming its books is permitted where a task calls for it -- the user authorized this for deduplication on 2026-09-08 -- but never commit its books, and generated output still belongs under `pdf-craft-output/`.
- Removing a book is destructive and unrecoverable. Record the decision and its evidence in the catalogue first, show the user the counts, and only then act; prefer moving a rejected copy into a quarantine directory over deleting it outright.
- The coordinator runs on bio10. `/scratch` is local to each machine; `/home` is NFS. Keep the SQLite queue on bio10's local disk. Transfer input and results explicitly.
- Preserve the current dirty worktree and running jobs. Inspect the handoff and live queue before changing a worker release, model configuration, or service.
- `~/.agents/skills/vibecoding` was unavailable during implementation. Follow these repository instructions and references if it is still unavailable.
