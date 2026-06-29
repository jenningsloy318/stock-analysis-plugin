# Stock-Analysis Plugin: Data Flow Audit (59 Scripts)

## Executive Summary

Out of 59 scripts, **43 are referenced in the workflow (73%), but only 13 feed the critical compute_scores.py bottleneck** (22%). This creates a two-tier system: **core scoring pipeline** (wired end-to-end) vs. **specialist agents** (produce narrative context, not scored metrics).

- **Wired (✅)**: 13 scripts → compute_scores → reports
- **Partial (⚠️)**: 30 scripts → agent markdown → templates  
- **Orphaned (❌)**: 16 scripts → never invoked

---

## Core Scoring Pipeline (✅ WIRED) — 13 Scripts

These scripts feed **compute_scores.py**, which produces conviction ratings for equity reports:

| Script | Output Keys | Invoked By | compute_scores Arg | Status |
|--------|------------|-----------|-------------------|--------|
| `calculate_metrics.py` | valuation_metrics, efficiency, profitability, fcf, roic | fundamental-analyst (S5) | `--metrics` | ✅ |
| `fetch_macro.py` | growth, inflation, rates, unemployment, spreads | data-collector (S1) | `--macro` | ✅ |
| `fetch_technicals.py` | sma_20/50/200, rsi, macd, bb, adx, volume | quant-analyst (S11) | `--technicals` | ✅ |
| `fetch_sentiment.py` | analyst_consensus, insider_net, earnings_rev | quant-analyst (S11) | `--sentiment` | ✅ |
| `fetch_alternatives.py` | google_trends, job_trends, web_traffic, app_rank | alt-data-analyst (S13) | `--alternatives` | ✅ |
| `fetch_capital_structure.py` | buyback_roi, sbc_dilution, debt_maturity | fundamental-analyst (S6) | `--capital_structure` | ✅ |
| `fetch_supply_chain_ecosystem.py` | upstream_health, downstream_risk, ecosystem_score | supply-chain-analyst (S8) | `--ecosystem` | ✅ |
| `compute_industry_trajectory.py` | revenue_accel, margin_direction, fund_flows, rs_momentum | industry-analyst (S7) | `--trajectory` | ✅ |
| `compute_liquidity.py` | market_cap_proxy, amihud_illiquidity, spread | quant-analyst (S11) | `--liquidity` | ✅ |
| `fetch_short_interest.py` | short_pct, short_ratio, squeeze_score | quant-analyst (S14) | `--short_interest` | ✅ |
| `fetch_activist_exposure.py` | activist_13d_prob, proxy_fight_risk | catalyst-analyst (S14) | `--activist` | ✅ |
| `calculate_options.py` | iv_surface, max_pain, put_call_ratio, unusual | quant-analyst (S11) | `--options` | ✅ |
| `compute_scores.py` | component_scores[1-11], conviction_rating, dimension_breakdown | scorer (S16) | N/A — it's the combiner | ✅ |

**Pattern**: Financial data (S5) → Risk/Macro (S1, S12) → Market signals (S11, S14) → **compute_scores** → conviction rating

---

## Specialist Agents (⚠️ PARTIAL) — 30 Scripts  

Invoked in stages 1-15 but outputs go to **markdown stage summaries**, not compute_scores:

