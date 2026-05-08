---
name: industry-screening
description: >
  Top-down sector-to-sub-industry screening funnel using GICS Level 4
  (Sub-Industry, 163 classifications) as the default atomic screening unit.
  Identifies the most profitable and fastest-growing sub-industry niches,
  performs deep-dive analysis at granular level, and screens all public
  companies to produce a ranked watchlist. Designed as a precursor to the
  stock-analysis skill for deep-dive research. Use when the user asks to
  screen sectors, find the best industries to invest in, run a top-down
  stock screen, discover promising companies in a sector, or perform sector
  rotation analysis. Triggers on phrases like "screen sectors," "best
  industries to invest," "which sectors are growing," "top-down screening,"
  "find stocks in [SECTOR]," "industry screening," or "sector rotation."
author: Jennings Liu
version: "1.0.45"
license: MIT
compatibility: Requires Firecrawl MCP, Tavily MCP, XCrawl MCP, Web Search Prime, Exa MCP, exec_shell, write_file, read_file. Python 3.10+ for bundled scripts. Optional: FRED_API_KEY (macro).
---

# Industry Screening — Top-Down Sub-Industry Funnel (GICS Level 4)

## Overview

<purpose>Industry-screening-orchestrator (team lead) agent team workflow. Uses GICS Level 4 (Sub-Industry, 163 classifications) as the ONLY screening unit. Reports present ONLY sub-industry classifications — never show Sector (Level 1), Industry Group (Level 2), or Industry (Level 3) as standalone categories. The orchestrator spawns specialized screener teammates — it NEVER performs deep analysis directly, only spawns, coordinates, and synthesizes.</purpose>

<default-granularity>
  GICS Level 4 (Sub-Industry) is the PRIMARY structural unit in all reports.
  STRICT RULE: Do NOT present Level 1/2/3 categories as standalone report SECTIONS or ranking dimensions.
  The REPORT STRUCTURE uses Level 4 sub-industries as the organizing principle — flat ranked list, no hierarchical grouping by sector.
  
  HOWEVER: Level 1 (Sector), Level 2 (Industry Group), and Level 3 (Industry) data IS CRUCIAL
  and MUST be included as CONTEXTUAL INFORMATION within each Level 4 sub-industry section.
  For example, a sub-industry entry should note its parent sector's macro sensitivity,
  industry-group competitive dynamics, and how it relates to adjacent sub-industries.
  
  Rule: Level 4 = STRUCTURE (sections, rankings). Level 1/2/3 = CONTEXT (within Level 4 sections).
  Reference: `references/gics_taxonomy.md` for full GICS hierarchy.
</default-granularity>

<triggers>Triggers on: "screen sectors," "best industries to invest," "which sectors are growing," "top-down screening," "find stocks in [SECTOR]," "industry screening," "sector rotation," "most promising sectors," "sector analysis," "what industries have the most growth potential," "screen [SECTOR] for best stocks," "which companies in [INDUSTRY] are worth investing in." Do NOT trigger on: single-stock analysis requests (use stock-analysis skill), general market commentary without screening intent, portfolio allocation questions without ticker discovery intent.</triggers>

This skill performs institutional-grade top-down screening through 4 phases, producing a ranked sector map and a company watchlist suitable as input to the `stock-analysis` skill for deep dives.

**Report language:** ALL screening reports MUST be written in Chinese (中文). Technical terms (P/E, EV/EBITDA, ROIC, ticker symbols) may remain in English. GICS classification names should include both English and Chinese: e.g., "Semiconductors (半导体)". Source citations remain in original language.

**Price filter:** Focus on growth-stage companies (成长型公司). US stocks: price < $100. China A-shares: price < ¥100. Filter OUT companies above threshold before ranking in watchlists.

**Stock price display:** Every company in any table/list/watchlist MUST include current stock price (当前股价) as a column. Format: "$XX.XX" or "¥XX.XX". Price must be fetched at analysis time.

**Critical constraint:** The context window is a shared resource. Follow the eviction protocol strictly. Raw data from completed phases is dropped; only phase summaries persist.

