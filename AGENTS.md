# Stock Analysis Plugin — Agent Team

## Cross-Platform Support

This plugin provides an agent team that works across both Claude Code and Codex:

| Platform | Agent Location | Format | Delegation |
|----------|---------------|--------|------------|
| **Claude Code** | `agents/*.md` | YAML frontmatter + markdown body | `Agent` tool with `subagent_type` |
| **Codex** | `.codex/agents/*.toml` | TOML with `developer_instructions` | Skill-embedded orchestration |

The `agents/` directory is used by Claude.

## Orchestrator

**stock-analysis-orchestrator** — Unified pipeline coordinator. Handles all modes:
- **Pipeline** (default): screen → pick top M companies → deep-dive each → reports
- **Screen**: sub-industry screening + company watchlist, no deep-dive
- **Analyze**: deep-dive specific tickers, no screening
- **Compare**: multi-ticker side-by-side comparison

Never performs analysis directly — always delegates to specialist agents.

## Specialist Agents

| Agent | Stages | Purpose |
|-------|--------|---------|
| **sector-screener** | 1, 2A | Sub-industry scoring (11 dimensions), deep-dive (Porter, TAM, catalysts) |
| **company-screener** | 2B | Company filtering, scoring, ranking across sub-industries |
| **screening-report-writer** | 5 | Screening overview reports (3 horizons) |
| **fundamental-analyst** | 3a, 3b | Financial health (DuPont), capital allocation, earnings quality |
| **industry-analyst** | 3c | Competitive landscape, Porter's Five Forces, TAM/SAM/SOM, moat |
| **supply-chain-analyst** | 3c | Supply chain mapping (tier 1-3), geographic HHI, disruption scenarios |
| **macro-analyst** | 3d | Economic cycle (Dalio), monetary policy, geopolitics, regulatory |
| **quant-analyst** | 3e | Multi-method valuation, technicals, sentiment, market regime, options |
| **risk-analyst** | 3f | Risk identification, scenario analysis, forensic, kill switch, ESG |
| **alt-data-analyst** | 3f | Digital footprint, NLP earnings, channel checks |
| **catalyst-analyst** | 3f | Catalyst calendar, event probability, PEAD |
| **china-market-analyst** | 3g | A-share: 政策敏感性, 北向资金, 融资融券, 龙虎榜 |
| **equity-report-writer** | 5 | Per-company deep-dive reports (3 horizons) |
| **search-agent** | All | Multi-source financial web search, script execution |
| **market-daily-orchestrator** | daily | Daily market macro report (spawned by macro trigger) |

## Stage Flow

### Pipeline Mode (default: --top-n 5 --total-m 10)
```
Stage 0: Setup & Shared Data
  └── Macro, RS, breadth, themes — fetched ONCE

Stage 1: Sub-Industry Screening
  └── Score all 163 → select top N (default 5)

Stage 2: Deep-Dive + Company Screening
  ├── Deep-dive top N sub-industries (Porter, TAM, catalysts)
  └── Screen companies → select top M across ALL sub-industries (default 10)

Stage 3: Analysis Branches (PARALLEL, max 4)
  For each of M companies:
  ├── 3a: Financial Health (fundamental-analyst)
  ├── 3b: Capital Allocation & Earnings Quality (fundamental-analyst)
  ├── 3c: Industry & Supply Chain (industry-analyst, supply-chain-analyst)
  ├── 3d: Macro & Geopolitics (macro-analyst)
  ├── 3e: Valuation & Market Regime (quant-analyst)
  ├── 3f: Risk & Alt-Data (risk-analyst, alt-data-analyst, catalyst-analyst)
  └── 3g: A-Share (china-market-analyst, .SH/.SZ only)

Stage 4: Scoring & Cross-Check
  └── compute_scores.py, cross_check.py, calibrate_conviction.py

Stage 5: Report Generation
  ├── Screening overview (3 horizons)
  └── Per-company deep-dives (M × 3 reports)
```

