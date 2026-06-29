---
name: stock-analysis
description: "Unified equity research pipeline: screen top sub-industries → pick best companies → deep-dive each. Modes: pipeline (default), screen, analyze, compare, walk. Single-flag dispatch via --mode <name>; or natural-language triggers."
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

<purpose>Team Lead orchestrates specialized analyst agents via the Agent tool — it NEVER analyzes directly, only spawns, coordinates, and quality-gates. Agents execute data collection, screening, multi-dimensional analysis, scoring, adversarial verification, and report generation in parallel where possible. Unified equity research pipeline: screen GICS Level 4 sub-industries → pick top companies across top sub-industries → deep-dive each in parallel waves → unified scoring → adversarial verify → judge panel → 3-horizon reports → completeness critic → best picks.</purpose>

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
- *(no `--mode`)* → falls through to trigger phrases, then default = pipeline

**Ticker normalization** (A-share support):
- Numeric-only tickers (e.g., "600519") → append `.SH` if starts with 6, `.SZ` otherwise
- Chinese stock names (e.g., "贵州茅台") → resolve to ticker via akshare lookup
- Tickers already suffixed (e.g., "600519.SH") → pass through unchanged

**Trigger phrases** (used when no `--mode` flag present):
- **pipeline** (default): "find best stocks", "top stocks", "全面筛选", "best companies", "screen and analyze", "top picks"
- **screen**: "screen sectors", "筛选行业", "best industries", "industry screening", "sector rotation"
- **analyze**: "analyze [TICKER]", "deep dive [TICKER]", "investment thesis [TICKER]", "valuation of [TICKER]", "due diligence [COMPANY]", "DCF [TICKER]"
- **compare**: "compare [T1],[T2]", "T1 vs T2", "which is better T1 or T2", "stock comparison"
- **walk**: "walk the chain for [theme]", "find bottleneck in [theme]", "chokepoint analysis [theme]", "supply chain bottleneck [theme]", "瓶颈分析 [行业]"

Do NOT trigger on: general market commentary, non-financial queries.
</triggers>

<note>Detailed agent protocols live in `agents/*.md` — the team-lead orchestrator loads stage-specific instructions at spawn time. Reference files in `references/*.md` and templates in `templates/*.md` are loaded lazily per-stage.</note>

<tool-disambiguation>
  All sub-agent spawning uses the harness's **`Agent`** tool (param: `subagent_type=stock-analysis:<agent-name>`, `prompt=...`). The `Task` tool was renamed to `Agent` in Claude Code v2.1.63 (2026-02-28); the `Task(...)` alias still works in settings/agent definitions but hook payloads emit `tool_name="Agent"`.

  Team scaffolding is DEPRECATED in modern Claude Code:
  - `TeamCreate` / `TeamDelete` tools were REMOVED in v2.1.178. Do not call them.
  - `team_name` on the `Agent` tool is accepted but silently ignored. Do not pass it.
  - Agent Teams (the feature) is experimental and double-gated; the skill MUST NOT depend on it.
  - The session uses a single implicit team. Agent lifecycle is managed by the team-lead via `run_in_background=true` + polling.
</tool-disambiguation>

<orchestration-model>
  **Agent Tool orchestration** — the team-lead agent spawns specialist agents directly via the `Agent` tool. No Dynamic Workflow dependency. Compatible with all Claude Code versions that support the Agent tool.

  Per-company stages (5-15) are delegated to company-orchestrator agents — one per company, scheduled by an ASYNC POOL with max 4 concurrent. Each company-orchestrator independently manages the dependency DAG within its own context window.

  **Retry policy**: If an agent returns null (terminal API error / crash), retry up to 10 times before marking that stage as failed. This applies to ALL agent spawns — data-collector, sector-screener, analyst stages, scoring, validation, and report generation. A stage marked "failed" after exhausting retries does NOT abort the pipeline — downstream stages continue with partial data, and the failure is logged in tracking.json.
</orchestration-model>

