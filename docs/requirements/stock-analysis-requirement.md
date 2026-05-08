# Stock Analysis Agent Skill — Requirements

## Overview

Create a multi-stage agent skill that systematically analyzes individual stocks by synthesizing methodologies from the world's top traders and investors. The skill produces comprehensive research reports across three time horizons, comparable in depth to professional sell-side equity research.

## Design Philosophy

- **Learn from the best**: study and codify top traders' actual analysis frameworks
- **Fusion approach**: combine value investing, macro, growth, and quantitative methodologies
- **Multi-dimensional**: cover all critical factors that move stock prices (traditional + alternative data)
- **Actionable output**: produce reports comparable to Goldman Sachs / Morgan Stanley initiation of coverage
- **Second-level thinking**: always ask "what's priced in?" not just "what's happening?"
- **Methodology transparency**: every conclusion traceable to a specific analytical framework

---

## Skill Packaging Specification

### Form Factor

The stock-analysis agent skill is delivered as a **DeepSeek skill package** — a self-contained directory following the standard skill format defined by the `skill-creator` conventions. This enables discovery via `load_skill`, progressive context loading, and bundling of executable scripts and reference material.

### Directory Structure

```
stock-analysis/
├── SKILL.md                              # Required: orchestrator + workflow instructions
│   ├── YAML frontmatter (name, description)
│   └── Markdown body (<500 lines)
├── agents/
│   └── openai.yaml                       # Required: UI metadata for skill listing
├── references/
│   ├── frameworks_value_growth.md        # Buffett, Munger, Fisher, Lynch methodologies
│   ├── frameworks_macro_quant.md         # Dalio, Soros, Druckenmiller, Greenblatt
│   ├── frameworks_risk_alt.md            # Marks, Burry, ARK, forensic accounting
│   ├── institutional_odd.md              # Operational Due Diligence checklists
│   ├── sector_metrics.md                 # Sector-specific KPIs and thresholds
│   └── equity_report_templates.md               # Long/Mid/Short-term report format templates
├── scripts/
│   ├── fetch_financials.py               # Financial data retrieval (SEC EDGAR, FRED, APIs)
│   ├── fetch_alternatives.py             # Alternative data scraping/API integration
│   └── calculate_metrics.py              # Deterministic metric computation (DCF, ratios, scores)
└── assets/
    └── report_styles.css                 # (optional) Report styling
```

### SKILL.md Frontmatter Specification

```yaml
---
name: stock-analysis
description: >
  Multi-stage equity research agent that produces institutional-grade stock
  analysis reports (long/mid/short-term). Synthesizes methodologies from
  Buffett, Dalio, Soros, Lynch, Fisher, Marks, Druckenmiller, Greenblatt,
  Burry, and ARK. Use when the user requests: stock analysis, equity research,
  company deep-dive, should I buy/sell [TICKER], analyze [COMPANY] stock,
  investment thesis, valuation analysis, or due diligence on a public company.
---
```

**Trigger phrases**: `analyze $TICKER`, `research $COMPANY`, `deep dive on $TICKER`, `should I buy $TICKER`, `investment thesis for $COMPANY`, `valuation of $TICKER`, `due diligence on $COMPANY`, `stock report for $TICKER`.

### Progressive Disclosure Architecture

The skill uses a three-tier loading strategy to manage context efficiently:

| Tier | Content | Load Trigger | Max Size |
|------|---------|-------------|----------|
| **Tier 1** | YAML frontmatter (name + description) | Always in context | ~100 words |
| **Tier 2** | SKILL.md body (orchestrator + workflow) | When skill triggers | <5,000 words |
| **Tier 3** | Reference files, scripts | On-demand per analysis stage | Unlimited |

**Reference file loading rules:**
- `frameworks_value_growth.md` — Load during Stages 1, 2, 3, and the Long-term report
- `frameworks_macro_quant.md` — Load during Stages 4, 5, 6, and the Mid-term report
- `frameworks_risk_alt.md` — Load during Stages 7, 8, and the Short-term report
- `institutional_odd.md` — Load when Stage 7 risk assessment begins
- `sector_metrics.md` — Load during Stage 1 when the company's GICS sector is identified
- `equity_report_templates.md` — Load during Stage 9 report generation

The SKILL.md orchestrator must instruct the agent to drop raw data from completed stages before loading the next stage's references, keeping the active context below 80% of the window.

### Required Tool Dependencies

The skill requires the following tool categories to be available in the agent's runtime:

| Tool | Purpose | Criticality |
|------|---------|------------|
| `web_search` | Fetch current financial data, news, analyst estimates, macro indicators | **Must-have** |
| `fetch_url` | Retrieve SEC filings (EDGAR), FRED data, central bank publications | **Must-have** |
| `finance` | Pull real-time price quotes, market cap, key statistics | **Must-have** |
| `exec_shell` | Execute bundled Python scripts for deterministic calculations | **Must-have** |
| `agent_spawn` | Parallelize independent analysis stages | **Should-have** |
| `write_file` | Save generated reports to disk | **Must-have** |
| `read_file` | Load reference files on demand | **Must-have** |
| `grep_files` | Search reference files for specific frameworks/metrics | **Nice-to-have** |

### Script Specifications

Three deterministic scripts handle data acquisition and computation where reliability matters:

**`scripts/fetch_financials.py`**
- Input: Ticker symbol (required), optional `--years` (default 5), optional `--api-key-env` for premium data
- Output: JSON with structured financial statements, key ratios, segment data, insider transactions, institutional holdings
- Fallback chain: Premium API (FMP/Alpha Vantage) → SEC EDGAR XBRL parsing → web scraping (Yahoo Finance)
- Environment variables: `FMP_API_KEY`, `ALPHAVANTAGE_API_KEY`
- Must validate: ticker validity, data freshness (<24h for real-time quotes, <90 days for quarterly filings), required fields presence

**`scripts/fetch_alternatives.py`**
- Input: Ticker symbol (required), optional `--sources` for specific alternative data
- Output: JSON with web traffic trends, app rankings, Glassdoor ratings, social sentiment, patent filings
- Must handle: paywalled sources via graceful degradation (return `null` with `source: "unavailable"` rather than error)
- Rate limiting: max 10 requests/minute to avoid IP blocks

**`scripts/calculate_metrics.py`**
- Input: JSON from `fetch_financials.py` output
- Output: JSON with computed metrics (DCF valuation with sensitivity table, WACC, Beneish M-Score, Altman Z-Score, PEG ratio, DuPont decomposition, reverse DCF implied growth)
- Deterministic calculations only — no LLM involvement in math
- Must include: methodology attribution for each calculation, input data version/timestamp

### Skill Discovery & Installation

- Install path: `$DEEPSEEK_HOME/skills/stock-analysis/` (falls back to `~/.deepseek/skills/stock-analysis/`)
- Discovery: DeepSeek auto-discovers skills in the skills directory via `load_skill`
- Initialization: Use `scripts/init_skill.py stock-analysis --path <skills-dir> --resources scripts,references,assets` to scaffold
- Validation: Use `scripts/quick_validate.py <path/to/stock-analysis>` before packaging
- Package: Use `scripts/package_skill.py <path/to/stock-analysis>` to produce a distributable `.zip` or verify the directory passes all checks

---

## Methodology Integration Rules

### Weighting Mechanism

Report-type methodology weights are applied across three dimensions simultaneously:

**Dimension 1 — Stage Depth Allocation**
Each stage's analysis depth is proportional to its alignment with the report type's priority frameworks:

| Stage | Long-term Weight | Mid-term Weight | Short-term Weight |
|-------|-----------------|-----------------|-------------------|
| Stage 1: Company Fundamentals | **Deep** (full 1.1-1.5, sector metrics, forensic checks) | **Standard** (1.1-1.3, skip forensic unless red flags surface) | **Light** (1.1 summary only) |
| Stage 2: Executive & Board | **Deep** (all 2.1-2.5) | **Standard** (2.1-2.3, skip compensation analysis) | **Skip** (unless insider cluster activity detected) |
| Stage 3: Product & Industry | **Deep** (all 3.1-3.6) | **Standard** (3.1-3.4, skip supply chain unless material) | **Light** (3.1 only) |
| Stage 4: Macro Economics | **Standard** (4.1-4.3) | **Deep** (all 4.1-4.6) | **Standard** (4.1-4.2) |
| Stage 5: Politics & Geopolitics | **Standard** (5.1, 5.3, 5.4) | **Deep** (all 5.1-5.5) | **Light** (5.1 only) |
| Stage 6: Valuation | **Deep** (6.1 all methods, 6.2) | **Deep** (6.1-6.5 all) | **Standard** (6.3-6.5, skip DCF) |
| Stage 7: Risk Assessment | **Deep** (all 7.1-7.6) | **Standard** (7.1-7.4) | **Light** (7.2, 7.4 only) |
| Stage 8: Alternative Data | **Light** (8.4 NLP only) | **Standard** (8.1, 8.4, 8.5) | **Deep** (all 8.1-8.5) |
| Stage 9: Report Generation | Full report | Full report | Full report |

**Dimension 2 — Conviction Score Contribution**
Each framework's weight determines its contribution to the composite conviction score (see algorithm below).

