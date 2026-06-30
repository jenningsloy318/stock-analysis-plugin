## Plugin versioning rule (MUST follow)
- Version bumps happen ONLY at commit time — one bump per commit, not per modification
- Every commit MUST include a version bump in ALL platform manifests simultaneously:
  - `.claude-plugin/plugin.json`
  - `.claude-plugin/marketplace.json` (the plugin entry version)
  - `.codex-plugin/plugin.json`
  - `plugin.json`
- Version format: `MAJOR.MINOR.PATCH` where MINOR and PATCH are always 2-digit zero-padded (01–99)
  - **Patch bump** (default): bug fixes, small tweaks → e.g., 1.00 → 1.01, 1.09 → 1.10
  - **Minor bump**: new features, new skills, significant changes → e.g., 1.01 → 2.01. When MINOR rolls over, reset PATCH to 01
  - Patch rolls over at 99 → trigger a MINOR bump (e.g., 1.99 → 2.01)
- ALL four manifest versions MUST always match each other

## Report Language Rule (MUST follow)

- ALL reports produced by the `stock-analysis` skill MUST be written in **Chinese (中文)**
- 所有分析报告必须使用中文撰写，不得使用英文撰写报告正文
- This applies to: equity research reports, screening reports, stage summaries, executive summaries, investment theses, and company commentaries
- Technical terms (ticker symbols, financial metric names like P/E, EV/EBITDA, ROIC) may remain in English
- GICS classification names should include both English and Chinese: e.g., "Semiconductors (半导体)"
- Source citations remain in their original language
- When writing report files, begin with Chinese headers (e.g., "# [TICKER] 长期投资分析报告") to ensure Chinese output

## Multi-Horizon Output Rule (MUST follow)

- The `stock-analysis` skill ALWAYS produces **3 reports per run** covering all horizons:
  - Long-term (growth + moat weighted)
  - Mid-term (macro cycle + valuation weighted)
  - Short-term (momentum + flows weighted)
- Do NOT ask the user which horizon — always produce all three automatically
- One shared data-collection pass feeds all 3 report types; reports diverge at scoring/synthesis
- Output filenames: `NNN-[TICKER]_long_[DATE].md`, `NNN-[TICKER]_mid_[DATE].md`, `NNN-[TICKER]_short_[DATE].md` where NNN is the zero-padded rank index (001 = top pick). Directory: `./reports/[RUN_ID]/NNN-[TICKER]/`.

## Stock Price Filter Rule (MUST follow)

- Focus on **growth-stage companies** (成长型公司), NOT mature blue-chips with high stock prices
- **Price filter** (`--top-price`, default 200): US stocks **under $N**, China A-shares **under ¥N**, all other markets **under $N USD equivalent**. Set `--top-price 0` to disable.
- **Growth Headroom filter** (`--min-headroom`, default 5): Score 1-10 computed by `compute_growth_headroom.py`. Stocks with headroom < N are rejected even if they pass the price filter. This eliminates "fully developed" cheap stocks (high TAM penetration, decelerating growth, expensive valuation, distribution phase).
- Both filters apply **ONLY during Stage 4 (Company Screening)** — they determine which companies enter the watchlist
- After screening, do NOT re-filter or exclude companies during analysis stages (5-15) or report generation (17-18)
- If analyzing a specific ticker requested by the user (analyze/compare mode), proceed regardless of filters (user override)
- For screening/watchlist: filter OUT companies above price threshold OR below headroom threshold before ranking

## Price Verification Anti-Hallucination Rule (MUST follow)

- **NEVER estimate stock prices from memory or training data** — prices change daily
- **ALWAYS compute prices from fetched data**: `fetch_financials.py` → `profile.current_price` or `market_cap / shares_outstanding`
- **The team-lead and company-screener MUST NOT suggest candidate stocks with "~$XX" approximate prices** — this is the #1 source of screening failures
- **Stage 4.5 validation is a REAL gate**: the validator must independently read financials.json for each stock and verify price < threshold
- **If the validator cannot find price data for a stock**: that stock is REJECTED (not "assumed to pass")
- **Audit trail required**: stage4.md must contain a "Price Verification Log" table showing: ticker | source | computed_price | threshold | PASS/FAIL

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

## Market Classification Rule (MUST follow)

- **A股 (China A-shares, .SH/.SZ/.BJ tickers)**: Use **板块** (concept/thematic boards) as the primary classification
  - 板块 examples: 半导体, 新能源汽车, 锂电池, AI算力, 军工, 医药创新, 光伏, 机器人, 消费电子
  - Format in tables: `板块` column showing thematic classification, e.g., "半导体/设备", "新能源/锂电", "AI/算力"
  - Use `[主题]/[细分]` two-level format when specificity helps (e.g., "新能源汽车/锂矿" not just "新能源")
  - 趋势板块 in dashboard: show the hottest A-share concept boards (from sector rotation data)
  - GICS codes are OPTIONAL context for A-shares — 板块 is what Chinese investors recognize and trade on

