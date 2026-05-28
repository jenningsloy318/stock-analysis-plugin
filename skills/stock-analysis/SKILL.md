---
name: stock-analysis
description: "Unified equity research pipeline: screen top sub-industries → pick best companies → deep-dive each. Modes: pipeline (default), screen, analyze, compare. Triggers on 'find best stocks', 'screen sectors', 'analyze [TICKER]', 'compare T1,T2'."
author: Jennings Liu
version: "1.03.01"
license: MIT
---

<platform-paths>
  PLUGIN_ROOT:
    claude: ${CLAUDE_PLUGIN_ROOT}
    gemini: ${extensionPath}
  PLUGIN_DATA:
    claude: ${CLAUDE_PLUGIN_DATA}
    gemini: ${extensionPath}/data
</platform-paths>

<purpose>Unified equity research pipeline. The orchestrator (team lead) coordinates the full funnel: screen GICS Level 4 sub-industries → pick top M companies across top N sub-industries → deep-dive each company in parallel branches → unified reports. Three modes: pipeline (default), screen, analyze, compare. NEVER performs analysis directly — only spawns, coordinates, scores, and quality-gates.</purpose>

<triggers>
Triggers on ALL of the following (mode detected from phrasing):
- **pipeline** (default): "find best stocks", "top stocks", "全面筛选", "best companies", "screen and analyze", "top picks"
- **screen**: "screen sectors", "筛选行业", "best industries", "industry screening", "sector rotation"
- **analyze**: "analyze [TICKER]", "deep dive [TICKER]", "investment thesis [TICKER]", "valuation of [TICKER]", "due diligence [COMPANY]", "DCF [TICKER]", "quick overview [TICKER]"
- **compare**: "compare [T1],[T2]", "T1 vs T2", "which is better T1 or T2", "stock comparison"
Do NOT trigger on: general market commentary, non-financial queries.
</triggers>

<modes>
  <mode name="pipeline" default="true">
    <description>Full funnel: screen → pick → deep-dive. Screen all 163 GICS Level 4 sub-industries, select top N, screen companies across them, pick top M, then deep-dive each company in parallel branches. Produces screening overview + per-company reports.</description>
    <trigger>"find best stocks", "top stocks", "全面筛选", "screen and analyze", "top picks"</trigger>
    <parameters>
      <parameter name="top-n" default="5" range="1-30">Number of top sub-industries to deep-dive after screening all 163.</parameter>
      <parameter name="total-m" default="10" range="1-100">Total companies to deep-dive. Selected by score across ALL top-n sub-industries — not quota per sub-industry. Sub-industry A may contribute 4 companies while B contributes 1.</parameter>
    </parameters>
    <stages>0→1→2→3(parallel branches)→4→5</stages>
    <max-agents>4</max-agents>
  </mode>

  <mode name="screen">
    <description>Industry screening only. Screen all 163 GICS Level 4 sub-industries → deep-dive top N → produce company watchlist. NO deep-dive analysis on individual companies. Produces screening reports only.</description>
    <trigger>"screen sectors", "筛选行业", "best industries", "industry screening", "sector rotation", "best sectors"</trigger>
    <parameters>
      <parameter name="top-n" default="30" range="1-163">Number of top sub-industries to deep-dive.</parameter>
    </parameters>
    <stages>0→1→2→5(screening reports only)</stages>
    <max-agents>4</max-agents>
  </mode>

  <mode name="analyze">
    <description>Deep-dive analysis on one or more specific tickers. Skips screening entirely. Runs full analysis stages per ticker in parallel branches.</description>
    <trigger>"analyze [TICKER]", "deep dive [TICKER]", "investment thesis", "valuation of [TICKER]", "due diligence", "quick overview [TICKER]", "DCF [TICKER]"</trigger>
    <parameters>
      <parameter name="tickers" required="true">One or more ticker symbols extracted from user prompt.</parameter>
    </parameters>
    <stages>0→3(parallel branches per ticker)→4→5</stages>
    <max-agents>4</max-agents>
  </mode>

  <mode name="compare">
    <description>Side-by-side comparison of 2-5 stocks. Skips screening. Runs analysis on all tickers in parallel, then produces ranked comparison table.</description>
    <trigger>"compare [T1],[T2]", "T1 vs T2", "which is better", "stock comparison"</trigger>
    <parameters>
      <parameter name="tickers" required="true">2-5 ticker symbols extracted from user prompt.</parameter>
    </parameters>
    <stages>0→3(parallel branches per ticker)→4(comparison merge)→5</stages>
    <max-agents>4</max-agents>
    <constraints>
      - Max 5 stocks per comparison
      - Identical valuation methodology across all stocks
    </constraints>
  </mode>