**Dimension 3 — Report Emphasis**
The Detailed Analysis section of each report allocates content proportionally: a framework with 35% weight receives approximately 35% of the analytical word count, a framework with 15% weight receives approximately 15%.

---

### Conviction Scoring Algorithm

The conviction rating (1-10) is derived from a weighted composite of seven component scores, each rated 1-10. The report type determines which frameworks' weights are applied to each component.

#### Component Score Definitions

| Component | Score 1-3 (Bearish) | Score 4-6 (Neutral) | Score 7-10 (Bullish) |
|-----------|---------------------|---------------------|----------------------|
| **Financial Health** | Declining margins, FCF negative, leverage >5x EBITDA | Stable margins, FCF covers capex, leverage 2-4x | Expanding margins, FCF >> capex, leverage <2x |
| **Moat Quality** | Narrowing moat, market share loss, pricing pressure | Stable moat, market share flat, pricing power intact | Widening moat, market share gaining, pricing power growing |
| **Management Quality** | Poor capital allocation, insider selling, guidance misses | Average allocation, neutral insider activity, mixed guidance | Excellent allocation, insider buying, consistent guidance beats |
| **Valuation Attractiveness** | >30% above intrinsic value, multiples at 5yr highs | Within ±15% of intrinsic value, multiples near historical avg | >30% below intrinsic value, multiples at 5yr lows |
| **Macro Tailwind** | Headwinds in 3+ of: rates, inflation, cycle, currency, geopolitics | Mixed: 1-2 headwinds, offset by tailwinds | Tailwinds in 3+ dimensions |
| **Risk Profile** | 3+ forensic red flags, high litigation/regulatory risk, Altman Z <1.81 | Manageable risks, some concerns but mitigants present | Clean forensic profile, low litigation risk, strong balance sheet |
| **Alternative Signal Alignment** | Digital signals diverging negatively from reported trends | Mixed signals, no clear divergence | Digital signals confirming or exceeding reported trends |

#### Composite Aggregation by Report Type

**Long-term Report:**
```
Conviction = (Financial_Health × 0.20) + (Moat_Quality × 0.25) + (Management_Quality × 0.20) +
             (Valuation_Attractiveness × 0.20) + (Macro_Tailwind × 0.05) +
             (Risk_Profile × 0.10)
```
Frameworks applied: Buffett/Munger + Fisher dominate (65% combined weight on moat, management, and financial health).

**Mid-term Report:**
```
Conviction = (Financial_Health × 0.15) + (Moat_Quality × 0.10) + (Management_Quality × 0.10) +
             (Valuation_Attractiveness × 0.25) + (Macro_Tailwind × 0.25) +
             (Risk_Profile × 0.15)
```
Frameworks applied: Lynch + Druckenmiller + Marks dominate (valuation, macro, and risk).

**Short-term Report:**
```
Conviction = (Valuation_Attractiveness × 0.15) + (Macro_Tailwind × 0.10) +
             (Risk_Profile × 0.10) + (Alternative_Alignment × 0.35) +
             (Technical_Setup × 0.30)
```
Technical Setup is scored separately: trend strength, volume confirmation, support/resistance proximity combined into 1-10.

#### Final Rating Anchors

| Score Range | Rating | Description |
|-------------|--------|-------------|
| 9.0-10.0 | **Strong Buy** | Exceptional alignment across all dimensions. Thesis supported by 5+ frameworks. Margin of safety >30%. |
| 7.5-8.9 | **Buy** | Strong alignment across most dimensions. Thesis supported by 3-4 frameworks. Margin of safety 15-30%. |
| 6.0-7.4 | **Hold / Accumulate on Dips** | Mixed signals. Positive long-term thesis but near-term headwinds or valuation not compelling. |
| 4.0-5.9 | **Hold / Reduce** | Thesis weakening. 1-2 dimensions deteriorating. Monitor for downgrade triggers. |
| 2.0-3.9 | **Sell** | Multiple dimensions negative. Thesis broken on 2+ frameworks. Better opportunities elsewhere. |
| 1.0-1.9 | **Strong Sell** | Thesis invalidated across all dimensions. Forensic red flags or structural decline. |

When an anchor boundary is crossed by ≤0.3 points, the agent must apply an override rule: if any single component scores ≤3, the rating cannot exceed "Hold."

#### Missing Data Handling

- If a component lacks sufficient data for scoring, it is excluded and remaining weights are renormalized proportionally
- The report must flag excluded components with a "Data Limitation" annotation explaining why
- If 3+ components are excluded, the confidence level is automatically downgraded to "Low" regardless of conviction score

---

### Scenario Probability Derivation

Replace the fixed probability ranges (Bull 20-25%, Base 50-60%, Bear 20-25%) with a derived methodology:

**Step 1: Define Driver Variables**
Identify the 3-5 variables that most impact the company's valuation (revenue growth rate, operating margin, terminal multiple, tax rate, commodity input cost).

**Step 2: Set Driver Ranges**
For each driver, define:
- **Base**: Consensus or management guidance midpoint
- **Bull**: Best realistic outcome (typically +1 standard deviation from base on 2+ drivers simultaneously)
- **Bear**: Worst realistic outcome (typically -1 standard deviation from base on 2+ drivers simultaneously)

**Step 3: Compute Implied Prices**
Run the DCF model (or primary valuation method) for each scenario's driver combination.

**Step 4: Assign Probabilities Using Regime Adjustment**

| Macro Regime | Bull Probability | Base Probability | Bear Probability |
|-------------|-----------------|------------------|------------------|
| Expansion (early cycle) | 30% | 55% | 15% |
| Expansion (mid cycle) | 20% | 60% | 20% |
| Expansion (late cycle) | 15% | 55% | 30% |
| Recession (early) | 10% | 40% | 50% |
| Recession (late) | 25% | 50% | 25% |
| Stagflation | 10% | 35% | 55% |

The macro regime is determined by Stage 4 analysis output. If the regime is ambiguous, default to: Bull 20%, Base 60%, Bear 20%.

**Step 5: Compute Risk/Reward Ratio**
```
Risk/Reward = (Bull_Price - Current_Price) × Bull_Prob /
              (Current_Price - Bear_Price) × Bear_Prob
```
A ratio >3:1 is attractive. A ratio <1:1 suggests avoid.

---

### Framework Conflict Resolution

When analytical frameworks produce contradictory conclusions, apply the following hierarchy:

**Rule 1 — Report-Type Priority**
The frameworks with highest weight for the active report type take precedence. For a Long-term report, Buffett/Munger's value assessment overrides ARK's disruption thesis if they conflict.

**Rule 2 — Quantitative Override**
When a quantitative screen produces an unambiguous signal (e.g., Beneish M-Score > -1.78, Altman Z-Score < 1.81), it overrides qualitative framework assessments. A company cannot receive a "Buy" rating with an active forensic red flag, regardless of moat quality.

**Rule 3 — Consensus Distance**
When frameworks disagree, quantify the disagreement explicitly in the report with a "Framework Divergence" callout:
```
Framework Divergence:
- Buffett/Munger: BULLISH (moat widening, ROE >20%, margin of safety present)
- Dalio: BEARISH (late-cycle regime, rising rates, credit tightening)
- Resolution: Long-term thesis intact, but entry timing delayed per macro overlay.
                Recommend: Hold with buy target at [price] (15% below current).
```

**Rule 4 — Second-Level Tiebreaker**
When Rules 1-3 don't resolve the conflict, apply Marks's second-level thinking: "What does consensus think, and how does my view differ?" If the agent cannot articulate a clear variant perception, default to the consensus-aligned framework.

---

## Foundational Frameworks (Learned from Top Traders)

### Value Investing — Buffett/Munger

**Buffett's Four Filters:**
1. Circle of Competence — Can I understand this business?
2. Economic Moat — Does it have durable competitive advantages?
3. Management Quality — Is management honest and competent?
4. Margin of Safety — Is the price sensible relative to intrinsic value?

**Munger's Mental Models Applied:**
- Inversion: "How could this investment destroy my capital?"
- Lollapalooza Effect: Where do multiple advantages combine synergistically?
- Checklist discipline: Systematic risk identification before commitment

**Key Quantitative Screens:**
- ROE > 15% consistently (with low leverage)
- For every $1 retained earnings, >$1 market value created
- Debt payable within 3-4 years of earnings
- Owner earnings yield > 10-year Treasury yield

### Macro/Global — Dalio/Soros/Druckenmiller

**Dalio's Economic Machine (Three Forces):**
1. Productivity Growth (~2% long-term trend)
2. Short-Term Debt Cycle (5-8 years)
3. Long-Term Debt Cycle (75-100 years)

**Dalio's Four-Box Framework:**

|  | Rising Growth | Falling Growth |
|--|---------------|----------------|
| **Rising Inflation** | Stocks, Commodities, EM | Commodities, Gold, TIPS |
| **Falling Inflation** | Stocks, Nominal Bonds | Long-term Bonds, Cash |

**Soros's Reflexivity Model (8 Phases):**
1. Unrecognized Trend → 2. Self-Reinforcing Phase → 3. Successful Testing → 4. Growing Conviction → 5. Flaw in Perceptions → 6. Climax → 7. Reversal → 8. Crash

**Druckenmiller's Integration:**
- Macro is the driver, micro is the vehicle
- Focus on liquidity (central bank direction)
- Size positions by conviction (10-50% of portfolio)
- Kill switch: define what makes you wrong BEFORE entering

