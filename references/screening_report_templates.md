# Screening Report Templates & Funnel Scoring

## Funnel Conviction Scoring

The screening report produces three conviction scores reflecting confidence at each funnel level:

### Sector Selection Confidence (1-10)
A measure of how clearly the top sector stands out from alternatives.
```
Sector_Confidence = (Score_Spread × 0.40) + (Macro_Alignment × 0.30) + (Data_Freshness × 0.30)

Where:
  Score_Spread = Top sector composite - 2nd sector composite (normalized to 1-10)
  Macro_Alignment = How well the top sector's sensitivity profile matches current macro regime
  Data_Freshness = Average freshness of sector data sources in days (inverse scored)
```
- ≥7.0: Clear sector leader — strong conviction
- 5.0–6.9: Competitive field — moderate conviction  
- <5.0: No clear winner — LOW CONVICTION, report must carry warning

### Industry Selection Confidence (1-10)
A measure of how compelling the chosen sub-industry's structural thesis is.
```
Industry_Confidence = (Structural_Thesis × 0.35) + (TAM_Visibility × 0.25) +
                       (Growth_Catalyst_Clarity × 0.25) + (Barrier_Strength × 0.15)

Where:
  Structural_Thesis = Quality of the secular growth narrative (1-10)
  TAM_Visibility = How well the TAM can be sized and verified (1-10)
  Growth_Catalyst_Clarity = Specificity and measurability of catalysts (1-10)
  Barrier_Strength = Porter's Five Forces composite score (1-10)
```

### Overall Screen Quality (1-10)
Weighted average of phase-level scores.
```
Screen_Quality = (Sector_Confidence × 0.30) + (Industry_Confidence × 0.35) +
                  (Company_Dispersion × 0.20) + (Methodology_Rigor × 0.15)

Where:
  Company_Dispersion = Inverse of score clustering (wide dispersion = more signal)
  Methodology_Rigor = Completeness of data coverage and source diversity
```
- ≥7.5: High-quality screen — actionable watchlist
- 5.0–7.4: Moderate screen — use watchlist as starting point, verify individually
- <5.0: LOW CONVICTION SCREEN — watchlist is directional only, do not act without further research

## Sector Scoring Dimensions (Phase 1)

| Dimension | Weight (Long) | Weight (Mid) | Weight (Short) | Description |
|-----------|--------------|-------------|----------------|-------------|
| Growth | 30% | 25% | 15% | Revenue/earnings CAGR, forward estimates, secular vs cyclical |
| Profitability | 20% | 15% | 10% | Aggregate margins, ROIC, ROE, FCF conversion |
| Valuation | 10% | 20% | 15% | Sector P/E, EV/EBITDA vs 5-year percentile, PEG |
| Macro Fit | 15% | 20% | 10% | Sensitivity to rates, inflation, GDP; current tailwind/headwind |
| Innovation | 15% | 10% | 5% | R&D intensity, patent activity, disruption exposure |
| Regulatory | 5% | 5% | 5% | Current/pending regulation, antitrust, subsidy exposure |
| Capital Flows | 5% | 5% | 20% | ETF flows (1M/3M/6M), institutional positioning |
| Relative Strength | 5% | 10% | 20% | Sector performance vs SPX over 1M/3M/6M/12M |
| Cyclicality | 5% | 5% | 5% | GDP beta, earnings volatility, early/mid/late-cycle fit |
| Constituent Quality | 0% | 0% | 10% | Breadth of profitable/FCF-positive companies, revision breadth, concentration risk |
| Supply/Demand Cycle | 0% | 0% | 0% | Inventory, utilization, backlog, input costs; use as disclosed reallocation for cycle-sensitive sectors |

For cycle-sensitive sectors, the analyst may reallocate up to 5% from Innovation or Capital Flows to Supply/Demand Cycle. Any reallocation must be stated in the Methodology Appendix.

