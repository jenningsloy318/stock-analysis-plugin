---
name: industry-screening
description: Top-down GICS Level 4 sub-industry screening funnel. Produces ranked watchlists. Triggers on "screen sectors", "best industries", "top-down screening", "sector rotation".
author: Jennings Liu
version: "1.0.51"
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

<purpose>Industry-screening-orchestrator (team lead) spawns specialist screener agents in parallel. NEVER performs analysis directly. Uses GICS Level 4 (Sub-Industry, 163) as the ONLY screening unit. Reports present flat sub-industry leaderboards — no Level 1/2/3 grouping as standalone sections.</purpose>

<triggers>Triggers on: "screen sectors", "best industries", "top-down screening", "find stocks in [SECTOR]", "industry screening", "sector rotation". Do NOT trigger on: single-stock analysis (use stock-analysis), non-screening queries.</triggers>

<rules>
  <rule name="Report Language">ALL reports MUST be written in Chinese (中文). Technical terms in English. GICS names: "Semiconductors (半导体)".</rule>
  <rule name="Price Filter">Growth-stage companies only. US < $100, China A-shares < ¥100. Filter before watchlist ranking.</rule>
  <rule name="All 3 Horizons">Always produce long/mid/short-term reports. Never ask — always produce all three.</rule>
  <rule name="UV Run">ALL Python scripts run via `uv run python ${PLUGIN_ROOT}/scripts/<script>.py`. Output to `./reports/screening/`.</rule>
</rules>

<agent-team-protocol>
  This skill ALWAYS operates as an agent team. Create team IMMEDIATELY as first action.

  Step 0: TeamCreate({ name: "industry-screening-[YYYYMMDD]" })
  Step 1: Spawn search-agent to run setup scripts (fetch_macro, fetch_economic_surprises, compute_sector_rs, persist.py init). Terminate after completion.
  Steps 2+: Spawn screener agents per parallel execution map. Each writes phase summaries. Terminate each after completion.
  Cleanup: Delete intermediate files; keep only 3 final reports. Delete team.

  ENFORCEMENT: Orchestrator MUST NOT run scripts or analysis directly. All work delegated to sub-agents.
</agent-team-protocol>

<workflow>
  <phase n="0" name="Setup" agent="orchestrator">
    1. Determine scope: all sectors / specific sector / theme. Default: ask user. 2. All 3 horizons auto-produced. 3. Run macro fetch + economic surprises + sector/sub-industry RS + persist.py init + source coverage plan. 4. Load references/gics_taxonomy.md, references/data_source_matrix.md.
  </phase>
  <phase n="1" name="Sub-Industry Screening" agent="sector-screener">
    Spawn up to 3 agents in parallel (batched by parent sector). Two-pass: Pass 1 scores Growth, Profitability, Valuation, Macro Fit, Innovation, Regulatory, Capital Flows, RS, Cyclicality, Constituent Quality, Supply/Demand. Pass 2 ranks sub-industries within above-median sectors. Orchestrator synthesizes into flat sub-industry leaderboard (top 15-20).
  </phase>
  <phase n="2" name="Deep Dive" agent="sector-screener">
    Spawn 1 per top sub-industry (max 2 parallel). Analyzes: definition, company universe, Porter, growth catalysts, barriers, TAM, key players, supply chain, life cycle, profit pool. Writes deepdive-[CODE]-[NAME].md.
  </phase>
  <phase n="3" name="Company Screening" agent="company-screener">
    Spawn 1-2 agents. Filter: market cap >$500M, revenue growth >median, positive FCF, ROIC>WACC. Score: Growth 20%, Profitability 20%, Moat 20%, Valuation 15%, Management 10%, Risk 10%, Liquidity 5%. Writes companies-[CODE].md.
  </phase>
  <phase n="4" name="Reports" agent="screening-report-writer">
    Pre-compute filenames: [SUB_INDUSTRY_CODE]_long_[DATE].md. Agent synthesizes phases into 3 horizon reports. Structure: Executive Summary → Macro → Leaderboard → Deep Dive → Watchlist → Next Actions → Risks → Appendix.
  </phase>
</workflow>

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
  Broad:  [S1 batch A + S1 batch B + S1 batch C] → [S2 top A + S2 top B] → [S3] → Report
  Single: [S1] → [S2] → [S3] → Report
  Theme:  [S1 themed] → [S2] → [S3] → Report
  Max 3 concurrent agents.
</parallel-execution>

<phase-depth>
  | Phase | Broad Screen | Single Sector | Thematic |
  |-------|-------------|---------------|----------|
  | 1: Sub-Industry Screening | Full (3 batches) | Light (1 sector) | Medium (3-5 sectors) |
  | 2: Deep Dive | Top 2-3 | Top 2 | Top 2 |
  | 3: Company Screening | Top 1-2 | Top 1-2 | Top 1-2 |
  | 4: Report | Full | Full | Full |
</phase-depth>

<context-eviction>
  After each phase: write phase summary → persist.py save → drop raw data from context. If context >80%, offload more.
</context-eviction>

<pre-delivery>
  Verify: macro ≤30d fresh, sub-industry data ≤90d fresh, leaderboard ≥10 sub-industries, NO Level 1/2/3 standalone sections, selected sub-industry has structural thesis with GICS code, watchlist ≥10 companies, all metrics cited with source+date, Chinese report, no invented data.
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
  After screening: "Top-ranked companies can be deep-dived with the stock-analysis skill. Run full equity research on any ticker?" Macro context and industry thesis feed directly into stock-analysis Stages 4 and 3.
</integration>
