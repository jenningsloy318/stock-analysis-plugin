---
name: stock-analysis
description: "Unified equity research pipeline: screen top sub-industries → pick best companies → deep-dive each. Modes: pipeline (default), screen, analyze, compare. Triggers on 'find best stocks', 'screen sectors', 'analyze [TICKER]', 'compare T1,T2'."
author: Jennings Liu
version: "1.05.01"
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

<purpose>Team Lead orchestrates specialized analyst agents — it NEVER analyzes directly, only spawns, coordinates, and quality-gates. Agents execute data collection, screening, multi-dimensional analysis, scoring, and report generation in parallel where possible. Unified equity research pipeline: screen GICS Level 4 sub-industries → pick top M companies across top N sub-industries → deep-dive each in parallel waves → unified scoring → reports.</purpose>

<triggers>
Triggers on ALL of the following (mode detected from phrasing):
- **pipeline** (default): "find best stocks", "top stocks", "全面筛选", "best companies", "screen and analyze", "top picks"
- **screen**: "screen sectors", "筛选行业", "best industries", "industry screening", "sector rotation"
- **analyze**: "analyze [TICKER]", "deep dive [TICKER]", "investment thesis [TICKER]", "valuation of [TICKER]", "due diligence [COMPANY]", "DCF [TICKER]"
- **compare**: "compare [T1],[T2]", "T1 vs T2", "which is better T1 or T2", "stock comparison"
Do NOT trigger on: general market commentary, non-financial queries.
</triggers>

<note>Detailed agent protocols live in `agents/*.md` — the team-lead orchestrator loads stage-specific instructions at spawn time. Reference files in `references/*.md` are loaded lazily per-stage.</note>

<workflow>
  <stage n="0" name="Setup">Detect mode. Extract parameters (--top-n, --total-m, or tickers). Create RUN_ID, output directory, tracking.json, agent team. MUST complete before any data fetch or agent spawning.</stage>
  <stage n="1" name="Data Collection" agent="data-collector">Fetch shared data ONCE: macro indicators, economic surprises, sector/sub-industry RS, market breadth, theme performance. Load references/gics_taxonomy.md and references/data_source_matrix.md. All downstream stages reuse this data.</stage>
  <stage n="2" name="Sub-Industry Screening" agent="sector-screener" modes="pipeline,screen">Score ALL 163 GICS Level 4 sub-industries on 11 dimensions (Growth, Profitability, Valuation, Macro Fit, Innovation, Regulatory, Capital Flows, RS, Cyclicality, Constituent Quality, Supply/Demand). Process in 3 parallel batches of ~54. Select top N sub-industries.</stage>
  <stage n="3" name="Sub-Industry Deep-Dive" agent="sector-screener" modes="pipeline,screen">Deep-dive top N sub-industries: Porter, TAM, catalysts, barriers, company universe, competitive dynamics, growth catalysts, profit pools. Process in parallel waves of max 4 agents.</stage>
  <stage n="4" name="Company Screening" agent="company-screener" modes="pipeline,screen">Screen companies across ALL top N sub-industries. Apply filters (market cap, growth, FCF, ROIC, price <$100/¥100). Score on growth/profitability/moat/valuation/management/risk/liquidity. Select top M by score across ALL sub-industries — NOT quota per sub-industry.</stage>

  <stage n="5" name="Financial Health" agent="fundamental-analyst" modes="pipeline,analyze,compare" per-company="true">DuPont 5-factor decomposition, Piotroski F-Score, Lynch categories, key ratio analysis. Scripts: fetch_financials.py, calculate_metrics.py.</stage>
  <stage n="6" name="Earnings Quality" agent="fundamental-analyst" modes="pipeline,analyze,compare" per-company="true" depends="5">Beneish M-Score, Montier C-Score, accruals quality, cash conversion, revenue recognition, capital allocation history (Buffett retention test, buyback ROI, M&A track record). Scripts: fetch_capital_structure.py, calculate_earnings_quality.py, diff_filings.py.</stage>
  <stage n="7" name="Industry & Competitive" agent="industry-analyst" modes="pipeline,analyze,compare" per-company="true">Porter's Five Forces, TAM/SAM/SOM, Morningstar moat assessment, BCG matrix, ecosystem mapping. REUSES industry thesis from Stage 3 if available. Scripts: fetch_peer_universe.py.</stage>
  <stage n="8" name="Supply Chain" agent="supply-chain-analyst" modes="pipeline,analyze,compare" per-company="true" depends="7">Tier 1-3 supplier mapping, geographic concentration (HHI), chokepoint identification, disruption scenario modeling, inventory-to-sales analysis. Scripts: fetch_supply_chain.py.</stage>
  <stage n="9" name="Macro & Geopolitics" agent="macro-analyst" modes="pipeline,analyze,compare" per-company="true">Dalio economic cycle, Druckenmiller liquidity, Four-Box Framework, Fed stance, CRP country risk, sanctions exposure, currency exposure. REUSES macro data from Stage 1. Scripts: fetch_global_macro.py, fetch_currency_exposure.py.</stage>
  <stage n="10" name="Valuation" agent="quant-analyst" modes="pipeline,analyze,compare" per-company="true" depends="5,7">DCF+Monte Carlo, comps, SOTP, LBO floor, reverse DCF, margin of safety. Scripts: calculate_metrics.py, forecast.py, fetch_private_comps.py.</stage>
  <stage n="11" name="Market Regime" agent="quant-analyst" modes="pipeline,analyze,compare" per-company="true" depends="10">Weinstein stage classification, CANSLIM, Soros reflexivity, factor attribution (Fama-French 5-factor), options signals, sentiment, institutional positioning. Scripts: fetch_technicals.py, compute_factors.py, fetch_cot.py, calculate_options.py, fetch_sentiment.py, fetch_short_interest.py, fetch_activist_exposure.py, compute_liquidity.py, compute_seasonality.py, compute_earnings_edge.py.</stage>
  <stage n="12" name="Risk Assessment" agent="risk-analyst" modes="pipeline,analyze,compare" per-company="true" depends="10">Scenario analysis (bull/base/bear), Marks 2nd-level thinking, Burry forensic, Klarman permanent-vs-temporary, kill switch definition, correlation regime. Scripts: fetch_credit.py, fetch_behavioral.py, compute_correlation_regime.py.</stage>
  <stage n="13" name="Alt Data & Digital" agent="alt-data-analyst" modes="pipeline,analyze,compare" per-company="true">Digital footprint (web traffic, app rankings), NLP earnings call analysis, channel checks, transaction data. Scripts: fetch_alternatives.py, fetch_news_nlp.py, calculate_candor.py.</stage>
  <stage n="14" name="Catalyst Intelligence" agent="catalyst-analyst" modes="pipeline,analyze,compare" per-company="true" depends="13">Catalyst calendar (FDA, earnings, product launches, regulatory), event-driven probability, pre/post-event drift (PEAD), catalyst sequencing. Scripts: compute_earnings_edge.py, event_study.py.</stage>
  <stage n="15" name="A-Share Analysis" agent="china-market-analyst" modes="pipeline,analyze,compare" per-company="true" condition="ticker ends with .SH or .SZ" depends="5-14">政策敏感性矩阵, 产业政策周期, 北向资金, 融资融券, 龙虎榜, 游资追踪. MANDATORY for .SH/.SZ tickers. SKIP for all others.</stage>

  <stage n="16" name="Scoring & Cross-Check" agent="scorer">Deterministic scoring (compute_scores.py) for each company. Cross-check contradictions (cross_check.py). Bayesian conviction calibration (calibrate_conviction.py). LLM agents may adjust Moat and Management ±2.0 based on qualitative findings. Rank companies by composite score.</stage>
  <stage n="17" name="Report Generation" agent="screening-report-writer,equity-report-writer">Pipeline: screening overview (3 horizons) + per-company deep-dives (3 horizons each). Screen: screening reports only. Analyze: per-company reports only. Compare: comparison reports with ranked table. All validated by validate_report.py before delivery.</stage>
