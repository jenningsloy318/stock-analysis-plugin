---
name: stock-analysis
description: >
  Multi-stage institutional equity research. Produces long-term, mid-term, and
  short-term stock analysis reports synthesizing methodologies from Buffett,
  Dalio, Soros, Lynch, Fisher, Marks, Druckenmiller, Greenblatt, Burry, and ARK.
  Use when the user asks to analyze a stock, research a company, generate an
  investment thesis, value a public company, or perform due diligence — even if
  they don't use the words "analysis" or "research." Triggers on phrases like
  "analyze AAPL," "should I buy NVDA," "deep dive on MSFT," or "what do you
  think of TSLA."
author: Jennings Liu
version: "1.0.2"
license: MIT
compatibility: Requires Firecrawl MCP, Tavily MCP, Tinyfish MCP (OAuth), XCrawl MCP, Web Search Prime, Exa MCP, exec_shell, write_file, read_file. Python 3.10+ for bundled scripts. Optional: FRED_API_KEY (macro), FINNHUB_API_KEY (sentiment/insider/earnings).
---

# Stock Analysis — Multi-Stage Equity Research

## Overview

This skill performs institutional-grade stock analysis through 9 sequential stages, producing 1-3 reports (long/mid/short-term) per ticker. Analysis depth adjusts per report type — see `${CLAUDE_PLUGIN_ROOT}/references/report_templates.md` for output formats.

**Critical constraint:** The context window is a shared resource. Follow the eviction protocol strictly. Raw data from completed stages is dropped; only stage summaries persist.

## Search Tools

This skill uses multiple web search tools for financial data acquisition. See `${CLAUDE_PLUGIN_ROOT}/agents/search-agent.md` for full search methodology.

**Priority order:**
1. **Firecrawl MCP** (`mcp__firecrawl__firecrawl_search`) — Primary search. Always run first. Supports `includeDomains`, search operators.
2. **Tavily MCP** (`mcp__tavily-remote-mcp__tavily_search`) — Domain-filtered search with date ranges. Use `tavily_research` for comprehensive multi-source analysis.
3. **Tinyfish MCP** (`mcp__tinyfish__authenticate`) — Social/alternative data. Requires OAuth auth per session. Post-auth: social metrics, app data, web traffic.
4. **XCrawl MCP** (`mcp__xcrawl-mcp__xcrawl_search`) — Google SERP for financial news, earnings dates.
5. **Web Search Prime** (`mcp__web-search-prime__web_search_prime`) — Quick summaries, macro data, analyst consensus.
6. **Exa** (`mcp__exa__web_search_exa`) — Semantic search for expert analysis, research papers, blogs.

**Scraping/extraction tools (for specific URLs):**
- `mcp__firecrawl__firecrawl_scrape` — SEC filings, earnings transcripts, IR pages (JSON format for structured data)
- `mcp__firecrawl__firecrawl_extract` — LLM-powered structured extraction from multiple URLs
- `mcp__tavily-remote-mcp__tavily_extract` — Extract content from known URLs in markdown
- `mcp__tavily-remote-mcp__tavily_crawl` — Crawl financial sites with depth/breadth control
- `mcp__xcrawl-mcp__xcrawl_scrape` — JS-heavy financial sites

**Research tools (multi-source synthesis):**
- `mcp__tavily-remote-mcp__tavily_research` — Comprehensive research agent (model: "pro" for broad, "mini" for narrow)
- `mcp__firecrawl__firecrawl_agent` — Multi-page research with custom instructions

## Gotchas

- Do not invent financial figures. If data is unavailable, state "Data not available" — never guess.
- Company fiscal years vary. A "Q4 2025" filing may cover April-June 2025. Always check the filing's period-end date.
- Tier 1 data sources (SEC filings, financial statements) block stage completion if unavailable. Do not proceed with stale data.
- The `finance` tool returns real-time quotes. For historical context, use the script output or search tools (Firecrawl/XCrawl/Tavily).
- Insider transaction analysis: open-market purchases are the strongest signal. 10b5-1 plan sales are noise.
- All source citations must use `[Source: ... | Retrieved: ... | Fact/Interpretation/Speculation]` format.

## Workflow

### Step 0: Triage

