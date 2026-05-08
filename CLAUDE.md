## Plugin versioning rule (MUST follow)
- Every modification MUST include a patch version bump in ALL platform manifests simultaneously:
  - `.claude-plugin/plugin.json`
  - `.claude-plugin/marketplace.json` (the plugin entry version)
  - `.codex-plugin/plugin.json`
  - `gemini-extension.json`
- Bump the patch level (e.g., 1.0.0 → 1.0.1) and include ALL four files in the same commit
- ALL four manifest versions MUST always match each other

## Analysis Philosophy (MUST follow)

- **Data integrity first**: Never invent financial figures. If data is unavailable, state "Data not available" — never guess.
- **Methodology transparency**: Every conclusion must be traceable to a specific analytical framework (Buffett, Dalio, Soros, Lynch, Fisher, Marks, Druckenmiller, Greenblatt, Burry, or ARK).
- **Second-level thinking**: Always ask "what's priced in?" not just "what's happening?"
- **Multi-dimensional analysis**: Cover all critical factors that move stock prices (fundamentals + macro + technicals + alternative data).
- **Progressive disclosure**: Load reference files on-demand per analysis stage. Drop raw data after each stage summary is written.
- **Source attribution**: Every data claim must use `[Source: ... | Retrieved: ... | Fact/Interpretation/Speculation]` format.

## Agent Orchestration (MUST follow)

- The main `stock-analysis` skill acts as the coordinator — it spawns specialized agents for parallel stage execution.
- Agents: `fundamental-analyst`, `industry-analyst`, `macro-analyst`, `quant-analyst`, `risk-analyst`, `alt-data-analyst`, `equity-report-writer`.
- The coordinator NEVER performs deep analysis directly — it delegates to specialist agents and synthesizes results.
- Parallel execution rules:
  - Long-term: Stages 1-3 can run in parallel
  - Mid-term: Stages 4-6 can run in parallel
  - Short-term: Stages 6+8 can pair
- Cap parallel sub-agents at 3.

## Web Search & Data Acquisition (MUST follow)

### Search Tool Priority (ordered by preference)

1. **Firecrawl MCP** (MANDATORY first for web research):
   - `mcp__firecrawl__firecrawl_search` — Primary web search for financial news, analyst reports, SEC filings. Supports `includeDomains`, `excludeDomains`, search operators.
   - `mcp__firecrawl__firecrawl_scrape` — Scrape specific pages (earnings transcripts, IR pages, SEC EDGAR). Use JSON format for structured extraction.
   - `mcp__firecrawl__firecrawl_extract` — LLM-powered structured extraction from multiple URLs (financial tables, analyst estimates).
   - `mcp__firecrawl__firecrawl_agent` — Complex multi-page research (industry reports, competitive analysis).

2. **Tavily MCP** (deep research + domain-filtered search):
   - `mcp__tavily-remote-mcp__tavily_search` — Web search with `include_domains`, `exclude_domains`, date range (`start_date`/`end_date`), search depth (basic/advanced/fast).
   - `mcp__tavily-remote-mcp__tavily_research` — Comprehensive multi-source research agent. Use `model: "pro"` for broad financial topics, `"mini"` for narrow queries.
   - `mcp__tavily-remote-mcp__tavily_extract` — Extract content from known URLs in markdown/text format.
   - `mcp__tavily-remote-mcp__tavily_crawl` — Crawl financial sites with depth/breadth control and path filtering.
   - `mcp__tavily-remote-mcp__tavily_map` — Map website structure (e.g., SEC EDGAR filing index, company IR pages).

3. **Tinyfish MCP** (social/alternative data — requires OAuth):
   - `mcp__tinyfish__authenticate` — Start OAuth flow. Must authenticate before first use each session.
   - `mcp__tinyfish__complete_authentication` — Complete OAuth with callback URL.
   - After auth: social media analytics, web traffic data, app store metrics, hiring signals.
   - Best for: Stage 8 alternative data, social sentiment, digital footprint analysis.

4. **XCrawl MCP** (SERP results + news):
   - `mcp__xcrawl-mcp__xcrawl_search` — Google SERP results for financial queries, news, earnings dates.
   - `mcp__xcrawl-mcp__xcrawl_scrape` — Scrape financial data pages with JS rendering support.

5. **Web Search Prime** (quick summaries):
   - `mcp__web-search-prime__web_search_prime` — Quick web search with summaries, good for macro data, analyst consensus, market news.

6. **Exa** (semantic search):
   - `mcp__exa__web_search_exa` — Semantic search for research papers, financial blogs, expert analysis.
   - Best for: "find blog posts comparing [company] to [peer]", "research papers on [industry trend]".

### Search Rules

- **Firecrawl FIRST**: Always run Firecrawl search before other tools. Use `includeDomains` for targeted financial sources.
- **Tavily for deep research**: Use `tavily_research` (model: "pro") for comprehensive topics requiring multi-source synthesis (industry analysis, macro outlook). Use `tavily_search` with `include_domains` for targeted lookups.
- **Tinyfish for social/alt data**: Authenticate once per session, then use for social media metrics, app rankings, web traffic signals.
- **Multi-source cross-reference**: Never trust a single source. Cross-reference financial data across 2+ search tools.
- **Financial domain targeting**: For financial data, prefer these domains:
  - SEC filings: `sec.gov`, `edgar.sec.gov`
  - Earnings: `seekingalpha.com`, `fool.com`, company IR pages
  - Analyst: `finance.yahoo.com`, `marketwatch.com`, `bloomberg.com`
  - Macro: `fred.stlouisfed.org`, `bls.gov`, `federalreserve.gov`
  - Social/Sentiment: `reddit.com/r/stocks`, `reddit.com/r/wallstreetbets`, `stocktwits.com`