<stages>
  <stage n="0" name="Setup">Detect mode: if `--mode <name>` present → use it (one of: pipeline, screen, analyze, compare, walk); else trigger phrase fallback; else default pipeline. Extract parameters: --top-industry (1-163), --total-company (1-40, pipeline only), tickers (positional after `--mode analyze` OR comma-list after `--mode compare`), theme (positional after `--mode walk`, quoted multi-word allowed), --universe (US|CN|ALL, default US). Normalize A-share tickers. Create RUN_ID (YYYYMMDDHHmm), output directory (./reports/[RUN_ID]/), tracking.json. MUST complete before any data fetch or agent spawning.</stage>
  <stage n="1" name="Data Collection" agent="data-collector">Fetch shared data ONCE: macro indicators, economic surprises, sector/sub-industry RS, market breadth, theme performance. Load references/gics_taxonomy.md and references/data_source_matrix.md. All downstream stages reuse this data.</stage>
  <stage n="1.5" name="Data Validation" agent="report-validator" modes="pipeline,screen,analyze,compare">Validate Stage 1 shared data: freshness check, source coverage, required files present. Blocks downstream stages if shared data is stale or incomplete. MUST PASS before Stages 2+.</stage>

  <stage n="2" name="Sub-Industry Screening" agent="sector-screener" modes="pipeline,screen">Score ALL 163 GICS Level 4 sub-industries on 11 dimensions (Growth, Profitability, Valuation, Macro Fit, Innovation, Regulatory, Capital Flows, RS, Cyclicality, Constituent Quality, Supply/Demand). Process in 3 parallel batches of ~54. Select top N sub-industries.</stage>
  <stage n="3" name="Sub-Industry Deep-Dive" agent="sector-screener" modes="pipeline,screen">Deep-dive top N sub-industries: Porter, TAM, catalysts, barriers, company universe, competitive dynamics, growth catalysts, profit pools. Process in parallel waves of max 4 agents.</stage>
  <stage n="4" name="Company Screening" agent="company-screener" modes="pipeline,screen">Screen companies across ALL top N sub-industries. Apply filters (market cap, growth, FCF, ROIC, price <$100/¥100, universe filter). Score on growth/profitability/moat/valuation/management/risk/liquidity. Select top M by score across ALL sub-industries — NOT quota per sub-industry.</stage>
  <stage n="4.5" name="Screening Validation" agent="report-validator" modes="pipeline,screen">Validate screening outputs: sub-industry leaderboard has 10+ entries with valid GICS codes, company watchlist has 10+ companies, price filter applied, universe filter applied, 推荐标的排名 format correct. Blocks report generation if screening is incomplete.</stage>

  <stage n="5" name="Financial Health" agent="fundamental-analyst" modes="pipeline,analyze,compare" per-company="true">DuPont 5-factor decomposition, Piotroski F-Score, Lynch categories, key ratio analysis. Scripts: fetch_financials.py, calculate_metrics.py.</stage>
  <stage n="6" name="Earnings Quality" agent="fundamental-analyst" modes="pipeline,analyze,compare" per-company="true" depends="5">Beneish M-Score, Montier C-Score, accruals quality, cash conversion, revenue recognition, capital allocation history (Buffett retention test, buyback ROI, M&A track record), CEO quality score. Scripts: fetch_capital_structure.py, calculate_earnings_quality.py, diff_filings.py, audit_capital_allocation.py, score_ceo_quality.py.</stage>
  <stage n="7" name="Industry & Competitive" agent="industry-analyst" modes="pipeline,analyze,compare" per-company="true">Porter's Five Forces, TAM/SAM/SOM, Morningstar moat assessment, BCG matrix, ecosystem mapping. REUSES industry thesis from Stage 3 if available. Scripts: fetch_peer_universe.py.</stage>
  <stage n="8" name="Supply Chain" agent="supply-chain-analyst" modes="pipeline,analyze,compare" per-company="true" depends="7">Tier 1-3 supplier mapping, geographic concentration (HHI), chokepoint identification, disruption scenario modeling, inventory-to-sales analysis. **Step 7b**: bottleneck asymmetry composite via score_bottleneck_asymmetry.py for each chokepoint candidate. Scripts: fetch_supply_chain.py, fetch_supply_chain_ecosystem.py, score_bottleneck_asymmetry.py.</stage>
  <stage n="9" name="Macro & Geopolitics" agent="macro-analyst" modes="pipeline,analyze,compare" per-company="true">Dalio economic cycle, Druckenmiller liquidity, Four-Box Framework, Fed stance, CRP country risk, sanctions exposure, currency exposure. REUSES macro data from Stage 1. Scripts: fetch_global_macro.py, fetch_currency_exposure.py.</stage>
  <stage n="10" name="Valuation" agent="quant-analyst" modes="pipeline,analyze,compare" per-company="true" depends="5,7">DCF+Monte Carlo, comps, SOTP, LBO floor, reverse DCF, margin of safety. Serenity TAM-Adj-PEG, Bayesian 5-hypothesis intrinsic CAGR. **Step 3c**: optionally read bottleneck_asymmetry.json from Stage 8 if already written, fold tier/asymmetry-band/earliness-band into valuation summary as ±15% qualitative adjustment. Scripts: calculate_metrics.py, forecast.py, fetch_private_comps.py, compute_tam_adj_peg.py, compute_bayesian_growth.py.</stage>
  <stage n="11" name="Market Regime" agent="quant-analyst" modes="pipeline,analyze,compare" per-company="true" depends="10">Weinstein stage classification, CANSLIM, Soros reflexivity, factor attribution (Fama-French 5-factor), options signals, sentiment, institutional positioning, GF-DMA Health Index. Scripts: fetch_technicals.py, compute_factors.py, fetch_cot.py, calculate_options.py, fetch_sentiment.py, fetch_short_interest.py, fetch_activist_exposure.py, compute_liquidity.py, compute_seasonality.py, compute_earnings_edge.py, compute_health_index.py, signal_evolution.py, alpha_factor_zoo.py.</stage>
  <stage n="12" name="Risk Assessment" agent="risk-analyst" modes="pipeline,analyze,compare" per-company="true" depends="10">Scenario analysis (bull/base/bear), Marks 2nd-level thinking, Burry forensic, Klarman permanent-vs-temporary, kill switch definition, correlation regime. Scripts: fetch_credit.py, fetch_behavioral.py, compute_correlation_regime.py, fetch_esg_carbon.py.</stage>
  <stage n="13" name="Alt Data & Digital" agent="alt-data-analyst" modes="pipeline,analyze,compare" per-company="true">Digital footprint (web traffic, app rankings), NLP earnings call analysis, channel checks, transaction data, Serenity-Alpha demand-transmission elasticity. Scripts: fetch_alternatives.py, fetch_news_nlp.py, calculate_candor.py, analyze_earnings_transcript.py, synthesize_primary_research.py, analyze_alpha_elasticity.py.</stage>
  <stage n="14" name="Catalyst Intelligence" agent="catalyst-analyst" modes="pipeline,analyze,compare" per-company="true" depends="13">Catalyst calendar (FDA, earnings, product launches, regulatory), event-driven probability, pre/post-event drift (PEAD), catalyst sequencing. Scripts: compute_earnings_edge.py, event_study.py.</stage>
  <stage n="15" name="A-Share Analysis" agent="china-market-analyst" modes="pipeline,analyze,compare" per-company="true" condition="ticker ends with .SH or .SZ" depends="5-14">政策敏感性矩阵, 产业政策周期, 北向资金, 融资融券, 龙虎榜, 游资追踪. MANDATORY for .SH/.SZ tickers. SKIP for all others.</stage>

  <stage n="walk" name="Bottleneck Walk" agent="roadmap-walker" modes="walk">Top-down chain decomposition: anchor quantitative dated demand roadmap → reverse-walk chain finished-product→raw-substrate (≥5 layers) → score 4-element chokepoint checklist per layer → identify candidates in chokepoint layers (score ≥3) → run score_bottleneck_asymmetry.py for each → write walk_roadmap.json, walk_chain.json, walk_candidates.json, walk.md. Replaces Stages 2-16.5 in walk mode. Universal across industries (AI infra, EV, robotics, defense, solar, biopharma, grid, semi capex, materials). Recommends `--mode analyze TICKER` follow-up for tier-1/strong candidates. Reference: references/frameworks_bottleneck_investing.md.</stage>

  <stage n="16" name="Scoring & Cross-Check" agent="scorer" modes="pipeline,analyze,compare">Deterministic scoring (compute_scores.py) for each company. Cross-check contradictions (cross_check.py). Bayesian conviction calibration (calibrate_conviction.py). LLM agents may adjust Moat and Management ±2.0 based on qualitative findings. Rank companies by composite score.</stage>
  <stage n="16.5" name="Score Validation" agent="report-validator" modes="pipeline,analyze,compare">Validate Stage 16 scoring: all 11 components present in 1-10 range, composite matches weighted sum, rating bracket consistent, no unresolved contradictions, ranking sorted correctly. Blocks report generation if scoring is invalid.</stage>
  <stage n="16.6" name="Adversarial Verify" agent="risk-analyst" modes="pipeline,analyze,compare">For top 5 picks: 3 perspective-diverse skeptics per company (fundamentals / macro / flow lens), prompted to REFUTE the bull thesis with Bayesian-skeptic default. A pick "survives" if ≥2 of 3 do NOT refute. Findings persisted to `verify_findings.json` and folded into reports + best-picks. Flagged picks are NOT dropped — surfaced to user with ⚠️ caution.</stage>
  <stage n="16.7" name="Judge Panel" agent="quant-analyst" modes="pipeline,analyze,compare">For top 5 picks: 4 investment-framework lenses (Buffett / Lynch / Marks / Druckenmiller), each independently rates 0-10 with verdict (STRONG_BUY/BUY/HOLD/AVOID). Synthesized to panel consensus (HIGH_CONSENSUS_BUY / MIXED / LOW_CONSENSUS / HIGH_CONSENSUS_AVOID) + score spread (wide spread = framework disagreement). Persisted to `judge_panel.json`.</stage>
  <stage n="17" name="Report Generation" agent="screening-report-writer,equity-report-writer">Pipeline: screening overview (3 horizons) + per-company deep-dives (3 horizons each). Screen: screening reports only. Analyze: per-company reports only. Compare: comparison reports with ranked table. Each report folds in bear-case verdicts and panel consensus as dedicated "对手方观点" and "多框架交叉验证" sections.</stage>
  <stage n="17.4" name="Completeness Critic" agent="report-validator" modes="pipeline,analyze,compare">One critic per report. Detects (a) missing modality / claim / source with HIGH/MEDIUM/LOW severity, (b) kill-switch falsifiability — extracts verbatim text, checks present + measurable + clear trigger. Per-report findings persisted to `critic_{horizon}.json`. HIGH-severity gaps and unfalsifiable kill switches surface in the final result.</stage>
  <stage n="17.5" name="Report Validation" agent="report-validator">Independent validation of all generated reports: run validate_report.py (8 gates) for each report, verify Chinese content, verify required sections, verify stock price display.</stage>
  <stage n="18" name="Best Picks Highlight" agent="equity-report-writer">After ALL reports pass validation, write HIGHLIGHTS_BEST_PICKS.md to ./reports/[RUN_ID]/. Single-file summary of the top-ranked companies including 对手方验证 (bear-case survives), 多框架共识 (panel consensus), and ⚠️ caution notes for flagged picks. Contains: rank, ticker, company name, current price, composite score, conviction, 2-sentence thesis, kill switch, key catalyst.</stage>
  <stage n="18.5" name="Best Picks Validation" agent="report-validator">Validate HIGHLIGHTS_BEST_PICKS.md: ranked table with required columns, kill switch for each company, 当前股价 present. MUST PASS before cleanup.</stage>
  <stage n="19" name="Cleanup" agent="team-lead">Final cleanup: remove intermediate files (stage*.md, raw-data.json, phase*.md), keep only tracking.json + final reports + HIGHLIGHTS_BEST_PICKS.md. MUST be the LAST stage — no work after this.</stage>