### Screen Mode (--top-n 30)
```
Stage 0 → Stage 1 → Stage 2 → Stage 5 (screening reports only)
```

### Analyze Mode (specific tickers)
```
Stage 0 → Stage 3 (branches) → Stage 4 → Stage 5
```

### Compare Mode (2-5 tickers)
```
Stage 0 → Stage 3 (branches) → Stage 4 (merge+rank) → Stage 5
```

### Branch Internal Parallelism
Within each analysis branch, sub-stages run in this order:
```
[3a + 3c] parallel → [3b + 3d] parallel → [3e] → [3f + 3g*]
```

Max concurrent agents: 4

## Stage Detail

| Stage | Name | Agent | Key Frameworks | Scripts |
|-------|------|-------|---------------|---------|
| **0** | Setup & Shared Data | orchestrator, search-agent | — | fetch_macro.py, fetch_economic_surprises.py, compute_sector_rs.py, fetch_market_breadth.py, fetch_theme_performance.py, persist.py |
| **1** | Sub-Industry Screening | sector-screener | 11-dimension composite scoring | compute_sector_rs.py |
| **2A** | Sub-Industry Deep Dive | sector-screener | Porter, TAM, catalysts, barriers | fetch_supply_chain.py, fetch_peer_universe.py |
| **2B** | Company Screening | company-screener | Multi-factor composite scoring | fetch_financials.py, calculate_metrics.py |
| **3a** | Financial Health | fundamental-analyst | DuPont 5-factor, Piotroski, Lynch | fetch_financials.py, calculate_metrics.py |
| **3b** | Capital Allocation & Earnings Quality | fundamental-analyst | Buffett retention, Mauboussin, Beneish, Montier | fetch_capital_structure.py, calculate_earnings_quality.py, diff_filings.py |
| **3c** | Industry & Supply Chain | industry-analyst, supply-chain-analyst | Porter's Five Forces, TAM/SAM/SOM, moat, HHI | fetch_peer_universe.py, fetch_supply_chain.py |
| **3d** | Macro & Geopolitics | macro-analyst | Dalio, Druckenmiller, Four-Box, CRP | fetch_global_macro.py, fetch_currency_exposure.py |
| **3e** | Valuation & Market Regime | quant-analyst | DCF+MC, comps, SOTP, Weinstein, CANSLIM, factors | calculate_metrics.py, forecast.py, fetch_private_comps.py, fetch_technicals.py, compute_factors.py, fetch_cot.py, calculate_options.py, fetch_sentiment.py, fetch_short_interest.py, fetch_activist_exposure.py, compute_liquidity.py, compute_seasonality.py, compute_earnings_edge.py |
| **3f** | Risk & Alt-Data | risk-analyst, alt-data-analyst, catalyst-analyst | Marks, Burry, Klarman, TCFD, NLP, PEAD | fetch_credit.py, fetch_behavioral.py, compute_correlation_regime.py, fetch_esg_carbon.py, fetch_alternatives.py, fetch_news_nlp.py, calculate_candor.py, event_study.py |
| **3g** | A-Share Specific | china-market-analyst | 政策敏感性, 北向资金, 融资融券 | (A-share only) |
| **4** | Scoring & Cross-Check | orchestrator | Bayesian calibration, divergence resolution | compute_scores.py, cross_check.py, calibrate_conviction.py |
| **5** | Report Generation | screening-report-writer, equity-report-writer | Narrative structure, conviction scoring | validate_report.py |

## Platform-Specific Notes

### Claude Code
The orchestrator uses the `Agent` tool to spawn sub-agents with `subagent_type` matching the agent names. Agents can nest (sub-agents may call search-agent).

### Codex
Agent definitions in `.codex/agents/` use TOML format with `developer_instructions`. Orchestration is skill-embedded — the SKILL.md contains the coordination logic.
