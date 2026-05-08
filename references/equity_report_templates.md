# Report Templates & Scoring Formulas

## Conviction Scoring Formulas

### Long-term Report Conviction
```
Conviction = (Financial_Health × 0.15) + (Moat_Quality × 0.20) + (Management_Quality × 0.15) +
             (Valuation_Attractiveness × 0.20) + (Capital_Structure × 0.10) +
             (Macro_Tailwind × 0.05) + (Risk_Profile × 0.10) + (Weinstein_Alignment × 0.05)
```

### Mid-term Report Conviction
```
Conviction = (Financial_Health × 0.10) + (Moat_Quality × 0.10) + (Management_Quality × 0.10) +
             (Valuation_Attractiveness × 0.20) + (Macro_Tailwind × 0.20) +
             (Risk_Profile × 0.10) + (Weinstein_Alignment × 0.10) + (CANSLIM × 0.10)
```

### Short-term Report Conviction
```
Conviction = (Valuation_Attractiveness × 0.10) + (Macro_Tailwind × 0.10) +
             (Risk_Profile × 0.10) + (Alternative_Alignment × 0.25) +
             (Technical_Setup × 0.20) + (Weinstein_Alignment × 0.15) + (CANSLIM × 0.10)
```

## Component Scoring (1-10 Scale)

| Component | 1-3 (Bearish) | 4-6 (Neutral) | 7-10 (Bullish) |
|-----------|--------------|---------------|----------------|
| Financial Health | Declining margins, FCF negative, leverage >5x | Stable margins, FCF covers capex, leverage 2-4x | Expanding margins, FCF >> capex, leverage <2x |
| Moat Quality | Narrowing moat, share loss, pricing pressure | Stable moat, flat share, pricing intact | Widening moat, gaining share, pricing power |
| Management Quality | Poor allocation, insider selling, guidance misses | Average allocation, neutral insider, mixed guidance | Excellent allocation, insider buying, beats |
| Valuation Attractiveness | >30% above intrinsic, 5yr high multiples | ±15% of intrinsic, near historical avg | >30% below intrinsic, 5yr low multiples |
| Capital Structure | Value-destructive buybacks, SBC >10%, suboptimal leverage | Neutral buybacks, moderate SBC, average capital returns | Buybacks at discount, low SBC, total return >4% |
| Macro Tailwind | 3+ headwinds | 1-2 headwinds, offset | 3+ tailwinds |
| Risk Profile | 3+ red flags, litigation, Altman Z <1.81 | Manageable risks, mitigants present | Clean, low litigation, strong balance sheet |
| Alternative Alignment | Digital diverging negative from reported | Mixed, no clear divergence | Digital confirming/exceeding reported |
| Technical Setup | Broken trend, distribution, below support | Mixed, range-bound | Strong trend, accumulation, above support |
| Weinstein Alignment | Stage 4 (Declining), RS < 0.9 | Stage 1/3 (Basing/Topping) | Stage 2 (Advancing), RS > 1.1 |
| CANSLIM | <3/7 factors passing, EPS declining | 3-4/7 factors, mixed signals | 5+/7 factors passing, strong EPS + RS |

## Rating Anchors

| Score | Rating | Description |
|-------|--------|-------------|
| 9.0-10.0 | Strong Buy | Exceptional alignment. 5+ frameworks supportive. Margin of safety >30%. |
| 7.5-8.9 | Buy | Strong alignment. 3-4 frameworks supportive. Margin of safety 15-30%. |
| 6.0-7.4 | Hold / Accumulate | Mixed. Positive thesis but near-term headwinds or valuation uncompelling. |
| 4.0-5.9 | Hold / Reduce | Weakening. 1-2 dimensions deteriorating. Monitor for downgrade. |
| 2.0-3.9 | Sell | Multiple negatives. Thesis broken in 2+ frameworks. |
| 1.0-1.9 | Strong Sell | Invalidated. Forensic red flags or structural decline. |

**Override rule**: If any single component scores ≤3, the rating cannot exceed "Hold."

## Data Coverage Confidence

Load `references/data_source_matrix.md` before report writing. Confidence is not just analyst certainty; it is capped by source coverage:

| Coverage Result | Maximum Confidence |
|-----------------|--------------------|
| All blocking Tier 0/Tier 1 dimensions pass freshness and source quorum | High |
| One non-central blocking dimension unavailable or stale | Medium |
| Any central blocking dimension unavailable or two or more blocking dimensions stale | Low |
| Thesis support relies mainly on Tier 3 alternative data | Low |
| Numeric claim fails fact check | Remove claim; rerun affected stage if material |