- **美股 (US stocks, no suffix or common US tickers)**: Use **GICS Sector + Industry** as the primary classification
  - GICS is the dominant standard (MSCI + S&P, used by SPDRs, Fidelity, institutional investors)
  - 4 levels: Sector(11) → Industry Group(25) → Industry(74) → Sub-Industry(163)
  - **Display in tables**: Show `Sector` column (11 categories: Technology, Financials, Industrials, etc.) — this is what retail traders recognize (equivalent to Yahoo Finance/Fidelity display)
  - For screening depth: use GICS Level 4 (Sub-Industry) internally but display as readable Industry name (e.g., "Semiconductors" not "45301020")
  - 趋势板块 equivalent for US: show "Sector Leaders" from SPDRs (XLK, XLF, etc.)
  - Do NOT use SIC/NAICS codes (government systems, not used by investors)

- **日韩台 (JP/KR/TW)**: Use GICS Industry names with local market context
  - Add local exchange sector classification as supplementary context if available

- **Mixed portfolio reports**: If report covers both A-shares and US stocks, use BOTH systems:
  - A-share rows show 板块 column
  - US rows show Industry column
  - Or use a unified "分类" column with market-appropriate labels for each row

- **Dashboard "趋势板块" field**:
  - A-share screening: show hottest 概念板块 (concept boards), e.g., "半导体, AI算力, 机器人"
  - US screening: show strongest GICS sectors/industries, e.g., "Technology, Industrials, Financials"
  - Mixed: show both with market prefix, e.g., "🇨🇳 半导体/AI算力 | 🇺🇸 Technology/Semis"

## Analysis Philosophy (MUST follow)

- **Data integrity first**: Never invent financial figures. If data is unavailable, state "Data not available" — never guess.
- **Methodology transparency**: Every conclusion must be traceable to a specific analytical framework (Buffett, Munger, Dalio, Soros, Lynch, Fisher, Marks, Druckenmiller, Greenblatt, Burry, ARK, Mauboussin, Damodaran, Taleb, or Graham).
- **Second-level thinking**: Always ask "what's priced in?" not just "what's happening?"
- **Multi-dimensional analysis**: Cover all critical factors that move stock prices (fundamentals + macro + technicals + alternative data).
- **Dimension transparency (data-driven)**: Every final report MUST decompose the conviction score into ALL individual dimensions with numeric scores AND the raw data behind each score. Never present only the composite — always show the dimension breakdown table with per-dimension rationale, key data points, and sources. Explain WHICH dimensions most influenced the ranking/rating and WHY (with figures). Include dimension discrimination analysis (standard deviation, correlation with rank) to show what truly drove the selection.
- **Progressive disclosure**: Load reference files on-demand per analysis stage. Drop raw data after each stage summary is written.
- **Source attribution**: Every data claim must use `[Source: ... | Retrieved: ... | Fact/Interpretation/Speculation]` format.

## Agent Orchestration (MUST follow)

- The `stock-analysis:stock-analysis` skill uses **Agent tool orchestration** — team-lead spawns specialist agents directly. It does NOT use the Workflow tool. It does NOT invoke `workflows/stock-analysis.js`.
- A separate skill (`stock-analysis:workflow`) exists for Workflow-based execution — its instructions are self-contained in `skills/workflow/SKILL.md` and `agents/team-lead-workflow.md`. CLAUDE.md does not describe that path.
- Modes: pipeline (default: screen → analyze), screen, analyze, compare, walk.
- **No TeamCreate / TeamDelete** — removed in Claude Code v2.1.178. No `team_name` parameter — silently ignored. The session has an implicit team.
- Screening agents: `data-collector`, `sector-screener`, `company-screener`, `scorer`.
- Orchestrator agents: `team-lead` (spawns agents via Agent tool), `company-orchestrator` (per-company stages 5-15 manager).
- Walk-mode agent: `roadmap-walker` (top-down chain decomposition for `--mode walk THEME`).
- Analysis agents (per-company): `fundamental-analyst`, `industry-analyst`, `supply-chain-analyst`, `macro-analyst`, `quant-analyst`, `risk-analyst`, `alt-data-analyst`, `catalyst-analyst`, `china-market-analyst`.
- Validation agent: `report-validator` — independent, runs validate_report.py, signals PASS/FAIL.
- Report agents: `screening-report-writer`, `equity-report-writer`.
- Support agents: `search-agent`, `market-daily-orchestrator`.
- Per-company wave pattern: Wave1[5+7+9+13] → Wave2[6+8+10+14] → Wave3[11+12] → Wave4[15]
- Async pool scheduling: max 4 concurrent company-orchestrators, next spawns as soon as any finishes.
- team-lead writes tracking.json (single-writer pattern), manages stage transitions, relays progress.
- Context eviction: after each stage write summary → drop raw data. Use persist.py if context >80%.
- Stage 1.5, 4.5, 16.5, 17.4, 17.5, 18.5: Independent validation gates (BLOCKING).
- Retry: if agent returns null or throws, retry up to 10 times before marking stage failed.
- A-share (SH/SZ): Stage 15 is MANDATORY (set `is_a_share=true`), SKIP for all others.
- **NEVER pause for user confirmation** between stages. The pipeline runs autonomously. No "Continue?" prompts.
- **NEVER skip stages 5-15** in pipeline mode. All deep-dive stages must run for every selected company. If `total_company` exceeds 40, cap at 40.