## Agent Team Activation (MANDATORY)

<agent-team-protocol>
This skill ALWAYS operates as an agent team. You are the team lead (industry-screening-orchestrator).

STEP 0 — Create the team IMMEDIATELY as the FIRST action (before ANY scripts or data fetches):
  Claude Code: TeamCreate({ name: "industry-screening-[TIMESTAMP]" })
  Gemini CLI: Team is implicit — agents are spawned via @agent-name syntax.

STEP 1 — Spawn data-fetch agent into the team to run all setup scripts:
  The orchestrator NEVER runs scripts directly. Delegate initial data collection to a search-agent
  teammate that runs: fetch_macro.py, fetch_economic_surprises.py, compute_sector_rs.py (both sector
  and --level sub-industry --flat), persist.py init SCREEN-[TIMESTAMP].

**Claude Code** — Spawn data-fetch agent:
```
Agent({
  subagent_type: "stock-analysis:search-agent",
  team_name: "industry-screening-[TIMESTAMP]",
  prompt: "PLUGIN_ROOT=... PLUGIN_SCRIPTS=... Run screening data fetch. Create ./reports/screening/, run fetch_macro.py, fetch_economic_surprises.py, compute_sector_rs.py --output ./reports/screening/sector_rs.json, compute_sector_rs.py --level sub-industry --flat --output ./reports/screening/sub_industry_rs.json, persist.py init SCREEN-[TIMESTAMP] --report-type screen."
})
```

**Gemini CLI:**
```
@search-agent Run screening data fetch. PLUGIN_ROOT=... PLUGIN_SCRIPTS=...
```

STEP 2+ — Spawn screening sub-agents into the team for ALL phases (Phases 1-4):

**Claude Code:**
```
Agent({
  subagent_type: "industry-screening:<agent-name>",
  team_name: "industry-screening-[TIMESTAMP]",
  prompt: "PLUGIN_ROOT=... PLUGIN_SCRIPTS=... Screen [SCOPE]. Macro data at ./reports/screening/macro.json..."
})
```

**Gemini CLI:**
```
@sector-screener Screen all sectors. PLUGIN_ROOT=... PLUGIN_SCRIPTS=...
```

ENFORCEMENT RULE: The orchestrator MUST NOT run any scripts or perform analysis directly.
ALL work is delegated to sub-agents within the team. The orchestrator's ONLY jobs are:
create team → spawn data-fetch → spawn screeners → collect phase summaries → spawn report writer → cleanup.

VIOLATION: If you find yourself running python scripts directly, writing sector analysis,
sub-industry deep-dives, or company scoring directly, STOP immediately and spawn the
appropriate agent instead.

TERMINATION: Terminate each sub-agent immediately after it completes its phase work. Do not
leave idle agents running.

CLEANUP (after final reports delivered):
1. Delete ALL intermediate files: ./reports/screening/phase*.md, sector_rs.json,
   sub_industry_rs.json, economic_surprises.json, macro.json, source-plan.md,
   and any other working files. Only the 3 final reports remain:
   [SUB_INDUSTRY_CODE]_long_[DATE].md, [SUB_INDUSTRY_CODE]_mid_[DATE].md, [SUB_INDUSTRY_CODE]_short_[DATE].md
2. Terminate ALL remaining agents.
3. Delete the team: TeamDelete({ name: "industry-screening-[TIMESTAMP]" })
</agent-team-protocol>

## Integration with stock-analysis

This skill is designed as a precursor pipeline. After a screening report is produced, the user can feed any watchlist ticker directly into the `stock-analysis` skill. The screening report provides:
- Macro regime context (reusable by stock-analysis Phase 0)
- Industry thesis (feeds stock-analysis Stage 3)
- Peer universe (feeds stock-analysis Stage 6 comps)

## Search Tools

This skill reuses the same search tool stack as `stock-analysis`. See `agents/search-agent.md` for full search methodology.

**Horizon-aware research:** Since all 3 horizons are produced per run, data collection must cover both structural/secular factors (long-term) and cyclical/momentum factors (short-term). See `agents/sector-screener.md` `<data-acquisition>` section for horizon-specific query templates.

