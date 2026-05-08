## Plugin versioning rule (MUST follow)
- Version bumps happen ONLY at commit time — one bump per commit, not per modification
- Every commit MUST include a patch version bump in ALL platform manifests simultaneously:
  - `.claude-plugin/plugin.json`
  - `.claude-plugin/marketplace.json` (the plugin entry version)
  - `.codex-plugin/plugin.json`
  - `gemini-extension.json`
- Bump the patch level (e.g., 1.0.0 → 1.0.1) and include ALL four files in the same commit
- ALL four manifest versions MUST always match each other

## Report Language Rule (MUST follow)

- ALL reports produced by both `stock-analysis` and `industry-screening` skills MUST be written in **Chinese (中文)**
- 所有分析报告必须使用中文撰写，不得使用英文撰写报告正文
- This applies to: equity research reports, screening reports, stage summaries, executive summaries, investment theses, and company commentaries
- Technical terms (ticker symbols, financial metric names like P/E, EV/EBITDA, ROIC) may remain in English
- GICS classification names should include both English and Chinese: e.g., "Semiconductors (半导体)"
- Source citations remain in their original language
- When writing report files, begin with Chinese headers (e.g., "# [TICKER] 长期投资分析报告") to ensure Chinese output

## Multi-Horizon Output Rule (MUST follow)

- Both skills (`stock-analysis` and `industry-screening`) ALWAYS produce **3 reports per run** covering all horizons:
  - Long-term (growth + moat weighted)
  - Mid-term (macro cycle + valuation weighted)
  - Short-term (momentum + flows weighted)
- Do NOT ask the user which horizon — always produce all three automatically
- One shared data-collection pass feeds all 3 report types; reports diverge at scoring/synthesis
- Output filenames: `[ID]_long_[DATE].md`, `[ID]_mid_[DATE].md`, `[ID]_short_[DATE].md`

## Stock Price Filter Rule (MUST follow)

- Focus on **growth-stage companies** (成长型公司), NOT mature blue-chips with high stock prices
- **US stocks**: Only select/recommend companies with current stock price **under $100**
- **China A-shares (A股)**: Only select/recommend companies with current stock price **under ¥100**
- This applies to: industry screening watchlists, stock-analysis recommendations, comparison candidates
- If analyzing a specific ticker requested by the user, proceed regardless of price (user override)
- For screening/watchlist: filter OUT companies above the price threshold before ranking

## Current Stock Price Display Rule (MUST follow)

- Whenever a company/stock appears in ANY report table, list, or comparison, include **current stock price** (当前股价) as a column
- This applies to: watchlists, company rankings, peer comparisons, screening results, recommendation tables
- Format: "$XX.XX" for US stocks, "¥XX.XX" for A-shares
- Price must be fetched at analysis time — never use stale/cached prices older than 1 trading day

## GICS Level 4 Screening Rule (MUST follow)

- Industry screening uses GICS Level 4 (Sub-Industry, 163 classifications) as the PRIMARY structural unit
- Level 1/2/3 (Sector, Industry Group, Industry) appear as CONTEXT within Level 4 sections — never as standalone report sections
- Report structure: flat ranked sub-industry leaderboard, no hierarchical sector grouping
- Reference: `references/gics_taxonomy.md` for full GICS hierarchy with codes and ETF proxies

## Analysis Philosophy (MUST follow)

- **Data integrity first**: Never invent financial figures. If data is unavailable, state "Data not available" — never guess.
- **Methodology transparency**: Every conclusion must be traceable to a specific analytical framework (Buffett, Dalio, Soros, Lynch, Fisher, Marks, Druckenmiller, Greenblatt, Burry, or ARK).
- **Second-level thinking**: Always ask "what's priced in?" not just "what's happening?"
- **Multi-dimensional analysis**: Cover all critical factors that move stock prices (fundamentals + macro + technicals + alternative data).
- **Dimension transparency (data-driven)**: Every final report MUST decompose the conviction score into ALL individual dimensions with numeric scores AND the raw data behind each score. Never present only the composite — always show the dimension breakdown table with per-dimension rationale, key data points, and sources. Explain WHICH dimensions most influenced the ranking/rating and WHY (with figures). Include dimension discrimination analysis (standard deviation, correlation with rank) to show what truly drove the selection.
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

