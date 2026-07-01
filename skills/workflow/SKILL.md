---
name: workflow
description: "Workflow-based equity research pipeline (requires Claude Code v2.1.154+ Dynamic Workflows). Screen top sub-industries → pick best companies → deep-dive each. Modes: pipeline (default), screen, analyze, compare, walk. Single-flag dispatch via --mode <name>; or natural-language triggers."
author: Jennings Liu
version: "1.05.58"
license: MIT
---

<platform-paths>
  PLUGIN_ROOT:
    claude: ${CLAUDE_PLUGIN_ROOT}
    gemini: ${extensionPath}
  PLUGIN_DATA:
    claude: ${CLAUDE_PLUGIN_DATA}
    gemini: ${extensionPath}/data
  Use whichever value resolved to an actual path (not a literal variable name).
</platform-paths>

<purpose>Team Lead delegates the entire pipeline to a single Dynamic Workflow (`workflows/stock-analysis.js`). The workflow script runs in an isolated runtime outside the team-lead context window; all per-stage data lives in script variables, and only the compressed final result returns to team-lead. Modes: screen GICS Level 4 sub-industries → pick top companies across top sub-industries → deep-dive each via per-company orchestrators (Wave1: 5,7,9,13 → Wave2: 6,8,10,14 → Wave3: 11,12 → Wave4: 15 for A-share) → unified scoring → 3-horizon reports → best picks.</purpose>

<triggers>
Mode dispatch (Stage 0). Order: explicit `--mode <name>` flag > trigger phrase > default.

**Flag** (authoritative — `--mode` ALWAYS overrides trigger phrases):
- `--mode pipeline` → pipeline mode (default if omitted)
- `--mode screen` → screen mode
- `--mode analyze TICKER [TICKER...]` → analyze mode (positional ticker(s) follow `--mode analyze`)
- `--mode compare T1,T2[,T3,...]` → compare mode (comma-list follows `--mode compare`)
- `--mode walk THEME` → walk mode (positional theme follows `--mode walk`; quoted multi-word allowed)
- `--top-industry N` → number of top sub-industries (or walk-mode candidates) (any mode that uses it)
- `--total-company M` → total companies to deep-dive (pipeline only)
- `--universe US|CN|ALL` → listing-exchange filter for screening (default: US — NYSE/NASDAQ only)
- `--days N` → hot sector discovery focus window: 1=today (default), 5=this week, 10=recent 2 weeks, 20=this month. Controls which timeframe is weighted most for "hot" ranking.
- `--top-price N` → maximum stock price for screening (default: 200). US stocks < $N, A-shares < ¥N, others < $N equiv. Applied in Stage 4. Set 0 to disable.
- `--min-headroom N` → minimum Growth Headroom score 1-10 (default: 5). Stocks scoring below this are filtered out at Stage 4 even if they pass price filter.
- *(no `--mode`)* → falls through to trigger phrases, then default = pipeline

**Trigger phrases** (used when no `--mode` flag present):
- **pipeline** (default): "find best stocks", "top stocks", "全面筛选", "best companies", "screen and analyze", "top picks"
- **screen**: "screen sectors", "筛选行业", "best industries", "industry screening", "sector rotation"
- **analyze**: "analyze [TICKER]", "deep dive [TICKER]", "investment thesis [TICKER]", "valuation of [TICKER]", "due diligence [COMPANY]", "DCF [TICKER]"
- **compare**: "compare [T1],[T2]", "T1 vs T2", "which is better T1 or T2", "stock comparison"
- **walk**: "walk the chain for [theme]", "find bottleneck in [theme]", "chokepoint analysis [theme]", "supply chain bottleneck [theme]", "瓶颈分析 [行业]"

Do NOT trigger on: general market commentary, non-financial queries.
</triggers>

<note>Detailed agent protocols live in `agents/*.md` — the team-lead orchestrator loads stage-specific instructions at spawn time. Reference files in `references/*.md` are loaded lazily per-stage.</note>

<tool-disambiguation>
  All sub-agent spawning uses the harness's **`Agent`** tool (param: `subagent_type=stock-analysis:<agent-name>`, `prompt=...`). The `Task` tool was renamed to `Agent` in Claude Code v2.1.63 (2026-02-28); the `Task(...)` alias still works in settings/agent definitions but hook payloads emit `tool_name="Agent"`.

  Team scaffolding is DEPRECATED in modern Claude Code:
  - `TeamCreate` / `TeamDelete` tools were REMOVED in v2.1.178. Do not call them.
  - `team_name` on the `Agent` tool is accepted but silently ignored. Do not pass it.
  - Agent Teams (the feature) is experimental and double-gated; the skill MUST NOT depend on it.
  - The `Agent.resume` parameter was removed in v2.1.77. Use `SendMessage({to: agentId})` only when Agent Teams are enabled.