**Priority order:**
1. **Firecrawl MCP** (`mcp__firecrawl__firecrawl_search`) — Primary search. Always run first.
2. **Tavily MCP** (`mcp__tavily-remote-mcp__tavily_search`) — Domain-filtered search with date ranges. Use `tavily_research` for comprehensive industry reports.
3. **XCrawl MCP** (`mcp__xcrawl-mcp__xcrawl_search`) — Google SERP for sector news, ETF flow data.
4. **Web Search Prime** (`mcp__web-search-prime__web_search_prime`) — Quick summaries, macro data, sector performance.
5. **Exa** (`mcp__exa__web_search_exa`) — Semantic search for industry research papers, sector analysis blogs.

**Scraping/extraction tools:**
- `mcp__firecrawl__firecrawl_scrape` — Industry reports, sector performance pages
- `mcp__firecrawl__firecrawl_extract` — LLM-powered structured extraction from multiple URLs (sector comparison tables)
- `mcp__tavily-remote-mcp__tavily_research` — Comprehensive multi-source industry research (model: "pro")
- `mcp__tavily-remote-mcp__tavily_extract` — Extract content from known URLs

## Data Source Coverage

Before Phase 1, load `references/data_source_matrix.md` and write `./reports/screening/source-plan.md`. The plan must define:
- Classification source for the universe (GICS, NAICS, ETF holdings, exchange lists)
- Required data by phase: macro, sector aggregates, industry structure, company metrics, valuation, flows, and catalysts
- Freshness windows and source quorum rules
- Sector-specific KPIs to apply once a top industry is selected
- Confidence cap if the company universe, sector valuation, or macro data is stale or incomplete

## Script Execution

<platform-paths>
  PLUGIN_ROOT:
    claude: ${CLAUDE_PLUGIN_ROOT}
    gemini: ${extensionPath}
  PLUGIN_DATA:
    claude: ${CLAUDE_PLUGIN_DATA}
    gemini: ${extensionPath}/.data
</platform-paths>

Scripts are bundled with the plugin. Set `PLUGIN_ROOT` based on platform, then derive:
- `PLUGIN_SCRIPTS` = `${PLUGIN_ROOT}/scripts`

**MANDATORY**: ALL Python scripts MUST be executed with `uv run python` — never bare `python` or `python3`. Example: `uv run python ${PLUGIN_SCRIPTS}/fetch_macro.py --output ./reports/screening/macro.json`

## Workflow

### Phase 0: Setup & Scope (orchestrator executes directly)

1. **Determine screening scope** from user request:
   - "all sectors" / "market overview" → Screen all 11 GICS sectors
   - "[specific sector]" (e.g., "technology," "healthcare") → Deep-dive that sector only, skip broad Phase 1 ranking
   - "[theme]" (e.g., "AI," "clean energy," "aging population") → Identify relevant sectors via web search, then screen those
   - Default (no scope specified) → Ask: "Screen all sectors or focus on a specific one?"

2. **Investment horizon — ALL THREE automatically**: Every screening run produces 3 reports covering all horizons. The composite weightings differ per horizon:
   - **Long-term** (growth + moat weighted)
   - **Mid-term** (macro cycle + valuation weighted)
   - **Short-term** (momentum + sentiment weighted)
   
   Do NOT ask the user which horizon — always produce all three. Each horizon generates a separate final report file.

3. **Fetch macro context**: Run `${PLUGIN_SCRIPTS}/fetch_macro.py --indicators GDPC1,CPIAUCSL,UNRATE,DFF,DGS10,T10Y2Y,NAPM --output ./reports/screening/macro.json`. This establishes the macro regime backdrop for sector sensitivity analysis.
3b. **Fetch economic surprises**: Run `${PLUGIN_SCRIPTS}/fetch_economic_surprises.py --output ./reports/screening/economic_surprises.json` for actual-vs-consensus data. Persistent positive surprises favor cyclicals; negative surprises favor defensives.
3c. **Compute sector relative strength**: Run `${PLUGIN_SCRIPTS}/compute_sector_rs.py --output ./reports/screening/sector_rs.json` for deterministic sector price momentum rankings vs SPY across 1M/3M/6M/12M. This provides the quantitative backbone for the Relative Strength dimension in Phase 1.
3d. **Compute sub-industry relative strength**: Run `${PLUGIN_SCRIPTS}/compute_sector_rs.py --level sub-industry --flat --output ./reports/screening/sub_industry_rs.json` for a flat-ranked GICS Level 4 sub-industry RS leaderboard across all sectors. Uses stock baskets for differentiation where sub-industries share an ETF proxy.

