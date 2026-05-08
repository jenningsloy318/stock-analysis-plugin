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
version: "1.0.23"
license: MIT
compatibility: Requires Firecrawl MCP, Tavily MCP, Tinyfish MCP (OAuth), XCrawl MCP, Web Search Prime, Exa MCP, exec_shell, write_file, read_file. Python 3.10+ for bundled scripts. Optional: FRED_API_KEY (macro), FINNHUB_API_KEY (sentiment/insider/earnings).
---

# Stock Analysis — Multi-Stage Equity Research

## Overview

<purpose>Stock-analyst (team lead) agent team workflow. The stock-analyst orchestrates specialized analyst teammates — it NEVER performs deep analysis directly, only spawns, coordinates, and verifies. Analyst agents execute fundamentals, industry, macro, valuation, risk, alternative data, and report stages in parallel where possible.</purpose>

<triggers>Triggers on: "analyze [TICKER]", "stock analysis", "equity research", "should I buy [TICKER]", "deep dive on [COMPANY]", "investment thesis", "valuation of [TICKER]", "due diligence on [COMPANY]". Do NOT trigger on: general market commentary, portfolio questions without specific tickers, non-financial queries.</triggers>

This skill performs institutional-grade stock analysis through 11 stages, producing 1-3 reports (long/mid/short-term) per ticker. Analysis depth adjusts per report type — see `references/equity_report_templates.md` for output formats.

**Critical constraint:** The context window is a shared resource. Follow the eviction protocol strictly. Raw data from completed stages is dropped; only stage summaries persist.

## Script Execution

All Python scripts are bundled with the plugin at `${CLAUDE_PLUGIN_ROOT}/scripts/`. Run via `uv run` to ensure correct dependencies:
```
uv run python ${CLAUDE_PLUGIN_ROOT}/scripts/fetch_financials.py AAPL --years 5 --output ./reports/AAPL/raw-data.json
```

If `uv` is not available, fall back to activating the `.venv` in `${CLAUDE_PLUGIN_DATA}` or using `python` directly with `${CLAUDE_PLUGIN_ROOT}/scripts/requirements.txt` installed.

**Path variables:**
- `${CLAUDE_PLUGIN_ROOT}` — Plugin installation directory (scripts, references, agents). Treat as read-only.
- `${CLAUDE_PLUGIN_DATA}` — Persistent plugin state (venvs, caches). Survives plugin updates.
- Output always goes to `./reports/` relative to the user's workspace.

## Search Tools

This skill uses multiple web search tools for financial data acquisition. See `agents/search-agent.md` for full search methodology.

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

## Data Source Coverage

Before starting any stage, load `references/data_source_matrix.md` and create a source coverage plan for the ticker. The plan must identify:
- Blocking Tier 0/Tier 1 sources required for the selected report type
- Sector-specific add-ons (banks, insurance, REITs, energy, biotech, SaaS, semis, industrials, consumer)
- Non-US substitutions for filings, macro, governance, and rates if the issuer is outside the US
- Freshness limits and source quorum for each major dimension
- Confidence cap if any blocking dimension is missing or stale

## Gotchas

- Do not invent financial figures. If data is unavailable, state "Data not available" — never guess.
- Company fiscal years vary. A "Q4 2025" filing may cover April-June 2025. Always check the filing's period-end date.
- Tier 1 data sources (SEC filings, financial statements) block stage completion if unavailable. Do not proceed with stale data.
- The `finance` tool returns real-time quotes. For historical context, use the script output or search tools (Firecrawl/XCrawl/Tavily).
- Insider transaction analysis: open-market purchases are the strongest signal. 10b5-1 plan sales are noise.
- All source citations must use `[Source: ... | Retrieved: ... | Fact/Interpretation/Speculation]` format.

## Workflow

### Step 0: Triage (orchestrator executes directly)

1. Identify the ticker symbol from the user's request. If ambiguous (e.g., "Apple"), resolve via `mcp__xcrawl-mcp__xcrawl_search`: "Apple Inc stock ticker symbol."
2. Determine report type(s) using the decision tree:
   - "long-term" / "invest" / "intrinsic value" → Long-term (1-3+ years)
   - "trade" / "swing" / "catalyst" / "earnings" → Mid-term (1-12 months)
   - "options" / "momentum" / "this week" / "setup" → Short-term (days-weeks)
   - "quick" / "overview" / "snapshot" → Quick Overview (reduced stages, Mid-term format)
   - Default (no horizon specified) → Mid-term, then ask: "Would you also like a long-term intrinsic value analysis?"