</workflow>

<dependencies>
  Per-company analysis stages (5-15) have a dependency DAG enabling pipeline-wave parallelism across companies:

  <wave n="1" agents="4" stages="5,7,9,13" note="All independent — maximum parallelism" />
  <wave n="2" agents="4" stages="6,8,10,14" note="6←5, 8←7, 10←5+7, 14←13" />
  <wave n="3" agents="2" stages="11,12" note="11←10, 12←10" />
  <wave n="4" agents="1" stages="15" note="15←all, A-share only" />

  Scheduling rule: across M companies, stages execute as soon as their dependencies are met and an agent slot is free (max 4 concurrent). This creates a pipeline wave where different companies can be at different stages simultaneously.
</dependencies>

<modes>
  <mode name="pipeline" default="true">
    <trigger>"find best stocks", "top stocks", "全面筛选", "screen and analyze", "top picks"</trigger>
    <parameters>
      <parameter name="top-n" default="5" range="1-30">Number of top sub-industries after screening all 163.</parameter>
      <parameter name="total-m" default="10" range="1-100">Total companies to deep-dive. Selected by score across ALL top-n sub-industries — NOT quota per sub-industry.</parameter>
    </parameters>
    <stages>0→1→2→3→4→5-15(waves)→16→17</stages>
  </mode>

  <mode name="screen">
    <trigger>"screen sectors", "筛选行业", "best industries", "industry screening"</trigger>
    <parameters>
      <parameter name="top-n" default="30" range="1-163">Number of top sub-industries to deep-dive.</parameter>
    </parameters>
    <stages>0→1→2→3→4→17(screening reports only)</stages>
  </mode>

  <mode name="analyze">
    <trigger>"analyze [TICKER]", "deep dive [TICKER]", "investment thesis", "valuation of", "DCF"</trigger>
    <parameters>
      <parameter name="tickers" required="true">One or more ticker symbols from user prompt.</parameter>
    </parameters>
    <stages>0→1→5-15(waves)→16→17</stages>
  </mode>

  <mode name="compare">
    <trigger>"compare [T1],[T2]", "T1 vs T2", "which is better", "stock comparison"</trigger>
    <parameters>
      <parameter name="tickers" required="true">2-5 ticker symbols from user prompt.</parameter>
    </parameters>
    <stages>0→1→5-15(waves)→16(rank+merge)→17(comparison reports)</stages>
    <constraints>Max 5 stocks. Identical valuation methodology across all.</constraints>
  </mode>