</tool-disambiguation>

<orchestration-model>
  **Dynamic Workflows REQUIRED** (Claude Code v2.1.154+ / TS Agent SDK v0.3.149+). The legacy async-pool orchestration was removed in v1.05.24 — there is no fallback path.

  The team-lead agent invokes ONE `Workflow` tool call with `scriptPath="${PLUGIN_ROOT}/workflows/stock-analysis.js"` and the mode/parameter args. The workflow runtime executes the script in an isolated environment outside Claude's context window. Intermediate per-stage results (financials, NLP outputs, technicals, scoring inputs) stay in JavaScript variables inside the script — they NEVER enter the team-lead context window. Only the final compressed result returns to team-lead, which relays it to the user.

  Caps: 16 concurrent subagents / 1000 total agents per workflow run (harness-enforced).

  Benefits over hand-rolled async pool:
  1. Context isolation — team-lead sees only the final summary, not per-stage data.
  2. Cached resume — `Workflow({scriptPath, resumeFromRunId})` replays completed `agent()` calls instantly; only failed/new agents re-run live.
  3. Structured output — `schema:` forces validated JSON from each subagent.
  4. Built-in concurrency + token-budget management via `budget` global.
  5. Progress streaming via `/workflows` view + `log()` + `phase()` markers.

  References: claude.com/blog/a-harness-for-every-task-dynamic-workflows-in-claude-code, code.claude.com/docs/en/workflows.md.
</orchestration-model>