4. **Create output directory**: `./reports/screening/`

5. **Initialize state**: Run `${PLUGIN_SCRIPTS}/persist.py init SCREEN-[TIMESTAMP] --report-type screen` to create a checkpointed screening session. Record the returned `analysis_id`. One session covers all 3 horizons — the horizons diverge at scoring/weighting time, not at data collection time.

6. **Source coverage plan**: Load `references/data_source_matrix.md` and `references/gics_taxonomy.md`. Write `./reports/screening/source-plan.md` with classification sources (GICS Level 4 sub-industries), required source tiers, freshness windows, and confidence cap rules.

### Phase 1: Sub-Industry Screening (GICS Level 4 — the ONLY output level)

**Objective:** Rank all 163 GICS Level 4 sub-industries directly to produce a flat sub-industry leaderboard. Sectors (Level 1) are used INTERNALLY for ETF-based data acquisition only — they NEVER appear in report output.

**GICS Granularity:** This phase uses `references/gics_taxonomy.md` as the authoritative classification.
- Internal only: Level 1 (Sector, 11) for ETF RS data acquisition
- **Report output: Level 4 (Sub-Industry, 163) ONLY** — flat ranked list, no hierarchical grouping

**Research approach:** ALL search queries target sub-industry names directly (e.g., "Semiconductors industry growth 2026") — never broad sector terms (e.g., "Technology sector").

**Spawn strategy:** Spawn up to 3 `sector-screener` agents in parallel. Each agent handles a batch of sub-industries grouped by parent sector for data acquisition efficiency:
- Batch A: Technology (11 sub-industries), Communication Services (10 sub-industries), Consumer Discretionary (19 sub-industries)
- Batch B: Financials (15 sub-industries), Healthcare (10 sub-industries), Industrials (19 sub-industries)
- Batch C: Energy (7 sub-industries), Materials (16 sub-industries), Consumer Staples (12 sub-industries), Utilities (6 sub-industries), Real Estate (14 sub-industries)

Or, if user specified a single sector, spawn 1 `sector-screener` for that sector's sub-industries and proceed to Phase 2.

**Each sector-screener performs a two-pass analysis:**

**Pass 1 — Sector-Level Scoring (quick filter):**
- [ ] **Growth** — Revenue and earnings CAGR (sector aggregate, past 3-5 years), forward growth estimates, secular vs cyclical drivers
- [ ] **Profitability** — Aggregate margins (gross, operating, net), ROIC, ROE, FCF conversion
- [ ] **Valuation** — Sector P/E, EV/EBITDA vs 5-year history (percentile), PEG ratio
- [ ] **Macro Fit** — Sensitivity to current macro regime (rates, inflation, GDP), correlation with leading indicators
- [ ] **Innovation** — R&D intensity, R&D productivity (pipeline value / cumulative R&D), disruption risk/opportunity, technology adoption curves
- [ ] **Regulatory** — Current and pending regulation, antitrust, subsidy exposure, political sensitivity
- [ ] **Capital Flows** — Sector ETF flows (1M/3M/6M), institutional positioning, insider sentiment
- [ ] **Relative Strength** — Price performance vs SPX over 1M/3M/6M/12M periods. Compute RS ranking (percentile rank vs all sectors). Sectors with top-quartile 3M+6M RS and improving 1M RS are strongest momentum candidates. **This is the single most predictive signal for sector rotation.**
- [ ] **Cyclicality** — Beta to GDP/economic cycle, earnings volatility (5-year std dev of EPS growth), revenue cyclicality classification (Defensive/Moderate/Cyclical/Highly Cyclical). In late-cycle environments, defensive sectors (Utilities, Staples, Healthcare) should receive a scoring bonus; in early-cycle, cyclicals (Industrials, Discretionary, Financials) receive the bonus.
- [ ] **Constituent Quality & Dispersion** — Percentage of sector market cap with positive FCF, ROIC > WACC, net cash/low leverage, and estimate revision momentum. A sector led by a few mega-caps must be marked as concentration-driven.
- [ ] **Supply/Demand & Capacity Cycle** — Inventory, backlog, utilization, pricing, capacity expansion, and input cost regime where sector-relevant.