- Python scripts are bundled with the plugin. `PLUGIN_ROOT` resolves per platform:
  - **Claude Code / Codex CLI**: `${CLAUDE_PLUGIN_ROOT}`
  - **Gemini CLI**: `${extensionPath}`
- `PLUGIN_SCRIPTS` = `${PLUGIN_ROOT}/scripts` (all script references use this).
- **ALL Python scripts MUST be run via `uv run python`** — never bare `python` or `python3`. When agents reference `${PLUGIN_SCRIPTS}/script.py`, execute as: `uv run python ${PLUGIN_SCRIPTS}/script.py [args]`. This ensures the correct virtual environment and dependencies are used.
- Persistent state (venvs, caches) goes in `${PLUGIN_DATA}`:
  - **Claude/Codex**: `${CLAUDE_PLUGIN_DATA}`
  - **Gemini**: `${extensionPath}/.data/`
- Scripts are called via `exec_shell` / `Bash` tool.
- Required environment: Python 3.10+, dependencies in `${PLUGIN_SCRIPTS}/requirements.txt`.
- API keys: `FRED_API_KEY` (macro/credit) and `FINNHUB_API_KEY` (sentiment/insider/earnings) are recommended. All other keys are optional with functional fallbacks.
- Output always goes to `./reports/` relative to the user's workspace.

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
| `fetch_currency_exposure.py` | ADR detection, geographic revenue mix, DXY correlation, FX EPS impact | 4 |
| `calculate_metrics.py` | Ratios, DCF, RIM, DDM, Piotroski F-Score, Beneish, Altman Z, peer comparison, Monte Carlo | 6 |
| `calculate_earnings_quality.py` | Accruals quality, cash conversion, revenue quality, expense signals, persistence | 1 |
| `calculate_candor.py` | Management candor NLP (hedging, certainty, Q&A delta) | 9 |
| `calculate_options.py` | Options signals: IV surface, max pain, put/call ratios, unusual activity | 6 |
| `forecast.py` | ARIMA/ETS ensemble + GARCH volatility + fat-tail Monte Carlo + regime detection | 6 |
| `compute_scores.py` | Deterministic 1-11 component scoring (incl. capital structure, Weinstein, CANSLIM) + conviction | 7 (cross-check) |
| `cross_check.py` | Automated contradiction detection between scoring dimensions (valuation vs moat, red flags, alt data divergence) | 10 (cross-check) |
| `compute_sector_rs.py` | Sector AND sub-industry relative strength rankings vs SPY (supports `--level sub-industry --flat` for GICS Level 4 flat leaderboard) | Screening |
| `compute_factors.py` | Fama-French 5-factor regression + factor attribution (Kenneth French data) | 7 |
| `compute_liquidity.py` | Market microstructure, Amihud illiquidity, position sizing constraints | 6,10 |
| `validate_report.py` | Pre-delivery quality gate enforcement (freshness, coverage, consistency, forensics) | 11 (pre-delivery) |
| `event_study.py` | Cumulative abnormal return (CAR) around corporate events | 10 (post-delivery) |
| `diff_filings.py` | 10-K/10-Q redline detection: risk factor changes, MD&A tone shift, forensic flags | 1,8 |
| `backtest.py` | Validate past reports against actual outcomes | 10 (post-delivery) |
| `persist.py` | SQLite state persistence, checkpointing, resume, kill switch monitor | All |
| `portfolio_context.py` | Portfolio correlation, position sizing, factor exposure, tail risk (VaR/CVaR), drawdown recovery | 10 |
| `fetch_short_interest.py` | Short interest dynamics, squeeze scoring, positioning divergence | 6, 7 |
| `fetch_activist_exposure.py` | Activist 13D tracking, proxy fight probability, insider cluster detection | 6, 7 |
| `calibrate_conviction.py` | Bayesian conviction calibration, historical accuracy, Brier score | 10 (post-delivery) |
| `compute_seasonality.py` | Quarterly seasonality indices, YoY decomposition, seasonal expectation assessment | 6 |
| `compute_correlation_regime.py` | Rolling beta, tail correlation, asymmetric beta, correlation regime, stress-adjusted sizing | 8 |
| `compute_earnings_edge.py` | Historical beat/miss rate, pre/post-earnings drift (PEAD), earnings quality trend | 6 |
| `fetch_sub_industry_universe.py` | GICS Level 4 sub-industry constituent discovery via ETF holdings + market cap filter | Screening |

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