<workflow>
  The full stage-by-stage orchestration logic lives in `workflows/stock-analysis.js` — that script is the authoritative source. Stages map to `agent()` calls inside the workflow; this table is for documentation only.

  <stage n="0" name="Setup" runs-in="team-lead">team-lead detects mode, extracts parameters, generates RUN_ID, resolves plugin_root, then invokes `Workflow({scriptPath: "${PLUGIN_ROOT}/workflows/stock-analysis.js", args})`. team-lead does no other work.</stage>
  <stage n="1" name="Data Collection" agent="data-collector" runs-in="workflow">Shared data once: macro, economic surprises, sector/sub-industry RS, market breadth, theme performance.</stage>
  <stage n="1.5" name="Data Validation" agent="report-validator" runs-in="workflow">Freshness check + source coverage. Blocks downstream stages on failure.</stage>

  <stage n="2" name="Sub-Industry Screening" agent="sector-screener" modes="pipeline,screen" runs-in="workflow">Score 163 GICS Level 4 sub-industries on 11 dimensions. Processed via `parallel()` over 3 batches of ~54.</stage>
  <stage n="3" name="Sub-Industry Deep-Dive" agent="sector-screener" modes="pipeline,screen" runs-in="workflow">Top N sub-industries: Porter, TAM, catalysts, profit pools.</stage>
  <stage n="4" name="Company Screening" agent="company-screener" modes="pipeline,screen" runs-in="workflow">Top companies across ALL top sub-industries. Price filter applied (US<$200, CN<¥200).</stage>
  <stage n="4.5" name="Screening Validation" agent="report-validator" modes="pipeline,screen" runs-in="workflow">Watchlist completeness + price-filter compliance.</stage>

  Stages 3 + 4 run as a `pipeline(top_sub_industries, deepdive, screen)` — no barrier between stages; fast sub-industries progress to company screening while slow ones are still in deep-dive.

  <stage n="5-15" name="Per-Company Deep-Dive" modes="pipeline,analyze,compare" runs-in="workflow">The workflow script drives the 4-wave dependency graph DIRECTLY via `parallel(watchlist, ...)` + `pipeline(c, wave1, wave2, wave3, wave4)` — no intermediate orchestrator agent. (The legacy `company-orchestrator` agent was deprecated in v1.05.27 because the Workflow runtime forbids nested sub-agent spawning.) Each wave uses `Promise.all()` for intra-wave parallelism:
    - Wave 1 (4 parallel): Stage 5 `fundamental-analyst` (financial health) | 7 `industry-analyst` | 9 `macro-analyst` | 13 `alt-data-analyst`
    - Wave 2 (4 parallel, depend on Wave 1): Stage 6 `fundamental-analyst` (earnings quality) | 8 `supply-chain-analyst` | 10 `quant-analyst` (valuation) | 14 `catalyst-analyst`
    - Wave 3 (2 parallel, depend on Wave 2): Stage 11 `quant-analyst` (market regime) | 12 `risk-analyst`
    - Wave 4 (1, A-share only): Stage 15 `china-market-analyst`
  Each specialist writes `{company_dir}/stage{N}.md` + `stage{N}.json` and returns a <500-token completion summary. Cross-company concurrency capped by the Workflow runtime at min(16, cpu-2).</stage>

  <stage n="walk" name="Bottleneck Walk" agent="roadmap-walker" modes="walk" runs-in="workflow">Replaces stages 2-16.5 in walk mode. Top-down chain decomposition + 4-element chokepoint scoring + bottleneck asymmetry composite. Reference: `references/frameworks_bottleneck_investing.md`.</stage>

  <stage n="16" name="Scoring & Cross-Check" agent="scorer" modes="pipeline,analyze,compare" runs-in="workflow">compute_scores.py + cross_check.py + calibrate_conviction.py. Writes ranking.json.</stage>
  <stage n="16.5" name="Score Validation" agent="report-validator" modes="pipeline,analyze,compare" runs-in="workflow">All 11 components in range, composite consistent, ranking sorted.</stage>
  <stage n="16.6" name="Adversarial Verify" agent="risk-analyst" modes="pipeline,analyze,compare" runs-in="workflow">For top 5 picks: 3 perspective-diverse skeptics per company (fundamentals / macro / flow lens), prompted to REFUTE the bull thesis with Bayesian-skeptic default. A pick "survives" if ≥2 of 3 do NOT refute. Findings persisted to `verify_findings.json` and folded into reports + best-picks. Flagged picks are NOT dropped — surfaced to user with ⚠️ caution.</stage>
  <stage n="16.7" name="Judge Panel" agent="quant-analyst" modes="pipeline,analyze,compare" runs-in="workflow">For top 5 picks: 4 investment-framework lenses (Buffett / Lynch / Marks / Druckenmiller), each independently rates 0-10 with verdict (STRONG_BUY/BUY/HOLD/AVOID). Synthesized to panel consensus (HIGH_CONSENSUS_BUY / MIXED / LOW_CONSENSUS / HIGH_CONSENSUS_AVOID) + score spread (wide spread = framework disagreement). Persisted to `judge_panel.json`.</stage>
  <stage n="17" name="Report Generation" agent="screening-report-writer,equity-report-writer" runs-in="workflow">3-horizon reports per company (long/mid/short × N companies) via `parallel()`. Each report folds in the bear-case verdicts and panel consensus as dedicated "对手方观点" and "多框架交叉验证" sections.</stage>
  <stage n="17.4" name="Completeness Critic" agent="report-validator" runs-in="workflow">One critic per report. Detects (a) missing modality / claim / source with HIGH/MEDIUM/LOW severity, (b) kill-switch falsifiability — extracts verbatim text, checks present + measurable + clear trigger. Per-report findings persisted to `critic_{horizon}.json`. HIGH-severity gaps and unfalsifiable kill switches surface in the final result.</stage>
  <stage n="17.5" name="Report Validation" agent="report-validator" runs-in="workflow">Mechanical 8-gate validate_report.py: Chinese content, sections, current price, sources, framework divergence, kill switch, methodology, no hallucinated figures. Runs at `effort: 'low'`.</stage>
  <stage n="18" name="Best Picks Highlight" agent="equity-report-writer" runs-in="workflow">HIGHLIGHTS_BEST_PICKS.md — single-file summary of top-ranked companies including 对手方验证 (bear-case survives), 多框架共识 (panel consensus), and ⚠️ caution notes for flagged picks.</stage>
  <stage n="18.5" name="Best Picks Validation" agent="report-validator" runs-in="workflow">Final gate before workflow returns. Runs at `effort: 'low'`.</stage>

  <stage n="19" name="Cleanup" runs-in="harness">Workflow auto-cleans on completion. No explicit teardown call. The session's implicit team is dismantled at session exit. team-lead surfaces the compressed result and exits.</stage>
</workflow>