**Pass 2 — Sub-Industry Ranking (within top sectors from Pass 1):**

For each sector scoring above median in Pass 1, rank all its GICS Level 4 sub-industries using:
- [ ] **Sub-Industry RS** — Use pre-computed data from `./reports/screening/sub_industry_rs.json`. Rank sub-industries by composite RS within the sector.
- [ ] **Sub-Industry Growth** — Which sub-industries have the fastest revenue/earnings growth among their constituents?
- [ ] **Structural Attractiveness** — Is the sub-industry in Growth/Emerging phase? Does it have secular tailwinds?
- [ ] **Concentration Risk** — Is the sub-industry dominated by 1-2 mega-caps (making it an idiosyncratic bet rather than a thematic one)?
- [ ] **Investable Depth** — How many publicly traded companies exist in the sub-industry? (Minimum 5 for a valid screen)

**Output per sector batch:** Each sector-screener writes `./reports/screening/sector-[BATCH].md` with:
- Per-sector scores (Pass 1)
- Per-sub-industry rankings within above-median sectors (Pass 2)
- Top 5 sub-industries across the batch with brief thesis

**Validation gate:** At least 3 data points per sector dimension. Growth and valuation data within 90 days freshness. Relative strength, flows, and cyclicality must be scored or explicitly marked "Data not available." Sub-industry RS data must be loaded from Phase 0 output.

**After all batches complete:** Orchestrator reads all batch summaries and:
1. Ranks sectors using weighted composite (same as before)
2. Collects all sub-industry rankings across batches
3. Produces a **unified sub-industry leaderboard** (top 10-15 sub-industries across all sectors)

| Dimension | Long-term Weight | Mid-term Weight | Short-term Weight |
|-----------|-----------------|-----------------|-------------------|
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

For long-term and mid-term reports, use constituent quality as a tiebreaker. For sector screens where supply/demand is central (energy, semis, industrials, commodities), reallocate up to 5% from Innovation or Capital Flows to Supply/Demand Cycle and disclose the adjustment.

**Deliverable:** 
- **Sub-industry leaderboard** (top 15-20 sub-industries ranked flat with GICS Level 4 codes, RS, growth, and structural scores — NO sector grouping)
- Top 2-3 sub-industries identified for Phase 2 deep dive
- NO sector ranking table in report output (sectors used internally only)

**Eviction:** After ranking is produced, drop raw batch files. Retain: sub-industry leaderboard, top-3 sub-industry summaries (3 sentences each).

### Phase 2: Sub-Industry Deep Dive (GICS Level 4 focused)

**Objective:** For each top sub-industry from Phase 1's leaderboard, perform a focused deep dive to validate the thesis and map the competitive landscape for company selection.

**Key difference from previous approach:** Phase 2 now operates at GICS Level 4 (sub-industry) granularity from the start, rather than drilling from sector → sub-industry. The sub-industry leaderboard from Phase 1 already identifies the target niches.

**Spawn strategy:** Spawn 1 `sector-screener` per top sub-industry (max 2 in parallel), each in "deep-dive" mode. Pass the specific GICS sub-industry code and name.