</stages>

<dependencies>
  Per-company analysis stages (5-15) are delegated to company-orchestrator agents — one per company, scheduled by an ASYNC POOL with max 4 concurrent.

  Each company-orchestrator independently manages the dependency DAG within its own context window:
  <wave n="1" agents="4" stages="5,7,9,13" note="All independent — orchestrator spawns up to 4 parallel analysts" />
  <wave n="2" agents="4" stages="6,8,10,14" note="6←5, 8←7, 10←5+7, 14←13" />
  <wave n="3" agents="2" stages="11,12" note="11←10, 12←10" />
  <wave n="4" agents="1" stages="15" note="15←all, A-share only" />

  Team-lead scheduling (across companies) — async pool, NOT synchronous batches:
  - Initialize: spawn first 4 company-orchestrators in parallel (run_in_background=true)
  - When ANY orchestrator finishes (whichever first), immediately spawn the next pending company
  - Pool stays saturated at min(4, remaining) at all times — no batch-edge stalls
  - Loop until queue empty AND pool empty
  This isolates per-company context, prevents team-lead context exhaustion, and avoids
  the 20-30% wall-clock penalty of synchronous batches on heterogeneous runtimes.
  Reference: agents/team-lead.md Phase 3 (Async Pool pattern).
</dependencies>