3. **Initialize state**: Run `${CLAUDE_PLUGIN_ROOT}/scripts/persist.py init [TICKER] --report-type [TYPE]` to create a checkpointed analysis session. Record the returned `analysis_id` — use it for all subsequent `persist.py save` calls.
4. Create output directory: `./reports/[TICKER]/`
5. **Source coverage plan**: Load `references/data_source_matrix.md`. Write `./reports/[TICKER]/source-plan.md` with required data by dimension, source tier, max freshness, and confidence cap rules. For non-US issuers, explicitly name local filing/statistical substitutes.
6. **Earnings calendar check**: Run `${CLAUDE_PLUGIN_ROOT}/scripts/fetch_sentiment.py [TICKER] --sources earnings` for upcoming earnings dates and past surprises. If FINNHUB_API_KEY is not set, fall back to `mcp__web-search-prime__web_search_prime` for "[TICKER] next earnings date [YEAR]". If earnings are within 14 days, warn the user: "Earnings report on [DATE] may invalidate this analysis. Proceed or wait?" If within 3 days, recommend waiting unless the user explicitly overrides.
7. Run `${CLAUDE_PLUGIN_ROOT}/scripts/fetch_financials.py [TICKER] --years 5 --output ./reports/[TICKER]/raw-data.json` to retrieve financial data.
8. Run `${CLAUDE_PLUGIN_ROOT}/scripts/fetch_macro.py --indicators GDPC1,CPIAUCSL,UNRATE,DFF,DGS10,T10Y2Y,NAPM,CPILFESL,PCEPI,PCEPILFE,T5YIFR,BAA10Y,BAMLH0A0HYM2,INDPRO,TCU,HOUST,UMCSENT --output ./reports/macro.json` to capture current macro, inflation, credit, and activity context.
8b. Run `${CLAUDE_PLUGIN_ROOT}/scripts/fetch_global_macro.py --output ./reports/global_macro.json` for non-US macro data (ECB, PBOC, BOJ, Eurostat, World Bank). Required for non-US issuers; informative for US companies with international revenue.
8c. Run `${CLAUDE_PLUGIN_ROOT}/scripts/fetch_economic_surprises.py --output ./reports/economic_surprises.json` for economic surprise indices (actual vs consensus for GDP, CPI, PMI, payrolls). Positive surprises = macro tailwind; negative = headwind.
9. **Time-series forecasting**: Run `${CLAUDE_PLUGIN_ROOT}/scripts/forecast.py ./reports/[TICKER]/raw-data.json --horizon 5 --method ensemble --output ./reports/[TICKER]/forecast.json` to produce ARIMA/ETS ensemble forecasts for revenue, EPS, and FCF. This replaces the old single constant-growth assumption.
10. **Credit market check**: Run `${CLAUDE_PLUGIN_ROOT}/scripts/fetch_credit.py [TICKER] --output ./reports/[TICKER]/credit.json` to retrieve credit spreads, debt maturity, and credit rating. Bond markets often price risk faster than equities.
11. **Filing redline analysis**: Run `${CLAUDE_PLUGIN_ROOT}/scripts/diff_filings.py [TICKER] --output ./reports/[TICKER]/filing_diff.json` for automated 10-K/10-Q redline detection (risk factor additions/deletions, MD&A tone shift, accounting policy changes). For ADRs/non-US issuers, use 20-F/40-F/6-K or local annual/interim reports. Supplement with `mcp__firecrawl__firecrawl_search` with `includeDomains: ["sec.gov"]` if script output is incomplete.
12. Run `${CLAUDE_PLUGIN_ROOT}/scripts/calculate_metrics.py ./reports/[TICKER]/raw-data.json --output ./reports/[TICKER]/metrics.json` to compute ratios and valuation. If market cap is known, add `--market-cap [VALUE]`.
13. Call `finance` tool for current price, market cap, 52-week range, shares outstanding.

### Stage 1: Company Fundamentals → Spawn fundamental-analyst

**Checklist:**
- [ ] 1.1 Financial Health — Revenue trends, margins, FCF, leverage, working capital, ROIC/ROE/ROA
- [ ] 1.2 Business Model — Revenue model type, quality (recurring %), unit economics, customer concentration
- [ ] 1.3 Competitive Moat — Morningstar framework: cost advantages, network effects, intangibles, switching costs, efficient scale; moat trajectory
- [ ] 1.4 Historical Performance — 5-year CAGR (revenue, EPS, FCF), guidance accuracy, recession performance
- [ ] 1.5 Forensic Accounting — Beneish M-Score, Altman Z-Score, Piotroski F-Score, revenue recognition, accruals check
- [ ] 1.6 Segment-Level (if multi-segment) — Per-segment revenue, margin, ROIC, moat; BCG classification
- [ ] 1.7 Sector KPI Coverage — Apply sector-specific operating metrics from `references/data_source_matrix.md` and `references/sector_metrics.md` (e.g., ARR/NRR for SaaS, CET1/NIM for banks, FFO/AFFO for REITs, reserves/decline rates for energy)

**Reference:** Load `references/frameworks_value_growth.md` for Buffett/Munger/Fisher/Lynch frameworks. Load `references/sector_metrics.md` for sector-specific KPIs.

**Validation gate:** At least 3 years of revenue, operating income, FCF, total debt from Tier 1 source. Beneish M-Score, Altman Z-Score, and Piotroski F-Score computed.

**After completion:** Write stage summary to `./reports/[TICKER]/stage1.md`. Drop raw financial data from context. Retain: key metrics (table), moat assessment (3 sentences), forensic flags (list).

### Stage 2: Executive & Board Profiles → Spawn fundamental-analyst

**Checklist:**
- [ ] 2.1 Leadership Assessment — CEO/CFO background, tenure, board composition, departures, succession
- [ ] 2.2 Capital Allocation — ROIC vs WACC spread, incremental ROIC, M&A track record, buyback discipline
- [ ] 2.3 Insider Ownership — CEO ownership multiple, total insider %, recent Form 4 activity, cluster detection. **Run `${CLAUDE_PLUGIN_ROOT}/scripts/fetch_sentiment.py [TICKER] --sources insider`** for structured insider transactions with automated cluster detection.
- [ ] 2.4 Compensation — Performance metrics (ROIC/FCF vs revenue-only), vesting, clawbacks, peer group
- [ ] 2.5 Management Quality — Guidance accuracy, promise-to-delivery ratio, Glassdoor trend, employee retention
- [ ] 2.6 Governance Structure — Dual-class shares (voting power concentration), poison pills, staggered board, shareholder proposal history, proxy fight history, director independence %, board diversity, audit committee financial expertise. **Governance red flags:** dual-class with >10:1 voting ratio, no lead independent director, same person as Chair + CEO without strong lead director.