**Each deep-dive analyzes (at sub-industry level):**
- [ ] **Sub-industry definition** — Exact GICS Level 4 code, name, what's included/excluded, boundary cases
- [ ] **Complete company universe** — All publicly traded companies classified in this sub-industry (using GICS code, ETF holdings, and exchange data). Reference `references/gics_taxonomy.md` for representative tickers.
- [ ] **Sub-industry ranking vs peers** — How does this sub-industry compare to adjacent sub-industries in the same Industry Group (Level 3)?
- [ ] **Competitive dynamics** — Porter's Five Forces for the sub-industry (light version: 2-3 forces)
- [ ] **Growth catalysts** — Secular trends, demand drivers, technology shifts, demographic tailwinds specific to this sub-industry
- [ ] **Barriers to entry** — Capital requirements, regulation, IP, network effects, scale economies
- [ ] **Market sizing** — TAM estimate (top-down), growth rate, penetration rate
- [ ] **Key players** — Top 5-10 companies by market cap, market share distribution, concentration
- [ ] **Supply chain** — Critical inputs, geographic concentration, supplier power
- [ ] **Industry life cycle** — Emerging / Growth / Mature / Decline classification
- [ ] **Profit Pool Map** — Where gross profit, pricing power, and bargaining leverage accumulate across the value chain
- [ ] **Adoption Curve & Unit Economics** — Penetration, payback period, utilization, churn/retention, or equivalent industry KPI; use sector-specific add-ons from `references/data_source_matrix.md`

**Output:** Each deep-dive writes `./reports/screening/deepdive-[SUB_INDUSTRY_CODE]-[NAME].md`.

**Validation gate:** At least 5 companies identified in the sub-industry. TAM estimate produced with stated source and bottom-up sanity check. Profit pool and sector-specific KPIs included or marked "Data not available."

**Orchestrator synthesizes:** After all deep-dives complete, the orchestrator selects the single best sub-industry (or top 2 if user wants broader coverage). Justification must reference specific scores from Phase 1 sub-industry leaderboard and deep-dive findings.

**Eviction:** Drop raw deep-dive files. Retain: selected sub-industry name + GICS code, sub-industry thesis (5 sentences), list of all public companies in the sub-industry.

### Phase 3: Company Screening (within selected sub-industry)

**Objective:** Screen all public companies in the selected industry and produce a ranked watchlist.

**Spawn strategy:** Spawn 1 `company-screener` agent for the selected industry. For large industries (50+ companies), split into 2 parallel `company-screener` instances by market cap tier (large-cap vs small/mid-cap).

**Company screener analyzes per company:**
- [ ] **Quantitative Filters** — Apply minimum thresholds:
  - Market cap > $500M (or user-specified minimum)
  - Revenue growth (3-year CAGR) > industry median (or > 0% for cyclical)
  - Positive free cash flow (trailing 12 months)
  - ROIC > WACC (or ROE > 10% for financials)
  - Debt/Equity < industry 75th percentile (or < 3.0x for capital-intensive)
- [ ] **Financial Health** — Quick ratio, interest coverage, Altman Z-Score
- [ ] **Moat Quality** — Morningstar framework (cost advantage, network effects, intangibles, switching costs, efficient scale)
- [ ] **Management Quality** — CEO tenure, insider ownership, capital allocation track record
- [ ] **Valuation** — P/E, EV/EBITDA, P/FCF vs industry peers, PEG ratio
- [ ] **Growth Trajectory** — Revenue and EPS growth consistency, guidance trend, estimate revisions
- [ ] **Risk Flags** — Concentration risk (customer/supplier), debt maturity wall, litigation, regulatory exposure
- [ ] **Business-Model Fit Metrics** — Apply sector-specific screening metrics from `references/data_source_matrix.md` (e.g., ARR/NRR, CET1/NIM, FFO/AFFO, reserves, pipeline probability, same-store sales)
- [ ] **Liquidity & Tradability** — Average dollar volume, free float, short interest, borrow/FTD risk for smaller names

**Scoring model:** Each company receives a composite score (1-10):
- Growth (20%), Profitability/Health (20%), Moat (20%), Valuation (15%), Management (10%), Risk (10%), Liquidity/Tradability (5%)

