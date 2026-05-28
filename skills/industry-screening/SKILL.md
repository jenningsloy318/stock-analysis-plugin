---
name: industry-screening
description: Top-down GICS Level 4 sub-industry screening funnel. Produces ranked watchlists. Triggers on "screen sectors", "best industries", "top-down screening", "sector rotation".
author: Jennings Liu
version: "1.01.01"
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

<purpose>Industry-screening-orchestrator (team lead) spawns specialist screener agents in parallel. NEVER performs analysis directly. Uses GICS Level 4 (Sub-Industry, 163) as the ONLY screening unit. Supports 5 screening modes: Broad, Thematic, Short-Candidate, Pair-Trade, QARP.</purpose>

<triggers>Triggers on: "screen sectors", "best industries", "top-down screening", "find stocks in [SECTOR]", "industry screening", "sector rotation", "short candidates", "pair trade ideas", "magic formula screen". Do NOT trigger on: single-stock analysis (use stock-analysis), non-screening queries.</triggers>

<rules>
  <rule name="Report Language">ALL reports MUST be written in Chinese (中文). Technical terms in English. GICS names: "Semiconductors (半导体)".</rule>
  <rule name="Price Filter">Growth-stage companies only. US < $100, China A-shares < ¥100. Filter before watchlist ranking.</rule>
  <rule name="All 3 Horizons">Always produce long/mid/short-term reports. Never ask — always produce all three.</rule>
  <rule name="UV Run">ALL Python scripts run via `uv run python ${PLUGIN_ROOT}/scripts/<script>.py`. Output to `./reports/YYYYMMDDHHmm/`.</rule>
  <rule name="Run Directory">Each run creates `./reports/YYYYMMDDHHmm/`. RUN_ID set once at run start.</rule>
  <rule name="Tracking JSON">Creates `./reports/[RUN_ID]/SCREENING-tracking.json`. Update phase status BEFORE advancing.</rule>
  <rule name="Numbered Stock Index">Every report includes "推荐标的排名" with 001, 002, 003 format. Top-ranked MUST be 001. Report filenames: [NNN]_[SECTOR]_[CODE]_[horizon]_[DATE].md.</rule>
</rules>

<agent-team-protocol>
  This skill ALWAYS operates as an agent team. Create team IMMEDIATELY as first action.

  Step 0: RUN_ID = $(date +%Y%m%d%H%M). TeamCreate({ name: "industry-screening-[RUN_ID]" }). Create `./reports/[RUN_ID]/`. Create `./reports/[RUN_ID]/SCREENING-tracking.json`.
  Step 1: Spawn search-agent for setup scripts (fetch_macro, fetch_economic_surprises, compute_sector_rs, persist.py init, source coverage plan).
  Steps 2+: Spawn screener agents per parallel execution map. Each writes to ./reports/[RUN_ID]/.
  Cleanup: Delete intermediate files; keep only 3 final reports. Delete team.

  ENFORCEMENT: Orchestrator MUST NOT run scripts or analysis directly.
</agent-team-protocol>

<workflow>
  <phase n="0" name="Setup" agent="orchestrator">
    1. Determine SCOPE and MODE. Modes: Broad (all 163), Thematic (theme-focused), Short-Candidate (vulnerability scan), Pair-Trade (RS dispersion), QARP (Magic Formula). 2. RUN_ID = $(date +%Y%m%d%H%M). 3. Create output directory. 4. Create tracking.json. 5. Run macro fetch + compute_sector_rs + persist.py init. 6. Load references/gics_taxonomy.md, references/data_source_matrix.md.
  </phase>

  <phase n="1" name="Full Level 4 Screening" agent="sector-screener">
    Scope depends on MODE:
    - **Broad**: Score ALL 163 GICS Level 4 sub-industries (3 batches × ~54)
    - **Thematic**: Score theme-relevant sub-industries (e.g., AI supply chain, green energy, aging population healthcare, cybersecurity)
    - **Short-Candidate**: Vulnerability scan — score sub-industries on: high leverage, declining RS, peak margins, negative estimate revisions, supply chain exposure
    - **Pair-Trade**: Score all 163 on RS dispersion — identify sectors with widest performance spread
    - **QARP**: Score all 163 on Greenblatt Magic Formula (Earnings Yield + ROC combined rank)

    Score on 11 dimensions: Growth, Profitability, Valuation, Macro Fit, Innovation, Regulatory, Capital Flows, RS, Cyclicality, Constituent Quality, Supply/Demand. Select top sub-industries based on mode.
  </phase>

  <phase n="2" name="Deep Dive" agent="sector-screener">
    Depth depends on MODE:
    - **Broad**: Top 30 sub-industries — Porter, TAM, catalysts, barriers, supply chain
    - **Thematic**: All theme-relevant sub-industries
    - **Short-Candidate**: Top 20 most vulnerable — deep dive into bear cases, structural deterioration
    - **Pair-Trade**: Top 5 sectors with widest dispersion — long/short pair fundamentals
    - **QARP**: Top 30 by combined rank — deep dive into competitive advantages
  </phase>

  <phase n="3" name="Company Screening" agent="company-screener">
    Target depends on MODE:
    - **Broad**: 100 long candidates (~3-4 per sub-industry)
    - **Thematic**: 50 theme-aligned candidates
    - **Short-Candidate**: 50 short candidates with specific bear theses
    - **Pair-Trade**: Long/short pairs within sectors (typically 5-10 pairs)
    - **QARP**: 50 quality-at-reasonable-price candidates
  </phase>

  <phase n="4" name="Reports" agent="screening-report-writer">
    Synthesize ALL phases into 3 horizon reports. Structure: Executive Summary → Macro Environment → Leaderboard → Deep Dive Highlights → Watchlist → Next Actions → Risks → Appendix.
  </phase>
