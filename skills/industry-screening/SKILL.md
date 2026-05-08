---
name: industry-screening
description: >
  Top-down sector-to-company screening funnel. Identifies the most profitable
  and fastest-growing industry sectors, drills into the best sub-industries,
  and screens all public companies to produce a ranked watchlist of the most
  promising stocks. Designed as a precursor to the stock-analysis skill for
  deep-dive research. Use when the user asks to screen sectors, find the best
  industries to invest in, run a top-down stock screen, discover promising
  companies in a sector, or perform sector rotation analysis. Triggers on
  phrases like "screen sectors," "best industries to invest," "which sectors
  are growing," "top-down screening," "find stocks in [SECTOR]," "industry
  screening," or "sector rotation."
author: Jennings Liu
version: "1.0.0"
license: MIT
compatibility: Requires Firecrawl MCP, Tavily MCP, XCrawl MCP, Web Search Prime, Exa MCP, exec_shell, write_file, read_file. Python 3.10+ for bundled scripts. Optional: FRED_API_KEY (macro).
---

# Industry Screening — Top-Down Sector-to-Company Funnel

## Overview

<purpose>Industry-screening-orchestrator (team lead) agent team workflow. The orchestrator spawns specialized screener teammates for sector analysis and company ranking — it NEVER performs deep screening directly, only spawns, coordinates, and synthesizes. Screener agents analyze sectors, sub-industries, and individual companies in a top-down funnel: Macro → Sector → Industry → Company.</purpose>

<triggers>Triggers on: "screen sectors," "best industries to invest," "which sectors are growing," "top-down screening," "find stocks in [SECTOR]," "industry screening," "sector rotation," "most promising sectors," "sector analysis," "what industries have the most growth potential," "screen [SECTOR] for best stocks," "which companies in [INDUSTRY] are worth investing in." Do NOT trigger on: single-stock analysis requests (use stock-analysis skill), general market commentary without screening intent, portfolio allocation questions without ticker discovery intent.</triggers>

This skill performs institutional-grade top-down screening through 4 phases, producing a ranked sector map and a company watchlist suitable as input to the `stock-analysis` skill for deep dives.

**Critical constraint:** The context window is a shared resource. Follow the eviction protocol strictly. Raw data from completed phases is dropped; only phase summaries persist.

## Integration with stock-analysis

This skill is designed as a precursor pipeline. After a screening report is produced, the user can feed any watchlist ticker directly into the `stock-analysis` skill. The screening report provides:
- Macro regime context (reusable by stock-analysis Phase 0)
- Industry thesis (feeds stock-analysis Stage 3)
- Peer universe (feeds stock-analysis Stage 6 comps)

## Search Tools

This skill reuses the same search tool stack as `stock-analysis`. See `agents/search-agent.md` for full search methodology.

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

## Workflow

### Phase 0: Setup & Scope (orchestrator executes directly)

1. **Determine screening scope** from user request:
   - "all sectors" / "market overview" → Screen all 11 GICS sectors
   - "[specific sector]" (e.g., "technology," "healthcare") → Deep-dive that sector only, skip broad Phase 1 ranking
   - "[theme]" (e.g., "AI," "clean energy," "aging population") → Identify relevant sectors via web search, then screen those
   - Default (no scope specified) → Ask: "Screen all sectors or focus on a specific one?"

2. **Determine investment horizon** (affects composite weightings):
   - "long-term" / "invest" / "5 years" → Long-term (growth + moat weighted)
   - "trade" / "6 months" / "cyclical" → Mid-term (macro cycle + valuation weighted)
   - "momentum" / "this quarter" → Short-term (momentum + sentiment weighted)
   - Default → Mid-term, then ask if the user wants a different horizon

3. **Fetch macro context**: Run `scripts/fetch_macro.py --indicators GDPC1,CPIAUCSL,UNRATE,DFF,DGS10,T10Y2Y,NAPM --output /tmp/industry-screening-macro.json`. This establishes the macro regime backdrop for sector sensitivity analysis.

4. **Create output directory**: `./reports/screening/`

5. **Initialize state**: Run `scripts/persist.py init SCREEN-[TIMESTAMP] --report-type screen` to create a checkpointed screening session. Record the returned `analysis_id`.