<modes>
  <mode name="pipeline" default="true">
    <flag>--mode pipeline (or omit)</flag>
    <trigger>"find best stocks", "top stocks", "全面筛选", "screen and analyze", "top picks"</trigger>
    <parameters>
      <parameter name="top-industry" default="8" range="1-30">Number of top sub-industries after screening all 163.</parameter>
      <parameter name="total-company" default="15" range="1-50">Total companies to deep-dive. Selected by score across ALL top sub-industries — NOT quota per sub-industry. Max 50: each company runs 11 analysis stages (5-15), so 50 companies = 550 agent runs minimum. Cap is performance-driven; raise only if you can wait.</parameter>
      <parameter name="top-price" default="200" range="0-9999">Maximum stock price. Set 0 to disable.</parameter>
      <parameter name="min-headroom" default="5" range="1-10">Minimum Growth Headroom score.</parameter>
      <parameter name="days" default="1" range="1-20">Hot sector discovery focus window. 1=today, 5=this week, 10=recent 2 weeks, 20=this month.</parameter>
    </parameters>
    <stages>0→1→1.5→2→3→4→4.5→5-15(waves)→16→16.5→17→17.5→18→18.5→19</stages>
  </mode>

  <mode name="screen">
    <flag>--mode screen</flag>
    <trigger>"screen sectors", "筛选行业", "best industries", "industry screening"</trigger>
    <parameters>
      <parameter name="top-industry" default="40" range="1-163">Number of top sub-industries to deep-dive.</parameter>
      <parameter name="top-price" default="200" range="0-9999">Maximum stock price. Set 0 to disable.</parameter>
      <parameter name="min-headroom" default="5" range="1-10">Minimum Growth Headroom score.</parameter>
      <parameter name="days" default="1" range="1-20">Hot sector discovery focus window. 1=today, 5=this week, 10=recent 2 weeks, 20=this month.</parameter>
    </parameters>
    <stages>0→1→1.5→2→3→4→4.5→17→17.5→18→18.5→19(screening reports + validation + best picks + cleanup)</stages>
  </mode>

  <mode name="analyze">
    <flag>--mode analyze TICKER [TICKER...]</flag>
    <trigger>"analyze [TICKER]", "deep dive [TICKER]", "investment thesis", "valuation of", "DCF"</trigger>
    <parameters>
      <parameter name="tickers" required="true">One or more ticker symbols (positional after `--mode analyze`, OR extracted from prompt).</parameter>
    </parameters>
    <stages>0→1→1.5→5-15(waves)→16→16.5→17→17.5→18→18.5→19(best picks + validation + cleanup)</stages>
  </mode>

  <mode name="compare">
    <flag>--mode compare T1,T2[,T3,...]</flag>
    <trigger>"compare [T1],[T2]", "T1 vs T2", "which is better", "stock comparison"</trigger>
    <parameters>
      <parameter name="tickers" required="true">2-5 ticker symbols (comma-list after `--mode compare`, OR extracted from prompt).</parameter>
    </parameters>
    <stages>0→1→1.5→5-15(waves)→16(rank+merge)→16.5→17→17.5→18→18.5→19(comparison + validation + best picks + cleanup)</stages>
    <constraints>Max 5 stocks. Identical valuation methodology across all.</constraints>
  </mode>

  <mode name="walk">
    <flag>--mode walk THEME</flag>
    <trigger>"walk the chain for [theme]", "find bottleneck in [theme]", "chokepoint analysis [theme]", "supply chain bottleneck [theme]", "瓶颈分析 [行业]"</trigger>
    <parameters>
      <parameter name="theme" required="true">Universal roadmap theme (positional after `--mode walk`, quoted multi-word allowed). Examples: "humanoid robotics", "AI optical interconnect", "rare-earth permanent magnets", "defense electronics", "grid transmission", "biologic manufacturing".</parameter>
      <parameter name="top-industry" default="7" range="1-20">Maximum candidate companies to score and return.</parameter>
    </parameters>
    <stages>0→1→1.5→walk(roadmap-walker)→17→17.5→18→18.5→19(walk report + validation + best picks + cleanup)</stages>
    <constraints>Universal — applies to AI infra, EV/battery, robotics, defense, solar, biopharma, grid, semi capex, advanced materials. Roadmap MUST be quantitative + dated (numbers + timeline). Output recommends `--mode analyze TICKER` follow-up for tier-1/strong candidates.</constraints>
  </mode>
</modes>