<modes>
  <mode name="pipeline" default="true">
    <flag>--mode pipeline (or omit)</flag>
    <trigger>"find best stocks", "top stocks", "全面筛选", "screen and analyze", "top picks"</trigger>
    <parameters>
      <parameter name="top-industry" default="5" range="1-30">Number of top sub-industries after screening all 163.</parameter>
      <parameter name="total-company" default="10" range="1-40">Total companies to deep-dive. Selected by score across ALL top sub-industries — NOT quota per sub-industry. Max 40: each company runs 11 analysis stages (5-15), so 40 companies = 440 agent runs minimum. Cap is performance-driven; raise only if you can wait.</parameter>
    </parameters>
    <stages>0→1→1.5→2→3→4→4.5→5-15(waves)→16→16.5→16.6→16.7→17→17.4→17.5→18→18.5→19</stages>
  </mode>

  <mode name="screen">
    <flag>--mode screen</flag>
    <trigger>"screen sectors", "筛选行业", "best industries", "industry screening"</trigger>
    <parameters>
      <parameter name="top-industry" default="30" range="1-163">Number of top sub-industries to deep-dive.</parameter>
    </parameters>
    <stages>0→1→1.5→2→3→4→4.5→17→17.5→18→18.5→19(screening reports + validation + best picks + cleanup)</stages>
  </mode>

  <mode name="analyze">
    <flag>--mode analyze TICKER [TICKER...]</flag>
    <trigger>"analyze [TICKER]", "deep dive [TICKER]", "investment thesis", "valuation of", "DCF"</trigger>
    <parameters>
      <parameter name="tickers" required="true">One or more ticker symbols (positional after `--mode analyze`, OR extracted from prompt).</parameter>
    </parameters>
    <stages>0→1→1.5→5-15(waves)→16→16.5→16.6→16.7→17→17.4→17.5→18→18.5→19</stages>
  </mode>

  <mode name="compare">
    <flag>--mode compare T1,T2[,T3,...]</flag>
    <trigger>"compare [T1],[T2]", "T1 vs T2", "which is better", "stock comparison"</trigger>
    <parameters>
      <parameter name="tickers" required="true">2-5 ticker symbols (comma-list after `--mode compare`, OR extracted from prompt).</parameter>
    </parameters>
    <stages>0→1→1.5→5-15(waves)→16(rank+merge)→16.5→16.6→16.7→17→17.4→17.5→18→18.5→19</stages>
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
  <rule name="Report Language">ALL reports MUST be written in Chinese (中文). Technical terms in English. GICS names: "Semiconductors (半导体)". Source citations in original language.</rule>
  <rule name="Price Filter" mandatory="true">Price filter applies ONLY during Stage 4 (Company Screening). ALL markets: US stocks < $100, China A-shares < ¥100, all other markets < equivalent of $100 USD. This filter determines which companies enter the watchlist and proceed to deep-dive (Stages 5-15). After screening, do NOT re-filter or exclude companies during analysis (5-15) or report generation (17-18). Exception: if user specifies a specific ticker (analyze/compare mode), proceed regardless of price (user override).</rule>
  <rule name="Universe Filter" mandatory="true">The --universe flag (default: US) restricts screening to listing exchanges. US = NYSE/NASDAQ only. CN = China A-shares (.SH/.SZ) only. ALL = no filter. Applied during Stage 4 company screening. Analyze/compare modes with user-specified tickers bypass the filter.</rule>
  <rule name="Stock Price Display">Every company in any table/list must include 当前股价. Format: "$XX.XX" or "¥XX.XX".</rule>
  <rule name="All 3 Horizons">Always produce long/mid/short-term reports. Never ask — always produce all three.</rule>
  <rule name="UV Run">ALL Python scripts run via `uv run python ${PLUGIN_ROOT}/scripts/<script>.py`.</rule>
  <rule name="Run Directory">Each run creates `./reports/[RUN_ID]/` where RUN_ID = YYYYMMDDHHmm.</rule>
  <rule name="Ranked Directories">Output directories use rank-prefixed names: `NNN-[TICKER]`. Pipeline/compare: rank after Stage 16. Single analyze: always 001.</rule>
  <rule name="Numbered Stock Index">Every report includes 推荐标的排名 with 001, 002, 003 format. Top-ranked MUST be 001.</rule>
  <rule name="Company Selection">Top M companies selected by score across ALL top-N sub-industries — NOT equally distributed.</rule>
  <rule name="A-Share Mandatory">Stage 15 is MANDATORY for .SH/.SZ tickers. SKIP for all others.</rule>
  <rule name="No team_name">Do NOT pass `team_name` on any `Agent` call — it is silently ignored in modern Claude Code (v2.1.178+). The implicit session team handles peer coordination.</rule>
  <rule name="team-lead-delegation" mandatory="true">Team Lead NEVER analyzes directly. Only spawns agents, coordinates, and quality-gates.</rule>
  <rule name="no-pause" mandatory="true">NEVER pause between stages to ask user for confirmation. The pipeline runs Stage 0 → 19 continuously. No "Continue?" prompts. Only stop if user explicitly asks a question.</rule>
  <rule name="no-stage-skip" mandatory="true">In pipeline mode, stages 5-15 MUST run for EVERY selected company. NEVER skip deep-dive stages because "too many companies" or "due to scale". If total-company exceeds 40, cap at 40 and proceed with all stages.</rule>
  <rule name="shared-data-once" mandatory="true">Macro, RS, breadth, theme data fetched ONCE in Stage 1. All downstream stages reuse — never re-fetch.</rule>
  <rule name="context-eviction" mandatory="true">After each stage: write summary → drop raw data. If context >80%, offload via persist.py.</rule>
  <rule name="retry-on-null" mandatory="true">If an agent spawn returns null (terminal API error after internal retries), retry up to 10 times. Log each retry. After 10 failures, mark stage as failed and continue — do NOT abort the pipeline. Failed stages are recorded in tracking.json with reason.</rule>