- **Recency enforcement**: Always add current year to search queries. Use Tavily `time_range` or `start_date`/`end_date` for time-sensitive data.
- **Rate limiting**: Space requests across tools to avoid throttling. Prefer batch queries. Tavily research: max 20 req/min.

## Script Execution (MUST follow)

- Python scripts in `scripts/` perform deterministic calculations (DCF, ratios, scores, forecasting) — no LLM involvement in math.
- Scripts are called via `exec_shell` / `Bash` tool.
- Required environment: Python 3.10+, dependencies in `scripts/requirements.txt`.
- API keys: `FRED_API_KEY` (macro/credit) and `FINNHUB_API_KEY` (sentiment/insider/earnings) are recommended. All other keys are optional with functional fallbacks.

### Script Inventory

| Script | Purpose | Stage |
|--------|---------|-------|
| `fetch_financials.py` | Financial data (yfinance → SEC EDGAR → akshare) | 0 |
| `fetch_macro.py` | FRED macro indicators (incl. ISM Services, JOLTS, LEI) + Dalio regime classification | 0 |
| `fetch_global_macro.py` | Global macro: ECB, PBOC, BOJ, Eurostat, World Bank (non-US coverage) | 0 |
| `fetch_technicals.py` | Technical indicators (SMA, RSI, MACD, BB, ADX, etc.) | 6 |
| `fetch_sentiment.py` | Finnhub sentiment, insider, earnings, analyst, estimate revisions | 2,6 |
| `fetch_alternatives.py` | Alt data (Google Trends, Similarweb, App Store, Glassdoor, LinkedIn, Reddit, USPTO) | 9 |
| `fetch_credit.py` | Credit spreads, ratings, debt maturity (FRED + SEC EDGAR) | 8 |
| `fetch_behavioral.py` | Narrative economics, analyst herding, overreaction, anchoring bias, reflexivity | 8 |
| `fetch_cot.py` | CFTC Commitments of Traders — institutional futures positioning | 7 |
| `fetch_realtime.py` | Real-time quotes, options chain, pre/post market | 6 (short-term) |
| `fetch_economic_surprises.py` | Economic surprise indices (CESI proxies, FRED nowcasts, actual vs consensus) | 4 |
| `fetch_peer_universe.py` | Automated peer identification via GICS + ETF holdings + description match | 6 |
| `fetch_news_nlp.py` | News sentiment, narrative theme tracking, coverage spike detection | 6,9 |
| `fetch_capital_structure.py` | Buyback ROI, SBC dilution, capital return yield, debt maturity, optimal leverage | 1,2 |
| `fetch_private_comps.py` | M&A target probability, LBO floor, activist probability, precedent transactions | 6,8 |
| `fetch_esg_carbon.py` | ESG materiality, carbon pricing scenarios, stranded assets, transition risk | 8 |
| `fetch_supply_chain.py` | Supply chain concentration, geographic HHI, sector chokepoints, resilience score | 3 |
| `calculate_metrics.py` | Ratios, DCF, RIM, DDM, Piotroski F-Score, Beneish, Altman Z, peer comparison, Monte Carlo | 6 |
| `calculate_earnings_quality.py` | Accruals quality, cash conversion, revenue quality, expense signals, persistence | 1 |
| `calculate_candor.py` | Management candor NLP (hedging, certainty, Q&A delta) | 9 |
| `calculate_options.py` | Options signals: IV surface, max pain, put/call ratios, unusual activity | 6 |
| `forecast.py` | ARIMA/ETS ensemble + GARCH volatility + fat-tail Monte Carlo + regime detection | 6 |
| `compute_scores.py` | Deterministic 1-11 component scoring (incl. capital structure, Weinstein, CANSLIM) + conviction | 7 (cross-check) |
| `compute_sector_rs.py` | Sector relative strength rankings vs SPY across 1M/3M/6M/12M | Screening |
| `compute_factors.py` | Fama-French 5-factor regression + factor attribution (Kenneth French data) | 7 |
| `compute_liquidity.py` | Market microstructure, Amihud illiquidity, position sizing constraints | 6,10 |
| `validate_report.py` | Pre-delivery quality gate enforcement (freshness, coverage, consistency, forensics) | 11 (pre-delivery) |
| `event_study.py` | Cumulative abnormal return (CAR) around corporate events | 10 (post-delivery) |
| `diff_filings.py` | 10-K/10-Q redline detection: risk factor changes, MD&A tone shift, forensic flags | 1,8 |
| `backtest.py` | Validate past reports against actual outcomes | 10 (post-delivery) |
| `persist.py` | SQLite state persistence, checkpointing, resume, kill switch monitor | All |
| `portfolio_context.py` | Portfolio correlation, position sizing, factor exposure | 10 |

## Report Quality Gates (MUST follow)

- Pre-delivery checklist must pass before any report is delivered:
  - All Tier 1 data sources within Max Freshness
  - No [STALE] flags on critical metrics
  - At least 1 framework divergence acknowledged
  - Kill switch defined for each report type
  - Methodology attribution present for all major conclusions
  - 5 random fact checks passed (hallucination protocol)
- If any gate fails, report must carry: "INCOMPLETE ANALYSIS — [reason]"

## Context Window Management (MUST follow)

- After each stage: write stage summary to `./reports/[TICKER]/stage[N].md`
- Drop raw data from context (SEC filings, full transcripts, raw financials)
- Retain only: key metrics table, stage scores, 3-sentence narrative per sub-section
- Maximum active context at any point: <80% of the context window