Every report must include a Data Quality & Coverage appendix with source freshness, missing/stale dimensions, source conflicts, and confidence impact.

## Framework Conflict Resolution (Rules 1-4)

When frameworks produce contradictory conclusions:

**Rule 1 — Report-Type Priority**: Highest-weight frameworks for the active report type take precedence.
**Rule 2 — Quantitative Override**: Beneish M-Score > -1.78 or Altman Z < 1.81 overrides all qualitative assessments. No Buy rating with active red flags.
**Rule 3 — Consensus Distance**: When rules 1-2 don't resolve, explicitly quantify the disagreement and synthesize an intermediate recommendation.
**Rule 4 — Second-Level Tiebreaker**: Apply Marks: "What does consensus think, and how does my view differ?" Default to consensus-aligned if no variant perception.

## Report Templates

### Long-term Report (1-3+ years)

**Methodology Weights**: Buffett/Munger (35%), Fisher (25%), Marks (20%), Dalio (20%)

```
# [COMPANY NAME] ([TICKER]) — Long-term Investment Analysis

**Header**
- Company Name | Ticker | Exchange
- Current Price | 52-week Range | Market Cap | Enterprise Value
- Report Date | Analyst: AI Stock Research Skill (stock-analysis)
- Report Type: Long-term (1-3+ years)

---

## Executive Summary
[1 paragraph, max 150 words]

**Conviction Rating: [X.X]/10 | Confidence: [Low/Medium/High]**
[Rationale in 1 sentence]

**Management Candor Index: [Score]/100 ([Verdict])**
[Lollapalooza Alert: (Only if synergistic advantages detected)]

---

## Investment Thesis
- [Bullet 1 — max 2 sentences]
- [Bullet 2 — max 2 sentences]
- [Bullet 3 — max 2 sentences]
- [Bullet 4 — max 2 sentences]
- [Bullet 5 — max 2 sentences]

**Rating: [Strong Buy / Buy / Hold / Sell / Strong Sell]**
- Target Price: $X ([X]% upside/downside)
- Time Horizon: 1-3+ years
- Key Catalyst: [single most important trigger]

---

## 1. Moat Assessment
[Detailed moat analysis using Morningstar framework. Evidence required per moat source. Trajectory statement: widening / stable / narrowing.]

## 2. Management Quality Score
[Score: X/10. Capital allocation track record. Insider ownership. Compensation structure. Fisher's 15 points assessment.]

## 3. Intrinsic Value Estimate
[Embed Mermaid charts (e.g., Revenue vs FCF trend) here if provided by the metrics data]
[Include Economic Value Added (EVA) calculation and ROIC vs WACC spread to assess moat expansion/destruction]
[Multiple methods: DCF (base case), Trading Comps, SOTP if applicable. Sensitivity table: WACC vs terminal growth. Reverse DCF implied growth. Margin of safety calculation.]
[Private market comp / LBO floor (if market cap < $100B): maximum PE buyout price at 20% IRR. Precedent transaction premiums in sector.]

## 4. Capital Structure & Shareholder Returns
[Buyback ROI: avg buyback price vs current price (value created/destroyed per dollar). SBC dilution rate (net share count trajectory). Total capital return yield: (Dividends + Net Buybacks) / Market Cap. Debt maturity assessment. Optimal leverage vs sector peers.]

## 5. Narrative & Growth Runway
[Damodaran Narrative+Numbers: 3-sentence company future narrative. Each sentence → model variable mapping (growth, margin, reinvestment, risk). Narrative plausibility score. TAM/SAM/SOM. Secular trends. Industry life cycle. Multi-year compounding potential.]

## 6. Key Long-term Risks
[Top 3-5 risks to permanent capital loss (Klarman: permanent vs temporary impairment distinction). Mitigants for each. ESG/carbon pricing risk for carbon-intensive sectors. M&A/activist probability flag (if score >60/100).]

## 7. Factor Attribution & Liquidity
[Fama-French 5-factor loadings (market, SMB, HML, RMW, CMA). Alpha after factor decomposition. Liquidity score and position sizing constraint. Days to liquidate at 10% participation. Market impact estimate for target position size. Short interest dynamics: SI% float, days to cover, squeeze score. Activist exposure: 13D presence, proxy fight probability, insider confidence ratio.]

## 7b. Tail Risk & Portfolio Context (if portfolio specified)
[VaR/CVaR at 95% and 99% confidence. Max drawdown and drawdown duration. Calmar ratio. Correlation regime (normal/elevated/crisis). Drawdown recovery history (mean/median recovery days). Current drawdown status.]

## 8. Recommendation
- **Rating**: [Buy/Hold/Avoid]
- **Target Price**: $X (X% upside) | Confidence interval: 60% probability $X-$Y
- **Margin of Safety**: X%
- **LBO Floor**: $X (PE takeout support, if applicable)
- **Hard Catalyst**: [specific, time-bound event — Klarman requirement]
- **Entry Criteria**: [price level or condition]
- **Weinstein Stage**: [1/2/3/4] — Only buy in Stage 2
- **Position Size**: X% of portfolio (Druckenmiller & Quarter-Kelly adjusted)
- **Monitoring Triggers**: [what to watch]

## Appendix: Data Quality & Coverage
- Blocking sources checked: [Tier 0/Tier 1 list]
- Missing/stale dimensions: [None / list with impact]
- Source conflicts: [None / list]
- Confidence cap applied: [None / Medium / Low]
```

