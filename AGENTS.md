<!-- BEGIN PROJECT AGENT WORKFLOW -->
## Agent workflow

Claude Code is the coordinator. Run it on Sonnet (`/model sonnet`); the
coordinator replays its context on every turn and is the largest share of the
budget, so keep Opus for coordination only when a task genuinely needs it.
Roles: `architect` and `reviewer` are Claude Code subagents in `.claude/agents/`;
`muse-coder`, `muse-investigator`, `muse-reviewer`, `glm-coder`, `glm-investigator`
and `glm-reviewer` are free OpenCode roles in `.opencode/agents/` — two
independent free backends (Muse Spark and GLM-5.3 via TokenRouter), same
role split, same guardrails. These instructions apply only to the
coordinator; delegated roles never spawn teams.

1. Gather a compact evidence packet: objective, relevant files, current behavior,
   constraints, acceptance checks. Reuse existing plans where applicable.
   Delegate the codebase investigation to `muse-investigator` so source files
   stay out of coordinator context; it returns paths, symbols and behavior.
2. Ask the `architect` subagent for one concise plan whose tasks each name owned
   files and a machine-checkable acceptance check. Save the plan before coding.
   Skip architecture for trivial unambiguous fixes.
3. Run OpenCode `muse-coder` using exactly
   `opencode/muse-spark-1.3-contributor-free`. Supply the plan, owned files and checks.
   Let the bounded task finish; do not edit its files concurrently or interrupt
   merely because output is quiet. Save its session ID and full output on disk.
   When a plan has two or more genuinely independent tasks (disjoint owned
   files, no shared state), dispatch one to `muse-coder` and one to
   `glm-coder` (`tokenrouter/z-ai/glm-5.3-free`) in parallel rather than
   serially — both are free, so this only costs wall-clock time, not money.
   Never split one task's file scope across both backends.
4. Run tests and lint through `muse-investigator`, which reports pass/fail and
   failing assertions rather than full logs. Validate anything that gates a
   commit yourself: a free model attesting to its own work is not evidence.
5. Run the `reviewer` subagent with the actual scoped diff, relevant source and
   test evidence. Reviewer cannot edit or run commands; the coordinator captures
   the diff and test evidence for it. Use `muse-reviewer` only as a free extra
   pass, never as the sole review of `muse-coder` output — same model, same
   blind spots.
6. Return concrete defects to the SAME coder session for one focused repair;
   ask the reviewer to recheck affected changes. Coordinator validates, documents,
   stages only intended paths and commits on the feature branch. Report remaining gaps.

Use `opencode run --pure --agent muse-coder --model
opencode/muse-spark-1.3-contributor-free --file /absolute/path/to/handoff.md
"Implement the attached task"` (one shell command). Use `--session ID` only for
coder repairs. Replace agent with `muse-investigator` or `muse-reviewer` and
attach the matching packet. Never reuse a coder session for review. Do not use
`--continue` for reviews. Store packets/logs under pdf-craft-output/agents/.

Routing rule: give a free backend (Muse or GLM) anything with a machine-checkable
acceptance criterion (investigation, tests, lint, mechanical refactors, draft
tests); split independent packets across both to run in parallel. Keep on Claude
anything whose check is judgment: architecture, security, final pre-commit
validation, and review of a free backend's own code — same-model review shares
that model's blind spots regardless of which free backend produced the change.

Cost controls: at most one active worker per free backend (so at most two
workers total, on disjoint file scopes); bounded handoffs and reports (roughly
400 words); logs on disk, not whole transcripts in chat; targeted tests once,
repeat only after changes/failures; reuse plans; no competing solutions or
recursive delegation.
Never silently substitute paid models. Do not route roles through OpenRouter:
an OpenRouter key is configured and spends real money, while Claude subagents and
the free backends do not. The TokenRouter key configured for `glm-coder`/
`glm-investigator`/`glm-reviewer` is scoped to exactly one model,
`z-ai/glm-5.3-free` ($0/$0) — TokenRouter is otherwise a paid marketplace billed
against a wallet balance, so never add another TokenRouter model to
`opencode.json`'s provider block or pass one on the command line without
confirming its price first. Prefer Sonnet over Opus, and never Fable, for
routine work — Fable 5.1 bills at 2x Opus and 5x Sonnet. On auth/quota failures
pause that route; honor retry hints, avoid repeated model switches. Model
listings are not proof of account access or unlimited free usage. Do not change
the selected model mid-turn.
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