</modes>

<rules>
  <rule name="Report Language">ALL reports MUST be written in Chinese (中文). Technical terms in English. GICS names: "Semiconductors (半导体)". Source citations in original language.</rule>
  <rule name="Price Filter">Growth-stage companies only. US < $100, China A-shares < ¥100. Skip filter if user specifies ticker. Filter BEFORE watchlist ranking.</rule>
  <rule name="Stock Price Display">Every company in any table/list must include 当前股价. Format: "$XX.XX" or "¥XX.XX".</rule>
  <rule name="All 3 Horizons">Always produce long/mid/short-term reports. Never ask — always produce all three.</rule>
  <rule name="UV Run">ALL Python scripts run via `uv run python ${PLUGIN_ROOT}/scripts/<script>.py`.</rule>
  <rule name="Run Directory">Each run creates `./reports/[RUN_ID]/` where RUN_ID = YYYYMMDDHHmm.</rule>
  <rule name="Ranked Directories">Output directories use rank-prefixed names: `NNN-[TICKER]`. Pipeline/compare: rank after Stage 16. Single analyze: always 001.</rule>
  <rule name="Numbered Stock Index">Every report includes 推荐标的排名 with 001, 002, 003 format. Top-ranked MUST be 001.</rule>
  <rule name="Company Selection">Top M companies selected by score across ALL top-N sub-industries — NOT equally distributed.</rule>
  <rule name="A-Share Mandatory">Stage 15 is MANDATORY for .SH/.SZ tickers. SKIP for all others.</rule>
  <rule name="agent-team" mandatory="true">ALL work MUST use agent team. Create team via TeamCreate before spawning any agents.</rule>
  <rule name="team-lead-delegation" mandatory="true">Team Lead NEVER analyzes directly. Only spawns agents, coordinates, and quality-gates.</rule>
  <rule name="shared-data-once" mandatory="true">Macro, RS, breadth, theme data fetched ONCE in Stage 1. All downstream stages reuse — never re-fetch.</rule>
  <rule name="context-eviction" mandatory="true">After each stage: write summary → drop raw data. If context >80%, offload via persist.py.</rule>
</rules>

<constraints>
  <constraint name="NEVER Analyze Directly">Team Lead NEVER runs scripts, fetches data, or performs analysis. ALL work delegated to specialist agents.</constraint>
  <constraint name="Tracking JSON Updated">Tracking JSON MUST be updated BEFORE advancing to the next stage. Both status changes (previous complete, next in_progress) in a single write.</constraint>
  <constraint name="Team First">Team creation (TeamCreate) is the FIRST action — before any scripts or data fetches.</constraint>
  <constraint name="Data via Agents">Data-fetch scripts are run by data-collector or search-agent teammates, NOT by the team lead directly.</constraint>
  <constraint name="Max 4 Concurrent">Cap parallel agents at 4 to manage context window.</constraint>
  <constraint name="Quality Gate">Report cannot be delivered until pre-delivery checklist passes. If any gate fails: "INCOMPLETE ANALYSIS — [reason]".</constraint>
  <constraint name="Level 4 Structure">Sub-Industry is the structural unit in reports — Level 1/2/3 appear only as context within Level 4 entries.</constraint>
  <constraint name="Cleanup">After report delivery: delete intermediate files, terminate all agents, delete team.</constraint>
</constraints>

<criteria name="Skip Conditions">
  Stage 2-4 (Screening): SKIP for analyze/compare modes.
  Stage 3 (Deep-Dive): SKIP if top-n = 1 (single sub-industry).
  Stage 15 (A-Share): SKIP for non-.SH/.SZ tickers.
  Stage 17 screening reports: SKIP for analyze/compare modes.
  Stage 17 company reports: SKIP for screen mode.
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
  <ref>Plugin root: `${PLUGIN_ROOT}` — agents, scripts, skills, references, rules</ref>
  <ref>Plugin data: `${PLUGIN_DATA}` — caches, venv, persisted state</ref>
  <ref>GICS taxonomy: `references/gics_taxonomy.md` — full 4-level hierarchy with codes and ETF proxies</ref>
  <ref>Data source matrix: `references/data_source_matrix.md` — source tiers, confidence caps</ref>
  <ref>Screening templates: `references/screening_report_templates.md` — report formats, scoring formulas</ref>
  <ref>Equity templates: `references/equity_report_templates.md` — deep-dive report formats</ref>
  <ref>Scoring calibration: `references/scoring_calibration.md` — calibration targets</ref>
</references>