| Script | Stage | Invoked By | Output Destination | Status |
|--------|-------|-----------|-------------------|--------|
| `fetch_financials.py` | S5 | fundamental-analyst | Internal to calculate_metrics | ⚠️ Pre-scored |
| `fetch_global_macro.py` | S1, S9 | data-collector, macro-analyst | Risk narrative | ⚠️ |
| `fetch_credit.py` | S1, S12 | data-collector, risk-analyst | Spreads + risk context | ⚠️ |
| `fetch_behavioral.py` | S12 | risk-analyst | Narrative (bias, reflexivity) | ⚠️ |
| `fetch_cot.py` | S11 | quant-analyst | Institutional positioning | ⚠️ |
| `fetch_realtime.py` | S11 | quant-analyst | Optional fallback | ⚠️ |
| `fetch_economic_surprises.py` | S1 | data-collector | Macro context | ⚠️ |
| `fetch_peer_universe.py` | S7 | industry-analyst | Peer set + valuation context | ⚠️ |
| `fetch_news_nlp.py` | S13 | alt-data-analyst | Sentiment narrative | ⚠️ |
| `fetch_private_comps.py` | S10 | quant-analyst | M&A floor context | ⚠️ |
| `fetch_esg_carbon.py` | S12 | risk-analyst | ESG risk | ⚠️ |
| `fetch_supply_chain.py` | S8 | supply-chain-analyst | Concentration HHI | ⚠️ |
| `fetch_currency_exposure.py` | S9 | macro-analyst | FX risk narrative | ⚠️ |
| `fetch_market_breadth.py` | S1 | data-collector | Market regime context | ⚠️ |
| `fetch_theme_performance.py` | S1 | data-collector | Thematic RS context | ⚠️ |
| `fetch_sub_industry_universe.py` | S2 | sector-screener | Company universe | ⚠️ Screening-only |
| `calculate_earnings_quality.py` | S6 | fundamental-analyst | Accruals quality | ⚠️ |
| `calculate_candor.py` | S13 | alt-data-analyst | Management tone analysis | ⚠️ |
| `compute_sector_rs.py` | S1, S2 | data-collector, sector-screener | Relative strength | ⚠️ Screening-only |
| `compute_tam_adj_peg.py` | S10 | quant-analyst | Growth category scoring | ⚠️ |
| `compute_bayesian_growth.py` | S10 | quant-analyst | CAGR hypothesis | ⚠️ |
| `compute_health_index.py` | S11 | quant-analyst | GF-DMA health score | ⚠️ |
| `compute_correlation_regime.py` | S12 | risk-analyst | Tail risk narrative | ⚠️ |
| `compute_earnings_edge.py` | S14 | catalyst-analyst | Beat/miss probability | ⚠️ |
| `event_study.py` | S14 | catalyst-analyst | CAR analysis narrative | ⚠️ |
| `diff_filings.py` | S6 | fundamental-analyst | 10-K redline narrative | ⚠️ |
| `signal_evolution.py` | S11 | quant-analyst | ISQ signal lifecycle | ⚠️ |
| `hypothesis_registry.py` | S11 | quant-analyst | Hypothesis tracking | ⚠️ |
| `alpha_factor_zoo.py` | S11 | quant-analyst | Factor definitions | ⚠️ |
| `validate_factors.py` | S11 | quant-analyst | Factor safety check | ⚠️ |

**Pattern**: These agents produce summaries → equity-report-writer consumes via stage file reads, NOT via compute_scores

---

## Orphaned Scripts (❌ NEVER INVOKED) — 16 Scripts

| Script | Reason | Reference | Impact |
|--------|--------|-----------|--------|
| `backtest.py` | Post-delivery validation only | CLAUDE.md S19 | None (post-pipeline) |
| `synthesize_primary_research.py` | Documented but not called | CLAUDE.md S13 | Duplicate alt-data-analyst role |
| `portfolio_context.py` | Portfolio-level aggregation | CLAUDE.md S16 | Not per-company flow |
| `forecast.py` | Mentioned in CLAUDE.md but no agent calls it | CLAUDE.md S10 | Price target forecasting skipped |
| `cross_check.py` | Only called directly in tests | CLAUDE.md S16 | Contradiction detection unused |
| `calibrate_conviction.py` | Only in test suite | CLAUDE.md S16 | Bayesian calibration unused |
| `audit_tool_calls.py` | Report post-processing, optional | CLAUDE.md S17 | Fact-check validation skipped |
| `audit_capital_allocation.py` | P0.1 quality gate | CLAUDE.md S5/6 | Capital allocation audit unused |
| `score_ceo_quality.py` | P0.3 quality gate | CLAUDE.md S5 | CEO score computation unused |
| `analyze_earnings_transcript.py` | P0.4 transcript NLP | CLAUDE.md S13 | Earnings call analysis unused |
| `score_bottleneck_asymmetry.py` | Walk-mode only | CLAUDE.md S8 | Supply chain walk feature incomplete |
| `analyze_alpha_elasticity.py` | Serenity-Alpha framework | CLAUDE.md S13 | Thematic elasticity scoring unused |
| `persist.py` | Persistence layer (called directly by workflow runtime) | No agent call | Used but not visible in agent list |
| + 3 more validation/internal utilities | Unclear status | Archives | Dead code candidate |

---

## Data Flow Diagram