</rules>

<constraints>
  <constraint name="NEVER Analyze Directly">Team Lead NEVER runs scripts, fetches data, or performs analysis. ALL work delegated to specialist agents.</constraint>
  <constraint name="Tracking JSON Updated">Tracking JSON MUST be updated BEFORE advancing to the next stage. Both status changes (previous complete, next in_progress) in a single write.</constraint>
  <constraint name="Pass PLUGIN_ROOT">Every spawn prompt MUST include `plugin_root` set to the resolved absolute path. Agents reference scripts as `{plugin_root}/scripts/`.</constraint>
  <constraint name="Data via Agents">Data-fetch scripts are run by data-collector or search-agent teammates, NOT by the team lead directly.</constraint>
  <constraint name="Max 4 Concurrent">Cap parallel agents at 4 to manage context window.</constraint>
  <constraint name="Company Orchestrator Delegation">For stages 5-15, team-lead spawns company-orchestrator agents (one per company) via an ASYNC POOL with max 4 concurrent (next company spawns as soon as any prior orchestrator finishes — no batch-edge stalls). Each orchestrator independently manages all analysis stages for its company. The team-lead NEVER spawns individual analyst agents (fundamental-analyst, industry-analyst, etc.) directly for stages 5-15.</constraint>
  <constraint name="Quality Gate">Report cannot be delivered until pre-delivery checklist passes. If any gate fails: "INCOMPLETE ANALYSIS — [reason]".</constraint>
  <constraint name="Level 4 Structure">Sub-Industry is the structural unit in reports — Level 1/2/3 appear only as context within Level 4 entries.</constraint>
  <constraint name="Cleanup">Stage 19 cleanup: delete intermediate files (stage*.md, raw-data.json, phase*.md). Keep only tracking.json + final reports + HIGHLIGHTS_BEST_PICKS.md. MUST be the LAST stage.</constraint>