1. Identify the ticker symbol from the user's request. If ambiguous (e.g., "Apple"), resolve via `mcp__xcrawl-mcp__xcrawl_search`: "Apple Inc stock ticker symbol."
2. Determine report type(s) using the decision tree:
   - "long-term" / "invest" / "intrinsic value" → Long-term (1-3+ years)
   - "trade" / "swing" / "catalyst" / "earnings" → Mid-term (1-12 months)
   - "options" / "momentum" / "this week" / "setup" → Short-term (days-weeks)
   - "quick" / "overview" / "snapshot" → Quick Overview (reduced stages, Mid-term format)
   - Default (no horizon specified) → Mid-term, then ask: "Would you also like a long-term intrinsic value analysis?"
3. Create output directory: `./reports/[TICKER]/`
4. **Earnings calendar check**: Run `${CLAUDE_PLUGIN_ROOT}/scripts/fetch_sentiment.py [TICKER] --sources earnings` for upcoming earnings dates and past surprises. If FINNHUB_API_KEY is not set, fall back to `mcp__web-search-prime__web_search_prime` for "[TICKER] next earnings date [YEAR]". If earnings are within 14 days, warn the user: "Earnings report on [DATE] may invalidate this analysis. Proceed or wait?" If within 3 days, recommend waiting unless the user explicitly overrides.
5. Run `${CLAUDE_PLUGIN_ROOT}/scripts/fetch_financials.py [TICKER] --years 5 --output /tmp/stock-analysis-[TICKER]-raw-data.json` to retrieve financial data.
6. Run `${CLAUDE_PLUGIN_ROOT}/scripts/fetch_macro.py --indicators GDPC1,CPIAUCSL,UNRATE,DFF,DGS10,T10Y2Y,NAPM --output /tmp/stock-analysis-macro.json` to capture current macro regime context.
7. **SEC Redline Analysis**: Use `mcp__firecrawl__firecrawl_search` with `includeDomains: ["sec.gov"]` to find the previous year's 10-K. Scrape via `mcp__firecrawl__firecrawl_scrape`. Identify "Risk Factor" deletions or new additions. Flag any hidden shifts in legal language or risk tolerance.
8. Run `${CLAUDE_PLUGIN_ROOT}/scripts/calculate_metrics.py /tmp/stock-analysis-[TICKER]-raw-data.json --output /tmp/stock-analysis-[TICKER]-metrics.json` to compute ratios and valuation. If market cap is known, add `--market-cap [VALUE]`.
9. Call `finance` tool for current price, market cap, 52-week range, shares outstanding.

### Stage 1: Company Fundamentals

**Checklist:**
- [ ] 1.1 Financial Health — Revenue trends, margins, FCF, leverage, working capital, ROIC/ROE/ROA
- [ ] 1.2 Business Model — Revenue model type, quality (recurring %), unit economics, customer concentration
- [ ] 1.3 Competitive Moat — Morningstar framework: cost advantages, network effects, intangibles, switching costs, efficient scale; moat trajectory
- [ ] 1.4 Historical Performance — 5-year CAGR (revenue, EPS, FCF), guidance accuracy, recession performance
- [ ] 1.5 Forensic Accounting — Beneish M-Score, Altman Z-Score, revenue recognition, accruals check
- [ ] 1.6 Segment-Level (if multi-segment) — Per-segment revenue, margin, ROIC, moat; BCG classification

**Reference:** Load `${CLAUDE_PLUGIN_ROOT}/references/frameworks_value_growth.md` for Buffett/Munger/Fisher/Lynch frameworks. Load `${CLAUDE_PLUGIN_ROOT}/references/sector_metrics.md` for sector-specific KPIs.

**Validation gate:** At least 3 years of revenue, operating income, FCF, total debt from Tier 1 source. Beneish M-Score and Altman Z-Score computed.

**After completion:** Write stage summary to `/tmp/stock-analysis-[TICKER]-stage1.md`. Drop raw financial data from context. Retain: key metrics (table), moat assessment (3 sentences), forensic flags (list).

### Stage 2: Executive & Board Profiles

**Checklist:**
- [ ] 2.1 Leadership Assessment — CEO/CFO background, tenure, board composition, departures, succession
- [ ] 2.2 Capital Allocation — ROIC vs WACC spread, incremental ROIC, M&A track record, buyback discipline
- [ ] 2.3 Insider Ownership — CEO ownership multiple, total insider %, recent Form 4 activity, cluster detection. **Run `${CLAUDE_PLUGIN_ROOT}/scripts/fetch_sentiment.py [TICKER] --sources insider`** for structured insider transactions with automated cluster detection.
- [ ] 2.4 Compensation — Performance metrics (ROIC/FCF vs revenue-only), vesting, clawbacks, peer group
- [ ] 2.5 Management Quality — Guidance accuracy, promise-to-delivery ratio, Glassdoor trend, employee retention