</workflow>

<screening-modes>
  <mode name="Broad" icon="🌐">
    <description>Full GICS Level 4 coverage. 163 sub-industries scored → top 30 deep-dived → 100 companies. Best for comprehensive market mapping and new idea generation.</description>
    <trigger>Default mode. "screen sectors", "best industries", "top-down"</trigger>
  </mode>
  <mode name="Thematic" icon="🎯">
    <description>Theme-focused screening. Select sub-industries aligned with a specific theme (AI, green energy, aging population, cybersecurity, space economy, fintech). Scores all theme-relevant sub-industries → deep dives → 50 candidates.</description>
    <trigger>"AI supply chain", "green energy transition", "aging population stocks", "cybersecurity companies", "space economy", "[THEME] theme screen"</trigger>
    <themes>
      <theme name="AI Supply Chain">Semiconductors, Semiconductor Equipment, Data Centers, Electronic Components, Application Software, Systems Software, IT Consulting</theme>
      <theme name="Green Energy Transition">Renewable Electricity, Solar, Wind, Electrical Components, Electric Utilities, Energy Storage, Lithium, Rare Earth</theme>
      <theme name="Aging Population Healthcare">Biotechnology, Health Care Equipment, Managed Health Care, Life Sciences Tools, Health Care Facilities, Pharmaceuticals</theme>
      <theme name="Cybersecurity">Systems Software, IT Consulting, Communications Equipment, Application Software</theme>
      <theme name="Space Economy">Aerospace & Defense, Communications Equipment, Semiconductors, Industrial Machinery</theme>
      <theme name="Fintech Disruption">Consumer Finance, Transaction Processing, Application Software, Regional Banks, Diversified Banks</theme>
      <theme name="Robotics & Automation">Industrial Machinery, Electrical Components, Semiconductors, Electronic Components, Application Software</theme>
      <theme name="Water Infrastructure">Water Utilities, Construction & Engineering, Industrial Machinery, Life Sciences Tools</theme>
    </themes>
  </mode>
  <mode name="Short-Candidate" icon="🔻">
    <description>Vulnerability scan. Score sub-industries on: high leverage (Net Debt/EBITDA > 4x), declining RS (bottom quartile over 6M), peak margins (margins >90th percentile of 10yr range), negative estimate revisions (3M), supply chain exposure (Taiwan/China HHI). Top 20 most vulnerable → bear case deep dives → 50 short candidates.</description>
    <trigger>"short candidates", "vulnerability screen", "what to avoid", "overvalued sectors", "bear case screening"</trigger>
  </mode>
  <mode name="Pair-Trade" icon="⚖️">
    <description>Sector RS leaderboard → identify sectors with widest dispersion between top and bottom performers → deep dive fundamentals for long/short pairs → pair-level comparative analysis. Produces long/short trade ideas within the same sector.</description>
    <trigger>"pair trade ideas", "long short pairs", "sector dispersion", "relative value pairs", "market neutral ideas"</trigger>
  </mode>
  <mode name="QARP" icon="📊">
    <description>Quality-At-Reasonable-Price using Greenblatt's Magic Formula methodology: rank all sub-industries by combined Earnings Yield (EBIT/EV) + Return on Capital (EBIT/(NWC+NFA)). Top 30 by combined rank → deep dive → 50 high-quality companies at reasonable prices.</description>
    <trigger>"magic formula", "quality at reasonable price", "QARP screen", "value quality screen", "Greenblatt screen"</trigger>
  </mode>
</screening-modes>

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

<parallel-execution>
  Broad:  [S1 batch A + S1 batch B + S1 batch C] → [S2 top sectors A-F] → [S3 batches 1-3] → Report
  Theme:  [S1 themed batches 1-2] → [S2 all themed] → [S3 single batch] → Report
  Short:  [S1 vulnerability scan] → [S2 bear cases batches 1-2] → [S3 short candidates] → Report
  Pair:   [S1 sector RS + S2 long batch + S2 short batch] → [S3 pair analysis] → Report
  QARP:   [S1 Magic Formula screen] → [S2 top 30 deep dive] → [S3 quality candidates] → Report
  Max 4 concurrent agents.
</parallel-execution>

<context-eviction>
  After each phase: write phase summary → persist.py save → drop raw data. If context >80%, offload.
</context-eviction>

<pre-delivery>
  Verify: macro ≤30d fresh, sub-industry data ≤90d fresh, leaderboard matches mode, screen-specific gates met, all metrics cited with source+date, Chinese report, no invented data.
</pre-delivery>

<agent-team>
  | Agent | Phases | Purpose |
  |-------|--------|---------|
  | sector-screener | 1, 2 | Sector ranking, sub-industry deep-dive |
  | company-screener | 3 | Company filtering, scoring, ranking |
  | screening-report-writer | 4 | Synthesize phases into final reports |
  | search-agent | All | Financial web search, script execution |
</agent-team>

<integration>
  After screening: top-ranked companies can be deep-dived with stock-analysis. Macro context and industry thesis feed directly into stock-analysis Stages 4 and 3.
</integration>