<rules>
  <rule name="Workflow Required" mandatory="true">Claude Code v2.1.154+ and the `Workflow` tool MUST be available. Older harnesses are not supported — there is no fallback. The team-lead agent verifies Workflow availability before invoking; on absence it aborts with an upgrade recommendation.</rule>
  <rule name="team-lead-delegation" mandatory="true">team-lead does ONE thing: invoke `Workflow({scriptPath: "${PLUGIN_ROOT}/workflows/stock-analysis.js", args})`. It does not spawn individual analyst agents, does not run scripts, does not write tracking.json. All stage logic lives in the workflow script.</rule>
  <rule name="Report Language">ALL reports MUST be written in Chinese (中文). Technical terms in English. GICS names: "Semiconductors (半导体)". Source citations in original language. The constraint is enforced inside the workflow script's report-writer `agent()` prompts.</rule>
  <rule name="Price Filter" mandatory="true">Price filter (`--top-price`, default 200) applies ONLY in Stage 4 (Company Screening): US < $N, China A-shares < ¥N, all other markets < $N USD equivalent. Set 0 to disable. Encoded in the company-screener `agent()` prompt inside the workflow. After screening, do NOT re-filter during analysis (5-15) or report generation. Analyze/compare modes with user-specified tickers bypass the filter.</rule>
  <rule name="Headroom Filter" mandatory="true">Growth Headroom filter (`--min-headroom`, default 5) applies in Stage 4. Run `compute_growth_headroom.py` on all price-passing candidates. Reject stocks scoring below threshold. Encoded in the company-screener `agent()` prompt inside the workflow.</rule>
  <rule name="Stock Price Display">Every company in any table/list must include 当前股价. Format: "$XX.XX" or "¥XX.XX".</rule>
  <rule name="All 3 Horizons">Always produce long/mid/short-term reports. The workflow's report phase fans out 3 horizons × N companies via `parallel()`. Never ask the user which horizon.</rule>
  <rule name="UV Run">ALL Python scripts run via `uv run python ${PLUGIN_ROOT}/scripts/<script>.py`. Encoded in each script-running `agent()` prompt.</rule>
  <rule name="Run Directory">Each run creates `./reports/[RUN_ID]/` where RUN_ID = YYYYMMDDHHmm in LOCAL TIME. Created by the workflow script, not team-lead.</rule>
  <rule name="Ranked Directories">Output directories use rank-prefixed names: `NNN-[TICKER]`. Pipeline/compare: rank after Stage 16. Single analyze: always 001.</rule>
  <rule name="Numbered Stock Index">Every report includes 推荐标的排名 with 001, 002, 003 format. Top-ranked MUST be 001.</rule>
  <rule name="Company Selection">Top companies selected by score across ALL top sub-industries — NOT equally distributed.</rule>
  <rule name="A-Share Mandatory">Stage 15 is MANDATORY for .SH/.SZ tickers. SKIP for all others. The workflow detects A-share via ticker suffix and passes `is_a_share` flag to company-orchestrator.</rule>
  <rule name="No team_name">Do NOT pass `team_name` on any `Agent` call — it is silently ignored in modern Claude Code (v2.1.178+). The implicit session team handles peer coordination.</rule>
  <rule name="no-pause" mandatory="true">team-lead never pauses to ask for confirmation. After parameter extraction, invoke the workflow immediately and run to completion. The workflow runs autonomously.</rule>
  <rule name="no-stage-skip" mandatory="true">In pipeline mode, stages 5-15 MUST run for EVERY selected company. The workflow does not skip stages because "too many companies". If total-company exceeds 50, cap at 50 — the workflow enforces this.</rule>
  <rule name="shared-data-once" mandatory="true">Macro, RS, breadth, theme data fetched ONCE in Stage 1 (workflow phase "Shared Data"). All downstream `agent()` calls read from `stage1.json` — never re-fetch.</rule>
  <rule name="context-eviction" mandatory="true">The workflow script's variables hold per-stage data; the team-lead context never sees raw analysis. No persist.py offloading needed — context isolation is structural.</rule>
</rules>

<constraints>
  <constraint name="NEVER Analyze Directly">team-lead invokes the workflow and relays its result. ALL analysis happens inside `agent()` calls within the workflow script.</constraint>
  <constraint name="Single Tool Call">A normal pipeline run is 1 (ToolSearch verify) + 1 (Workflow invocation) + 1 (relay result) = ~3 turns in team-lead context. Beyond that means team-lead is doing work that belongs in the script.</constraint>
  <constraint name="No Tracking JSON Writes">team-lead does not write `tracking.json`. The workflow script writes per-stage outputs to disk; the final compressed result returned to team-lead serves as the run summary.</constraint>
  <constraint name="Max Concurrency">Workflow runtime caps at min(16, cpu-2) concurrent agents per run. Total cap: 1000 agents per workflow. The script does not need to manage its own pool.</constraint>
  <constraint name="Quality Gate">Validation runs inside the workflow at stages 1.5 / 4.5 / 16.5 / 17.5 / 18.5. If any gate fails, the workflow returns status='failed' or 'partial' with the failing stage and reason.</constraint>
  <constraint name="Level 4 Structure">Sub-Industry is the structural unit in reports — Level 1/2/3 appear only as context within Level 4 entries.</constraint>
  <constraint name="Resume on Failure">If the workflow returns status='failed', users can re-run with `Workflow({scriptPath, resumeFromRunId})` to replay cached `agent()` calls and only re-run the failed stage onward.</constraint>