### Sector Score Interpretation
| Score | Rating | Action |
|-------|--------|--------|
| 8.0-10.0 | Top Tier | Strong candidate for Phase 2 deep-dive |
| 6.0-7.9 | Competitive | Worthy of Phase 2 if structural thesis is compelling |
| 4.0-5.9 | Neutral | Monitor only — no Phase 2 unless theme-driven |
| 2.0-3.9 | Avoid | Structural headwinds or cyclical trough |
| 1.0-1.9 | Toxic | Regulatory/structural collapse risk |

## Company Scoring Model (Phase 3)

```
Company_Score = (Growth × 0.20) + (Profitability/Health × 0.20) + (Moat × 0.20) +
                 (Valuation × 0.15) + (Management × 0.10) + (Risk × 0.10) +
                 (Liquidity/Tradability × 0.05)
```

| Component | Sub-Factors |
|-----------|------------|
| Growth (20%) | Revenue CAGR (3Y), EPS CAGR (3Y), analyst estimate revision momentum |
| Profitability/Health (20%) | ROIC, FCF margin, Altman Z-Score, interest coverage |
| Moat (20%) | Morningstar framework: cost advantages, network effects, intangibles, switching costs, efficient scale |
| Valuation (15%) | P/E percentile vs industry, EV/EBITDA percentile, P/FCF yield, PEG ratio |
| Management (10%) | CEO tenure, insider ownership %, capital allocation track record |
| Risk (10%) | Inverse of risk flags: customer concentration, debt maturity wall, litigation, regulatory |
| Liquidity/Tradability (5%) | Average dollar volume, free float, short interest, borrow/FTD risk |

### Watchlist Rating Anchors
| Score | Rating | Action |
|-------|--------|--------|
| 8.5-10.0 | Top Pick | Immediate candidate for stock-analysis deep-dive (Long-term recommended) |
| 7.5-8.4 | Strong Buy | High-priority deep-dive candidate (Mid-term or Long-term) |
| 6.5-7.4 | Buy | Solid candidate — deep-dive when bandwidth available |
| 5.5-6.4 | Watch | Monitor for catalysts; re-screen in 3-6 months |
| 4.0-5.4 | Hold | Passes filters but lacks compelling thesis |
| <4.0 | Not Rated | Did not pass quantitative filters or scored below threshold |

**Override rule**: Any company with a recent (90-day) insider selling cluster OR Altman Z-Score below 1.8 cannot receive a rating above "Watch" regardless of composite score.

---

## Report Templates

### Broad Screen Report (all 11 GICS sectors → top industry → company watchlist)