**Output:** Company-screener writes `./reports/screening/companies-[INDUSTRY].md` with:
- Full ranked list of all qualifying companies
- Top 10-20 in detail with 2-sentence thesis per company
- Key metrics table (Ticker, Name, Market Cap, P/E, Rev Growth 3Y, ROIC, FCF Yield, Score)

**Validation gate:** At least 10 companies must pass quantitative filters. If fewer, flag the industry as "concentrated" and relax filters with justification.

**Eviction:** After ranking is produced, drop raw company data. Retain: ranked company table with scores and metrics.

### Phase 4: Report Generation → Spawn screening-report-writer

**BEFORE spawning the report writer**, the team lead MUST pre-compute the 3 final report filenames:
- `./reports/screening/[SUB_INDUSTRY_CODE]_long_[YYYY-MM-DD].md`
- `./reports/screening/[SUB_INDUSTRY_CODE]_mid_[YYYY-MM-DD].md`
- `./reports/screening/[SUB_INDUSTRY_CODE]_short_[YYYY-MM-DD].md`

Use the top-ranked sub-industry's 8-digit GICS code and today's date. Pass these EXACT filenames in the spawn prompt. The report writer writes ONLY these 3 files — no other output files.

**Objective:** Synthesize all phase summaries into final screening reports with conviction scoring. Produce **3 separate reports** — one per investment horizon (long-term, mid-term, short-term) — each with horizon-specific composite weightings.

**Spawn strategy:** Spawn 1 `screening-report-writer` agent. The orchestrator provides the analysis_id, phase summary file paths, the 3 target filenames, and instructs the writer to produce all 3 horizon variants.

**Screening-report-writer workflow:**
- [ ] Load all phase summaries from `./reports/screening/phase[0-3].md`
- [ ] Cross-validate internal consistency (selected sub-industry companies match GICS Level 4 code)
- [ ] For EACH horizon (long-term, mid-term, short-term), apply the corresponding weighting scheme and produce a report with this structure (ALL output in Chinese, Level 4 as PRIMARY structure):
  - **Executive Summary** — 1 paragraph: macro → top sub-industries → top picks
  - **Macro Context** — Current regime, key indicators, implications for sub-industry selection
  - **Sub-Industry Leaderboard** — Flat ranked table of top 15-20 sub-industries with GICS Level 4 codes, NO sector grouping as separate sections. Each sub-industry entry includes its parent sector/industry-group context inline.
  - **Sub-Industry Deep Dive** — Selected sub-industry thesis with GICS code, growth catalysts, competitive dynamics, TAM. MUST include parent-level context: sector tailwinds, industry-group dynamics, and where this sub-industry sits in the broader value chain.
  - **Company Watchlist** — Ranked table with key metrics, 2-sentence thesis per company
  - **Next Actions** — Which companies to deep-dive with `stock-analysis` skill, suggested report horizon
  - **Risks to Thesis** — What would invalidate the sub-industry/company recommendations, kill switch conditions
  - **Methodology Appendix** — Weighting scheme, GICS Level 4 classification source, data sources, freshness dates, source coverage gaps
- [ ] Compute conviction scores (Sub-Industry Selection Confidence, Overall Screen Quality) per horizon
- [ ] Run pre-delivery checklist and fact verification
- [ ] Write 3 reports:
  - `./reports/screening/[SUB_INDUSTRY_CODE]_long_[YYYY-MM-DD].md`
  - `./reports/screening/[SUB_INDUSTRY_CODE]_mid_[YYYY-MM-DD].md`
  - `./reports/screening/[SUB_INDUSTRY_CODE]_short_[YYYY-MM-DD].md`
- [ ] Run `${PLUGIN_SCRIPTS}/persist.py complete [ANALYSIS_ID]`
- [ ] Generate handoff recommendation for stock-analysis deep-dive

**Note:** Rankings may differ across horizons because weighting schemes prioritize different factors (growth/moat for long-term vs momentum/flows for short-term).

**Validation gate:** All phase summaries loaded and internally consistent. At least 3 fact checks passed. Kill switch conditions defined.

## Pre-Delivery Checklist