</modes>

<rules>
  <rule name="Report Language">ALL reports MUST be written in Chinese (中文). Technical terms in English. GICS names: "Semiconductors (半导体)". Source citations in original language.</rule>
  <rule name="Price Filter">Growth-stage companies only. US < $100, China A-shares < ¥100. Skip filter if user specifies ticker. Filter BEFORE watchlist ranking.</rule>
  <rule name="Stock Price Display">Every company in any table/list must include 当前股价. Format: "$XX.XX" or "¥XX.XX". Fetched at analysis time.</rule>
  <rule name="All 3 Horizons">Always produce long/mid/short-term reports. Never ask — always produce all three.</rule>
  <rule name="UV Run">ALL Python scripts run via `uv run python ${PLUGIN_ROOT}/scripts/<script>.py`.</rule>
  <rule name="Run Directory">Each run creates `./reports/[RUN_ID]/` where RUN_ID = YYYYMMDDHHmm. Within it: `NNN-[TICKER]/` per stock.</rule>
  <rule name="Ranked Directory Naming">Output directories use rank-prefixed names: `NNN-[TICKER]`. Pipeline/compare: rank after scoring. Single analyze: always 001.</rule>
  <rule name="Numbered Stock Index">Every report includes 推荐标的排名 with 001, 002, 003 format. Top-ranked MUST be 001.</rule>
  <rule name="Tracking JSON">Each run creates `./reports/[RUN_ID]/tracking.json` (pipeline/screen) or `./reports/[RUN_ID]/NNN-[TICKER]/tracking.json` (analyze/compare). Update BEFORE advancing stages.</rule>
  <rule name="A-Share Detection">If ticker ends with .SH or .SZ, CN1+CN2 stages are MANDATORY in analysis branches.</rule>
  <rule name="Company Selection">In pipeline mode, top M companies are selected by score across ALL top-N sub-industries — NOT equally distributed. Higher-scoring sub-industries naturally contribute more companies.</rule>
</rules>

<agent-team-protocol>
This skill ALWAYS operates as an agent team. Create team IMMEDIATELY as first action.

Pipeline mode: orchestrator runs stages 0→1→2 sequentially, then spawns parallel analysis branches in stage 3 (max 4 concurrent), then stage 4 scoring, then stage 5 reports.
Screen mode: orchestrator runs stages 0→1→2, then stage 5 (screening reports only).
Analyze mode: orchestrator runs stage 0, then stage 3 branches for each specified ticker.
Compare mode: same as analyze, but stage 4 merges into ranked comparison.

ENFORCEMENT: Orchestrator MUST NOT run scripts or analysis directly — always delegate to specialist agents.
</agent-team-protocol>