### Phase 1: Sector Screening (parallel per sector)

**Objective:** Score and rank all major sectors by composite attractiveness.

**Spawn strategy:** Spawn up to 3 `sector-screener` agents in parallel. Each agent handles a batch of sectors:
- Batch A: Technology, Communication Services, Consumer Discretionary
- Batch B: Financials, Healthcare, Industrials
- Batch C: Energy, Materials, Consumer Staples, Utilities, Real Estate

Or, if user specified a single sector, spawn 1 `sector-screener` for that sector and proceed to Phase 2.

**Each sector-screener analyzes per sector:**
- [ ] **Growth** — Revenue and earnings CAGR (sector aggregate, past 3-5 years), forward growth estimates, secular vs cyclical drivers
- [ ] **Profitability** — Aggregate margins (gross, operating, net), ROIC, ROE, FCF conversion
- [ ] **Valuation** — Sector P/E, EV/EBITDA vs 5-year history (percentile), PEG ratio
- [ ] **Macro Fit** — Sensitivity to current macro regime (rates, inflation, GDP), correlation with leading indicators
- [ ] **Innovation** — R&D intensity, R&D productivity (pipeline value / cumulative R&D), disruption risk/opportunity, technology adoption curves
- [ ] **Regulatory** — Current and pending regulation, antitrust, subsidy exposure, political sensitivity
- [ ] **Capital Flows** — Sector ETF flows (1M/3M/6M), institutional positioning, insider sentiment
- [ ] **Relative Strength** — Price performance vs SPX over 1M/3M/6M/12M periods. Compute RS ranking (percentile rank vs all sectors). Sectors with top-quartile 3M+6M RS and improving 1M RS are strongest momentum candidates. **This is the single most predictive signal for sector rotation.**
- [ ] **Cyclicality** — Beta to GDP/economic cycle, earnings volatility (5-year std dev of EPS growth), revenue cyclicality classification (Defensive/Moderate/Cyclical/Highly Cyclical). In late-cycle environments, defensive sectors (Utilities, Staples, Healthcare) should receive a scoring bonus; in early-cycle, cyclicals (Industrials, Discretionary, Financials) receive the bonus.

**Output per sector batch:** Each sector-screener writes `/tmp/industry-screening-sector-[BATCH].md` with per-sector scores.

**Validation gate:** At least 3 data points per sector dimension. Growth and valuation data within 90 days freshness.

**After all batches complete:** Orchestrator reads all batch summaries and ranks sectors using weighted composite:

| Dimension | Long-term Weight | Mid-term Weight | Short-term Weight |
|-----------|-----------------|-----------------|-------------------|
| Growth | 25% | 20% | 10% |
| Profitability | 20% | 15% | 5% |
| Valuation | 10% | 15% | 10% |
| Macro Fit | 10% | 15% | 10% |
| Innovation | 15% | 10% | 5% |
| Regulatory | 5% | 5% | 5% |
| Capital Flows | 5% | 5% | 25% |
| Relative Strength | 5% | 10% | 25% |
| Cyclicality | 5% | 5% | 5% |

**Deliverable:** Sector ranking table with scores. Top 2-3 sectors identified for Phase 2 deep dive.

**Eviction:** After ranking is produced, drop raw sector batch files. Retain: ranking table, top-3 sector summaries (3 sentences each).

### Phase 2: Industry Deep Dive (within top sectors)

**Objective:** For each top sector from Phase 1, drill into sub-industries to find the single most attractive industry for stock selection.

**Spawn strategy:** Spawn 1 `sector-screener` per top sector (max 2 in parallel), each in "deep-dive" mode.

**Each deep-dive analyzes:**
- [ ] **Sub-industry mapping** — List all GICS sub-industries within the sector, with brief descriptions
- [ ] **Sub-industry ranking** — Rank sub-industries by growth, profitability, and structural attractiveness
- [ ] **Competitive dynamics** — Porter's Five Forces for the top sub-industry (light version: 2-3 forces)
- [ ] **Growth catalysts** — Secular trends, demand drivers, technology shifts, demographic tailwinds
- [ ] **Barriers to entry** — Capital requirements, regulation, IP, network effects, scale economies
- [ ] **Market sizing** — TAM estimate (top-down), growth rate, penetration rate
- [ ] **Key players** — Top 5-10 companies by market cap, market share distribution, concentration
- [ ] **Supply chain** — Critical inputs, geographic concentration, supplier power
- [ ] **Industry life cycle** — Emerging / Growth / Mature / Decline classification