Before delivering the screening report, verify:
- [ ] Macro data within 30 days freshness
- [ ] Source coverage plan completed and confidence caps applied
- [ ] Sub-industry data within 90 days freshness
- [ ] Sub-industry leaderboard contains at least 10 ranked sub-industries (Level 4 only)
- [ ] NO sector-level (Level 1/2/3) categories used as standalone report SECTIONS (they appear only as context within Level 4 entries)
- [ ] Selected sub-industry has a clear structural thesis with GICS Level 4 code (not just momentum)
- [ ] At least 10 companies in the watchlist
- [ ] Universe construction source stated and missing-universe risk assessed
- [ ] All company metrics cited with source and date
- [ ] Sub-industry-specific KPIs included where material
- [ ] Methodology weights stated
- [ ] Kill switch conditions defined (what would invalidate the sub-industry thesis)
- [ ] Report written in Chinese (中文)
- [ ] No invented data — "数据不可用" used where appropriate

## Context Eviction Protocol

After every phase, execute this sequence:
1. Write phase summary to `./reports/screening/phase[N].md`
2. Run `${PLUGIN_SCRIPTS}/persist.py save [ANALYSIS_ID] [N] ./reports/screening/phase[N].md`
3. Drop raw data from context (full search results, per-company data, raw sector reports)
4. Load next phase
5. If context usage exceeds ~80%, offload additional intermediate data

## Phase Depth Allocation

| Phase | Broad Screen (all sectors) | Single Sector | Thematic Screen |
|-------|---------------------------|---------------|-----------------|
| 1: Sector Screening | Full (all 11 sectors, 3 batches) | Light (1 sector only) | Medium (3-5 relevant sectors) |
| 2: Industry Deep Dive | Top 2-3 sectors | Top 2 sub-industries | Top 2 sectors |
| 3: Company Screening | Top 1-2 industries | Top 1-2 industries | Top 1-2 industries |
| 4: Report | Full | Full | Full |

## Agent Team

The industry-screening-orchestrator spawns specialist teammates for ALL screening work — it NEVER performs deep analysis directly. Sub-agents are defined in `agents/`:

| Agent | Phases | Spawn When |
|-------|--------|------------|
| `sector-screener` | 1, 2 | Sector ranking, sub-industry deep-dive analysis |
| `company-screener` | 3 | Company filtering, scoring, and ranking within an industry |
| `screening-report-writer` | 4 | Synthesizes phase summaries into final screening report with conviction scoring |
| `search-agent` | All | Financial web search when screener agents need data |

**Claude Code**: Orchestrator spawns via the `Agent` tool with `subagent_type: "industry-screening:<agent-name>"`.
**Gemini CLI**: Orchestrator auto-delegates based on agent descriptions, or user forces via `@agent-name` syntax.

**Path passing**: When spawning any sub-agent, include in the spawn prompt:
- `PLUGIN_ROOT` = the resolved plugin root path (platform-specific, resolved by orchestrator)
- `PLUGIN_SCRIPTS` = `PLUGIN_ROOT/scripts`

Agents reference scripts as `PLUGIN_SCRIPTS/script_name.py`. The orchestrator resolves the platform path and passes it; agents never resolve paths themselves. All scripts run via `uv run python`.

## Parallelism

Industry-screening-orchestrator spawns sub-agents in parallel (max 3 concurrent):
- Phase 1: Up to 3 sector-screeners in parallel (one per sector batch)
- Phase 2: Up to 2 sector-screeners in parallel (deep-dive on top sectors)
- Phase 3: 1-2 company-screeners (1 for normal, 2 for large industries split by cap tier)
- Phase 4: 1 screening-report-writer (spawned by orchestrator, synthesizes phase summaries into final report)

## Integration with Stock Analysis

After a screening report is produced, the orchestrator should explicitly offer:

> "Top-ranked companies from this screen can be deep-dived with the stock-analysis skill. Would you like me to run a full equity research analysis on any of these tickers?"

The screening report's macro context and industry thesis feed directly into stock-analysis Stages 4 and 3 respectively, reducing redundant work.