### Mid-term Report (1-12 months)

**Methodology Weights**: Lynch (25%), Druckenmiller (20%), Greenblatt (15%), Marks (20%), Weinstein/CANSLIM (20%)

```
# [COMPANY NAME] ([TICKER]) — Mid-term Investment Analysis

**Header**
- Company Name | Ticker | Exchange
- Current Price | 52-week Range | Market Cap | Enterprise Value
- Report Date | Analyst: AI Stock Research Skill (stock-analysis)
- Report Type: Mid-term (1-12 months)

---

## Executive Summary
[1 paragraph, max 150 words]

**Conviction Rating: [X.X]/10 | Confidence: [Low/Medium/High]**

---

## 1. Category & Thesis
**Lynch Category**: [Slow Grower / Stalwart / Fast Grower / Cyclical / Turnaround / Asset Play]
[Why this category? Why now? PEG ratio context. 1-paragraph thesis.]

## 2. Catalyst Map
| Catalyst | Date (est.) | Direction | Magnitude | Probability |
|----------|-------------|-----------|-----------|-------------|
| [Event] | [Q/Month] | Positive | High/Med/Low | X% |
| ... | ... | ... | ... | ... |

## 3. Earnings Estimate vs. Consensus
- Our Estimate: Revenue $X, EPS $X
- Consensus: Revenue $X, EPS $X
- Variant View: [where and why we differ]

## 4. Relative Valuation
[P/E (trailing/forward/NTM) vs 5yr avg and peers. EV/EBITDA vs peers with growth justification. P/FCF yield vs risk-free rate. PEG ratio. Private market comp: LBO floor price (if market cap < $100B). Precedent transaction premium range.]

## 5. Technical Structure & Timing
**Weinstein Stage**: [1/2/3/4] — [Evidence: 30-week MA direction, volume pattern, RS rank]
**CANSLIM Score**: [X/7 pass] — C:[P/F] A:[P/F] N:[P/F] S:[P/F] L:[P/F] I:[P/F] M:[P/F]
[Stage 2 breakout confirmed? Volume confirmation? Relative strength rank position.]

## 6. Macro Tailwinds/Headwinds
[Tailwinds: 1-3 factors. Headwinds: 1-3 factors. Net assessment.]

## 7. Position Sizing & Recommendation
- **Rating**: [Buy / Hold / Sell]
- **Target Price**: $X (X% upside, 12-month) | Confidence interval: 60% probability $X-$Y
- **Hard Catalyst**: [specific, time-bound — Klarman requirement for Buy ratings]
- **Position Size**: X% of portfolio (Druckenmiller: conviction-adjusted)
- **Weinstein Stage Gate**: [Stage 2 confirmed? If Stage 3/4, do not initiate long]
- **Entry**: [price or condition]
- **Stop Loss**: $X (-X%)
- **Monitoring Triggers**: [1-3 specific conditions]

## Appendix: Data Quality & Coverage
- Blocking sources checked: [Tier 0/Tier 1 list]
- Missing/stale dimensions: [None / list with impact]
- Source conflicts: [None / list]
- Confidence cap applied: [None / Medium / Low]
```

### Short-term Report (days to weeks)

**Methodology Weights**: Quantitative/Technical (35%), Soros (25%), Alternative Data (25%), Druckenmiller (15%)