## Web Search & Data Acquisition (MUST follow)

### Data Cross-Validation Rule (MANDATORY)

- **ALL stock data (price, PE, PB, market cap, ticker-name mapping) MUST be cross-validated** using `validate_stock_data.py` before being used in reports
- Run validation at two checkpoints: (1) after Stage 4 screening, (2) before Stage 17 report generation
- A-share data sources (priority order): **StockDB local** (free-stockdb, `127.0.0.1:7899`) → **yfinance** → **akshare** → web search
- US stock data sources: **yfinance** (primary) → web search for confirmation
- If a ticker scores INVALID (<50 validation score): **remove from analysis** — do not proceed with bad data
- If a ticker scores SUSPICIOUS (50-69): **flag with ⚠️** in all tables, note the discrepancy
- **StockDB integration** (A-share only): If the local StockDB service (`free-stockdb`) is running at `127.0.0.1:7899`, use it as the fastest and most reliable A-share data source. It provides: daily/weekly/monthly OHLCV, minute data, PE, PB, name, volume, turnover for 7400+ A-share stocks since 2000. Connection is optional — if unavailable, fall back to yfinance/akshare.
- **Never trust single-source data** for critical fields (price, PE, PB, market cap). If only one source available, lower confidence and note in data gap disclosure section.

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
- **ALL Python scripts MUST be run via `uv run python`** — never bare `python` or `python3`. When agents reference `${PLUGIN_ROOT}/scripts/script.py`, execute as: `uv run python ${PLUGIN_ROOT}/scripts/script.py [args]`. This ensures the correct virtual environment and dependencies are used.
- Persistent state (venvs, caches) goes in `${PLUGIN_DATA}`:
  - **Claude/Codex**: `${CLAUDE_PLUGIN_DATA}`
  - **Gemini**: `${extensionPath}/data/`
- Scripts are called via `exec_shell` / `Bash` tool.
- Required environment: Python 3.10+, dependencies in `${PLUGIN_ROOT}/scripts/requirements.txt`.
- API keys: `FRED_API_KEY` (macro/credit) and `FINNHUB_API_KEY` (sentiment/insider/earnings) are recommended. All other keys are optional with functional fallbacks.
- Output always goes to `./reports/[RUN_ID]/` where RUN_ID = YYYYMMDDHHmm in **local time** (e.g., 202605251430), relative to the user's workspace.

### Script Inventory