### Growth Investing — Lynch/Fisher

**Lynch's Six Stock Categories:**
1. Slow Growers — dividend yield focus
2. Stalwarts — PEG < 1.5, rotate at 30-50% gain
3. Fast Growers — PEG < 1, untapped market runway
4. Cyclicals — inverse P/E logic (low P/E = sell signal)
5. Turnarounds — cash vs. burn rate, restructuring credibility
6. Asset Plays — breakup value vs. market cap

**Fisher's 15 Points (summarized essence):**
- Multi-year sales growth potential
- R&D effectiveness relative to size
- Above-average profit margins with clear maintenance strategy
- Outstanding labor/personnel relations and management depth
- Long-range orientation (sacrifices short-term for positioning)
- Management integrity (non-negotiable)

**Fisher's Scuttlebutt Method:**
- Interview competitors, suppliers, customers, former employees
- Listen for convergence from independent sources
- Management reputation among people who deal with them directly

### Quantitative/Special Situations — Greenblatt/Burry/ARK

**Greenblatt's Magic Formula:**
- Rank by Earnings Yield (EBIT/EV) + Return on Capital (EBIT/(NWC + NFA))
- Buy top 20-30 combined-rank stocks, hold 1 year, rebalance

**Burry's SEC Filing Deep-Dive:**
- Footnotes first (where problems hide and assets are buried)
- Cash flow statement over income statement (harder to fake)
- MD&A tone analysis year-over-year
- Accounts receivable growth vs. revenue growth

**ARK's Disruption Framework:**
- Technology S-curve position (past 10-15% adoption tipping point?)
- Wright's Law cost modeling (cost decline per cumulative doubling)
- First-principles TAM (not incumbent TAM)
- 5-year forward valuation at scale

### Risk Assessment — Howard Marks

**Second-Level Thinking Questions:**
1. What is the range of likely outcomes?
2. Which outcome do I think will occur?
3. What does consensus think?
4. How does my expectation DIFFER from consensus?
5. How does current price fit consensus vs. my view?
6. Is psychology driving price too optimistic or pessimistic?

**Cycle Position Checklist:**
- Economy: Vigor or Slowing?
- Lenders: Eager or Restrained?
- Spreads: Narrow or Wide?
- Investors: Optimistic or Pessimistic?
- If most answers left-column → defensive; right-column → aggressive

---

## Skill Analysis Stages (Detailed)

### Stage 1: Company Fundamentals

**1.1 Financial Health Assessment**
- Revenue trends (3-5 years) with segmentation by product, geography, customer
- Gross/operating/net margin trajectory and drivers
- Free cash flow generation and conversion ratio (OCF/Net Income)
- Balance sheet strength: leverage ratios (Debt/EBITDA, Debt/Equity), liquidity (current ratio, quick ratio)
- Working capital efficiency (DSO, DIO, DPO, cash conversion cycle)
- Return metrics: ROIC, ROE (DuPont decomposition), ROA
- Capital expenditure requirements vs. depreciation (maintenance vs. growth capex)
- Earnings quality: accruals ratio, cash flow vs. earnings divergence

**1.2 Business Model Analysis**
- Revenue model type (subscription, transaction, licensing, advertising, etc.)
- Revenue quality (recurring %, contract backlog, deferred revenue trends)
- Unit economics (CAC, LTV, LTV/CAC ratio, payback period)
- Scalability assessment (incremental margins on revenue growth)
- Customer concentration (top 10 customers as % revenue)
- Revenue visibility and predictability

**1.3 Competitive Moat Assessment (Morningstar Framework)**
- **Cost Advantages**: structural cost position, economies of scale, process patents
- **Network Effects**: direct (same-side) vs. indirect (cross-side), data network effects
- **Intangible Assets**: brands, patents, regulatory licenses, proprietary data
- **Switching Costs**: contractual lock-in, data migration pain, workflow dependency
- **Efficient Scale**: natural monopoly characteristics, limited market serving
- Moat trajectory: widening, stable, or narrowing (with evidence)

**1.4 Historical Performance Context**
- 5-year financial CAGR (revenue, EPS, FCF)
- Management guidance accuracy (actual vs. guidance deviation over time)
- Consistency vs. volatility of returns
- Performance through last recession/downturn

**1.5 Forensic Accounting Red Flags**
- Beneish M-Score calculation (>-1.78 = manipulation probability)
- Altman Z-Score (bankruptcy risk assessment)
- Revenue recognition policy review
- Unusual fourth-quarter adjustments
- Receivables vs. revenue growth divergence
- Capitalization of expenses (R&D, SBC treatment)
- Auditor changes or qualified opinions
- SEC comment letters review

**1.6 Segment-Level Analysis (Multi-Segment Companies)**
When the company operates in multiple reporting segments, perform per-segment analysis to isolate which units drive value and which are drags:

- **Revenue & Profit Contribution**: % of total revenue and % of operating profit per segment, with 3-year trend
- **Segment Margin Comparison**: Operating margin per segment vs. corporate average — identify above-average and below-average units
- **Segment Growth Rates**: Revenue CAGR per segment vs. corporate CAGR — which segments are accelerating vs. decelerating?
- **Return on Segment Capital**: Allocated capital per segment and implied ROIC per unit
- **Segment Moats**: Apply the Morningstar moat framework per segment — a wide moat in one unit can subsidize a narrow moat in another
- **Cross-Segment Synergies**: Revenue synergies (cross-selling), cost synergies (shared infrastructure), or negative synergies (cannibalization) between segments
- **Sum-of-the-Parts Tension**: Does the market value the conglomerate at a discount to the sum of segment values? If so, is there an activist/spin-off catalyst to unlock value?
- **Segment Classification**: Flag which segments are Core (strategic, growing, profitable), Harvest (mature, cash-generating), or Divest (declining, capital-intensive, low-return) using BCG matrix logic

**Sector-Specific Metrics:**

| Sector | Key Metrics |
|--------|-------------|
| SaaS/Tech | ARR, NDR, Rule of 40, DAU/MAU, RPO |
| Pharma/Biotech | Pipeline rNPV, probability of success by phase, patent cliff |
| Financials | NIM, ROTCE, CET1, efficiency ratio, net charge-offs |
| Retail/Consumer | Same-store sales, sales/sqft, inventory turnover, e-commerce % |
| Industrials | Book-to-bill, capacity utilization, backlog quality |
| Energy | Reserve replacement ratio, F&D costs/BOE, breakeven price |
| REITs | FFO/AFFO, NAV/share, cap rate, occupancy, leasing spreads |

---

### Stage 2: Executive & Board Profiles

**2.1 Leadership Assessment**
- CEO/CFO background, tenure, and track record at prior companies
- Board composition: independence ratio, diversity, relevant expertise
- Key executive departures in past 2 years (red flag signal)
- Succession planning depth (single-person risk assessment)
- Management communication quality: candor vs. promotional tone

**2.2 Capital Allocation Track Record**
- ROIC vs. WACC spread over time (value creation or destruction?)
- Incremental ROIC on new investments
- M&A track record: % of acquisitions meeting stated targets
- Buyback discipline: average price paid vs. intrinsic value
- Dividend sustainability (payout ratio, growth vs. earnings growth)

**2.3 Insider Ownership & Transactions**
- CEO/CFO ownership as multiple of annual compensation (>10x ideal)
- Total insider ownership percentage (5-20% sweet spot)
- Recent Form 4 activity: open-market purchases (strongest signal)
- Cluster buying detection (3+ insiders within 30 days)
- 10b5-1 plan modifications (timing, size changes)

**2.4 Compensation Structure Analysis**
- Performance metrics tied to: ROIC/FCF (positive) vs. revenue only (concerning)
- Vesting periods and clawback provisions
- Stock ownership requirements
- Peer group composition (biased upward to justify pay?)
- Total compensation vs. value created for shareholders

**2.5 Management Quality Quantification**
- Guidance accuracy: average deviation between guidance and actual results
- Promise-to-delivery ratio: % of strategic initiatives completed on time
- Glassdoor CEO approval trend (2-3 year trajectory)
- Employee retention: senior leadership tenure vs. industry average
- Fisher's Scuttlebutt signals from competitors, suppliers, customers

---

### Stage 3: Product & Industry

**3.1 Product/Service Analysis**
- Product portfolio mapping (revenue contribution, growth rate per product line)
- Product life cycle position (introduction, growth, maturity, decline)
- Innovation pipeline: R&D spend as % revenue vs. peers, output quality
- Product-market fit signals (NPS, retention, expansion within customers)
- Pricing power assessment (ability to raise prices without volume loss)