```
# [COMPANY NAME] ([TICKER]) — Short-term Trading Setup

**Header**
- Current Price | 52-week Range | Market Cap
- Report Date | Analyst: AI Stock Research Skill (stock-analysis)
- Report Type: Short-term (days to weeks)

---

## Setup Summary
[1 paragraph: why now, what's the trade? What is priced in vs what is likely?]

**Conviction Rating: [X.X]/10 | Confidence: [Low/Medium/High]**

---

## 1. Technical Analysis
- **Weinstein Stage**: [1/2/3/4] — [30-week MA direction, volume confirmation]
- **Trend**: [primary trend direction, moving averages, higher highs/lows]
- **Key Levels**: Support $X, Resistance $X
- **Momentum**: RSI [X], MACD [bullish/bearish cross]
- **Volume**: [accumulation / distribution, OBV trend]
- **CANSLIM M-factor**: [Market direction confirmed uptrend? Follow-through day?]

## 2. Flow & Sentiment Signals
- Put/Call ratio: [value] — [contrarian interpretation]
- Short interest: X% of float, X days to cover — Squeeze score: X/10 ([Low/Moderate/High/Extreme])
- Positioning divergence: [convergent/divergent] — momentum [direction] vs short interest [direction]
- Options flow: [unusual activity callout]
- Institutional flow: [dark pool, 13F timing]
- Activist exposure: [None / Fund name (X% ownership)] — Proxy fight probability: [Low/Moderate/High]
- AAII sentiment: [% bullish — contrarian at extremes >50% or <25%]

## 3. Alternative Data Readings
[Digital signals: web traffic, app engagement, social sentiment. Composite score. Real-time divergences.]

## 4. Trade Setup
- **Entry Price**: $X
- **Stop Loss**: $X (-X%)
- **Target**: $X (+X%)
- **Risk/Reward Ratio**: X:1
- **Position Size**: X% of portfolio

## 5. Kill Switch
**Exit immediately if**: [specific, observable condition]
**Current monitoring status**: [NOT present / approaching trigger level]

## Appendix: Data Quality & Coverage
- Quote/options/technicals freshness: [timestamp]
- Missing/stale dimensions: [None / list with impact]
- Source conflicts: [None / list]
- Confidence cap applied: [None / Medium / Low]
```

## Scenario Analysis Template (All Reports)

| Scenario | Probability | Key Assumptions | Implied Price |
|----------|------------|-----------------|---------------|
| Bull | X% | [Best realistic outcome: revenue, margin, multiple] | $X |
| Base | X% | [Most likely outcome] | $X |
| Bear | X% | [Worst realistic outcome] | $X |

**Risk/Reward Ratio**: X:1

### Scenario Probability Derivation (Regime-Adjusted)

Do NOT assign fixed probabilities. Derive them from the macro regime identified in Stage 4:

**Step 1**: Identify 3-5 key driver variables (revenue growth rate, operating margin, terminal multiple, etc.)
**Step 2**: Set driver ranges — Base = consensus midpoint; Bull/Bear = ±1 standard deviation on 2+ drivers
**Step 3**: Run DCF for each scenario's driver combination
**Step 4**: Apply regime-adjusted probabilities:

| Macro Regime (from Stage 4) | Bull % | Base % | Bear % |
|-----------------------------|--------|--------|--------|
| Expansion (early cycle) | 30 | 55 | 15 |
| Expansion (mid cycle) | 20 | 60 | 20 |
| Expansion (late cycle) | 15 | 55 | 30 |
| Recession (early) | 10 | 40 | 50 |
| Recession (late) | 25 | 50 | 25 |
| Stagflation | 10 | 35 | 55 |
| Ambiguous / Transition | 20 | 60 | 20 |

**Step 5**: Compute Risk/Reward Ratio:
```
R/R = (Bull_Price - Current_Price) × Bull_Prob / (Current_Price - Bear_Price) × Bear_Prob
```
- R/R > 3:1 → Attractive
- R/R 1.5-3:1 → Moderate
- R/R < 1:1 → Avoid

## Update Report Template (Re-Analysis)

When re-running analysis after a trigger event (earnings, price target hit, macro regime change,
kill switch approaching), produce an **UPDATE REPORT** rather than a full re-report. The update
report focuses on what changed, what stayed the same, and conviction delta.

**When to use**: Trigger events from the Post-Report Monitoring Protocol (see SKILL.md):
- Earnings release (within 3 days)
- Price hits bull or bear scenario target
- Kill switch condition >80% of trigger level
- Material news (M&A, regulatory, executive departure)
- Macro regime change (Dalio quadrant shift)
- 90/30/7-day elapsed (long/mid/short reports)

**Update report is NOT a full re-report.** Only re-run affected stages. If conviction changes
by ≥1.5 points, flag as "MATERIAL CHANGE."