</constraints>

<criteria name="Skip Conditions">
  Stage 2-4 (Screening): SKIP for analyze/compare/walk modes.
  Stage 4.5 (Screening Validation): SKIP for analyze/compare/walk modes.
  Stage 3 (Deep-Dive): SKIP if top-industry = 1 (single sub-industry).
  Stage 5-15 (Per-company Deep-Dive): SKIP for screen/walk modes.
  Stage 15 (A-Share): SKIP for non-.SH/.SZ tickers.
  Stage 16-16.7 (Scoring + Verify + Panel): SKIP for screen/walk modes (no per-company composite scoring).
  Stage walk (Bottleneck Walk): RUN ONLY for walk mode.
  Stage 17 screening reports: SKIP for analyze/compare/walk modes.
  Stage 17 company reports: SKIP for screen/walk modes.
  Stage 17 walk report: RUN ONLY for walk mode.
  Stage 17.4 (Completeness Critic): SKIP for screen/walk modes.
  Stage 18.5 (Best Picks Validation): NEVER skip if Stage 18 ran.
  Stage 19 (Cleanup): NEVER skip — always runs as the final stage.
</criteria>

<composite-weights>
  | Dimension | Long-term | Mid-term | Short-term |
  |-----------|-----------|----------|------------|
  | Growth | 25% | 20% | 10% |
  | Profitability | 20% | 15% | 5% |
  | Valuation | 10% | 15% | 10% |
  | Macro Fit | 10% | 15% | 10% |
  | Innovation | 15% | 10% | 5% |
  | Regulatory | 5% | 5% | 5% |
  | Capital Flows | 5% | 5% | 20% |
  | Relative Strength | 5% | 10% | 20% |
  | Cyclicality | 5% | 5% | 5% |
  | Constituent Quality | 0% | 0% | 10% |
  | Supply/Demand Cycle | 0% | 0% | 0% |