**Reference:** Use frameworks from `references/frameworks_value_growth.md` (Fisher's 15 points, Scuttlebutt method).

**Validation gate:** At least one Form 4 filing from last 90 days reviewed.

**After completion:** Write stage summary to `./reports/[TICKER]/stage2.md`. Drop raw data. Retain: management score (1-10), key red flags.

**Skip rule:** Skip this stage for Short-term reports unless insider cluster activity is detected.

### Stage 3: Product & Industry → Spawn industry-analyst

**Checklist:**
- [ ] 3.1 Product Analysis — Portfolio mapping, life cycle, innovation pipeline, NPS, pricing power
- [ ] 3.2 Industry Structure — Porter's Five Forces with evidence per force
- [ ] 3.3 Competitive Landscape — Market share trends, positioning map, peer comparisons, disruption threats
- [ ] 3.4 Market Sizing — TAM/SAM/SOM (top-down + bottom-up), penetration rate, adjacent markets
- [ ] 3.5 Platform Economics (if applicable) — Network effects, liquidity, multi-tenanting, take rate
- [ ] 3.6 Supply Chain — Supplier diversification, geographic concentration, critical components
- [ ] 3.7 Ecosystem Mapping — Upstream/downstream dependency, single-point-of-failure, complementor health
- [ ] 3.8 Unit Economics & KPI Benchmarking — Identify the 3-7 KPIs that actually drive valuation in this industry; benchmark against peers and historical ranges
- [ ] 3.9 TAM Reality Check — Cross-check top-down TAM with bottom-up spend/customer math. Flag any TAM that depends on unrealistic adoption, pricing, or penetration assumptions.

**Reference:** Use frameworks from `references/frameworks_value_growth.md` (Porter, Morningstar moat).

**Validation gate:** At least 3 peer companies with GICS alignment justification. TAM must include both top-down and bottom-up sanity checks. Sector KPIs must be listed even if "Data not available."

**After completion:** Write stage summary to `./reports/[TICKER]/stage3.md`. Drop raw data. Retain: moat score (1-10), competitive position (3 sentences), TAM estimate.

### Stage 4: Macro Economics → Spawn macro-analyst

**Checklist:**
- [ ] 4.1 Economic Cycle — Short-term debt cycle position (Dalio), PMI, housing starts, yield curve
- [ ] 4.2 Interest Rates — Company sensitivity (floating/fixed debt), central bank direction, valuation impact
- [ ] 4.3 Inflation — Input cost pressure, pricing power, margin regime analysis, TIPS breakeven
- [ ] 4.4 Supply/Demand — Capacity utilization, backlog, inventory levels, pricing cycle position
- [ ] 4.5 Currency — Revenue by currency, natural hedging, hedging effectiveness
- [ ] 4.6 Sector Drivers — 3-5 macro variables most correlated with sector; historical sensitivity

**Data acquisition:** Run `${CLAUDE_PLUGIN_ROOT}/scripts/fetch_macro.py --output ./reports/macro.json` to pull FRED indicators. If `./reports/macro.json` already exists from Step 0, reuse it. **If analyzing a non-US company,** explicitly use `mcp__tavily-remote-mcp__tavily_search` to pull regional equivalents (e.g., ECB rates, Eurozone inflation, PBOC rates, China PMI) since FRED is US-centric.

**Reference:** Load `references/frameworks_macro_quant.md` for Dalio/Soros/Druckenmiller frameworks.

**Validation gate:** PMI, Fed funds rate, 10-year yield, and CPI all within Max Freshness (30 days).

**After completion:** Write stage summary to `./reports/[TICKER]/stage4.md`. Drop raw data. Retain: macro regime classification, 3 key tailwinds/headwinds.

### Stage 5: Politics & Geopolitics → Spawn macro-analyst

**Checklist:**
- [ ] 5.1 Regulatory — Current framework, upcoming changes, risk probability × impact, antitrust concerns
- [ ] 5.2 Trade Policy — Tariff exposure (% COGS), trade agreement dependency, export controls
- [ ] 5.3 Geopolitical — Revenue HHI by country, GPR scores, sanctions exposure, conflict scenarios
- [ ] 5.4 Government Policy — Subsidies (IRA, CHIPS), tax direction, government-as-customer exposure
- [ ] 5.5 ESG — Rating trajectory, material issues, climate risk, social license, controversies
- [ ] 5.6 Legal/Policy Docket — Identify pending rules, litigation, antitrust actions, export controls, reimbursement decisions, rate cases, or permitting decisions with concrete dates where available

**Reference:** Use frameworks from `references/frameworks_macro_quant.md`.

**Validation gate:** Countries representing >80% of revenue assessed. Material regulatory/legal catalysts within the next 12 months listed or marked "None found."

**After completion:** Write stage summary to `./reports/[TICKER]/stage5.md`. Drop raw data.

**Skip rule:** Skip this stage for Short-term reports unless a geopolitical catalyst is flagged.

### Stage 6: Valuation → Spawn quant-analyst

**Checklist:**
- [ ] 6.1 Multi-Method — **DCF using ensemble forecast growth rates** (from `./reports/[TICKER]/forecast.json`), WACC, terminal value, sensitivity table, reverse DCF. **Run `${CLAUDE_PLUGIN_ROOT}/scripts/calculate_metrics.py ./reports/[TICKER]/raw-data.json --wacc [WACC] --growth [ENSEMBLE_CAGR] --market-cap [VALUE] --output ./reports/[TICKER]/metrics.json`** with the ensemble forecast FCF CAGR instead of a fixed constant. Trading Comps (peer universe, EV/EBITDA, P/E, P/FCF, PEG), SOTP if multi-segment. **For financial companies (banks, insurance):** Use Residual Income Model (RIM) instead of DCF — `calculate_metrics.py` produces this automatically when equity and ROE are available. **For mature dividend payers (utilities, REITs, staples):** Use Dividend Discount Model (DDM) — produced automatically when dividend_per_share is in profile data.
- [ ] 6.1b **Monte Carlo Simulation**: Run `${CLAUDE_PLUGIN_ROOT}/scripts/calculate_metrics.py ./reports/[TICKER]/raw-data.json --monte-carlo --mc-growth-mu [ENSEMBLE_CAGR] --mc-growth-sigma [RESIDUAL_STD] --wacc [WACC] --market-cap [VALUE] --shares [SHARES] --output ./reports/[TICKER]/metrics.json`. Produces 10K-run distribution with VaR, CVaR, and percentile-based price targets. **Do this for Long-term and Mid-term reports.**
- [ ] 6.2 Relative Value — P/E vs history/peers, EV/EBITDA with growth justification, P/FCF vs risk-free rate, PEG. **Run `${CLAUDE_PLUGIN_ROOT}/scripts/fetch_peer_universe.py [TICKER] --source all --max 10 --fetch-metrics --output ./reports/[TICKER]/peers.json`** to algorithmically identify peers via GICS + ETF holdings + description matching for an unbiased comparison group.
- [ ] 6.3 Technical — Trend (MAs, higher highs/lows), momentum (RSI, MACD), volume (OBV), support/resistance. **Run `${CLAUDE_PLUGIN_ROOT}/scripts/fetch_technicals.py [TICKER] --period 2y`** for deterministic indicator computation and composite trend/momentum scores.
- [ ] 6.4 Sentiment — Put/call ratio, VIX term structure, short interest, options flow, dark pool prints. **Run `${CLAUDE_PLUGIN_ROOT}/scripts/fetch_sentiment.py [TICKER] --sources news,social`** for news sentiment buzz and social media metrics. **Run `${CLAUDE_PLUGIN_ROOT}/scripts/fetch_news_nlp.py [TICKER] --output ./reports/[TICKER]/news_nlp.json`** for NLP-based news sentiment, narrative theme tracking, and coverage spike detection. **For Short-term reports, also run `${CLAUDE_PLUGIN_ROOT}/scripts/fetch_realtime.py [TICKER] --mode options`** for options chain data (put/call OI, max pain, ATM IV).
- [ ] 6.4b Options-Implied Signals — **Run `${CLAUDE_PLUGIN_ROOT}/scripts/calculate_options.py [TICKER] --output ./reports/[TICKER]/options.json`** for IV surface analysis, max pain computation, put/call ratios, skew interpretation, and unusual activity detection. Options markets price tail risk — divergence from equity price signals early.
- [ ] 6.5 Institutional Flow — 13F analysis, activist 13D, Form 4 clusters, ownership concentration. **Run `${CLAUDE_PLUGIN_ROOT}/scripts/fetch_sentiment.py [TICKER] --sources analyst`** for analyst consensus and price targets.
- [ ] 6.6 Estimate Revisions — **Run `${CLAUDE_PLUGIN_ROOT}/scripts/fetch_sentiment.py [TICKER] --sources revisions`** for earnings revision velocity (3-month direction and magnitude). Positive revision momentum is among the strongest short-term alpha signals. Flag if 3+ consecutive months of upward/downward revisions.
- [ ] 6.7 Valuation Method Fit — Select methods by business type: DCF for cash-generative operating companies, RIM for banks/insurers, DDM for mature dividend payers, NAV for asset-heavy/REIT/resource businesses, SOTP for multi-segment companies, probability-weighted pipeline valuation for biotech, and revenue/FCF multiples only as supporting evidence for unprofitable high-growth firms.
- [ ] 6.8 Consensus Bridge — Show where the model differs from consensus: revenue growth, margin, reinvestment, terminal multiple/growth, WACC, and share count. If no variant view exists, conviction cannot exceed 7.4.
- [ ] 6.9 Factor Attribution — **Run `${CLAUDE_PLUGIN_ROOT}/scripts/compute_factors.py [TICKER] --output ./reports/[TICKER]/factors.json`** for Fama-French 5-factor regression (market, SMB, HML, RMW, CMA). Reveals whether returns are driven by systematic exposure or alpha. High factor loadings reduce conviction in idiosyncratic thesis.
- [ ] 6.10 Liquidity & Microstructure — **Run `${CLAUDE_PLUGIN_ROOT}/scripts/compute_liquidity.py [TICKER] --position-size [SIZE] --output ./reports/[TICKER]/liquidity.json`** for Amihud illiquidity ratio, market impact estimate, days-to-liquidate, and position sizing constraints. Flag if liquidity score < 4 (micro/nano-cap) — requires reduced position sizing regardless of conviction.
- [ ] 6.11 Short Interest & Squeeze — **Run `${CLAUDE_PLUGIN_ROOT}/scripts/fetch_short_interest.py --ticker [TICKER] --output ./reports/[TICKER]/short_interest.json`** for short % float, days to cover, squeeze score (1-10), positioning divergence, and catalyst proximity. Critical for short-term reports.
- [ ] 6.12 Activist & Governance Catalysts — **Run `${CLAUDE_PLUGIN_ROOT}/scripts/fetch_activist_exposure.py --ticker [TICKER] --output ./reports/[TICKER]/activist.json`** for activist investor presence, 13D exposure, proxy fight probability, insider cluster detection, and governance vulnerability scoring.
- [ ] 6.13 Seasonality Analysis — **Run `${CLAUDE_PLUGIN_ROOT}/scripts/compute_seasonality.py ./reports/[TICKER]/raw-data.json --output ./reports/[TICKER]/seasonality.json`** for quarterly revenue/EPS seasonal strength indices, YoY growth decomposition, and current-quarter assessment vs seasonal expectation.

**Reference:** Load `references/frameworks_macro_quant.md` for Greenblatt's Magic Formula. Load `references/frameworks_risk_alt.md` for Burry's SEC deep-dive. For sector-specific valuation, load the relevant deep-dive reference: `references/industry_saas.md` (Tech/SaaS), `references/industry_biotech.md` (Pharma/Biotech), `references/industry_banks.md` (Financials), `references/industry_reits.md` (REITs/Real Estate — use FFO/AFFO/NAV, NOT P/E or DCF), `references/industry_industrials.md` (Industrials/Manufacturing — cycle-adjusted, backlog-driven), `references/industry_semis.md` (Semiconductors), `references/industry_energy.md` (Energy), `references/industry_insurance.md` (Insurance), `references/industry_healthcare.md` (Healthcare), `references/industry_consumer.md` (Consumer), `references/industry_utilities.md` (Utilities).

**Validation gate:** At least 2 independent valuation methods applied and one must be fit-for-business-model. DCF sensitivity table produced when DCF is applicable. Monte Carlo run for Long-term/Mid-term. Variant-view bridge included.

**After completion:** Write stage summary to `./reports/[TICKER]/stage6.md`. Run `${CLAUDE_PLUGIN_ROOT}/scripts/persist.py save [ANALYSIS_ID] 6 ./reports/[TICKER]/stage6.md`. Drop raw data. Retain: intrinsic value range (with Monte Carlo percentiles), relative value assessment, key technical levels.

### Stage 7: Market Regime & Positioning → Spawn quant-analyst

**Checklist:**
- [ ] 7.1 Risk-Off Indicators — VIX level + term structure (contango/backwardation), credit spreads (IG/HY OAS, TED spread), gold/USD/Treasury safe-haven flows, Fear & Greed Index
- [ ] 7.2 Liquidity Conditions — Fed balance sheet trend, reverse repo facility, M2 growth, bank lending standards, repo rates
- [ ] 7.3 Correlation Regime — Cross-asset correlation (risk-off = correlations → 1), sector dispersion, implied correlation index
- [ ] 7.4 Speculative Positioning — NYSE margin debt levels vs S&P 500, FINRA margin statistics, leveraged ETF flows
- [ ] 7.5 Retail Speculation — 0DTE options volume, call/put skew, retail order flow (PFOF data), meme stock momentum (social volume × price acceleration)
- [ ] 7.6 Short Squeeze Metrics — Short interest % float, cost to borrow, days to cover, FTD data, utilization rate
- [ ] 7.7 Fund Flows & Rotation — ETF inflows/outflows by sector, active fund positioning (CFTC COT), sector rotation signals
- [ ] 7.8 Speculation Thermometer — IPO/SPAC pipeline activity, crypto correlation (BTC as risk appetite proxy), SPX put/call ratio, AAII sentiment
- [ ] 7.9 Positioning Source Hygiene — Distinguish FINRA short interest from short-sale volume, CFTC futures positioning from equity ownership, and delayed 13F positions from current flow. Label lags explicitly.

**Classification output:**
- Market Regime: `Risk-Off Defensive` | `Neutral` | `Risk-On Speculative`
- Regime Confidence: High/Medium/Low with supporting evidence
- Impact on [TICKER]: How current regime affects this stock specifically (beta-adjusted, sector sensitivity)

**Data acquisition:**
- Run `${CLAUDE_PLUGIN_ROOT}/scripts/fetch_sentiment.py [TICKER] --sources market_regime` for VIX, credit spreads, margin data.
- **CFTC Commitments of Traders**: Run `${CLAUDE_PLUGIN_ROOT}/scripts/fetch_cot.py --market SP500,VIX,10Y_NOTE,USD,GOLD --output ./reports/[TICKER]/cot.json` for institutional futures positioning. Crowded longs = contrarian bearish; crowded shorts = squeeze potential. COT data leads equity moves by 1-3 weeks.
- **Credit market data**: Run `${CLAUDE_PLUGIN_ROOT}/scripts/fetch_credit.py [TICKER] --output ./reports/[TICKER]/credit.json` for HY/IG OAS spreads, TED spread, credit rating, and debt maturity. Credit markets often lead equities by 2-4 weeks.
- **Behavioral analysis**: Run `${CLAUDE_PLUGIN_ROOT}/scripts/fetch_behavioral.py [TICKER] --analyst-json ./reports/[TICKER]/sentiment.json --output ./reports/[TICKER]/behavioral.json` for analyst herding detection, sentiment divergence, and contrarian signals.
- `mcp__firecrawl__firecrawl_search` — "VIX term structure credit spreads [month] [year]", "NYSE margin debt latest data"
- `mcp__tavily-remote-mcp__tavily_search` with `time_range: "week"` — "market regime risk-on risk-off indicators [year]"
- `mcp__tavily-remote-mcp__tavily_research` with `model: "mini"` — "Current market positioning: VIX, credit spreads, margin debt, retail speculation, fund flows as of [date]"
- Tinyfish (post-auth): retail sentiment metrics, social media speculation intensity
- `mcp__xcrawl-mcp__xcrawl_search` — "[TICKER] short interest days to cover cost to borrow"

**Reference:** Load `references/frameworks_macro_quant.md` for Dalio's risk regime framework and Soros's reflexivity model.

**Validation gate:** VIX and credit spread data within 7 days freshness. At least 4 of 8 sub-items have current data. Any positioning metric with reporting lag must state the lag and cannot be used as a same-day signal.

**After completion:** Write stage summary to `./reports/[TICKER]/stage7.md`. Run `${CLAUDE_PLUGIN_ROOT}/scripts/persist.py save [ANALYSIS_ID] 7 ./reports/[TICKER]/stage7.md`. Drop raw data. Retain: regime classification, speculation score (1-10), top 3 positioning signals, impact assessment on [TICKER].

### Stage 8: Risk Assessment → Spawn risk-analyst

**Checklist:**
- [ ] 8.1 Risk Identification — Categorize: operational, financial, competitive, regulatory, macro, geopolitical, ESG
- [ ] 8.2 Risk Quantification — Probability × Impact matrix per risk, EPS impact, mitigants
- [ ] 8.3 Scenario Analysis — Bull/Base/Bear with explicit assumptions, regime-adjusted probabilities, implied prices. **Use Monte Carlo percentile outputs from Stage 6.1b for scenario price ranges.**
- [ ] 8.4 Catalyst Timeline — Upcoming events, timeframe, expected impact, probability
- [ ] 8.5 Cross-Dimensional Synthesis — Marks's 2nd-level thinking, Soros reflexivity, Dalio cycle position. **Incorporate behavioral findings from `./reports/[TICKER]/behavioral.json`**: narrative dominance, analyst herding, sentiment divergence, contrarian signals.
- [ ] 8.5b **Credit Risk Integration**: Load credit data from `./reports/[TICKER]/credit.json`. Assess: credit regime (stress/wide/normal/tight), debt maturity wall risk, interest coverage adequacy, credit rating trajectory. Flag if credit signals diverge from equity signals.
- [ ] 8.6 Forensic Red Flag Summary — Flag if 3+ of the 9 red flags present. Cross-reference with Beneish M-Score and Altman Z-Score from Stage 6 metrics.
- [ ] 8.7 Operational Due Diligence — Cybersecurity, legal history, DR/BC, insurance, IP, compliance, 3rd-party risk
- [ ] 8.8 Thesis Falsifiability — Pre-mortem, falsification conditions, dissenting view search, inversion checklist, kill switch. **Run `${CLAUDE_PLUGIN_ROOT}/scripts/persist.py kill-switch [TICKER]`** to check if prior kill switch conditions are approaching trigger levels.
- [ ] 8.9 Risk Signal Ladder — Define leading, coincident, and lagging indicators for the top 3 risks. Each kill switch must include observable source, threshold, and review cadence.

**Reference:** Load `references/frameworks_risk_alt.md` for Marks's risk framework and forensic red flag details. Load `references/institutional_odd.md` for ODD checklists. Load credit findings from `./reports/[TICKER]/credit.json`.

**Validation gate:** Beneish M-Score, Altman Z-Score, and 5+ forensic checks completed. Credit risk assessment performed. Top 3 risks each have source-linked early warning indicators.

**After completion:** Write stage summary to `./reports/[TICKER]/stage8.md`. Run `${CLAUDE_PLUGIN_ROOT}/scripts/persist.py save [ANALYSIS_ID] 8 ./reports/[TICKER]/stage8.md`. Drop raw data. Retain: risk score (1-10), top 3 risks, scenario price targets.

### Stage 9: Alternative Data → Spawn alt-data-analyst

**Checklist:**
- [ ] 9.1 Digital Footprint — Web traffic trends (Google Trends + Similarweb), app rankings/downloads (Apple App Store public API), social media metrics (Reddit praw), hiring trends (LinkedIn public page), patents (USPTO public API)
- [ ] 9.2 Transaction Data — Consumer demand proxy via Google Trends product search queries ("buy [TICKER]", "[TICKER] purchase"). Directional only.
- [ ] 9.3 Satellite/Sensor — Foot traffic, industrial activity, shipping/logistics flow (research via web search)
- [ ] 9.4 NLP Earnings Call — Tone analysis, Q&A vs prepared remarks differential, uncertainty, deception indicators. Save the latest earnings transcript to `./reports/[TICKER]/transcript.txt`, then **run `${CLAUDE_PLUGIN_ROOT}/scripts/calculate_candor.py ./reports/[TICKER]/transcript.txt`**.
- [ ] 9.5 Composite Score — Weighted alternative data score (web 20%, app 20%, social 15%, employee 15%, hiring 15%, innovation 15%)
- [ ] 9.6 Primary Research — Expert network synthesis, channel checks (supplier/customer/competitor/former employee), convergence scoring
- [ ] 9.7 Bias/Representativeness Check — State sample limitations, survivorship bias, platform bias, bot/noise risk, and whether alternative signals lead, lag, or simply confirm reported fundamentals

**Reference:** Load `references/frameworks_risk_alt.md` for ARK's disruption framework.

**Data acquisition:** Run `${CLAUDE_PLUGIN_ROOT}/scripts/fetch_alternatives.py [TICKER] --sources web,similarweb,app,glassdoor,social,patents,hiring,transactions --output ./reports/[TICKER]/alt-data.json`. All 8 sources are functional free/public APIs — no paywalled endpoints. Glassdoor and LinkedIn provide public page data. Google Trends proxies for web traffic and transaction signals.

**Validation gate:** At least 3 of 6 alternative data dimensions have non-null readings. Alternative data cannot raise conviction above 7.4 unless it converges with Tier 1/Tier 2 evidence.

**After completion:** Write stage summary to `./reports/[TICKER]/stage9.md`. Run `${CLAUDE_PLUGIN_ROOT}/scripts/persist.py save [ANALYSIS_ID] 9 ./reports/[TICKER]/stage9.md`.

### Stage 10: Deterministic Scoring & Cross-Check (orchestrator executes directly)

**Run BEFORE report generation:**

**10a — Deterministic Scoring:** Run `${CLAUDE_PLUGIN_ROOT}/scripts/compute_scores.py` to produce reproducible 1-10 component scores:
```
scripts/compute_scores.py \
  --metrics ./reports/[TICKER]/metrics.json \
  --macro ./reports/macro.json \
  --technicals ./reports/[TICKER]/tech.json \
  --alternatives ./reports/[TICKER]/alt-data.json \
  --sentiment ./reports/[TICKER]/sentiment.json \
  --capital-structure ./reports/[TICKER]/capital_structure.json \
  --liquidity ./reports/[TICKER]/liquidity.json \
  --short-interest ./reports/[TICKER]/short_interest.json \
  --activist ./reports/[TICKER]/activist.json \
  --report-type [long|mid|short|quick] \
  --gics-sector [SECTOR_CODE] \
  --ticker [TICKER] \
  --output ./reports/[TICKER]/scores.json
```
This produces deterministic Financial Health, Moat Quality, Management Quality, Valuation Attractiveness, Capital Structure, Macro Tailwind, Risk Profile, Alternative Alignment, Technical Setup, Weinstein Alignment, and CANSLIM scores. Includes liquidity-adjusted position sizing caps, short squeeze catalysts (for short-term reports), and activist exposure flags. The LLM agent may adjust Moat and Management scores ±2.0 based on qualitative findings from Stages 1-3. All other scores are fixed.

**10b — Cross-Check Pass:** After scoring, validate for internal contradictions:
1. If Valuation Attractiveness ≤3.0 (significant overvaluation) AND Moat Quality ≥7.5 (wide moat): re-examine the moat assessment — is the market correctly pricing moat erosion?
2. If Risk Profile has 3+ red flags: re-examine Financial Health and Moat Quality with higher skepticism. Flag any downgrade.
3. If Alternative Alignment ≤3.0 (negative divergence) BUT Financial Health ≥7.0: investigate — are alternative data signals an early warning of undetected deterioration?
4. If Behavioral analysis shows herding score ≥8.0 with dominant "Strong Buy" consensus: apply contrarian overlay — reduce conviction by 0.5-1.0 points.
5. Check `framework_divergence` in scores.json — if `investigation_required: true`, examine each divergence pair's `investigation_prompt` and resolve or flag.
6. Record all cross-check findings. If contradictions cannot be resolved, flag the report: "CONTRADICTION UNRESOLVED — [specific issue]."
7. Apply source coverage confidence caps from `./reports/[TICKER]/source-plan.md`: missing/stale blocking dimensions cap confidence at Medium or Low per `references/data_source_matrix.md`.

**10c — Save conviction:** Run `${CLAUDE_PLUGIN_ROOT}/scripts/persist.py conviction [ANALYSIS_ID] [CONVICTION] [RATING] --component-scores ./reports/[TICKER]/scores.json` to record the conviction in state history for future backtesting.

### Stage 11: Report Generation → Spawn equity-report-writer

**Workflow:**
1. Read all stage summaries from `./reports/[TICKER]/stage[1-9].md`
2. Load deterministic scores from `./reports/[TICKER]/scores.json`
3. Load `references/equity_report_templates.md` for output structure and `references/data_source_matrix.md` for confidence/data-quality disclosure
4. Determine which report types to generate (from Step 0 triage)
5. For each report type:
   - Use the deterministic conviction score and rating from `compute_scores.py` output (do NOT invent a new conviction number)
   - Apply methodology weights per report type
   - Apply framework conflict resolution if needed (Rules 1-4 in equity_report_templates.md)
   - Incorporate cross-check findings from Step 10b
   - Include a Data Quality & Coverage section in the appendix with stale/missing source impacts
   - Generate the report following the template structure exactly
   - Run the pre-delivery checklist (see below)
6. Write each report to `./reports/[TICKER]/[TICKER]_[ReportType]_[YYYY-MM-DD].md`
7. Run `${CLAUDE_PLUGIN_ROOT}/scripts/persist.py complete [ANALYSIS_ID]` to mark the analysis as completed.

**Post-Delivery:**
- Run `${CLAUDE_PLUGIN_ROOT}/scripts/backtest.py --ticker [TICKER]` to compare this report against any prior predictions for the same ticker.
- Run `${CLAUDE_PLUGIN_ROOT}/scripts/event_study.py [TICKER] --events ./reports/[TICKER]/catalysts.json --output ./reports/[TICKER]/event_study.json` to measure cumulative abnormal returns (CAR) around identified catalyst events. Provides forward-looking expectation calibration.
- Run `${CLAUDE_PLUGIN_ROOT}/scripts/calibrate_conviction.py --db ./reports/state.db --output ./reports/calibration.json` to assess historical prediction accuracy, Brier score, and Bayesian adjustment recommendations. If calibration suggests reducing bullish/bearish bias, note in next report.
- If the user has specified a portfolio, run `${CLAUDE_PLUGIN_ROOT}/scripts/portfolio_context.py [TICKER] --portfolio '[PORTFOLIO_JSON]' --conviction [CONVICTION]` for position sizing, correlation guidance, tail risk (VaR/CVaR at 95%/99%), drawdown recovery analysis, and correlation regime detection.

## Pre-Delivery Checklist

Before writing each report, verify:
- [ ] Source coverage plan completed and confidence caps applied
- [ ] All Tier 1 data sources within Max Freshness
- [ ] Source quorum met for all numeric investment claims
- [ ] No [STALE] flags on critical metrics
- [ ] Deterministic scores from `compute_scores.py` used (not LLM-invented)
- [ ] At least 1 framework divergence acknowledged (if applicable)
- [ ] Cross-check pass completed — no unresolved contradictions
- [ ] Kill switch defined for each report type
- [ ] Methodology attribution present for all major conclusions
- [ ] Sector-specific KPIs included or marked "Data not available"
- [ ] Data Quality & Coverage appendix included
- [ ] Fact/Interpretation/Speculation tags on all source citations
- [ ] 5 random fact checks: trace claims back to source — remove any unverifiable claim
- [ ] Cost budget not exceeded by >20% without user notification

## Context Eviction Protocol

After every stage, execute this sequence:
1. `write_file` → `./reports/[TICKER]/stage[N].md` with: key metrics table, stage scores, 3-sentence narrative per sub-section
2. Run `${CLAUDE_PLUGIN_ROOT}/scripts/persist.py save [ANALYSIS_ID] [N] ./reports/[TICKER]/stage[N].md` to checkpoint
3. Drop raw data from context (SEC filing text, full transcripts, raw financials, full search results)
4. Load next stage's reference file
5. If context usage exceeds ~80%, offload additional intermediate data before continuing

## Validation Loops

After Stage 11 report generation:
1. Run `${CLAUDE_PLUGIN_ROOT}/scripts/backtest.py --ticker [TICKER]` to compare against prior predictions
2. Select 5 random numeric claims from the report
3. Trace each back to its source file
4. If any claim is unverifiable → remove it, flag the gap
5. If 2+ verified claims contain errors → restart the affected stage
6. Run `${CLAUDE_PLUGIN_ROOT}/scripts/persist.py complete [ANALYSIS_ID]` to finalize

## Stage Depth Allocation

| Stage | Long-term | Mid-term | Short-term |
|-------|-----------|----------|------------|
| 1: Fundamentals | Deep (1.1-1.6) | Standard (1.1-1.3) | Light (1.1 summary) |
| 2: Executive | Deep (2.1-2.5) | Standard (2.1-2.3) | Skip (unless insider flags) |
| 3: Product/Industry | Deep (3.1-3.7) | Standard (3.1-3.4) | Light (3.1 only) |
| 4: Macro | Standard (4.1-4.3) | Deep (4.1-4.6) | Standard (4.1-4.2) |
| 5: Geopolitics | Standard (5.1-5.4) | Deep (5.1-5.5) | Light (5.1 only) |
| 6: Valuation | Deep (6.1-6.5) | Deep (6.1-6.5) | Standard (6.3-6.5) |
| 7: Market Regime | Light (7.1-7.3) | Deep (7.1-7.8) | Deep (7.4-7.8) |
| 8: Risk | Deep (8.1-8.8) | Standard (8.1-8.6) | Light (8.2, 8.4, 8.5b) |
| 9: Alternative Data | Light (9.1, 9.4) | Standard (9.1, 9.4-9.5) | Deep (9.1-9.6) |
| 10: Scoring + Cross-Check | Full | Full | Full |
| 11: Reports | Full | Full | Full |

## Agent Team

The stock-analyst (team lead) spawns specialist teammates for ALL analysis work — it NEVER performs deep analysis directly. Sub-agents are defined in `agents/`:

| Agent | Stages | Spawn When |
|-------|--------|------------|
| `fundamental-analyst` | 1-2 | Company financials, moat, executive/insider analysis |
| `industry-analyst` | 3 | Competitive landscape, Porter's Five Forces, TAM/SAM |
| `macro-analyst` | 4-5 | Economic cycle, monetary policy, geopolitics |
| `quant-analyst` | 6-7 | Valuation (DCF, comps), technicals, market regime |
| `risk-analyst` | 8 | Risk quantification, scenarios, forensic red flags |
| `alt-data-analyst` | 9 | Web traffic, app data, NLP earnings, social sentiment |
| `search-agent` | All | Financial web search when specialist agents need data |
| `equity-report-writer` | 10 | Synthesize stage summaries into final reports |

**Claude Code**: Stock-analyst spawns via the `Agent` tool with `subagent_type: "stock-analysis:<agent-name>"`.
**Gemini CLI**: Stock-analyst auto-delegates based on agent descriptions, or user forces via `@agent-name` syntax.

## Parallelism

Stock-analyst (team lead) spawns sub-agents in parallel per report type (max 3 concurrent):
- Long-term: [fundamental-analyst + industry-analyst] → [macro-analyst] → [quant-analyst] → [risk-analyst] → [alt-data-analyst] → Scoring → [equity-report-writer]
- Mid-term: [macro-analyst + quant-analyst] → [fundamental-analyst + risk-analyst] → [alt-data-analyst] → Scoring → [equity-report-writer]
- Short-term: [quant-analyst + alt-data-analyst] → [risk-analyst] → Scoring → [equity-report-writer]
- Quick Overview: [fundamental-analyst + quant-analyst + risk-analyst] → Scoring → [equity-report-writer]

Post-stage-9: always run deterministic scoring (Stage 10) and cross-check before report generation (Stage 11).

Cap parallel sub-agents at 3.
Max concurrent script executions: 2 (scripts are I/O-bound, not CPU-bound).

## Post-Report Monitoring Protocol

After delivering a report, establish monitoring triggers for re-analysis:

### Automatic Re-Analysis Triggers
The following events should prompt re-running relevant stages:

| Trigger Event | Re-Run Stages | Urgency |
|---|---|---|
| Earnings release (actual vs estimate) | 1, 6, 10, 11 | Within 3 days |
| Kill switch condition approaching (>80% of trigger level) | 8, 10, 11 | Immediate |
| Price hits target (bull or bear scenario) | 6, 7, 10, 11 | Within 1 week |
| Material news (M&A, regulatory action, executive departure) | Relevant stage + 8, 10, 11 | Within 3 days |
| Macro regime change (Dalio quadrant shift) | 4, 7, 10, 11 | Within 1 week |
| 90 days elapsed since report (Long-term) | Full re-run | Scheduled |
| 30 days elapsed since report (Mid-term) | 6, 7, 9, 10, 11 | Scheduled |
| 7 days elapsed since report (Short-term) | 6, 7, 10, 11 | Scheduled |

### Monitoring Commands

After report delivery, suggest to the user:
> "Monitor this analysis with `/stock-analysis:watchlist [TICKER]` to check kill switch status and trigger conditions."

### State Persistence for Monitoring

- `${CLAUDE_PLUGIN_ROOT}/scripts/persist.py kill-switch [TICKER]` — Checks all active kill switch conditions against current data
- `${CLAUDE_PLUGIN_ROOT}/scripts/persist.py watchlist` — Lists all active analyses with staleness flags
- `${CLAUDE_PLUGIN_ROOT}/scripts/persist.py stale --days 30` — Identifies reports exceeding their refresh cadence

### Re-Analysis Protocol

When a trigger fires:
1. Load prior report from `./reports/[TICKER]/`
2. Load prior component scores from `persist.py`
3. Re-run only the affected stages (not full analysis)
4. Compare new scores vs prior — flag any that moved ≥2.0 points
5. If conviction rating changes by ≥1.5 points, generate an **UPDATE REPORT** (not full report)
6. Update `persist.py` state with new scores and timestamp
