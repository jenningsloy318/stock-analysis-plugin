---
name: industry-screening
description: Top-down GICS Level 4 sub-industry screening funnel. Produces ranked watchlists. Triggers on "screen sectors", "best industries", "top-down screening", "sector rotation".
author: Jennings Liu
version: "1.0.54"
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
    1. Determine scope: all sectors / specific sector / theme. Default: ask user. 2. All 3 horizons auto-produced. 3. Run macro fetch + economic surprises + compute_sector_rs.py --level sub-industry --flat + persist.py init + source coverage plan. 4. Load references/gics_taxonomy.md, references/data_source_matrix.md.
  </phase>
  <phase n="1" name="Full Level 4 Screening" agent="sector-screener">
    Score ALL 163 GICS Level 4 sub-industries directly — no sector-level pre-filtering. Spawn up to 3 agents in parallel, each handling a batch of ~54 sub-industries. Score on 11 dimensions: Growth, Profitability, Valuation, Macro Fit, Innovation, Regulatory, Capital Flows, RS, Cyclicality, Constituent Quality, Supply/Demand. Orchestrator synthesizes into flat sub-industry leaderboard and selects top 30 sub-industries.
  </phase>
  <phase n="2" name="Top 30 Deep Dive" agent="sector-screener">
    Deep dive ALL 30 top sub-industries — stay at Level 4 granularity, never aggregate back to Level 3/2/1. Spawn in batches of 3 (10 batches total). Each analyzes: definition, company universe, Porter 5-Forces, growth catalysts, barriers, TAM, key players, supply chain, life cycle, profit pool, competitive positioning. Writes deepdive-[CODE]-[NAME].md per sub-industry. Orchestrator compiles unified 30-sub-industry deep dive summary.
  </phase>
  <phase n="3" name="Company Screening (100 Companies)" agent="company-screener">
    Screen companies across ALL 30 sub-industries. Target: 100 total companies (~3-4 per sub-industry, flexible based on universe size). Spawn up to 3 agents in parallel, each handling ~10 sub-industries. Filter: market cap >$500M, revenue growth >median, positive FCF, ROIC>WACC, stock price <$100 (US) / ¥100 (A-shares). Score: Growth 20%, Profitability 20%, Moat 20%, Valuation 15%, Management 10%, Risk 10%, Liquidity 5%. Writes companies-[CODE].md per sub-industry. Orchestrator compiles unified watchlist of 100 companies ranked by composite score.
  </phase>
  <phase n="4" name="Reports" agent="screening-report-writer">
    Pre-compute filenames: SCREEN_long_[DATE].md, SCREEN_mid_[DATE].md, SCREEN_short_[DATE].md. Agent synthesizes ALL phases into 3 horizon reports covering 30 sub-industries and 100 companies. Structure: Executive Summary → Macro Environment → Top 30 Sub-Industry Leaderboard → Deep Dive Highlights → Top 100 Company Watchlist (grouped by sub-industry) → Next Actions → Risks → Appendix (full 30-industry detail).
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
  Phase 1: [Batch A (~54) + Batch B (~54) + Batch C (~55)] — score all 163 Level 4 sub-industries → top 30
  Phase 2: [DD 1-3] → [DD 4-6] → ... → [DD 28-30] — 10 sequential batches, 3 parallel per batch
  Phase 3: [Companies 1-10] + [Companies 11-20] + [Companies 21-30] — 3 parallel batches
  Phase 4: Report
  Max 3 concurrent agents.
</parallel-execution>

<phase-depth>
  | Phase | Scope | Detail |
  |-------|-------|--------|
  | 1: Full Level 4 Screening | ALL 163 sub-industries (3 batches × ~54) | Score 11 dimensions → top 30 |
  | 2: Top 30 Deep Dive | 30 sub-industries (10 batches × 3 parallel) | Porter, TAM, catalysts, barriers |
  | 3: Company Screening | 30 sub-industries (3 batches × 10) | 100 companies total, ~3-4 per sub-industry |
  | 4: Report | 3 horizon reports | Full 30-industry + 100-company coverage |
</phase-depth>

<context-eviction>
  After each phase: write phase summary → persist.py save → drop raw data from context. If context >80%, offload more.
</context-eviction>

<pre-delivery>
  Verify: macro ≤30d fresh, sub-industry data ≤90d fresh, leaderboard = 30 sub-industries, deep dives = 30 sub-industries, watchlist = 100 companies, NO Level 1/2/3 standalone sections, each sub-industry has structural thesis with GICS code, all metrics cited with source+date, Chinese report, no invented data.
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
