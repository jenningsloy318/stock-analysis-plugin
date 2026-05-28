# Stock Analysis Plugin — Agent Team

## Cross-Platform Support

This plugin provides an agent team that works across both Claude Code and Codex:

| Platform | Agent Location | Format | Delegation |
|----------|---------------|--------|------------|
| **Claude Code** | `agents/*.md` | YAML frontmatter + markdown body | `Agent` tool with `subagent_type` |
| **Codex** | `.codex/agents/*.toml` | TOML with `developer_instructions` | Skill-embedded orchestration |

The `agents/` directory is used by Claude.

## Orchestrators

| Agent | Purpose |
|-------|---------|
| **stock-analysis-orchestrator** | Central coordinator for stock deep-dive analysis. Spawns specialists, manages parallel execution, enforces quality gates. Never performs deep analysis directly. |
| **industry-screening-orchestrator** | Central coordinator for top-down industry screening. Spawns sector-screener and company-screener agents, ranks sectors and companies, produces screening reports with watchlists. Never performs deep screening directly. |

## Specialist Agents

| Agent | Stages/Phases | Purpose |
|-------|---------------|---------|
| **fundamental-analyst** | 1a, 1b, 1c, 2 | Financial health (DuPont), capital allocation history (Buffett retention test, buyback ROI, M&A track record), quality-of-earnings (accruals, cash conversion, revenue recognition), executive profiles, insider activity |
| **industry-analyst** | 3a, 3b | Product analysis, Porter's Five Forces, competitive landscape, TAM/SAM/SOM, supply chain resilience & concentration risk |
| **supply-chain-analyst** | 3b (deep-dive) | Supply chain mapping (tier 1-3), geographic HHI, chokepoint identification, disruption scenario modeling, inventory-to-sales ratios across chain |
| **macro-analyst** | 4, 5 | Economic cycle (Dalio), monetary policy, inflation, geopolitics, regulatory, currency exposure |
| **quant-analyst** | 6, 7 | Multi-method valuation (DCF, comps, SOTP, LBO floor), technicals, sentiment, institutional flow, market regime & positioning (risk-off/speculative), options signals |
| **risk-analyst** | 8, 8b | Risk identification/quantification, scenario analysis, forensic red flags, ODD, kill switch, ESG & sustainability (carbon pricing, physical/transition risk, TCFD alignment) |
| **alt-data-analyst** | 9 | Digital footprint, NLP earnings, transaction data, primary research, channel checks |
| **catalyst-analyst** | 9b | Catalyst calendar (FDA, earnings, product launches, regulatory), event-driven probability assessment, pre/post-event drift analysis, catalyst sequencing & dependency mapping |
| **china-market-analyst** | CN1, CN2 | A-share specific: policy sensitivity (政策敏感性), 国家队资金流向, 北向资金 (northbound flows), 融资融券 (margin trading), 龙虎榜 (top seats), 行业轮动 (sector rotation), 游资追踪 |
| **equity-report-writer** | 11 | Synthesizes stage summaries into final reports with conviction scoring |
| **search-agent** | All | Multi-source financial web search (Firecrawl, Tavily, Tinyfish, XCrawl, Exa) with provenance |
| **sector-screener** | S1, S2 | Sector growth/profitability/valuation analysis, sub-industry deep-dive, Porter's Five Forces, TAM, key player mapping |
| **company-screener** | S3 | Quantitative company filtering, multi-factor composite scoring, ranked watchlist generation with investment theses |
| **screening-report-writer** | S4 | Synthesizes screening phase summaries into final reports with conviction scoring and stock-analysis handoff |

## Parallel Execution Map

### Stock Analysis (deep-dive per ticker)
```
Standard:    [1a+1b+3a] → [1c+2+3b+CN*] → [4+5+8b] → [6+7] → [8] → [9+9b] → Scoring → [11]
Long-term:   [1a+1b+1c+3a] → [2+3b+CN*] → [4+5+8b] → [6+7] → [8] → [9] → [9b] → Scoring → [11]
Mid-term:    [4+5+6] → [1a+7] → [2+8] → [9+9b] → Scoring → [11]
Short-term:  [6+7+9+9b] → Scoring → [11]
Quick:       [1a+6+7+8] → Scoring → [11]

CN* stages (CN1, CN2) are mandatory for A-share tickers (SH/SZ suffix), skipped for US/non-China.
```

### Industry Screening (top-down funnel)
```
Broad:     [S1 batch A + S1 batch B + S1 batch C] → [S2 top sectors A-F] → [S3 batches 1-3] → Report
Single:    [S1] → [S2] → [S3] → Report
Theme:     [S1 themed] → [S2] → [S3] → Report
Short:     [S1 vulnerability scan] → [S2 bear cases] → [S3 short candidates] → Report
PairTrade: [S1 sector RS] → [S2 long/short pairs] → [S3 pair analysis] → Report
```

Max concurrent agents: 4 (increased from 3 to accommodate expanded parallel paths)

## Stage Detail

### Stock Analysis Stages