<workflow>
  <!-- Pipeline mode (default): 0→1→2→3→4→5 -->
  <!-- Screen mode: 0→1→2→5(screening) -->
  <!-- Analyze mode: 0→3→4→5 -->
  <!-- Compare mode: 0→3→4(comparison)→5 -->

  <stage n="0" name="Setup & Shared Data">
    1. Detect mode from user prompt (pipeline/screen/analyze/compare). 2. Extract parameters: --top-n, --total-m, or tickers. 3. RUN_ID = $(date +%Y%m%d%H%M). 4. Create output directory. 5. Create tracking.json. 6. Create agent team: TeamCreate({ name: "stock-analysis-[RUN_ID]" }). 7. Spawn search-agent for shared data: fetch_macro.py, fetch_economic_surprises.py, compute_sector_rs.py (--level sub-industry --flat), fetch_market_breadth.py (--skip-constituents), fetch_theme_performance.py, persist.py init. 8. Load references/gics_taxonomy.md, references/data_source_matrix.md. MACRO/RS/BREADTH DATA FETCHED ONCE — reused by all subsequent stages.
  </stage>

  <!-- SCREENING STAGES (pipeline + screen only) -->

  <stage n="1" name="Sub-Industry Screening" agent="sector-screener" modes="pipeline,screen">
    Score ALL 163 GICS Level 4 sub-industries on 11 dimensions: Growth, Profitability, Valuation, Macro Fit, Innovation, Regulatory, Capital Flows, RS, Cyclicality, Constituent Quality, Supply/Demand. Process in 3 parallel batches of ~54. Select top N sub-industries (default: 5 for pipeline, 30 for screen). Write screening summary to ./reports/[RUN_ID]/stage1.md.
  </stage>

  <stage n="2" name="Deep-Dive + Company Screening" agent="sector-screener,company-screener" modes="pipeline,screen">
    Phase A — Sub-Industry Deep Dive: Deep-dive top N sub-industries (Porter, TAM, catalysts, barriers, supply chain). Process in batches of 3 parallel agents.
    Phase B — Company Screening: Screen companies across ALL top N sub-industries. Apply filters: market cap >$500M, revenue growth >median, positive FCF, ROIC>WACC, stock price <$100/$100. Score on growth/profitability/moat/valuation/management/risk/liquidity. Select top M companies by score ACROSS ALL sub-industries (not quota per sub-industry). Write to ./reports/[RUN_ID]/stage2.md.
  </stage>

  <!-- ANALYSIS BRANCHES (pipeline + analyze + compare) -->

  <stage n="3" name="Analysis Branches" agent="parallel branches" modes="pipeline,analyze,compare">
    For each company/ticker, spawn an analysis branch. Max 4 concurrent branches. Each branch runs sub-stages sequentially:

    3a. Financial Health & DuPont (fundamental-analyst): DuPont 5-factor, Piotroski, Lynch categories. Writes stage3a.md.
    3b. Capital Allocation & Earnings Quality (fundamental-analyst): Buffett retention, Mauboussin, Beneish, cash conversion. Writes stage3b.md.
    3c. Industry & Supply Chain (industry-analyst, supply-chain-analyst): Porter's Five Forces, TAM/SAM/SOM, moat, supply chain mapping. REUSES industry thesis from Stage 2 if available. Writes stage3c.md.
    3d. Macro & Geopolitics (macro-analyst): Dalio cycle, Four-Box, Fed stance, CRP risk, sanctions, currency. REUSES macro data from Stage 0. Writes stage3d.md.
    3e. Valuation & Market Regime (quant-analyst): DCF+Monte Carlo, comps, SOTP, reverse DCF, Weinstein, CANSLIM, sentiment, options. Writes stage3e.md.
    3f. Risk & Alt-Data (risk-analyst, alt-data-analyst): Scenario analysis, Marks, Burry, kill switch, ESG, web traffic, NLP, channel checks, catalysts. Writes stage3f.md.
    3g. A-Share Specific (china-market-analyst): CN1 policy + CN2 capital flows. MANDATORY for .SH/.SZ tickers. Writes stage3g.md.

    Pipeline mode: branches receive pre-loaded artifacts from Stage 0-2 (macro, industry thesis, supply chain, sector RS). Avoids redundant fetching.
    Analyze/Compare mode: branches fetch their own data (no prior screening).
  </stage>

  <!-- SCORING & REPORTING -->

  <stage n="4" name="Scoring & Cross-Check" agent="orchestrator">
    Run compute_scores.py for each company → deterministic 1-10 component scores + conviction. Run cross_check.py: if valuation implies >30% overvaluation, re-examine moat. If forensic red flags >=3, re-examine financial health. Flag contradictions.
    Compare mode: merge scores into ranked comparison table.
  </stage>

  <stage n="5" name="Report Generation" agent="screening-report-writer,equity-report-writer">
    Pipeline mode: screening-report-writer produces 3 screening overview reports. equity-report-writer produces 3 reports per company (NNN-[TICKER]_long/mid/short_[DATE].md). Total: 3 screening + (M × 3) company reports.
    Screen mode: screening-report-writer produces 3 screening reports with watchlist.
    Analyze mode: equity-report-writer produces 3 reports per ticker.
    Compare mode: equity-report-writer produces 3 comparison reports with ranked table.
    All reports validated by validate_report.py before delivery.
  </stage>
