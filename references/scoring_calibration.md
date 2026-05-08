# Scoring Calibration & Interpretation Guide

## Score-to-Outcome Mapping

This reference defines what each conviction score should mean in terms of expected forward returns. Use it to calibrate analyst judgments and avoid grade inflation.

### Expected 12-Month Return Ranges by Rating

| Score | Rating | Expected Return Range | Win Rate Target | Notes |
|-------|--------|----------------------|-----------------|-------|
| 9.0-10.0 | Strong Buy | +25% to +50%+ | >70% | Multiple framework convergence required |
| 7.5-8.9 | Buy | +15% to +30% | >60% | At least 3 frameworks supportive |
| 6.0-7.4 | Hold / Accumulate | +5% to +15% | >55% | Market-perform or slight outperformance |
| 4.0-5.9 | Hold / Reduce | -5% to +5% | N/A | Market-perform; no edge |
| 2.0-3.9 | Sell | -10% to -25% | >60% (decline) | Active deterioration expected |
| 1.0-1.9 | Strong Sell | -25% to -50%+ | >65% (decline) | Structural impairment |

### Position Sizing by Conviction

| Conviction | Max Position (% AUM) | Kelly Fraction Estimate |
|------------|---------------------|------------------------|
| 9.0+ | 8-12% | Full Kelly |
| 7.5-8.9 | 5-8% | Half Kelly |
| 6.0-7.4 | 3-5% | Quarter Kelly |
| < 6.0 | 0% (no new position) | Zero |

## Confidence Level Definitions

| Confidence | Quantitative Meaning | Source Coverage | Score Uncertainty |
|------------|---------------------|-----------------|-------------------|
| High | 80%+ probability that true value is within ±1.0 of stated score | All blocking dimensions pass, 0-1 stale non-critical | ±0.5 points |
| Medium | 65-80% probability | One non-central dimension missing/stale | ±1.5 points |
| Low | 50-65% probability | Two+ dimensions missing or stale | ±2.5 points |

### Confidence Impact on Position Sizing
- High confidence → use full conviction-based sizing
- Medium confidence → reduce position by 40%
- Low confidence → reduce position by 70% (or skip entirely)

## Component Score Calibration

### What a "7" Means for Each Component

| Component | Score = 7 Benchmark |
|-----------|---------------------|
| Financial Health | Top-quartile margins for sector, 10-15% ROE, D/E < 1.5x, positive FCF growth |
| Moat Quality | Clear competitive advantage, stable/gaining share, 5yr ROIC > WACC |
| Management Quality | 3+ consecutive earnings beats, net insider buying, competent capital allocation |
| Valuation | 10-20% below DCF fair value, PEG 1.0-1.3, FCF yield > 4% |
| Capital Structure | Buybacks creating value (above-market ROI), SBC < 5% revenue, near-optimal leverage |
| Macro Tailwind | Goldilocks or reflation regime, no yield curve inversion, PMI > 52 |
| Risk Profile | Altman Z safe, Beneish clean, manageable leverage, stable earnings |
| Alternative Alignment | 3+ alt signals confirming (web traffic rising, social positive, patents growing) |
| Technical Setup | Stage 2 advancing OR above rising 200-day MA with positive RSI |
| Weinstein Alignment | Stage 2 with 30WMA slope positive, RS composite > 1.0 |
| CANSLIM | 5+/7 factors passing, EPS growth > 25%, near 52-week high, above-avg volume |

### Score Inflation Warnings

Avoid these common biases that inflate scores:
1. **Halo effect**: One exceptional metric lifting all scores (e.g., amazing growth → inflated moat score)
2. **Recency bias**: Weighting last quarter too heavily vs 5-year trend
3. **Narrative capture**: High score because the story is compelling, not the data
4. **Anchoring to prior rating**: Reluctance to downgrade from a prior Buy rating
5. **Denominator neglect**: Ignoring small sample sizes in alt data

## Override Rules (Mandatory)

| Condition | Override | Rationale |
|-----------|----------|-----------|
| Any component ≤ 3.0 | Max rating = Hold (5.9) | Single catastrophic weakness dominates |
| 3+ red flags (Beneish + Altman + poor OCF) | Max rating = Sell (3.9) | Forensic evidence of distress |
| Weinstein Stage 4 | Max rating for short-term = Sell | Never buy into a declining trend |
| 3+ components missing | Confidence = Low | Insufficient data to have conviction |
| Lollapalooza (3+ components ≥ 7.5) | +1.5 bonus | Multiple force convergence (Munger) |
| Carbon breakeven < current carbon price trajectory | Flag as stranded asset risk | For energy/materials only |

## Historical Calibration Benchmarks

Use these as sanity checks for output scores:

| Market Condition | Expected Score Distribution |
|-----------------|----------------------------|
| Bull market (SPY up >15% YTD) | Median score 6.5-7.0; more Buys than Sells |
| Bear market (SPY down >15% YTD) | Median score 4.5-5.5; more opportunities but higher risk |
| Neutral market (SPY ±5% YTD) | Median score 5.5-6.5; selective opportunities |

### Score Stability Expectations
- Long-term scores should change by ≤ 0.5 points per quarter (unless material event)
- Mid-term scores may shift 1-2 points per quarter (macro-sensitive)
- Short-term scores can shift 2-3 points per week (sentiment/technical-driven)

## Backtest Validation Protocol

When running `scripts/backtest.py`, verify:
1. Strong Buys (9+) outperformed index by >15% over 12 months in >65% of cases
2. Sells (2-3.9) underperformed index by >10% over 12 months in >60% of cases
3. Kill switches triggered before >20% adverse move in >50% of cases
4. Confidence level correlated with accuracy (High > Medium > Low)

If backtest shows systematic over/under-performance vs expectations, recalibrate thresholds.