**3.2 Industry Structure (Porter's Five Forces)**
- **Threat of New Entrants**: capital requirements, regulatory barriers, brand loyalty, scale advantages
- **Supplier Power**: concentration, switching costs, input differentiation
- **Buyer Power**: concentration, price sensitivity, information availability
- **Substitution Threat**: availability of alternatives, relative price-performance
- **Competitive Rivalry**: number of competitors, growth rate, exit barriers, differentiation

**3.3 Competitive Landscape**
- Market share analysis with 3-5 year trend data
- Competitive positioning map (price vs. quality, breadth vs. depth)
- Peer comparison on key operational metrics
- Barriers to entry height and durability
- Disruptive threat assessment (new entrants from adjacent markets, technology shifts)

**3.4 Market Sizing & Growth**
- TAM/SAM/SOM with methodology (top-down and bottom-up cross-check)
- Market growth rate and drivers
- Penetration rate and remaining runway
- Adjacent market expansion opportunities
- Industry life cycle stage (with implications for expected growth, margins, capex)

**3.5 Platform & Network Economics (if applicable)**
- Network effect type (direct, indirect, data, platform)
- Liquidity metrics: % listings transacting, match rate, time-to-transaction
- Multi-tenanting rate (% users on competing platforms)
- Take rate and GMV growth trajectory
- Metcalfe's Law application: value scaling with user growth
- Platform defensibility: switching costs, data moat, supply-side lock-in

**3.6 Supply Chain Analysis**
- Supplier diversification (single-source dependencies)
- Geographic concentration risk (HHI of supplier country locations)
- Critical component identification (no substitutes available)
- Inventory buffer assessment (days of safety stock for critical inputs)
- Post-COVID resilience investments and strategy

**3.7 Ecosystem & Value Chain Mapping**
Extend supply chain analysis to map the full ecosystem in which the company operates:

- **Upstream Dependency Map**: Identify the top 5 suppliers by spend. For each: what do they supply, are there substitutes, what is the switching cost to an alternative?
- **Downstream Customer Map**: Identify the top 5 customers by revenue. For each: what % of their COGS does this company represent, what is their bargaining power, is the relationship contractual or transactional?
- **Single-Point-of-Failure Analysis**: List every input, partner, or infrastructure element without which the company cannot operate for >48 hours. Score each by probability of disruption × impact severity.
- **Ecosystem Dependency**: Does the company's growth depend on another platform/company's success? (e.g., "AWS expanding in Southeast Asia," "Shopify merchant growth," "iOS remaining the dominant mobile platform")
- **Complementor Analysis**: Identify companies whose products make this company's products more valuable (e.g., app developers for smartphone platforms). Assess complementor ecosystem health.
- **Industry Architecture Evolution**: Is the value chain consolidating (vertical integration) or fragmenting (specialization)? How does this shift affect the company's position and pricing power?
- **Geographic Value Chain Concentration**: Map the value chain geographically — design (where?), sourcing (where?), manufacturing (where?), assembly (where?), distribution (where?). Score each node for geopolitical/operational risk.

---

### Stage 4: Macro & Micro Economics

**4.1 Economic Cycle Positioning**
- Current position in short-term debt cycle (Dalio framework)
- Leading indicators: PMIs, housing starts, initial claims, yield curve
- Credit conditions: spreads, lending standards, bank loan growth
- Consumer/business confidence and spending trends
- Inventory/sales ratios (economy-wide and sector-specific)

**4.2 Interest Rate & Monetary Policy Impact**
- Company sensitivity to rate changes (floating vs. fixed debt, duration of assets)
- Central bank policy direction and expected trajectory
- Impact on company's discount rate and valuation multiples
- Impact on customer demand (rate-sensitive end markets)
- Dollar direction impact on international competitiveness

**4.3 Inflation Dynamics**
- Input cost pressure (commodity exposure, labor cost trends)
- Pricing power: ability to pass through cost increases
- Margin compression/expansion under different inflation regimes
- Real vs. nominal growth distinction
- TIPS breakeven spread as market inflation expectation

**4.4 Industry Supply/Demand Dynamics**
- Capacity utilization rates and new capacity pipeline
- Order backlog trends and book-to-bill ratios
- Inventory levels across the value chain
- Lead times and delivery schedules
- Pricing cycle position (trough, recovery, peak, correction)

**4.5 Currency & Trade Exposure**
- Revenue by currency (unhedged foreign exposure %)
- Natural hedging (costs in same currency as revenue)
- Hedging strategy effectiveness
- Currency direction impact on competitiveness
- Cross-border tariff and trade policy exposure

**4.6 Sector-Specific Economic Drivers**
- Identify the 3-5 macro variables most correlated with sector performance
- Historical sensitivity analysis (how did this stock perform in prior cycle phases?)
- Leading indicator identification specific to this company's demand drivers

---

### Stage 5: Politics & Geopolitics

**5.1 Regulatory Environment**
- Current regulatory framework affecting the company
- Upcoming regulatory changes (proposed legislation, agency rulemaking)
- Regulatory risk: probability of adverse change × impact magnitude
- Compliance cost trajectory
- Regulatory capture or favorable positioning (licenses, approvals)
- Antitrust/competition concerns (market share thresholds, M&A scrutiny)

**5.2 Trade Policy & Tariffs**
- Tariff exposure: % COGS from tariff-affected imports
- Trade agreement dependency (USMCA, EU FTAs, RCEP, etc.)
- Supply chain rerouting costs under trade war escalation
- Export control exposure (technology restrictions, entity lists)
- Nearshoring/reshoring trends and company positioning

**5.3 Geopolitical Risk Assessment**
- Revenue geographic concentration (HHI by country)
- Revenue from high-GPR-score countries (Caldara-Iacoviello index)
- Asset seizure risk: fixed assets in politically unstable jurisdictions
- Sanctions exposure (OFAC, EU sanctions lists)
- Military conflict impact scenarios on supply chain and demand
- Key country election calendars and policy scenario modeling

**5.4 Government Policy Impact**
- Subsidies and incentives (IRA, CHIPS Act, Green Deal, etc.)
- Tax policy direction in key jurisdictions
- Government as customer (defense, healthcare, infrastructure spending)
- Industrial policy alignment or misalignment

**5.5 ESG & Political Sentiment**
- ESG rating trajectory (MSCI, Sustainalytics, S&P Global CSA)
- Material ESG issues for this specific industry
- Climate transition risk and physical climate risk
- Social license to operate (community relations, labor practices)
- Governance quality score vs. peers
- Controversy monitoring (real-time ESG incident tracking)
- Regulatory anticipation: which ESG factors face upcoming mandates?

---

### Stage 6: Valuation & Quantitative Signals

**6.1 Multi-Method Valuation**

**Discounted Cash Flow (DCF):**
- 5-10 year unlevered free cash flow projections
- WACC calculation (CAPM-based cost of equity + cost of debt)
- Terminal value (perpetuity growth method + exit multiple cross-check)
- Sensitivity tables: WACC vs. terminal growth rate, WACC vs. exit multiple
- Reverse DCF: what growth rate is implied by current price?

**Comparable Company Analysis (Trading Comps):**
- Peer universe selection (GICS, business model, size, growth, margins)
- Multiple comparison: EV/Revenue, EV/EBITDA, P/E, P/FCF, PEG
- Premium/discount justification based on growth differential, margin, risk
- Historical multiple context (where does current multiple sit vs. 5-year range?)

**Sum-of-the-Parts (SOTP) — if multi-segment:**
- Independent valuation per business segment
- Holding company overhead deduction
- Conglomerate discount consideration (10-20% typical)

**Additional Methods:**
- Dividend Discount Model (for mature, stable-dividend companies)
- Residual Income / EVA (for financials)
- M&A / LBO floor price (what would a private buyer pay?)
- Precedent transaction analysis (recent M&A comps)
- Asset-based valuation (for asset-heavy businesses)

**6.2 Relative Value Metrics**
- P/E (trailing, forward, NTM) vs. historical average and peers
- EV/EBITDA vs. peers with growth/margin justification
- P/FCF yield vs. risk-free rate (equity risk premium implied)
- PEG ratio (Lynch: <1 buy, 1-2 fair, >2 expensive)
- EV/Revenue for high-growth/unprofitable companies
- Sector-specific multiples (P/NAV, P/Book, EV/subscriber, etc.)

**6.3 Technical & Momentum Signals**
- Trend assessment (moving averages, trend lines, higher highs/lows)
- Momentum indicators (RSI, MACD, rate of change)
- Volume analysis (accumulation/distribution, OBV)
- Support/resistance levels
- Relative strength vs. sector and market
- Seasonality patterns

**6.4 Sentiment & Flow Data**
- Put/call ratio (extremes as contrarian signal)
- VIX term structure (contango vs. backwardation)
- Short interest and days-to-cover
- Options flow: unusual activity in OTM calls/puts
- Dark pool prints (above/below midpoint)
- Retail vs. institutional flow divergence
- AAII sentiment survey context

**6.5 Institutional & Insider Flow**
- 13F analysis: new positions, increases, liquidations by top funds
- Activist accumulation detection (13D filings)
- Form 4 cluster buying/selling patterns
- Institutional ownership % and concentration
- Smart money consensus (top 10 holders' position changes)

---

### Stage 7: Risk Assessment & Synthesis

**7.1 Risk Identification (Categorized)**

| Category | Examples |
|----------|----------|
| Operational | Execution risk, key person dependency, technology failure |
| Financial | Leverage, liquidity, covenant breach, refinancing wall |
| Competitive | Market share loss, pricing pressure, disruption |
| Regulatory/Legal | Adverse regulation, litigation, antitrust |
| Macro | Recession, rate spikes, currency moves, trade wars |
| Geopolitical | Sanctions, conflict, regime change |
| ESG/Reputational | Controversy, governance failure, social backlash |

**7.2 Risk Quantification**
- Probability × Impact matrix for each identified risk
- Earnings impact quantification (EPS impact under each risk scenario)
- Mitigants for each risk (what reduces probability or impact?)
- Time horizon: which risks are near-term vs. tail risks?

**7.3 Scenario Analysis (Bull/Base/Bear)**

| Scenario | Probability | Key Assumptions | Implied Price Target |
|----------|------------|-----------------|---------------------|
| Bull | 20-25% | Best realistic outcome | [derived from valuation] |
| Base | 50-60% | Most likely outcome | [derived from valuation] |
| Bear | 20-25% | Worst realistic outcome | [derived from valuation] |

Each scenario must include:
- Explicit revenue/margin/growth assumptions
- Valuation multiple applied and why
- Specific conditions under which this scenario materializes

**7.4 Catalyst Timeline**
- Upcoming catalysts (earnings, product launches, regulatory decisions, M&A)
- Timeframe for each catalyst
- Expected direction and magnitude of price impact
- Probability of positive vs. negative resolution

**7.5 Cross-Dimensional Synthesis**
- Marks's Second-Level Thinking applied: What does consensus think vs. my view?
- Soros's Reflexivity check: Are there self-reinforcing loops (positive or negative)?
- Dalio's Cycle Position: What macro environment regime and how does it affect this stock?
- Conviction scoring: How many independent analytical dimensions align?

**7.6 Forensic Red Flag Summary**
Immediate deep investigation required if 3+ present simultaneously:
- Beneish M-Score > -1.78
- Altman Z-Score < 1.81
- OCF declining while net income grows
- Multiple insider sales (non-10b5-1)
- Glassdoor rating declining >0.5 points in 6 months
- Top institutional holders reducing positions
- Auditor change or qualified opinion
- Web traffic declining while company reports growth
- Senior leadership departures clustering

**7.7 Operational Due Diligence (ODD)**
Institutional-grade operational risk assessment beyond financial metrics:

- **Cybersecurity Posture**: History of data breaches (count, severity, remediation time), security certifications (SOC 2, ISO 27001), CISO reporting structure (to CEO/Board vs. to CIO), cyber insurance coverage limits
- **Legal & Regulatory History**: Material litigation (past 5 years) — class actions, IP disputes, employment suits, environmental penalties. Pattern analysis: recurring issues or one-off events?
- **Disaster Recovery & Business Continuity**: Documented DR plan (yes/no, last tested), geographic redundancy of critical operations, RTO/RPO targets for critical systems, historical downtime incidents
- **Insurance Coverage**: Directors & Officers (D&O) limits, key person insurance (if founder-led), business interruption coverage adequacy relative to revenue run rate
- **Intellectual Property Protection**: Patent portfolio strength (citation count, grant rate, geographic coverage), trade secret protection protocols, IP litigation history (plaintiff or defendant posture)
- **Regulatory Compliance Infrastructure**: Dedicated compliance team size relative to industry, regulatory examination history (findings, remediation), whistleblower program existence and quality
- **Third-Party Risk Management**: Vendor due diligence program maturity, concentration of critical vendors, fourth-party risk awareness (your vendors' vendors)

**7.8 Thesis Falsifiability (Pre-Mortem)**
Before finalizing any investment thesis, run a structured pre-mortem to identify what would prove the thesis wrong:

- **Pre-Mortem Prompt**: "Assume it is [report horizon + 6 months]. The investment in [TICKER] has been a complete disaster — we lost [X]% of capital. Write the post-mortem explaining exactly what happened."
- **Falsification Conditions**: Define 3-5 specific, observable conditions that would invalidate the thesis. Each must be:
  - **Falsifiable**: Can be objectively verified true/false
  - **Timely**: Observable within the report's time horizon
  - **Actionable**: Triggers a specific portfolio action (reduce, exit, hedge)
- **Dissenting View Search**: Actively search for the strongest bear case arguments. Do not strawman — find the most credible analysts, short sellers, or competitors arguing against this stock and engage with their best points
- **Inversion Checklist** (from Munger):
  1. "How could this investment destroy my capital?"
  2. "What am I not seeing because of my own biases?"
  3. "If I had to argue the opposite side, what would be my 3 strongest points?"
  4. "What would need to happen for this company to go bankrupt in 5 years?"
- **Confidence Calibration**: Rate each thesis pillar by how confident the agent is in the underlying analysis (1-10). Pillars rated <6 must be explicitly flagged as "speculative" in the report
- **Kill Switch Definition**: For each report, define the explicit condition that triggers immediate exit:
  ```
  Kill Switch: Exit [TICKER] immediately if [specific condition] occurs.
  Current monitoring status: [condition is NOT present / IS approaching trigger level]
  ```

---

### Stage 8: Alternative Data & Digital Signals

**8.1 Digital Footprint Analysis**
- Web traffic trends (SimilarWeb): visits, engagement, source mix
- App rankings and downloads (Sensor Tower, data.ai): DAU/MAU ratio, retention curves
- Social media metrics: brand mention volume, sentiment score, share of voice
- Hiring trends (LinkedIn, Revelio Labs): headcount growth by department, new role types
- Patent filing velocity and technology domain mapping

**8.2 Transaction & Consumer Data**
- Credit/debit card transaction trends (Second Measure, Earnest Research)
- Real-time revenue estimation from payment panels
- Consumer behavior shifts and wallet share changes
- E-commerce channel tracking

**8.3 Satellite & Sensor Data**
- Foot traffic to physical locations (parking lot counts)
- Construction and industrial activity monitoring
- Shipping and logistics flow data (container volumes, port activity)
- Agricultural/commodity supply monitoring

**8.4 NLP & Earnings Call Analysis**
- Tone analysis: positive/negative word ratio in management commentary
- Q&A vs. prepared remarks tone differential (spontaneous answers more revealing)
- Uncertainty quantification: hedging language frequency
- Topic avoidance detection: what subjects does management dodge?
- Year-over-year language comparison: buried trend changes
- Deception indicators: increased complexity, passive voice, distancing language

**8.5 Composite Alternative Data Score**
- Web traffic trend (20%)
- App engagement (20%)
- Social sentiment (15%)
- Employee satisfaction (15%)
- Hiring momentum (15%)
- Innovation activity (15%)

**8.6 Primary Research & Channel Checks**
When feasible, supplement quantitative alternative data with qualitative primary research:

- **Expert Network Synthesis**: Search for publicly available expert interviews, industry conference transcripts, or podcast appearances by former executives, competitors, or suppliers. Extract converging themes across independent sources.
- **Channel Check Methodology** (Fisher's Scuttlebutt applied):
  - **Supplier Checks**: What are suppliers saying about order volumes, payment terms, relationship quality?
  - **Customer Checks**: What do customer reviews, forums, and social media reveal about satisfaction, switching intent, pricing sensitivity?
  - **Competitor Checks**: How do competitors describe this company in their own earnings calls and investor presentations? (Defensive or dismissive language is a positive signal.)
  - **Former Employee Checks**: Glassdoor reviews + LinkedIn departure analysis + publicly available exit interviews. Focus on departments relevant to the thesis (R&D departures matter more for a tech thesis; sales departures matter more for a growth thesis).
- **Convergence Scoring**: Rate the degree of independent-source convergence:
  - **High Convergence** (4+ independent sources agree): Strong signal, high confidence
  - **Moderate Convergence** (2-3 sources agree): Indicative, moderate confidence
  - **Low Convergence** (single source or conflicting): Weak signal, flag as unverified
- **Conflicting Source Handling**: When sources disagree, report both sides. Do not cherry-pick confirming evidence. The report must state: "Channel checks produced mixed signals: [bull signal] from [source A], but [bear signal] from [source B]."
- **Limitations Disclosure**: Primary research is inherently non-representative. Every channel check finding must carry a disclaimer: "Based on [N] independent sources. Not a statistically representative sample. Directional only."

---

### Stage 9: Report Generation

Generate three report versions with shared research but different emphasis and weighting:

#### Long-term Report (1-3+ years)

**Methodology Weight:**
- Buffett/Munger: 35% (moat, intrinsic value, management quality)
- Fisher: 25% (15 points, scuttlebutt, growth runway)
- Marks: 20% (cycle position, risk assessment)
- Dalio: 20% (macro backdrop, economic regime)

**Focus Areas:**
- Intrinsic value vs. current price (margin of safety calculation)
- Moat durability and trajectory (widening or narrowing?)
- Management quality and capital allocation track record
- Secular growth trends and multi-year compounding potential
- Long-term risk to permanent capital loss

**Report Structure:**
1. Investment Thesis (3-5 bullet points)
2. Moat Assessment (detailed with evidence)
3. Management Quality Score
4. Intrinsic Value Estimate (multiple methods, sensitivity)
5. Long-term Growth Runway
6. Key Long-term Risks
7. Recommendation: Buy/Hold/Avoid with target price and margin of safety

#### Mid-term Report (1-12 months)

**Methodology Weight:**
- Lynch: 30% (category, PEG, catalysts)
- Druckenmiller: 25% (macro-micro integration, sizing)
- Greenblatt: 20% (relative value, special situations)
- Marks: 25% (cycle position, second-level thinking)

**Focus Areas:**
- Stock category classification (Lynch's 6 categories)
- Upcoming catalysts with timeline and probability
- Earnings trajectory (consensus vs. proprietary estimate)
- Relative value vs. peers (is this the best vehicle for the theme?)
- Cycle positioning and sector rotation implications
- What is priced in vs. what is likely to happen

**Report Structure:**
1. Category & Thesis (which Lynch category, why now?)
2. Catalyst Map (upcoming events, timeline, probability)
3. Earnings Estimate vs. Consensus
4. Relative Valuation (vs. peers, vs. history)
5. Macro Tailwinds/Headwinds
6. Position Sizing Guidance
7. Recommendation: Buy/Hold/Sell with 12-month target and catalysts

#### Short-term Report (days to weeks)

**Methodology Weight:**
- Quantitative/Technical: 35% (momentum, flow, sentiment)
- Soros: 25% (reflexivity, self-reinforcing dynamics)
- Alternative Data: 25% (real-time digital signals)
- Druckenmiller: 15% (conviction sizing, kill switch)

**Focus Areas:**
- Technical setup (trend, support/resistance, volume)
- Sentiment extremes (contrarian opportunities)
- Options flow and unusual activity
- Institutional flow signals (dark pool, 13F timing)
- Alternative data real-time readings
- Entry/exit timing optimization
- Risk/reward ratio for the trade setup

**Report Structure:**
1. Setup Summary (1 paragraph: why now, what's the trade?)
2. Technical Analysis (key levels, trend, momentum)
3. Flow & Sentiment Signals
4. Alternative Data Readings
5. Entry Price, Stop Loss, Target (explicit levels)
6. Risk/Reward Ratio
7. Kill Switch: What makes us wrong (exit immediately if X happens)

---

## Output Format Specification

### Each Report Version Includes:

```
Header:
- Company Name | Ticker | Exchange
- Current Price | 52-week Range | Market Cap | Enterprise Value
- Report Date | Analyst: AI Stock Research Skill
- Report Type: [Long-term / Mid-term / Short-term]

Executive Summary: (1 paragraph, max 150 words)

Conviction Rating: [1-10] | Confidence Level: [Low/Medium/High]
- Rationale for rating in 1 sentence

Key Thesis: (3-5 bullet points, each max 2 sentences)

Rating: [Strong Buy / Buy / Hold / Sell / Strong Sell]
- Target Price: $X (X% upside/downside)
- Time Horizon: [X months/years]
- Key Catalyst: [single most important upcoming trigger]

Detailed Analysis: (organized by relevant stages)

Risk/Reward Summary:
- Bull Case: $X (probability %)
- Base Case: $X (probability %)
- Bear Case: $X (probability %)
- Risk/Reward Ratio: X:1

Actionable Recommendation:
- Entry criteria
- Position size guidance
- Stop loss / exit criteria
- Monitoring triggers (what to watch for thesis change)

Methodology Attribution:
- Key frameworks applied
- Where this analysis agrees/disagrees with each framework

Sources & Data:
- All data sources cited with dates
- Distinction: fact vs. interpretation vs. speculation
```

---

## Data Sources Strategy

### Tiering System

| Tier | Label | Behavior When Unavailable |
|------|-------|--------------------------|
| **Tier 1** | Must-have | Block stage completion. Report must flag the gap. |
| **Tier 2** | Should-have | Attempt acquisition; if unavailable, proceed with annotation. |
| **Tier 3** | Nice-to-have | Attempt if convenient; skip silently if unavailable. |

### Tier 1 — Must-Have (Blocking)

| Data Source | Acquisition Method | Max Freshness | Fallback Chain |
|-------------|-------------------|---------------|----------------|
| **SEC Filings** (10-K, 10-Q, 8-K, DEF 14A) | `fetch_url` → SEC EDGAR | <90 days (quarterly filing cycle) | EDGAR XBRL → `web_search` cached copies → flag as stale if >90 days |
| **Earnings Call Transcripts** (last 4 quarters) | `web_search` → Seeking Alpha / Fool.com | <90 days per transcript | `fetch_url` → company IR page → flag missing quarters |
| **Current Price & Market Data** | `finance` tool | <15 minutes (real-time during market hours) | `web_search` → Yahoo Finance / Google Finance → flag as delayed |
| **Financial Statements** (standardized: income, balance sheet, cash flow) | `exec_shell` → `scripts/fetch_financials.py` | <90 days | Premium API → EDGAR XBRL → `web_search` manual extraction → **block stage if unavailable** |
| **Key Ratios** (P/E, EV/EBITDA, ROE, Debt/EBITDA, FCF yield) | `exec_shell` → `scripts/calculate_metrics.py` | <90 days | Compute from raw financials if script unavailable → flag as manually derived |
| **Macro Indicators** (Fed funds rate, 10Y yield, CPI, PMI, unemployment) | `web_search` → FRED / BLS / ISM | <30 days | Central bank publications → `fetch_url` → flag as potentially stale |
| **Insider Transactions** (Form 4 filings) | `web_search` → SEC EDGAR / OpenInsider | <30 days | `fetch_url` → EDGAR RSS → flag if >60 days stale |

### Tier 2 — Should-Have (Attempt with Annotation)

| Data Source | Acquisition Method | Max Freshness | Fallback Behavior |
|-------------|-------------------|---------------|-------------------|
| **Institutional Holdings** (13F filings) | `web_search` → SEC EDGAR / WhaleWisdom | <120 days (quarterly filing) | Proceed with annotation: "13F data is [N] days old; quarter-end positions may differ" |
| **Short Interest Data** | `web_search` → FINRA / MarketBeat | <15 days (bi-monthly settlement) | Proceed with last available reading, flag staleness |
| **Analyst Consensus Estimates** | `web_search` → Yahoo Finance / MarketScreener | <30 days | Proceed with last available consensus, flag if >60 days stale |
| **Peer Company Financials** (for trading comps) | `exec_shell` → `scripts/fetch_financials.py --ticker PEER1,PEER2,...` | <90 days | Reduce peer universe to available tickers; proceed with smaller set |
| **Industry Reports** (Gartner, IDC, etc.) | `web_search` | <365 days | If paywalled, use press release summaries or trade association publications |
| **Credit Rating & Bond Spreads** | `web_search` → Moody's / S&P / FRED | <30 days | Proceed with last known rating; flag if unrated |
| **Central Bank Minutes & Policy Statements** | `fetch_url` → Fed / ECB / BoJ / PBoC websites | <90 days | Use `web_search` for news summaries; flag as secondary source |

### Tier 3 — Nice-to-Have (Optional)

| Data Source | Acquisition Method | Max Freshness | Skip Protocol |
|-------------|-------------------|---------------|---------------|
| **Web Traffic** (SimilarWeb) | `web_search` or `scripts/fetch_alternatives.py --sources web` | <30 days | Return `null` with `source: "unavailable_paywall"` |
| **App Analytics** (Sensor Tower, data.ai) | `web_search` or `scripts/fetch_alternatives.py --sources app` | <30 days | Return `null` with `source: "unavailable_paywall"` |
| **Employee Sentiment** (Glassdoor) | `web_search` or `scripts/fetch_alternatives.py --sources glassdoor` | <90 days | Retrieve publicly visible snapshot; skip if insufficient data |
| **Job Postings** (LinkedIn, Revelio Labs) | `web_search` | <30 days | Retrieve trend direction only; skip absolute counts if behind login |
| **Social Media Sentiment** (Reddit, StockTwits) | `web_search` | <7 days | Sample recent mentions; flag as "non-representative sample" |
| **Patent Filings** (USPTO, EPO) | `web_search` → USPTO / Google Patents | <365 days | Retrieve count + key technology domains; skip full text |
| **Credit/Debit Card Transactions** (Second Measure, Earnest) | `scripts/fetch_alternatives.py --sources transactions` | <30 days | Return `null` with `source: "unavailable_paywall"` |
| **Satellite & Sensor Data** | `web_search` for public research reports | <90 days | Skip entirely unless publicly available research exists |
| **Geopolitical Risk Indices** (Caldara-Iacoviello GPR) | `fetch_url` → matteoiacoviello.com/gpr | <30 days | Proceed with qualitative assessment |
| **ESG Ratings** (MSCI, Sustainalytics) | `web_search` | <365 days | Retrieve publicly disclosed tier/score; skip detailed breakdown if paywalled |
| **Trade Policy Tracking** (USTR, tariff schedules) | `web_search` → USTR / WTO | <90 days | Proceed with qualitative summary |

### Data Freshness Enforcement

Before any stage output is finalized, the agent must check:

1. **Timestamp verification**: Every data point must carry a `retrieved_at` timestamp
2. **Staleness flagging**: Data exceeding Max Freshness must be annotated `[STALE: X days]` in the report
3. **Tier 1 staleness**: If a Tier 1 source exceeds 2× its Max Freshness, the stage is blocked and the report must state: "Analysis deferred — critical data is stale"
4. **Cross-reference**: Alternative data readings that contradict reported financials must be triple-checked before inclusion

### Source Attribution Format

Every data claim in the report must follow this format:
```
[Source: EDGAR 10-K FY2024 | Retrieved: 2026-01-15 | Fact]
[Source: Seeking Alpha Q3 2025 Transcript | Retrieved: 2026-01-14 | Interpretation]
[Source: FRED Series T10Y2Y | Retrieved: 2026-01-16 | Fact]
```

The `Fact` / `Interpretation` / `Speculation` tag must appear on every source citation.

### Report File Naming & Persistence

**Output Directory**: `./reports/[TICKER]/` (created if it doesn't exist)

**File Naming Convention**:
```
[TICKER]_[ReportType]_[YYYY-MM-DD].md
```

Examples:
```
AAPL_LongTerm_2026-01-15.md
AAPL_MidTerm_2026-01-15.md
AAPL_ShortTerm_2026-01-15.md
```

**Intermediate Artifacts** (for audit trail):
```
/tmp/stock-analysis-[TICKER]-stage[N].md    # Per-stage summaries
/tmp/stock-analysis-[TICKER]-raw-data.json  # Raw financial data (from scripts)
/tmp/stock-analysis-[TICKER]-metrics.json   # Computed metrics (from scripts)
```

Intermediate artifacts are:
- Written at the end of each completed stage (for stage summaries)
- Written by `scripts/fetch_financials.py` and `scripts/calculate_metrics.py` (for raw data and metrics)
- Preserved until the final report is successfully written to `./reports/`, then deleted
- If a stage fails, intermediate artifacts are preserved for debugging — do not auto-delete on failure

**Multi-Report Behavior**: If the user requests all three report types, generate in order: Long-term → Mid-term → Short-term (each reuses stage summaries from previous runs). Write all three to `./reports/[TICKER]/`.

**Overwrite Policy**: If a report for the same ticker, type, and date already exists, overwrite with a warning: "Existing report overwritten. Diff available in git history."

### Report Completion Criteria

A report is considered complete only when ALL of the following are true:
1. Header populated with all required fields (ticker, exchange, price, market cap, EV, 52-week range)
2. Executive Summary ≤150 words
3. Conviction Rating populated with derivation traceable to the scoring algorithm
4. Key Thesis has 3-5 bullet points
5. Rating assigned (Strong Buy through Strong Sell) with target price and time horizon
6. Detailed Analysis covers all stages per the Stage Depth Allocation table
7. Risk/Reward Summary includes all three scenarios with probabilities and implied prices
8. Actionable Recommendation has entry criteria, stop loss, and monitoring triggers
9. Methodology Attribution cites specific frameworks and notes divergences
10. All source citations use the `[Source: ... | Retrieved: ... | Tag]` format
11. Kill Switch defined (if applicable to report type)
12. Pre-Delivery Checklist (from Validation section) fully checked

Any missing item downgrades the report status from "Complete" to "Draft — missing [item]".

---

## Constraints & Performance Budget

### Context Window Management

The skill's progressive disclosure architecture (see Skill Packaging Specification) manages context through three tiers. However, additional operational rules are required to prevent context exhaustion during a live analysis:

**Per-Stage Token Budget:**

| Report Type | Max Tokens per Stage | Max Concurrent Reference Files | Parallel Sub-Agent Limit |
|-------------|---------------------|-------------------------------|--------------------------|
| Long-term | 80,000 | 1 at a time | 2 (Stages 1-3 can parallelize) |
| Mid-term | 60,000 | 1 at a time | 3 (Stages 4-6 can parallelize) |
| Short-term | 40,000 | 1 at a time | 2 (Stages 7-8 can parallelize) |

**Context Eviction Protocol:**
1. After completing a stage, write the stage summary to a temp file (`/tmp/stock-analysis-[TICKER]-stage[N].md`)
2. Drop raw data (SEC filing text, full transcripts, raw financials) from active context
3. Retain only: key metrics summary, stage scores, and a 3-sentence narrative per sub-section
4. Load the next stage's reference file and proceed
5. At Stage 9, read all temp files to synthesize the final report

**Maximum active context at any point:** <80% of the context window. If approaching the limit, offload intermediate data to temp files before continuing.

### API Call Budget

| Report Type | Max web_search Calls | Max fetch_url Calls | Max finance Calls | Max exec_shell Calls |
|-------------|---------------------|--------------------|--------------------|----------------------|
| Long-term | 25 | 15 | 3 | 5 |
| Mid-term | 20 | 10 | 3 | 4 |
| Short-term | 15 | 5 | 5 | 3 |

Budget enforcement: If 80% of any category budget is consumed before Stage 9, the agent must flag remaining stages as "resource-constrained" and prioritize the highest-weight analysis dimensions.

### Stage Skipping Rules

The agent may skip or reduce a stage's depth when:

| Condition | Action |
|-----------|--------|
| User requests a specific report type only | Apply the Stage Depth Allocation table from Methodology Integration Rules |
| Company lacks segment reporting | Skip 1.6 Segment-Level Analysis |
| Company has no platform/network business model | Skip 3.5 Platform & Network Economics |
| Company operates entirely domestically | Reduce 4.5 Currency & Trade Exposure to a single check |
| Short-term report requested | Skip Stages 2 (Executive) and 5 (Geopolitics) unless insider activity or geopolitical events are flagged as catalysts |
| User explicitly says "quick analysis" or "overview only" | Run Stages 1, 6, 7, 9 only; produce Mid-term report format |

### Time-to-Completion Estimates

| Report Type | Estimated Wall Time | Parallelism Enabled |
|-------------|---------------------|---------------------|
| Long-term | 8-15 minutes | Stages 1-3 parallel, 4-5 parallel, 6-7 parallel, 8 sequential, 9 sequential |
| Mid-term | 5-10 minutes | Stages 4-6 parallel, 1+7 parallel, 2+8 parallel, 9 sequential |
| Short-term | 2-5 minutes | Stages 6+8 parallel, all other sequential |
| Quick Overview | 1-3 minutes | Stages 1+6+7 parallel, 9 sequential |

### Cost Estimate per Analysis

| Report Type | Estimated Input Tokens | Estimated Output Tokens | Approximate Cost (V4 Pro) |
|-------------|----------------------|------------------------|---------------------------|
| Long-term | 200,000-400,000 | 15,000-25,000 | $2.50-$5.00 |
| Mid-term | 120,000-250,000 | 10,000-18,000 | $1.50-$3.00 |
| Short-term | 60,000-150,000 | 5,000-10,000 | $0.75-$1.50 |
| Quick Overview | 40,000-80,000 | 3,000-6,000 | $0.40-$0.80 |

Costs are approximate and depend on data availability, company complexity, and API call requirements.

---

## Validation & Quality Assurance

### Per-Stage Validation Gates

Before a stage is marked complete, the agent must pass these gates:

| Stage | Validation Gate | Pass Condition |
|-------|----------------|----------------|
| Stage 1 | Financial data completeness | At least 3 years of revenue, operating income, FCF, and total debt are populated from a Tier 1 source |
| Stage 1 | Metric consistency check | Revenue growth rate derived from income statement matches segment-level revenue growth rates within ±5% |
| Stage 2 | Insider transaction recency | At least one Form 4 filing from the last 90 days has been reviewed |
| Stage 3 | Peer universe completeness | At least 3 peer companies identified with GICS alignment justification |
| Stage 4 | Macro indicators recency | PMI, Fed funds rate, 10-year yield, and CPI all retrieved within their Max Freshness windows |
| Stage 5 | Key jurisdiction coverage | Countries representing >80% of revenue have been assessed for regulatory/geopolitical risk |
| Stage 6 | Valuation method multiplicity | At least 2 independent valuation methods applied; DCF sensitivity table produced |
| Stage 7 | Red flag screen execution | Beneish M-Score, Altman Z-Score, and at least 5 of the 9 forensic checks completed |
| Stage 8 | Alternative data composite | At least 3 of the 6 alternative data dimensions have non-null readings |
| Stage 9 | Methodology attribution | Every major claim traces to at least one specific trader framework |

### Backtesting Methodology

To validate the skill's analytical quality, run retrospective analysis against known outcomes:

**Test Universe:**
- 20 stocks across 5 sectors (4 per sector) representing different Lynch categories
- Time period: Analysis date set to 12 months ago; compare recommendations against actual 12-month returns
- Include: 5 winners (>20% return), 5 losers (<-20% return), 10 range-bound

**Success Metrics:**

| Metric | Target | Measurement |
|--------|--------|------------|
| **Directional Accuracy** | >65% | % of Buy/Hold/Sell recommendations that matched the direction of actual 12-month return |
| **Rating Discrimination** | Strong Buy > Buy > Hold in average returns | Mean return for Strong Buy stocks > mean return for Buy > mean return for Hold |
| **Price Target Accuracy** | Within ±25% for 50% of targets | % of 12-month price targets that bracket the actual 12-month price within ±25% |
| **Conviction Calibration** | High conviction ratings outperform Low | Mean absolute return of High confidence recommendations > Low confidence |
| **Risk/Reward Accuracy** | >60% of trades with R/R >2:1 were profitable | Profitability rate of high-conviction setups |
| **False Positive Rate** | <20% | % of Strong Buy/Buy ratings that resulted in >15% loss |

**Calibration Check:**
After backtesting, if any metric falls below target, identify the specific stage or framework causing the miss and recalibrate before Phase 2 completion.

### Hallucination Detection & Fact Verification

Financial analysis is high-stakes — fabricated numbers can mislead. The following checks are mandatory:

**Pre-Publication Fact Verification:**
1. **Number Cross-Reference**: Every financial figure in the report must appear in at least one Tier 1 or Tier 2 source. If a number is computed (e.g., CAGR, DCF value), the source inputs must be cited.
2. **Quote Integrity**: If the report quotes management ("CEO said..."), the exact quote must be traceable to an earnings call transcript or investor presentation. Paraphrased statements must be tagged `[Paraphrased — see source for exact wording]`.
3. **Date Consistency**: All dates (filing dates, event dates, data retrieval dates) must be internally consistent. A report cannot cite "Q4 2025 earnings" if the fiscal year ends in June 2025 — check the company's fiscal calendar.
4. **Unit Consistency**: Verify that billions/millions/thousands are used consistently. "Revenue of $50" vs. "$50 billion" — the agent must state units on every figure.

**Self-Verification Protocol (Post-Write):**
After generating the report, the agent must run a second pass:
1. Select 5 random numeric claims from the report
2. Trace each back to its source
3. If any claim cannot be verified within 30 seconds, remove it and flag the gap
4. If 2+ verified claims contain errors, restart the affected stage analysis

**Hallucination Prevention Rules:**
- Never invent a financial figure when a source is unavailable — state "Data not available" instead
- Never guess a management comment or insider sentiment — cite the source or omit
- Never fabricate peer comparison data — if a peer's financials are unavailable, reduce the peer set
- When an LLM-generated interpretation is uncertain, prefix with "Our analysis suggests..." and flag as `[Interpretation — not directly stated by company]`

### Review Gate

Before delivering a report to the user, the agent must complete this checklist:

```
Pre-Delivery Checklist:
□ All Tier 1 data sources verified as within Max Freshness
□ No [STALE] flags on critical metrics
□ At least 1 framework divergence acknowledged (if applicable)
□ Kill switch defined for each report type delivered
□ Methodology attribution present for all major conclusions
□ Fact/Interpretation/Speculation tags applied to all source citations
□ 5 random fact checks passed (hallucination protocol)
□ Cost budget not exceeded by >20% without user notification
```

If any item is unchecked, the report must carry a visible warning: "⚠ INCOMPLETE ANALYSIS — [reason]"

---

## Quality Standards

### Analytical Quality
- Depth comparable to professional sell-side initiation of coverage (30-80 pages equivalent)
- Every conclusion traceable to a specific trader's methodology
- Explicit statement of what is priced in vs. what is the differentiated view
- Quantified risk with probability × impact
- Multi-method valuation with cross-checks and sensitivity analysis

### Intellectual Rigor
- Second-level thinking applied (Marks): never just "good company, buy"
- Variant perception stated (how does our view differ from consensus?)
- Reflexivity check (Soros): are self-reinforcing loops present?
- Inversion applied (Munger): how could this thesis be wrong?
- Acknowledgment of uncertainty and confidence calibration

### Data Integrity
- All data sources cited with dates
- Clear separation: facts → interpretation → speculation
- Acknowledge data limitations and staleness
- Cross-reference alternative data with reported financials
- Flag any potential survivorship bias or selection bias

### Actionability
- Specific price targets with derivation methodology
- Clear entry/exit criteria (not vague "accumulate on dips")
- Position sizing guidance based on conviction level
- Monitoring triggers: what would change the thesis?
- Timeline: when should the thesis play out?

---

## Glossary & Sector Classification

### Acronym Glossary

| Acronym | Definition |
|---------|------------|
| **AFFO** | Adjusted Funds From Operations |
| **ARR** | Annual Recurring Revenue |
| **CAPM** | Capital Asset Pricing Model |
| **CET1** | Common Equity Tier 1 (capital ratio) |
| **COGS** | Cost of Goods Sold |
| **CAGR** | Compound Annual Growth Rate |
| **DCF** | Discounted Cash Flow |
| **DSO** | Days Sales Outstanding |
| **DIO** | Days Inventory Outstanding |
| **DPO** | Days Payable Outstanding |
| **EBIT** | Earnings Before Interest and Taxes |
| **EBITDA** | Earnings Before Interest, Taxes, Depreciation, and Amortization |
| **EPS** | Earnings Per Share |
| **EV** | Enterprise Value |
| **EVA** | Economic Value Added |
| **FCF** | Free Cash Flow |
| **FFO** | Funds From Operations |
| **FTA** | Free Trade Agreement |
| **GICS** | Global Industry Classification Standard |
| **GMV** | Gross Merchandise Value |
| **GPR** | Geopolitical Risk (Caldara-Iacoviello index) |
| **HHI** | Herfindahl-Hirschman Index (concentration measure) |
| **IRA** | Inflation Reduction Act |
| **ISM** | Institute for Supply Management |
| **LBO** | Leveraged Buyout |
| **LTV** | Customer Lifetime Value |
| **CAC** | Customer Acquisition Cost |
| **MD&A** | Management Discussion & Analysis |
| **M&A** | Mergers and Acquisitions |
| **NAV** | Net Asset Value |
| **NDR** | Net Dollar Retention |
| **NFA** | Net Fixed Assets |
| **NIM** | Net Interest Margin |
| **NPS** | Net Promoter Score |
| **NTM** | Next Twelve Months |
| **NWC** | Net Working Capital |
| **OBV** | On-Balance Volume |
| **OCF** | Operating Cash Flow |
| **ODD** | Operational Due Diligence |
| **OTM** | Out of the Money (options) |
| **PEG** | Price/Earnings to Growth ratio |
| **PMI** | Purchasing Managers' Index |
| **R&D** | Research and Development |
| **RCEP** | Regional Comprehensive Economic Partnership |
| **ROA** | Return on Assets |
| **ROE** | Return on Equity |
| **ROIC** | Return on Invested Capital |
| **ROTCE** | Return on Tangible Common Equity |
| **RPO** | Remaining Performance Obligations |
| **rNPV** | Risk-Adjusted Net Present Value |
| **RSI** | Relative Strength Index |
| **SBC** | Stock-Based Compensation |
| **SOTP** | Sum-of-the-Parts valuation |
| **TAM/SAM/SOM** | Total / Serviceable / Serviceable Obtainable Market |
| **TIPS** | Treasury Inflation-Protected Securities |
| **USTR** | United States Trade Representative |
| **VIX** | CBOE Volatility Index |
| **WACC** | Weighted Average Cost of Capital |
| **WTO** | World Trade Organization |

### Sector Classification Logic

The agent determines the company's sector using the following priority:

1. **GICS Sector** (primary): Retrieve from financial data source (Yahoo Finance, FMP API, or Bloomberg). GICS 11-sector classification:
   - Energy, Materials, Industrials, Consumer Discretionary, Consumer Staples, Health Care, Financials, Information Technology, Communication Services, Utilities, Real Estate

2. **Business Description Override**: If GICS classification is ambiguous (e.g., Amazon: Consumer Discretionary vs. Technology), use the company's own business description and revenue segmentation to determine dominant sector

3. **Sector-Specific Metric Selection**: Once sector is identified, apply the corresponding metrics from the Sector-Specific Metrics table in Stage 1. If a company spans multiple GICS sectors, apply metrics from the sector representing the largest revenue share

4. **Sector Classification Confidence**: Flag the classification with:
   - **High Confidence**: Single GICS sector with >80% revenue from that sector
   - **Medium Confidence**: Primary sector is 50-80% of revenue; secondary sector metrics may be relevant
   - **Low Confidence**: No dominant sector (<50% revenue); apply multi-sector analysis

### Report Type Selection Logic

When the user does not explicitly request a specific report type, the agent applies this decision tree:

```
User request contains...
├── "long-term" / "invest" / "hold for years" / "intrinsic value"
│   → Generate Long-term Report (1-3+ year horizon)
├── "trade" / "swing" / "next quarter" / "earnings play" / "catalyst"
│   → Generate Mid-term Report (1-12 month horizon)
├── "options" / "day trade" / "this week" / "momentum" / "setup"
│   → Generate Short-term Report (days to weeks horizon)
├── "quick" / "overview" / "snapshot" / "summary"
│   → Generate Quick Overview (Mid-term format, reduced stages)
└── Default (no horizon specified)
    → Generate Mid-term Report + ask: "Would you also like a long-term intrinsic value analysis?"
```

If the user asks a question about a stock (e.g., "What do you think of AAPL?"), default to the Mid-term report but offer to produce the Long-term version.

---

## Development Path

### Phase 0: Research & Design (Current)
- [x] Define requirements
- [ ] Research and document trader methodologies (detailed frameworks)
- [ ] Design unified analysis model
- [ ] Define skill architecture (stages, data flow, tools)

### Phase 1: Core Skill Build
- [ ] Implement Stage 1-3 (Company, Leadership, Industry)
- [ ] Implement Stage 4-5 (Macro, Geopolitics)
- [ ] Implement Stage 6-7 (Valuation, Risk)
- [ ] Implement Stage 8 (Alternative Data)
- [ ] Implement Stage 9 (Report Generation)

### Phase 2: Refinement
- [ ] Backtest against historical analyst reports
- [ ] Calibrate conviction scoring
- [ ] Add sector-specific metric modules
- [ ] Optimize for different market conditions

### Phase 3: Enhancement
- [ ] Real-time data integration
- [ ] Multi-stock comparison mode
- [ ] Portfolio-level analysis
- [ ] Automated monitoring and alert triggers