| Stage | Name | Agent | Key Frameworks | Scripts |
|-------|------|-------|---------------|---------|
| **0** | Setup | orchestrator | — | persist.py init, tracking.json |
| **1a** | Financial Health & DuPont | fundamental-analyst | DuPont 5-factor, Piotroski F-Score, Lynch categories | fetch_financials.py, calculate_metrics.py |
| **1b** | Capital Allocation | fundamental-analyst | Buffett retention test, Mauboussin capital allocation, buyback ROI, M&A track record | fetch_capital_structure.py |
| **1c** | Quality of Earnings | fundamental-analyst | Beneish M-Score, Montier C-Score, accruals quality, cash conversion, revenue recognition | calculate_earnings_quality.py, diff_filings.py |
| **2** | Executive & Board | fundamental-analyst | Fisher's 15 Points (management), insider cluster detection, compensation alignment | fetch_sentiment.py (insider), fetch_activist_exposure.py |
| **3a** | Industry & Competitive | industry-analyst | Porter's Five Forces, Morningstar moat, BCG matrix, TAM/SAM/SOM, ecosystem mapping | fetch_peer_universe.py |
| **3b** | Supply Chain Resilience | supply-chain-analyst | Tier 1-3 mapping, geographic HHI, chokepoint ID, disruption scenario, inventory-to-sales | fetch_supply_chain.py |
| **4** | Macro Economics | macro-analyst | Dalio's Economic Machine, Druckenmiller liquidity, Four-Box Framework | fetch_macro.py, fetch_global_macro.py, fetch_economic_surprises.py |
| **5** | Geopolitics & Regulation | macro-analyst | CRP country risk, sanctions exposure, trade policy dependency | fetch_currency_exposure.py |
| **6** | Valuation | quant-analyst | DCF+Monte Carlo, comps, SOTP, Greenblatt Magic Formula, LBO floor, reverse DCF | calculate_metrics.py, forecast.py, fetch_private_comps.py |
| **7** | Market Regime & Positioning | quant-analyst | Weinstein stage, CANSLIM, Soros reflexivity, factor attribution, options signals | fetch_technicals.py, compute_factors.py, fetch_cot.py, compute_sector_rs.py, calculate_options.py |
| **8** | Risk Assessment | risk-analyst | Marks 2nd-level thinking, Burry forensic, Klarman permanent-vs-temporary, Taleb antifragility | fetch_credit.py, fetch_behavioral.py, compute_correlation_regime.py |
| **8b** | ESG & Sustainability | risk-analyst | TCFD/ISSB alignment, carbon pricing scenarios, physical/transition risk, SASB materiality | fetch_esg_carbon.py |
| **9** | Alt Data & Digital | alt-data-analyst | ARK disruption, Shiller narrative economics, Fisher scuttlebutt, channel checks | fetch_alternatives.py, fetch_behavioral.py, calculate_candor.py, fetch_news_nlp.py |
| **9b** | Catalyst Intelligence | catalyst-analyst | Event-driven probability, pre/post-event drift, catalyst sequencing, dependency mapping | compute_earnings_edge.py, event_study.py |
| **CN1** | China Policy & Regulatory | china-market-analyst | 政策敏感性矩阵, 产业政策周期, 监管风险评分, 中央经济工作会议解读 | (new scripts) |
| **CN2** | China Capital Flows | china-market-analyst | 北向资金, 融资融券, 龙虎榜, 行业轮动, 游资追踪 | (new scripts) |
| **10** | Scoring & Cross-Check | orchestrator | Bayesian calibration, divergence resolution, Lollapalooza detection | compute_scores.py, cross_check.py, calibrate_conviction.py |
| **11** | Report Generation | equity-report-writer | Narrative structure, conviction scoring, scenario trees | validate_report.py |

### Industry Screening Phases

| Phase | Name | Agent | Purpose |
|-------|------|-------|---------|
| **0** | Setup | orchestrator | Macro fetch, RS compute, source coverage plan |
| **1** | Full Level 4 Screening | sector-screener | Score ALL 163 GICS Level 4 sub-industries on 11 dimensions |
| **2** | Top 30 Deep Dive | sector-screener | Porter, TAM, catalysts, barriers, supply chain per sub-industry |
| **3** | Company Screening | company-screener | Filter → Score → Rank 100 companies across 30 sub-industries |
| **4** | Reports | screening-report-writer | 3 horizon reports, 30 sub-industries, 100 companies |

### Screening Modes

| Mode | Phase 1 Scope | Phase 2 Focus | Phase 3 Target |
|------|-------------|---------------|----------------|
| **Broad** | All 163 sub-industries | Top 30 by composite | 100 long candidates |
| **Thematic** | Theme-relevant sub-industries (e.g., AI, green energy) | All theme-relevant | 50 theme-aligned candidates |
| **Short-Candidate** | Vulnerability scan (high leverage, declining RS, peak margins) | Top 20 most vulnerable | 50 short candidates |
| **Pair-Trade** | Sector RS leaderboard | Top 5 sectors with widest dispersion | Long/short pairs within sector |
| **QARP** | Greenblatt Magic Formula screen across all 163 | Top 30 by combined rank | 50 quality-at-reasonable-price |

## Platform-Specific Notes

### Claude Code

The orchestrator (`stock-analysis-orchestrator` or `industry-screening-orchestrator`) uses the `Agent` tool to spawn sub-agents with `subagent_type` matching the agent names. Agents can nest (sub-agents may call search-agent).

### Codex

Agent definitions in `.codex/agents/` use TOML format with `developer_instructions`. Orchestration is skill-embedded — the SKILL.md contains the coordination logic. Codex plugins do not have native agent team spawning; the agent files serve as configuration reference.