**Output:** Each deep-dive writes `/tmp/industry-screening-deepdive-[SECTOR].md`.

**Validation gate:** At least 5 companies identified in the sub-industry. TAM estimate produced with stated source.

**Orchestrator synthesizes:** After all deep-dives complete, the orchestrator selects the single best industry (or top 2 if user wants broader coverage). Justification must reference specific scores from Phase 1 and deep-dive findings.

**Eviction:** Drop raw deep-dive files. Retain: selected industry name, industry thesis (5 sentences), list of all public companies in the industry.

### Phase 3: Company Screening (within selected industry)

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

**Scoring model:** Each company receives a composite score (1-10):
- Growth (25%), Profitability/Health (20%), Moat (20%), Valuation (15%), Management (10%), Risk (10%)

**Output:** Company-screener writes `/tmp/industry-screening-companies-[INDUSTRY].md` with:
- Full ranked list of all qualifying companies
- Top 10-20 in detail with 2-sentence thesis per company
- Key metrics table (Ticker, Name, Market Cap, P/E, Rev Growth 3Y, ROIC, FCF Yield, Score)

**Validation gate:** At least 10 companies must pass quantitative filters. If fewer, flag the industry as "concentrated" and relax filters with justification.

**Eviction:** After ranking is produced, drop raw company data. Retain: ranked company table with scores and metrics.

### Phase 4: Report Generation → Spawn screening-report-writer

**Objective:** Synthesize all phase summaries into a final screening report with conviction scoring.

**Spawn strategy:** Spawn 1 `screening-report-writer` agent. The orchestrator provides the analysis_id and phase summary file paths.

**Screening-report-writer workflow:**
- [ ] Load all phase summaries from `/tmp/industry-screening-phase[0-3].md`
- [ ] Cross-validate internal consistency (selected industry aligns with top sector, companies match industry)
- [ ] Structure the report:
  - **Executive Summary** (1 paragraph covering the funnel: macro → sector → industry → top picks)
  - **Macro Context** — Current regime, key indicators, implications for sector selection
  - **Sector Ranking** — Table with scores, 1-paragraph commentary per top-3 sector
  - **Industry Deep Dive** — Selected industry thesis, growth catalysts, competitive dynamics, TAM
  - **Company Watchlist** — Ranked table with key metrics, 2-sentence thesis per company
  - **Next Actions** — Which companies to deep-dive with `stock-analysis` skill, suggested report horizon
  - **Risks to Thesis** — What would invalidate the industry/company recommendations, kill switch conditions
  - **Methodology Appendix** — Weighting scheme, data sources, freshness dates
- [ ] Compute funnel conviction scores (Sector Selection Confidence, Industry Selection Confidence, Overall Screen Quality)
- [ ] Run pre-delivery checklist and fact verification
- [ ] Write report to `./reports/screening/[SECTOR]_[INDUSTRY]_[YYYY-MM-DD].md`
- [ ] Run `scripts/persist.py complete [ANALYSIS_ID]`
- [ ] Generate handoff recommendation for stock-analysis deep-dive

**Validation gate:** All phase summaries loaded and internally consistent. At least 3 fact checks passed. Kill switch conditions defined.

## Pre-Delivery Checklist

Before delivering the screening report, verify:
- [ ] Macro data within 30 days freshness
- [ ] Sector data within 90 days freshness
- [ ] At least 3 sectors scored and ranked (for broad screens)
- [ ] Selected industry has a clear structural thesis (not just momentum)
- [ ] At least 10 companies in the watchlist
- [ ] All company metrics cited with source and date
- [ ] Methodology weights stated
- [ ] Kill switch conditions defined (what would invalidate the industry thesis)
- [ ] No invented data — "Data not available" used where appropriate

## Context Eviction Protocol

After every phase, execute this sequence:
1. Write phase summary to `/tmp/industry-screening-phase[N].md`
2. Run `scripts/persist.py save [ANALYSIS_ID] [N] /tmp/industry-screening-phase[N].md`
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