```
# [TICKER] — Analysis Update

**Update Type**: [Earnings Update / Price Target Hit / Catalyst Triggered / Macro Shift / Scheduled Refresh]
**Update Date**: YYYY-MM-DD
**Original Report**: [TICKER]_[Type]_[Original Date].md (Conviction: X.X/10)

---

## What Changed

| Dimension | Prior (Date) | Current (Date) | Δ | Impact |
|-----------|-------------|----------------|----|--------|
| Price | $X | $Y | +Z% | [Closer to/further from target] |
| Earnings/Fundamentals | [key metric change] | [value] | [delta] | [Thesis strengthened/weakened] |
| Valuation | $X/share (MoS: +Y%) | $Z/share (MoS: +W%) | [delta] | [More/less attractive] |
| Macro | [Regime before] | [Regime now] | [delta] | [Tailwind/headwind shift] |
| Technical | [Setup before] | [Setup now] | - | [Trend intact/broken] |
| Risk | [Red flags: N] | [Red flags: M] | [delta] | [Risk increased/decreased] |

## Conviction Delta

| Component | Prior Score | Current Score | Δ |
|-----------|------------|---------------|----|
| Financial Health | X.X | Y.Y | ±Z.Z |
| Moat Quality | X.X | Y.Y | ±Z.Z |
| Management Quality | X.X | Y.Y | ±Z.Z |
| Valuation Attractiveness | X.X | Y.Y | ±Z.Z |
| Capital Structure | X.X | Y.Y | ±Z.Z |
| Macro Tailwind | X.X | Y.Y | ±Z.Z |
| Risk Profile | X.X | Y.Y | ±Z.Z |
| Alternative Alignment | X.X | Y.Y | ±Z.Z |
| Technical Setup | X.X | Y.Y | ±Z.Z |
| Weinstein Alignment | X.X | Y.Y | ±Z.Z |
| CANSLIM | X.X | Y.Y | ±Z.Z |

**Prior Conviction**: X.X/10 ([Rating]) | **Current Conviction**: Y.Y/10 ([Rating]) | **Δ**: ±Z.Z

**[If Δ ≥ 1.5: "MATERIAL CHANGE — thesis significantly altered"]**
**[If Δ < 1.5: "MINOR ADJUSTMENT — thesis largely intact"]**

## Thesis Status

### Still Valid
- [Aspect of thesis that remains unchanged]
- [Aspect of thesis that remains unchanged]

### Modified
- [What changed and why]
- [What changed and why]

### New Considerations
- [New factor not in original thesis]
- [New factor not in original thesis]

## Updated Recommendation

- **Rating**: [Buy/Hold/Sell] (Prior: [Rating])
- **Target Price**: $X (Prior: $Y) — [X% upside from current]
- **Stop Loss**: $X (Prior: $Y)
- **Time Remaining**: [X months/days] from original horizon
- **Position Size**: X% [Unchanged / Adjust to Y%]

### Action
- [ ] Maintain position (thesis intact, within target range)
- [ ] Add to position (thesis strengthened, larger margin of safety)
- [ ] Reduce position (thesis partially invalidated, reduce risk)
- [ ] Exit position (kill switch triggered or thesis broken)

## Kill Switch Status

| Condition | Trigger Level | Current Level | Status |
|-----------|--------------|---------------|--------|
| [Condition 1] | [Threshold] | [Value] | [OK / APPROACHING / TRIGGERED] |
| [Condition 2] | [Threshold] | [Value] | [OK / APPROACHING / TRIGGERED] |

## Next Update
[Scheduled / Trigger-based: next earnings date, X days, or if price reaches $Y]

## Appendix: Data Quality & Coverage (for re-run stages only)
- Re-run stages: [List of stage numbers]
- Data freshness of re-run data: [Dates]
- Source conflicts introduced: [None / list]
```

### Update Report Rules

1. **Only re-run affected stages.** Don't redo the full analysis for a minor trigger.
2. **Compare scores explicitly.** Always show prior vs current component scores side-by-side.
3. **Flag material changes.** If conviction moves ≥1.5 points, the update report carries "MATERIAL CHANGE" warning.
4. **Action clarity.** Every update report must give an explicit action (maintain/add/reduce/exit).
5. **Kill switch always checked.** Re-evaluate all kill switch conditions against fresh data.
6. **Update report replaces nothing.** The original report remains for audit trail; the update is a supplement.
7. **Scheduled refreshes are lighter.** A 90-day scheduled refresh for a long-term report only re-runs Stages 6+7+10+11; fundamentals/moat assessments carry forward unless a material event occurred.

## Source Attribution Format

Every data claim must use:
```
[Source: EDGAR 10-K FY2024 | Retrieved: YYYY-MM-DD | Fact]
[Source: Seeking Alpha Q3 Transcript | Retrieved: YYYY-MM-DD | Interpretation]
[Source: Analyst estimate | Retrieved: YYYY-MM-DD | Speculation]
```