```
STAGE 1 (Data Collector)
├─ fetch_financials → calculate_metrics ─┐
├─ fetch_macro ──────────────────────────┤
├─ fetch_technicals ─────────────────────┤
├─ fetch_sentiment ──────────────────────┤
├─ fetch_alternatives ───────────────────┤
├─ fetch_capital_structure ──────────────┤
├─ fetch_supply_chain_ecosystem ─────────┤
├─ compute_industry_trajectory ──────────┤
├─ compute_liquidity ────────────────────┤
├─ fetch_short_interest ─────────────────┤
├─ fetch_activist_exposure ──────────────┤
└─ calculate_options ────────────────────┤
                                         ↓
                              COMPUTE_SCORES (S16)
                                         ↓
                            EQUITY_REPORT_WRITER (S17)
                                         ↓
                              Templates → Output

SPECIALIST AGENTS (Parallel)
├─ Stages 5-15 (Financial, Industry, Risk, Macro, Supply Chain)
│   └─ All output → stage[N].md files
└─ Summaries consumed by report writers as **narrative context**
    (NOT scored, NOT fed to compute_scores)
```

---

## Critical Issues

### 1. **compute_scores Bottleneck**
- 13 inputs required, but compute_scores.py checks for all simultaneously
- If any single input missing → entire scoring fails
- **Recommendation**: Make inputs optional with fallback defaults (e.g., fetch_macro defaults to 0-vector)

### 2. **Two-Tier Output System**
- **Tier 1 (Scored)**: 13 scripts + compute_scores → conviction metrics
- **Tier 2 (Narrative)**: 30 scripts → markdown summaries
- Templates **only** consume Tier 1 outputs
- **Recommendation**: Clarify intent — either move specialist outputs to scoring, or remove from workflow

### 3. **Screening Phase Isolation**
- `fetch_sub_industry_universe.py` + `compute_sector_rs.py` → screening watchlist
- Watchlist **never feeds** deep-dive stages (S5-15)
- Deep-dive analyzes user-selected companies, not screened universe
- **Recommendation**: Add bridge from watchlist to Stage 5 if goal is top-down screening → bottom-up analysis

### 4. **Post-Processing Unused**
- `audit_tool_calls.py` is an optional gate but never systematically invoked
- `cross_check.py` and `calibrate_conviction.py` are documented but test-only
- **Recommendation**: Either integrate into scorer (S16) or mark as future work

---

## Recommendations

### Priority 1: Fix compute_scores Brittleness
```python
# Current: all inputs required
parser.add_argument("--metrics", required=True)  # ← FAILS if missing

# Proposed: optional with fallback
parser.add_argument("--metrics", default=None)  # ← graceful degrade
if args.metrics is None:
    metrics = {"valuation": null, "efficiency": null}  # fallback
```

### Priority 2: Decouple Specialist Outputs from Scoring
- Move 30 specialist scripts to **narrative-only** (output to markdown, consumed by report writers via file reads)
- Move 13 core scripts to **scoring path** (output to JSON, fed to compute_scores)
- No hybrid consumption

### Priority 3: Archive Dead Code
Move to `/scripts/archive/`:
- `backtest.py` (post-delivery only)
- `synthesize_primary_research.py` (duplicate role)
- `portfolio_context.py` (not per-company)
- Optional/test-only: `cross_check.py`, `calibrate_conviction.py`, `audit_tool_calls.py`

### Priority 4: Screening → Deep-Dive Bridge
Add explicit link from screening watchlist (S4) to deep-dive Stage 5:
- Pass top N companies from screening into per-company-orchestrator
- Currently: deep-dive is user-selected only, screening is isolated

---

## Summary Table: Wiring Status by Stage

| Stage | Phase | Scripts | Scored? | Status |
|-------|-------|---------|---------|--------|
| S1 | Data Collection | 10 scripts | 6/10 | ⚠️ Mixed |
| S2-4 | Screening | 2 scripts | 0/2 | ❌ Isolated |
| S5-15 | Deep-Dive | 25 scripts | 6/25 | ⚠️ Mostly narrative |
| S16 | Scoring | 3 scripts | 3/3 | ✅ Wired |
| S17-18 | Reports | 2 scripts | 2/2 | ✅ Wired |
| Post | Validation | 5 scripts | 0/5 | ❌ Unused |

**Verdict**: Core pipeline (S16-18) is solid. Specialist agents (S5-15) produce narrative summaries that feed templates but don't feed scoring. Screening (S2-4) is completely isolated. Post-processing gates are unused.