</composite-weights>

<references>
  <ref>Plugin root: `${PLUGIN_ROOT}` — agents, scripts, skills, references, templates</ref>
  <ref>Plugin data: `${PLUGIN_DATA}` — caches, venv, persisted state</ref>
  <ref>GICS taxonomy: `references/gics_taxonomy.md` — full 4-level hierarchy with codes and ETF proxies</ref>
  <ref>Data source matrix: `references/data_source_matrix.md` — source tiers, confidence caps</ref>
  <ref>Screening templates: `templates/screening-report.md` — report formats, scoring formulas</ref>
  <ref>Equity templates: `templates/equity-report.md` — deep-dive report formats</ref>
  <ref>Bottleneck framework: `references/frameworks_bottleneck_investing.md` — universal 5-step methodology, 4-element chokepoint checklist, 6-input asymmetry composite</ref>
  <ref>Scoring calibration: `references/scoring_calibration.md` — calibration targets</ref>
  <ref>Serenity frameworks: `references/serenity/` — TAM-Adj-PEG (`tam-adj-peg.md`), Bayesian intrinsic growth (`bayesian-intrinsic-growth.md`), GF-DMA Health Index (`gf-dma-health-index.md`), Serenity-Alpha demand-transmission (`serenity-alpha.md`), and buy-side memo template (`buy-side-memo.md`)</ref>
</references>