```
# Top-Down Industry Screening Report — Broad Market Screen

**Header**
- Screen Type: Broad Market (all 11 GICS sectors)
- Investment Horizon: [Long-term / Mid-term / Short-term]
- Report Date: YYYY-MM-DD | Analyst: AI Stock Research Skill (industry-screening)
- Macro Regime: [Regime classification from Phase 0]

---

## Executive Summary
[1 paragraph covering the full funnel: macro backdrop → winning sector → selected industry → top company picks.
Max 150 words.]

**Overall Screen Quality: [X.X]/10 | Confidence: [Low/Medium/High]**
Sector Selection Confidence: [X.X]/10 | Industry Selection Confidence: [X.X]/10

---

## Macro Context
[Current macro regime. Key indicators: GDP growth, inflation, Fed funds, 10Y yield, PMI, yield curve.
Implications for sector selection: which sectors benefit from current regime, which face headwinds.]

| Indicator | Current Value | Trend | Sector Implication |
|-----------|--------------|-------|-------------------|
| GDP Growth | X.X% | ↑/→/↓ | [Sectors impacted] |
| CPI (YoY) | X.X% | ↑/→/↓ | [Sectors impacted] |
| Fed Funds | X.XX% | ↑/→/↓ | [Sectors impacted] |
| 10Y Yield | X.XX% | ↑/→/↓ | [Sectors impacted] |
| PMI | XX.X | ↑/→/↓ | [Sectors impacted] |

[Source: FRED | Retrieved: YYYY-MM-DD | Fact]

---

## Sector Ranking

### Composite Sector Scores

| Rank | Sector | Growth | Profit. | Val. | Macro | Innov. | Reg. | Flows | RS | Cycle | Quality | **Score** |
|------|--------|--------|---------|------|-------|--------|------|-------|----|-------|---------|-----------|
| 1 | [Sector] | X.X | X.X | X.X | X.X | X.X | X.X | X.X | X.X | X.X | X.X | **X.X** |
| 2 | [Sector] | X.X | X.X | X.X | X.X | X.X | X.X | X.X | X.X | X.X | X.X | **X.X** |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |

**Weighting**: [Long-term / Mid-term / Short-term] scheme applied.

### Top 3 Sectors — Commentary

**[#1 Sector Name] (Score: X.X/10)**
[1 paragraph: why it ranked first. Key strengths. Macro alignment. Primary risk. 3-sentence maximum.]

**[#2 Sector Name] (Score: X.X/10)**
[1 paragraph.]

**[#3 Sector Name] (Score: X.X/10)**
[1 paragraph.]

**Selection Rationale**: [Why the #1 sector was advanced to Phase 2 deep-dive. Score spread vs #2. Tiebreaker factors.]

---

## Industry Deep Dive

### Selected Industry: [Industry Name] (GICS Sub-Industry: [Code])

**Industry Thesis**
[5 sentences: what the industry does, why it's structurally attractive, secular tailwinds, competitive dynamics, why now.]

**Growth Catalysts**
- [Catalyst 1 — specific, measurable]
- [Catalyst 2]
- [Catalyst 3]

**Competitive Dynamics**
- Rivalry: [High/Medium/Low — evidence]
- Barriers to Entry: [High/Medium/Low — evidence]
- Supplier Power: [High/Medium/Low — evidence]
- Buyer Power: [High/Medium/Low — evidence]
- Threat of Substitution: [High/Medium/Low — evidence]

**Market Sizing**
- TAM: $X billion | Growth Rate: X% CAGR | Penetration: X%
- Source: [Report name / publication | Retrieved: YYYY-MM-DD]
- Bottom-up sanity check: [customers/units/spend × penetration × pricing]

**Profit Pool & Unit Economics**
- Profit pool concentration: [Where value accrues across the value chain]
- Key industry KPIs: [Sector-specific KPIs from data_source_matrix.md]
- Adoption/unit economics: [Payback, utilization, churn/retention, capacity, or equivalent]

**Industry Life Cycle**: [Emerging / Growth / Mature / Decline]
[Evidence: revenue growth trajectory, capacity expansion, consolidation activity, innovation rate.]

**Key Players**
| Rank | Company | Ticker | Market Cap | Market Share (est.) | Moat Source |
|------|---------|--------|------------|---------------------|-------------|
| 1 | [Name] | [TICK] | $XB | ~X% | [Source] |
| 2 | [Name] | [TICK] | $XB | ~X% | [Source] |
| ... | ... | ... | ... | ... | ... |

---

## Company Watchlist

### Screening Summary
- Companies in universe: [N]
- Passed quantitative filters: [N] ([X]%)
- Failed: [N] — [top 3 failure reasons with counts]
- Watchlist size: [N]

### Ranked Watchlist

| Rank | Ticker | Company | Market Cap | P/E | Rev Growth 3Y | ROIC | FCF Yield | Liquidity | **Score** |
|------|--------|---------|------------|-----|---------------|------|-----------|-----------|-----------|
| 1 | [TICK] | [Name] | $XB | XX.X | XX% | XX% | X.X% | $XM/day | **X.X** |
| 2 | [TICK] | [Name] | $XB | XX.X | XX% | XX% | X.X% | $XM/day | **X.X** |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |

### Top Picks — Investment Theses

**[#1 — TICKER] Company Name (Score: X.X/10 — Top Pick)**
[2 sentences: what the company does, why it's best-positioned in this industry, primary growth catalyst.]
→ Recommended stock-analysis report type: [Long-term / Mid-term]

**[#2 — TICKER] Company Name (Score: X.X/10 — Strong Buy)**
[2 sentences.]
→ Recommended stock-analysis report type: [Long-term / Mid-term]

[... continue for top 10-20 ...]

---

## Next Actions

1. **Immediate deep-dives**: [TICKER], [TICKER], [TICKER] — run `/stock-analysis:analyze [TICKER] --type [long/mid]`
2. **Monitor for entry**: [TICKER] — currently overvalued vs industry; re-screen when P/E drops below [X]
3. **Re-screen triggers**: Re-run this screen if [macro condition changes / sector ETF drops X% / key regulation passes]

---

## Risks to Thesis

**Industry-Level Risks**
| Risk | Probability | Impact | Mitigant / Kill Switch |
|------|-------------|--------|------------------------|
| [Risk 1] | [Low/Med/High] | [Low/Med/High] | [What to watch] |
| [Risk 2] | [Low/Med/High] | [Low/Med/High] | [What to watch] |

**Kill Switch Conditions**: Exit the industry thesis if [specific, observable conditions]. Currently: [NOT triggered / approaching].

---

## Methodology Appendix

- **Scope**: Broad market screen — all 11 GICS sectors
- **Horizon**: [Long-term / Mid-term / Short-term] — see weighting table above
- **Quantitative Filters**: Market cap ≥ $[X]M, Revenue growth 3Y CAGR ≥ [X]%, FCF positive, ROIC ≥ WACC, D/E ≤ [X]x
- **Data Freshness**: Macro: [date], Sector data: [date range], Company data: [date range]
- **Sources**: [List primary data sources used]
- **Source Coverage Gaps**: [Missing/stale dimensions and confidence impact]
- **Universe Completeness Risk**: [Classification and source limitations]
- **Framework Attribution**: Morningstar (moat), Porter (competitive dynamics), GICS (classification)
```

