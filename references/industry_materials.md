# Industry Deep-Dive: Materials & Mining

## Sector Context

Materials (GICS 15) encompasses chemicals, metals & mining, construction materials, containers & packaging, and paper & forest products. Mining companies are valued on reserves and cost position, NOT earnings multiples. Commodity price sensitivity dominates short-term returns.

## Sector-Specific KPIs

### Mining (Gold, Copper, Lithium, Iron Ore)

| Metric | Definition | Good | Average | Poor |
|--------|-----------|------|---------|------|
| All-In Sustaining Cost (AISC) | Total cost per unit produced (includes sustaining capex) | Bottom quartile | 2nd quartile | Top quartile |
| Reserve Life | Proven+Probable reserves / annual production | >15 years | 8-15 years | <8 years |
| Reserve Replacement Ratio | Reserves added / reserves depleted | >1.2x | 0.8-1.2x | <0.8x |
| Grade Trend | Ore grade trajectory (declining grades = rising costs) | Stable/improving | Declining <3%/yr | Declining >5%/yr |
| Production Growth | Year-over-year production increase | >5% | 0-5% | Declining |
| Net Debt / EBITDA | Leverage at current commodity prices | <1.0x | 1.0-2.5x | >2.5x |
| FCF Yield (at spot) | FCF / Market Cap at current commodity prices | >8% | 4-8% | <4% |
| Jurisdiction Risk | Political/regulatory risk of mine locations | Tier 1 (Aus/Can/US) | Tier 2 (Chile/Peru) | Tier 3 (DRC/Russia) |

### Specialty Chemicals

| Metric | Definition | Good | Average | Poor |
|--------|-----------|------|---------|------|
| Gross Margin | Revenue - COGS / Revenue | >40% | 25-40% | <25% |
| Volume vs Pricing Growth | Decomposition of revenue growth | Both positive | Price-driven only | Volume declining |
| R&D Intensity | R&D / Revenue | >4% | 2-4% | <2% |
| Customer Concentration | Top 10 customers as % revenue | <30% | 30-50% | >50% |
| Working Capital / Revenue | Inventory + AR - AP / Revenue | <15% | 15-25% | >25% |
| Specialty Mix | % revenue from differentiated products | >60% | 40-60% | <40% |

### Construction Materials (Aggregates, Cement)

| Metric | Definition | Good | Average | Poor |
|--------|-----------|------|---------|------|
| EBITDA Margin | Operating leverage from local monopolies | >30% | 20-30% | <20% |
| Price Increases | Annual pricing power (inflation+) | CPI + 2-3% | CPI + 0-2% | Below CPI |
| Reserve Position | Permitted reserves in high-growth markets | >20 years | 10-20 years | <10 years |
| Vertical Integration | % of revenue from downstream (ready-mix, asphalt) | >30% | 15-30% | <15% |

## Valuation Methodology

### Primary: Net Asset Value (NAV)

For mining companies, DCF of individual mine cash flows is the standard:

1. **Project-level DCF**: Each mine/project modeled separately:
   - Production profile (ramp-up, steady-state, decline)
   - Cost curve position (AISC per unit)
   - Commodity price assumptions (spot, consensus, cycle-normalized)
   - Mine life (reserves / annual production)
   - Country risk discount
2. **Sum-of-Parts NAV**: Aggregate project DCFs + exploration upside + corporate costs
3. **P/NAV multiple**: Market cap / NAV (1.0x = fair value at assumed prices)
   - Premium (>1.2x): High-quality operator, growth pipeline, discovery optionality
   - Discount (<0.8x): Jurisdiction risk, management issues, or bear commodity view

### Secondary: EV/EBITDA (Cycle-Adjusted)

- Use mid-cycle commodity prices, NOT current spot
- Compare at same point in commodity cycle
- Miners: 4-6x mid-cycle EBITDA is fair; <3x is deep value
- Chemicals: 8-12x depending on specialty mix

### Tertiary: Price/FCF at Multiple Commodity Scenarios

| Scenario | Commodity Price | FCF Estimate | Implied Value |
|----------|----------------|--------------|---------------|
| Bear | -30% from spot | $X | $X/share |
| Base | Consensus/mid-cycle | $X | $X/share |
| Bull | +30% from spot | $X | $X/share |

## Commodity Cycle Framework

### Cycle Position Assessment

| Indicator | Early Cycle | Mid Cycle | Late Cycle | Downturn |
|-----------|-------------|-----------|------------|----------|
| Commodity price | Rising from lows | Above mid-cycle | Near/above historical highs | Falling toward cost support |
| Industry capex | Low, cuts recent | Expanding cautiously | Peak spending, mega-projects | Cuts beginning |
| Inventory levels | Depleted | Building | Elevated | Liquidating |
| Cost inflation | Low | Moderate | High (labor, equipment) | Moderating |
| M&A activity | Distressed sales | Selective | Peak premiums | Frozen |
| Sector sentiment | Neglected | Neutral | Euphoric | Capitulation |

### Investment Strategy by Cycle Position

- **Early cycle**: Buy low-cost producers with clean balance sheets. High leverage to recovery.
- **Mid cycle**: Own quality operators with growth projects. Start trimming high-cost juniors.
- **Late cycle**: Take profits on cyclicals. Only hold lowest-cost quartile producers.
- **Downturn**: Avoid. Only re-enter when industry capex cuts >20% and spot approaches marginal cost of production.

## Critical Risk Factors

1. **Commodity price collapse**: Single largest risk. Model at -30% and -50% spot.
2. **Jurisdiction risk**: Nationalization, tax hikes, permit revocation (e.g., Chile lithium royalties, DRC mining code changes)
3. **Reserve depletion**: Declining grade = rising costs = margin compression without new discoveries
4. **Capex blowouts**: Mine construction 30-50% over budget is common
5. **Water/energy access**: Mining is water/energy-intensive; scarcity = cost or closure risk
6. **ESG/community opposition**: Social license to operate; tailings dam risk (Brumadinho precedent)
7. **Chinese demand**: 50%+ of global metals demand; any slowdown cascades

## Kill Switches

- AISC rises above commodity price (cash-burn territory)
- Reserve life falls below 5 years with no replacement pipeline
- Jurisdiction risk escalates (royalty increase >5%, nationalization rhetoric)
- Net Debt/EBITDA exceeds 3.0x at current prices
- Commodity enters sustained downturn with capex cycle still expanding
- Community opposition halts permits for growth projects

## Data Sources (Free)

- yfinance: Price, financial statements, basic segment data
- SEC EDGAR: 10-K (US-listed miners), reserve statements
- FRED: Commodity price indices (gold, copper, aluminum)
- USGS: Annual mineral commodity summaries
- Company IR: Production reports, reserve/resource estimates, AISC disclosure
- World Gold Council: Gold supply/demand data
- LME: Base metal price benchmarks (via web search)