</constraints>

<criteria name="Skip Conditions">
  Stage 2-4 (Screening): SKIP for analyze/compare/walk modes.
  Stage 4.5 (Screening Validation): SKIP for analyze/compare/walk modes.
  Stage 3 (Deep-Dive): SKIP if top-industry = 1 (single sub-industry).
  Stage 5-15 (Per-company Deep-Dive): SKIP for screen/walk modes.
  Stage 15 (A-Share): SKIP for non-.SH/.SZ tickers.
  Stage 16-16.5 (Scoring): SKIP for screen/walk modes (no per-company composite scoring).
  Stage walk (Bottleneck Walk): RUN ONLY for walk mode.
  Stage 17 screening reports: SKIP for analyze/compare/walk modes.
  Stage 17 company reports: SKIP for screen/walk modes.
  Stage 17 walk report: RUN ONLY for walk mode.
  Stage 18.5 (Best Picks Validation): NEVER skip if Stage 18 ran.
  Stage 19 (Cleanup): NEVER skip — always runs as the final stage.
</criteria>

<composite-weights>
  Source of truth: `scripts/compute_scores.py` → `compute_conviction()`

  | Dimension | Long-term | Mid-term | Short-term |
  |-----------|-----------|----------|------------|
  | financial_health | 15% | 10% | — |
  | moat_quality | 15% | 10% | — |
  | management_quality | 15% | 10% | — |
  | valuation_attractiveness | 15% | 15% | 10% |
  | capital_structure | 10% | — | — |
  | macro_tailwind | 5% | 10% | 10% |
  | risk_profile | 10% | 10% | 10% |
  | alternative_alignment | — | — | 15% |
  | technical_setup | — | — | 15% |
  | weinstein_alignment | 5% | 10% | 10% |
  | canslim | — | 10% | 10% |
  | ecosystem_momentum | 5% | 5% | 10% |
  | industry_trajectory | 5% | 5% | 5% |
  | money_flow_confirmation | — | 5% | 5% |
</composite-weights>

<references>
  <ref>Canonical workflow script: `workflows/stock-analysis.js` — all orchestration logic lives here</ref>
  <ref>Plugin root: `${PLUGIN_ROOT}` — agents, scripts, skills, references, workflows</ref>
  <ref>Plugin data: `${PLUGIN_DATA}` — caches, venv, persisted state</ref>
  <ref>GICS taxonomy: `references/gics_taxonomy.md` — full 4-level hierarchy with codes and ETF proxies</ref>
  <ref>Data source matrix: `references/data_source_matrix.md` — source tiers, confidence caps</ref>
  <ref>Screening templates: `templates/screening-report.md` — report formats, scoring formulas</ref>
  <ref>Equity templates: `templates/equity-report.md` — deep-dive report formats</ref>
  <ref>Bottleneck framework: `references/frameworks_bottleneck_investing.md` — universal 5-step methodology, 4-element chokepoint checklist, 6-input asymmetry composite</ref>
  <ref>Scoring calibration: `references/scoring_calibration.md` — calibration targets</ref>
  <ref>Serenity frameworks: `references/serenity/` — TAM-Adj-PEG (`tam-adj-peg.md`), Bayesian intrinsic growth (`bayesian-intrinsic-growth.md`), GF-DMA Health Index (`gf-dma-health-index.md`), Serenity-Alpha demand-transmission (`serenity-alpha.md`), and buy-side memo template (`buy-side-memo.md`) — sourced from haskaomni/serenity-skill, wired into Stage 10/11/13 scripts</ref>
  <ref>Workflow tool docs: https://code.claude.com/docs/en/workflows.md</ref>
  <ref>Dynamic Workflows announcement: https://claude.com/blog/a-harness-for-every-task-dynamic-workflows-in-claude-code (2026-05-28)</ref>
</references>