</workflow>

<parallel-execution>
  Pipeline: [0] → [1: 3 batches × sector-screener] → [2A: deep-dive batches + 2B: company-screener] → [3: branches max 4] → [4] → [5]
  Screen:   [0] → [1: 3 batches × sector-screener] → [2A+2B] → [5: screening reports]
  Analyze:  [0] → [3: branches max 4] → [4] → [5]
  Compare:  [0] → [3: branches max 4] → [4: merge+rank] → [5]
  Max concurrent agents: 4
</parallel-execution>

<agent-team>
  | Agent | Stages | Purpose |
  |-------|--------|---------|
  | sector-screener | 1, 2A | Sub-industry scoring and deep-dive |
  | company-screener | 2B | Company filtering, scoring, ranking across sub-industries |
  | screening-report-writer | 5 | Screening overview reports |
  | fundamental-analyst | 3a, 3b | Financial health, capital allocation, earnings quality |
  | industry-analyst | 3c | Competitive landscape, TAM, moat |
  | supply-chain-analyst | 3c | Supply chain resilience, concentration |
  | macro-analyst | 3d | Economic cycle, monetary, geopolitical |
  | quant-analyst | 3e | Valuation, technicals, sentiment, regime |
  | risk-analyst | 3f | Risk assessment, kill switch, ESG |
  | alt-data-analyst | 3f | Digital footprint, NLP, channel checks |
  | catalyst-analyst | 3f | Catalyst calendar, event probability |
  | china-market-analyst | 3g | A-share policy, northbound flows, margin trading |
  | equity-report-writer | 5 | Per-company deep-dive reports |
  | search-agent | All | Multi-source financial web search, script execution |
</agent-team>

<integration>
  <shared-data>
    Stage 0 fetches macro, sector RS, market breadth, theme performance ONCE. All subsequent stages reuse this data:
    - Stage 1: RS + breadth feed Capital Flows, RS, Constituent Quality scoring dimensions
    - Stage 2: macro context feeds company screening
    - Stage 3 branches: macro → sub-stage 3d, industry thesis → sub-stage 3c, supply chain → sub-stage 3c
  </shared-data>
  <output-structure>
    Pipeline: ./reports/[RUN_ID]/
    ├── tracking.json
    ├── SCREEN_long_[DATE].md
    ├── SCREEN_mid_[DATE].md
    ├── SCREEN_short_[DATE].md
    ├── 001-[TICKER]/
    │   ├── 001-[TICKER]_long_[DATE].md
    │   ├── 001-[TICKER]_mid_[DATE].md
    │   └── 001-[TICKER]_short_[DATE].md
    ├── 002-[TICKER]/
    │   └── ...
    └── [M]-[TICKER]/
        └── ...

    Screen: ./reports/[RUN_ID]/
    ├── tracking.json
    ├── SCREEN_long_[DATE].md
    ├── SCREEN_mid_[DATE].md
    └── SCREEN_short_[DATE].md

    Analyze: ./reports/[RUN_ID]/
    ├── 001-[TICKER]/
    │   ├── tracking.json
    │   ├── 001-[TICKER]_long_[DATE].md
    │   ├── 001-[TICKER]_mid_[DATE].md
    │   └── 001-[TICKER]_short_[DATE].md

    Compare: ./reports/[RUN_ID]/
    ├── 001-[TICKER]/... (ranked by score)
    ├── 002-[TICKER]/...
    └── COMPARE_[DATE].md (3 horizon comparison reports)
  </output-structure>
  <consumes-from-market-daily>
    If market-daily report exists within 24 hours, reuse macro/breadth data.
  </consumes-from-market-daily>
</integration>

<context-eviction>
After each stage: write stage summary → persist.py save → drop raw data. If context >80%, offload.
</context-eviction>

<pre-delivery>
Verify: macro ≤30d fresh, sub-industry data ≤90d fresh, all metrics cited with source+date, Chinese report, no invented data, kill switches defined, methodology attribution present, 5 random fact checks passed.
If any gate fails: "INCOMPLETE ANALYSIS — [reason]"
</pre-delivery>

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