**Reference:** Use frameworks from `${CLAUDE_PLUGIN_ROOT}/references/frameworks_value_growth.md` (Fisher's 15 points, Scuttlebutt method).

**Validation gate:** At least one Form 4 filing from last 90 days reviewed.

**After completion:** Write stage summary to `/tmp/stock-analysis-[TICKER]-stage2.md`. Drop raw data. Retain: management score (1-10), key red flags.

**Skip rule:** Skip this stage for Short-term reports unless insider cluster activity is detected.

### Stage 3: Product & Industry

**Checklist:**
- [ ] 3.1 Product Analysis — Portfolio mapping, life cycle, innovation pipeline, NPS, pricing power
- [ ] 3.2 Industry Structure — Porter's Five Forces with evidence per force
- [ ] 3.3 Competitive Landscape — Market share trends, positioning map, peer comparisons, disruption threats
- [ ] 3.4 Market Sizing — TAM/SAM/SOM (top-down + bottom-up), penetration rate, adjacent markets
- [ ] 3.5 Platform Economics (if applicable) — Network effects, liquidity, multi-tenanting, take rate
- [ ] 3.6 Supply Chain — Supplier diversification, geographic concentration, critical components
- [ ] 3.7 Ecosystem Mapping — Upstream/downstream dependency, single-point-of-failure, complementor health

**Reference:** Use frameworks from `${CLAUDE_PLUGIN_ROOT}/references/frameworks_value_growth.md` (Porter, Morningstar moat).

**Validation gate:** At least 3 peer companies with GICS alignment justification.

**After completion:** Write stage summary to `/tmp/stock-analysis-[TICKER]-stage3.md`. Drop raw data. Retain: moat score (1-10), competitive position (3 sentences), TAM estimate.

### Stage 4: Macro Economics

**Checklist:**
- [ ] 4.1 Economic Cycle — Short-term debt cycle position (Dalio), PMI, housing starts, yield curve
- [ ] 4.2 Interest Rates — Company sensitivity (floating/fixed debt), central bank direction, valuation impact
- [ ] 4.3 Inflation — Input cost pressure, pricing power, margin regime analysis, TIPS breakeven
- [ ] 4.4 Supply/Demand — Capacity utilization, backlog, inventory levels, pricing cycle position
- [ ] 4.5 Currency — Revenue by currency, natural hedging, hedging effectiveness
- [ ] 4.6 Sector Drivers — 3-5 macro variables most correlated with sector; historical sensitivity

**Data acquisition:** Run `${CLAUDE_PLUGIN_ROOT}/scripts/fetch_macro.py --output /tmp/stock-analysis-macro.json` to pull FRED indicators. If `/tmp/stock-analysis-macro.json` already exists from Step 0, reuse it.

**Reference:** Load `${CLAUDE_PLUGIN_ROOT}/references/frameworks_macro_quant.md` for Dalio/Soros/Druckenmiller frameworks.

**Validation gate:** PMI, Fed funds rate, 10-year yield, and CPI all within Max Freshness (30 days).

**After completion:** Write stage summary to `/tmp/stock-analysis-[TICKER]-stage4.md`. Drop raw data. Retain: macro regime classification, 3 key tailwinds/headwinds.

### Stage 5: Politics & Geopolitics

**Checklist:**
- [ ] 5.1 Regulatory — Current framework, upcoming changes, risk probability × impact, antitrust concerns
- [ ] 5.2 Trade Policy — Tariff exposure (% COGS), trade agreement dependency, export controls
- [ ] 5.3 Geopolitical — Revenue HHI by country, GPR scores, sanctions exposure, conflict scenarios
- [ ] 5.4 Government Policy — Subsidies (IRA, CHIPS), tax direction, government-as-customer exposure
- [ ] 5.5 ESG — Rating trajectory, material issues, climate risk, social license, controversies

**Reference:** Use frameworks from `${CLAUDE_PLUGIN_ROOT}/references/frameworks_macro_quant.md`.

**Validation gate:** Countries representing >80% of revenue assessed.

**After completion:** Write stage summary to `/tmp/stock-analysis-[TICKER]-stage5.md`. Drop raw data.

**Skip rule:** Skip this stage for Short-term reports unless a geopolitical catalyst is flagged.

### Stage 6: Valuation

**Checklist:**
- [ ] 6.1 Multi-Method — DCF (5-10yr projections, WACC, terminal value, sensitivity table, reverse DCF), Trading Comps (peer universe, EV/EBITDA, P/E, P/FCF, PEG), SOTP if multi-segment, DDM/Residual Income/LBO as applicable
- [ ] 6.2 Relative Value — P/E vs history/peers, EV/EBITDA with growth justification, P/FCF vs risk-free rate, PEG
- [ ] 6.3 Technical — Trend (MAs, higher highs/lows), momentum (RSI, MACD), volume (OBV), support/resistance. **Run `${CLAUDE_PLUGIN_ROOT}/scripts/fetch_technicals.py [TICKER] --period 2y`** for deterministic indicator computation and composite trend/momentum scores.
- [ ] 6.4 Sentiment — Put/call ratio, VIX term structure, short interest, options flow, dark pool prints. **Run `${CLAUDE_PLUGIN_ROOT}/scripts/fetch_sentiment.py [TICKER] --sources news,social`** for news sentiment buzz and social media metrics.
- [ ] 6.5 Institutional Flow — 13F analysis, activist 13D, Form 4 clusters, ownership concentration. **Run `${CLAUDE_PLUGIN_ROOT}/scripts/fetch_sentiment.py [TICKER] --sources analyst`** for analyst consensus and price targets.

**Reference:** Load `${CLAUDE_PLUGIN_ROOT}/references/frameworks_macro_quant.md` for Greenblatt's Magic Formula. Load `${CLAUDE_PLUGIN_ROOT}/references/frameworks_risk_alt.md` for Burry's SEC deep-dive.

**Validation gate:** At least 2 independent valuation methods applied. DCF sensitivity table produced.

**After completion:** Write stage summary to `/tmp/stock-analysis-[TICKER]-stage6.md`. Drop raw data. Retain: intrinsic value range, relative value assessment, key technical levels.

### Stage 7: Risk Assessment

**Checklist:**
- [ ] 7.1 Risk Identification — Categorize: operational, financial, competitive, regulatory, macro, geopolitical, ESG
- [ ] 7.2 Risk Quantification — Probability × Impact matrix per risk, EPS impact, mitigants
- [ ] 7.3 Scenario Analysis — Bull/Base/Bear with explicit assumptions, regime-adjusted probabilities, implied prices
- [ ] 7.4 Catalyst Timeline — Upcoming events, timeframe, expected impact, probability
- [ ] 7.5 Cross-Dimensional Synthesis — Marks's 2nd-level thinking, Soros reflexivity, Dalio cycle position
- [ ] 7.6 Forensic Red Flag Summary — Flag if 3+ of the 9 red flags present
- [ ] 7.7 Operational Due Diligence — Cybersecurity, legal history, DR/BC, insurance, IP, compliance, 3rd-party risk
- [ ] 7.8 Thesis Falsifiability — Pre-mortem, falsification conditions, dissenting view search, inversion checklist, kill switch

**Reference:** Load `${CLAUDE_PLUGIN_ROOT}/references/frameworks_risk_alt.md` for Marks's risk framework and forensic red flag details. Load `${CLAUDE_PLUGIN_ROOT}/references/institutional_odd.md` for ODD checklists.

**Validation gate:** Beneish M-Score, Altman Z-Score, and 5+ forensic checks completed.

**After completion:** Write stage summary to `/tmp/stock-analysis-[TICKER]-stage7.md`. Drop raw data. Retain: risk score (1-10), top 3 risks, scenario price targets.

### Stage 8: Alternative Data

**Checklist:**
- [ ] 8.1 Digital Footprint — Web traffic trends, app rankings/downloads, social media metrics, hiring trends, patents
- [ ] 8.2 Transaction Data — Credit/debit card trends, revenue estimation, wallet share shifts
- [ ] 8.3 Satellite/Sensor — Foot traffic, industrial activity, shipping/logistics flow
- [ ] 8.4 NLP Earnings Call — Tone analysis, Q&A vs prepared remarks differential, uncertainty, deception indicators. Save the latest earnings transcript to `/tmp/stock-analysis-[TICKER]-transcript.txt`, then **run `${CLAUDE_PLUGIN_ROOT}/scripts/calculate_candor.py /tmp/stock-analysis-[TICKER]-transcript.txt`**.
- [ ] 8.5 Composite Score — Weighted alternative data score (web 20%, app 20%, social 15%, employee 15%, hiring 15%, innovation 15%)
- [ ] 8.6 Primary Research — Expert network synthesis, channel checks (supplier/customer/competitor/former employee), convergence scoring

**Reference:** Load `${CLAUDE_PLUGIN_ROOT}/references/frameworks_risk_alt.md` for ARK's disruption framework.

**Data acquisition:** Run `${CLAUDE_PLUGIN_ROOT}/scripts/fetch_alternatives.py [TICKER]`. Paywalled sources return `null` — this is expected, proceed.

**Validation gate:** At least 3 of 6 alternative data dimensions have non-null readings.

**After completion:** Write stage summary to `/tmp/stock-analysis-[TICKER]-stage8.md`.

### Stage 9: Report Generation

**Workflow:**
1. Read all stage summaries from `/tmp/stock-analysis-[TICKER]-stage[1-8].md`
2. Load `${CLAUDE_PLUGIN_ROOT}/references/report_templates.md` for output structure
3. Determine which report types to generate (from Step 0 triage)
4. For each report type:
   - Apply the conviction scoring formula from `${CLAUDE_PLUGIN_ROOT}/references/report_templates.md`
   - Apply methodology weights per report type
   - Apply framework conflict resolution if needed (Rules 1-4 in report_templates.md)
   - Generate the report following the template structure exactly
   - Run the pre-delivery checklist (see below)
5. Write each report to `./reports/[TICKER]/[TICKER]_[ReportType]_[YYYY-MM-DD].md`
6. Clean up temp files on success. Preserve on failure.

## Pre-Delivery Checklist

Before writing each report, verify:
- [ ] All Tier 1 data sources within Max Freshness
- [ ] No [STALE] flags on critical metrics
- [ ] At least 1 framework divergence acknowledged (if applicable)
- [ ] Kill switch defined for each report type
- [ ] Methodology attribution present for all major conclusions
- [ ] Fact/Interpretation/Speculation tags on all source citations
- [ ] 5 random fact checks: trace claims back to source — remove any unverifiable claim
- [ ] Cost budget not exceeded by >20% without user notification

## Context Eviction Protocol

After every stage, execute this sequence:
1. `write_file` → `/tmp/stock-analysis-[TICKER]-stage[N].md` with: key metrics table, stage scores, 3-sentence narrative per sub-section
2. Drop raw data from context (SEC filing text, full transcripts, raw financials, full search results)
3. Load next stage's reference file
4. If context usage exceeds ~80%, offload additional intermediate data before continuing

## Validation Loops

After Stage 9 report generation:
1. Select 5 random numeric claims from the report
2. Trace each back to its source file
3. If any claim is unverifiable → remove it, flag the gap
4. If 2+ verified claims contain errors → restart the affected stage

## Stage Depth Allocation

| Stage | Long-term | Mid-term | Short-term |
|-------|-----------|----------|------------|
| 1: Fundamentals | Deep (1.1-1.6) | Standard (1.1-1.3) | Light (1.1 summary) |
| 2: Executive | Deep (2.1-2.5) | Standard (2.1-2.3) | Skip (unless insider flags) |
| 3: Product/Industry | Deep (3.1-3.7) | Standard (3.1-3.4) | Light (3.1 only) |
| 4: Macro | Standard (4.1-4.3) | Deep (4.1-4.6) | Standard (4.1-4.2) |
| 5: Geopolitics | Standard (5.1-5.4) | Deep (5.1-5.5) | Light (5.1 only) |
| 6: Valuation | Deep (6.1-6.2) | Deep (6.1-6.5) | Standard (6.3-6.5) |
| 7: Risk | Deep (7.1-7.8) | Standard (7.1-7.4) | Light (7.2, 7.4) |
| 8: Alternative Data | Light (8.4 only) | Standard (8.1, 8.4-8.5) | Deep (8.1-8.6) |
| 9: Reports | Full | Full | Full |

## Parallelism

Use `agent_spawn` to parallelize independent stages:
- Long-term: Stages 1-3 can run in parallel
- Mid-term: Stages 4-6 can run in parallel; Stages 1+7, 2+8 can pair
- Short-term: Stages 6+8 can pair
- Quick Overview: Stages 1+6+7 can parallelize

Cap parallel sub-agents at 2 (Long-term/Short-term) or 3 (Mid-term).