### Single Sector Report (focused deep-dive on one sector)

Same structure as Broad Screen but with these modifications:
- **Sector Ranking section**: Replaced with "Sector Overview" — a 1-paragraph summary instead of the full 11-sector table. States why this sector was chosen.
- **Sub-Industry Ranking**: A table ranking the top 3-5 sub-industries within the sector before the deep-dive.
- **Industry Deep Dive**: Covers the top-ranked sub-industry.
- **Watchlist**: 10-15 companies (smaller universe than broad screen).
- **Report title format**: `./reports/screening/[SECTOR]_[INDUSTRY]_[YYYY-MM-DD].md`

### Thematic Screen Report (theme-driven subset of sectors)

Same structure as Broad Screen but with these modifications:
- **Executive Summary**: Opens with theme definition and justification.
- **Sector Ranking**: Only includes sectors relevant to the theme (3-5 sectors). Each sector entry includes a "Theme Relevance" column explaining the connection.
- **Weights**: May be adjusted for theme alignment — any weight adjustments must be explicitly stated and justified.
- **Watchlist**: 10-15 companies. Each company thesis must tie back to the theme.
- **Report title format**: `./reports/screening/THEME_[THEME_NAME]_[YYYY-MM-DD].md`

---

## Source Attribution Format

Every data claim must use:
```
[Source: [Publication/URL] | Retrieved: YYYY-MM-DD | Fact]
[Source: [Publication/URL] | Retrieved: YYYY-MM-DD | Interpretation]
[Source: [Publication/URL] | Retrieved: YYYY-MM-DD | Speculation]
```

## Handoff to Stock Analysis

Every screening report must conclude with an explicit handoff:

> "Top-ranked companies from this screen can be deep-dived with the `stock-analysis` skill. The screening report's macro context (Phase 0) and industry thesis (Phase 2) feed directly into stock-analysis Stages 4 and 3 respectively, reducing redundant work."
>
> **Recommended starting ticker**: [TICKER] (Score: X.X/10, [Top Pick / Strong Buy])
> **Suggested command**: `/stock-analysis:analyze [TICKER] --type [long/mid]`
>
> Would you like me to run this deep-dive now?