| Script | Purpose | Stage |
|--------|---------|-------|
| `fetch_financials.py` | Financial data (yfinance → SEC EDGAR → akshare) | 1, 5 |
| `fetch_macro.py` | FRED macro indicators (incl. ISM Services, JOLTS, LEI) + Dalio regime | 1 |
| `fetch_global_macro.py` | Global macro: ECB, PBOC, BOJ, Eurostat, World Bank | 9 |
| `fetch_technicals.py` | Technical indicators (SMA, RSI, MACD, BB, ADX, etc.) | 11 |
| `fetch_sentiment.py` | Finnhub sentiment, insider, earnings, analyst, estimate revisions | 11 |
| `fetch_alternatives.py` | Alt data (Google Trends, Similarweb, App Store, Glassdoor, LinkedIn, Reddit, USPTO) | 13 |
| `fetch_credit.py` | Credit spreads, ratings, debt maturity (FRED + SEC EDGAR) | 12 |
| `fetch_behavioral.py` | Narrative economics, analyst herding, overreaction, anchoring bias, reflexivity | 12 |
| `fetch_cot.py` | CFTC Commitments of Traders — institutional futures positioning | 11 |
| `fetch_realtime.py` | Real-time quotes, options chain, pre/post market | 11 |
| `fetch_economic_surprises.py` | Economic surprise indices (CESI proxies, FRED nowcasts, actual vs consensus) | 1 |
| `fetch_peer_universe.py` | Automated peer identification via GICS + ETF holdings + description match | 7 |
| `fetch_news_nlp.py` | News sentiment, narrative theme tracking, coverage spike detection | 13 |
| `fetch_capital_structure.py` | Buyback ROI, SBC dilution, capital return yield, debt maturity, optimal leverage | 6 |
| `fetch_private_comps.py` | M&A target probability, LBO floor, activist probability, precedent transactions | 10 |
| `fetch_esg_carbon.py` | ESG materiality, carbon pricing scenarios, stranded assets, transition risk | 12 |
| `fetch_supply_chain.py` | Supply chain concentration, geographic HHI, sector chokepoints, resilience score | 3, 8 |
| `fetch_supply_chain_ecosystem.py` | Upstream supplier + downstream customer financial health (rev growth, margins, stock perf, FCF), ecosystem momentum score, propagation risk detection | 4, 8 |
| `compute_industry_trajectory.py` | Industry trajectory: revenue acceleration, margin direction, RS momentum, fund flows, valuation change, capital cycle position — is the industry improving or deteriorating? | 2, 7 |
| `fetch_currency_exposure.py` | ADR detection, geographic revenue mix, DXY correlation, FX EPS impact | 9 |
| `calculate_metrics.py` | Ratios, DCF, RIM, DDM, Piotroski F-Score, Beneish, Altman Z, peer comparison, Monte Carlo | 5, 10 |
| `calculate_earnings_quality.py` | Accruals quality, cash conversion, revenue quality, expense signals, persistence | 6 |
| `calculate_candor.py` | Management candor NLP (hedging, certainty, Q&A delta) | 13 |
| `calculate_options.py` | Options signals: IV surface, max pain, put/call ratios, unusual activity | 11 |
| `forecast.py` | ARIMA/ETS ensemble + GARCH volatility + fat-tail Monte Carlo + regime detection | 10 |
| `compute_scores.py` | Deterministic 1-11 component scoring (incl. capital structure, Weinstein, CANSLIM) + conviction | 16 |
| `cross_check.py` | Automated contradiction detection between scoring dimensions | 16 |
| `compute_sector_rs.py` | Sector AND sub-industry RS vs SPY (supports `--level sub-industry --flat`) | 1 |
| `compute_factors.py` | Fama-French 5-factor regression + factor attribution (Kenneth French data) | 11 |
| `compute_liquidity.py` | Market microstructure, Amihud illiquidity, position sizing constraints | 11 |
| `validate_report.py` | Pre-delivery quality gate enforcement | 17 |
| `event_study.py` | Cumulative abnormal return (CAR) around corporate events | 14 |
| `diff_filings.py` | 10-K/10-Q redline detection: risk factor changes, MD&A tone shift, forensic flags | 6 |
| `backtest.py` | Validate past reports against actual outcomes | post-delivery |
| `persist.py` | SQLite state persistence, checkpointing, resume, kill switch monitor | All |
| `portfolio_context.py` | Portfolio correlation, position sizing, factor exposure, tail risk (VaR/CVaR) | 16 |
| `fetch_short_interest.py` | Short interest dynamics, squeeze scoring, positioning divergence | 11 |
| `fetch_activist_exposure.py` | Activist 13D tracking, proxy fight probability, insider cluster detection | 11 |
| `calibrate_conviction.py` | Bayesian conviction calibration, historical accuracy, Brier score | 16 |
| `compute_seasonality.py` | Quarterly seasonality indices, YoY decomposition, seasonal expectation assessment | 11 |
| `compute_correlation_regime.py` | Rolling beta, tail correlation, asymmetric beta, correlation regime | 12 |
| `compute_earnings_edge.py` | Historical beat/miss rate, pre/post-earnings drift (PEAD) | 14 |
| `fetch_sub_industry_universe.py` | GICS Level 4 sub-industry constituent discovery via ETF holdings + market cap filter | 2, 4 |
| `signal_evolution.py` | ISQ 5-dimension signal tracking with lifecycle states | 11 |
| `hypothesis_registry.py` | Hypothesis lifecycle tracking, Bayesian belief updating, run cards | 11, 16 |
| `alpha_factor_zoo.py` | Factor computation engine with 19 base operators, 4 factor zoos | 11 |
| `validate_factors.py` | AST safety validation for factor expressions, lookahead bias detection | 11 |
| `audit_tool_calls.py` | Post-hoc report grounding verification | 17 |
| `audit_capital_allocation.py` | Capital allocation audit (P0.1): buyback ROI, dividend coverage, M&A track record | 5, 6 |
| `score_ceo_quality.py` | CEO quality score (P0.3): tenure, capital allocation skill, candor, alignment | 5 |
| `synthesize_primary_research.py` | Primary research synthesis (P0.2): per-claim convergence scoring across expert/channel sources | 13 |
| `analyze_earnings_transcript.py` | Earnings transcript NLP (P0.4): tone, guidance shift, miss-classification, Q&A evasion score | 13 |
| `score_bottleneck_asymmetry.py` | Universal bottleneck-investing asymmetry composite (0-100) per chokepoint candidate + geographic strategic scoring | 8, walk |
| `fetch_asia_market_momentum.py` | Asia market (JP/KR/CN/TW) sector momentum, RS vs SPY, cross-market tech leadership, semiconductor momentum | 1, 9 |
| `detect_growth_inflection.py` | Growth inflection detection: revenue acceleration 2nd derivative, segment mix shift, margin regime change, R&D transmission, concentration change | 5, 6 |
| `compute_money_flow.py` | Money flow confirmation: MFI/OBV/CMF aggregation, consecutive inflow streak detection, volume-price symmetry (量价齐升), valuation snapshot (P/B, trailing PE, forward PE) | 4, 11, 16 |
| `compute_trade_signals.py` | Trade signal engine: 6 BUY signals (量价突破/超跌反转/金叉/回踩支撑/蓄势/突破回踩) + 6 SELL signals (跌破支撑/超买反转/死叉/量价背离/资金流出/跌破200日线) + stop-loss/target | 11, 17 |
| `compute_signal_aggregator.py` | 7-layer institutional signal aggregator: L1 Technical + L2 Factor + L3 Event + L4 Flow + L5 Options + L6 Alt Data + L7 Cross-Asset → unified multi-layer verdict with confluence detection | 11, 16, 17 |
| `detect_chart_patterns.py` | O'Neil chart pattern recognition: 前高放量突破/前高回踩/杯柄/大平台突破/前高蓄势/楔形突破 + pattern scoring 0-100 + category classification (突破确认/回踩预警/强势蓄力/无形态) | 4, 11 |
| `classify_uptrend_phase.py` | Uptrend phase classifier: 加速上涨/匀速上涨/波动阶段/底部区域/下跌阶段 + momentum score + trend health + phase change risk | 4, 11 |
| `validate_stock_data.py` | Multi-source cross-validation: yfinance + StockDB + akshare — ticker/price/PE/PB/name consistency checks, discrepancy detection, consensus price | 4, 5 |
| `cross_validate_prices.py` | Lightweight post-fetch price verifier: reads ANY script's JSON output, checks price against 2nd source (StockDB/yfinance fast_info), auto-patches stale data with --patch flag | All |
| `discover_hot_sectors.py` | Real-time hot sector discovery: 1D/5D momentum + volume spike + breadth breakout for US (ETFs) + A-share (akshare概念板块 + ETF proxy), rotation signal | 1, 2 |
| `fetch_market_breadth.py` | Market breadth: % above MAs, A/D, McClellan, VIX term structure, credit spreads | 1 |
| `fetch_theme_performance.py` | Theme/style ETF performance, sector RS, regime summary | 1 |
| `compute_tam_adj_peg.py` | Serenity TAM-Adj-PEG: PEG ÷ (TAM runway × quality). Category: CORE_GROWTH / HIGH_BETA_GROWTH / OPTION_LIKE / TURNAROUND / CYCLICAL | 10 |
| `compute_bayesian_growth.py` | Bayesian 5-hypothesis intrinsic CAGR vs market-implied growth, FOMO score | 10 |
| `compute_health_index.py` | GF-DMA Health Index 0-100: fundamental speed × DMA structure × escape ratio | 11 |
| `compute_growth_headroom.py` | Growth Headroom Score 1-10: TAM runway + growth gap + inflection + phase + valuation + money flow. Filters "fully developed" stocks at Stage 4 | 4 |
| `analyze_alpha_elasticity.py` | Serenity-Alpha 7-dim composite: demand→revenue transmission elasticity (thematic theses only) | 13 |

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

- After each stage: write stage summary to `./reports/[RUN_ID]/stage[N].md`
- Drop raw data from context (SEC filings, full transcripts, raw financials)
- Retain only: key metrics table, stage scores, 3-sentence narrative per sub-section
- Maximum active context at any point: <80% of the context window
