# Data Centers & Cloud Infrastructure Deep-Dive

## Industry Structure

### Value Chain Segments
| Segment | Description | Key Players | Moat Source |
|---------|------------|-------------|-------------|
| **Hyperscalers** | Self-built mega-campuses for cloud/AI | AMZN (AWS), MSFT (Azure), GOOG (GCP), META | Scale, capital access, demand captivity |
| **Wholesale Colocation** | Large-scale leased capacity (1+ MW) | EQIX, DLR, CyrusOne, QTS (Blackstone) | Land + power + permits, long-term leases |
| **Retail Colocation** | Smaller deployments, shared facilities | EQIX, CoreSite (AMTI), Cyxtera | Interconnection density, ecosystem |
| **Interconnection** | Cross-connects, IX peering, fabric | EQIX (Fabric), Megaport, PCCW | Network effects, peering hub status |
| **Edge** | Distributed micro-DCs for latency-sensitive apps | EdgeConneX, Vapor IO, Fastly | Proximity to end users, fiber access |
| **Fiber/Network** | Dark fiber, lit services, long-haul | Zayo, Lumen, Crown Castle (fiber) | Right-of-way, route density |
| **Power/Cooling** | Electrical infrastructure, cooling systems | Vertiv, Schneider, Eaton | Thermal expertise, GPU-era density |

### AI/GPU Cluster Demand Dynamics
The AI training and inference buildout is the defining demand driver for 2024-2030+:
- **Training clusters**: 50-100+ MW single deployments, 40-80 kW/rack density (vs traditional 8-12 kW)
- **Inference at scale**: Lower density per rack (15-30 kW) but massive aggregate demand
- **Liquid cooling requirement**: Air cooling hits physical limits above ~40 kW/rack. Direct-to-chip and immersion cooling are table stakes for AI-ready capacity.
- **GPU refresh cycles**: Each new GPU generation (H100 → B200 → next) requires electrical and cooling retrofits
- **Cluster networking**: AI pods require high-bandwidth, low-latency InfiniBand/RoCE fabric — specialized DC design

### Power as Competitive Moat
Power availability is the primary constraint on data center supply:
1. **Grid capacity**: Many metros (N. Virginia, Dublin, Singapore, Amsterdam) face utility moratoriums
2. **Substations & transmission**: 3-5 year lead time for new high-voltage infrastructure
3. **On-site generation**: Gas turbines, fuel cells, small modular reactors (SMRs) as grid alternatives
4. **Renewable PPAs**: Hyperscalers require 24/7 carbon-free energy (CFE) matching
5. **Water access**: Evaporative cooling requires significant water rights (drought-prone regions = risk)

### Land & Permitting Barriers by Geography
| Market | Power Availability | Permitting Timeline | Competitive Dynamics |
|--------|-------------------|--------------------|-----------------------|
| **N. Virginia (NOVA)** | Constrained (Dominion backlog) | 18-36 months | Most competitive; premium pricing |
| **Dallas-Fort Worth** | Available (ERCOT) | 12-18 months | Emerging AI hub, power-rich |
| **Phoenix/Mesa** | Available (APS/SRP) | 12-24 months | Strong growth, water concerns |
| **Singapore** | Moratorium (easing) | 36+ months | Regulated, premium rents |
| **Dublin** | Moratorium | 24-48 months | Power grid constraints |
| **Tokyo/Osaka** | Moderate | 24-36 months | Earthquake risk, premium land |

## Key Data Center Metrics

### Core Operating Metrics

| Metric | Formula/Definition | Bullish Threshold | Bearish Threshold |
|--------|-------------------|-------------------|-------------------|
| **MW Under Management** | Total critical IT load capacity | >15% YoY growth | <5% growth (land/power constrained) |
| **Utilization Rate** | Occupied MW / Total Available MW | >85% (pricing power) | <70% (oversupply) |
| **PUE (Power Usage Effectiveness)** | Total facility power / IT load power | <1.3 (efficient) | >1.6 (inefficient, legacy) |
| **Revenue per MW** | Annualized revenue / Installed MW | >$2.5M/MW (premium) | <$1.5M/MW (commodity) |
| **WALE (Weighted Avg Lease Expiry)** | Weighted avg remaining lease term | >5 years | <3 years (re-leasing risk) |
| **Customer Concentration** | Revenue from top customer | <25% (diversified) | >50% (single-tenant risk) |
| **Interconnection Revenue %** | Cross-connect + fabric revenue / Total | >20% (high-value, sticky) | <5% (commodity wholesale) |
| **Same-Store NOI Growth** | YoY growth in existing portfolio | >5% | <0% (pricing pressure) |

### Development & Growth Metrics

| Metric | Formula/Definition | Bullish Threshold | Bearish Threshold |
|--------|-------------------|-------------------|-------------------|
| **Development Pipeline / Existing** | MW under construction / Operational MW | 30-60% (healthy growth) | >100% (execution risk) or <10% (no growth) |
| **Pre-Leasing %** | Leased MW / Under-construction MW | >60% (de-risked) | <30% (speculative build) |
| **Construction Cost ($/MW)** | Total build cost per critical MW | <$8M/MW (efficient) | >$12M/MW (cost inflation) |
| **Time to Delivery** | Ground-break to revenue-generating | <18 months | >30 months (permitting/power delays) |
| **Stabilized Yield on Cost** | Stabilized NOI / Total development cost | >8% | <5% (capital misallocation) |
| **Land Bank (Years of Supply)** | Owned/controlled MW capacity / Annual absorption | 5-10 years | <2 years (growth ceiling) or >15 years (idle capital) |

### Financial Metrics (REIT-Specific)

| Metric | Formula/Definition | Bullish Threshold | Bearish Threshold |
|--------|-------------------|-------------------|-------------------|
| **AFFO per Share Growth** | Adjusted Funds From Operations growth | >8% YoY | <3% (REIT underperformer) |
| **AFFO Payout Ratio** | Dividends / AFFO | <75% (retained for growth) | >90% (no self-funding ability) |
| **Net Debt / EBITDA** | Total debt less cash / EBITDA | <5.5x | >7.0x (over-leveraged) |
| **Fixed Charge Coverage** | EBITDA / (Interest + Preferred Divs) | >3.0x | <2.0x (financial stress) |
| **Debt Maturity Profile** | Weighted avg debt maturity | >5 years | <3 years (refinancing risk) |

### AI-Specific Capacity Metrics

| Metric | Formula/Definition | Bullish Threshold | Bearish Threshold |
|--------|-------------------|-------------------|-------------------|
| **High-Density Capacity %** | MW rated >30 kW/rack / Total MW | >30% of new deliveries | <10% (not AI-ready) |
| **Liquid Cooling Capability** | MW with DLC/immersion ready | >20% and growing | 0% (competitive disadvantage) |
| **GPU-Ready Power Density** | Max supported kW per rack | >60 kW/rack | <20 kW/rack (legacy only) |
| **Rear-Door/CDU Retrofit Pipeline** | MW being upgraded for liquid cooling | Active retrofit program | No upgrade path for existing fleet |

## Supply/Demand Dynamics

### Hyperscaler Capacity Planning
- **Capex guidance as leading indicator**: AMZN, MSFT, GOOG, META capex guides signal 12-24 month demand
- **Aggregate hyperscaler capex**: >$200B/year = strong demand; track YoY growth rate
- **Cloud revenue growth → DC demand**: Every $1B in incremental cloud revenue requires ~30-50 MW of DC capacity
- **AI training FLOP demand**: Doubling every 6-10 months, directly translating to MW demand

### Pre-Leasing & Absorption Trends
- **Pre-leasing velocity**: Track quarters to fill a new build. Accelerating = pricing power.
- **Absorption rate**: Net MW absorbed per quarter in major markets.
- **Vacancy rate by market**: Below 5% = extreme tightness. Above 15% = oversupply.
- **Rental rate trends**: $/kW/month increasing = demand exceeds supply. Mark-to-market uplift on lease expirations.

### Key Demand Drivers (Ranked by Magnitude)
1. **AI training & inference** (largest incremental driver 2024+)
2. **Public cloud migration** (enterprise workloads moving to hyperscalers)
3. **SaaS/digital transformation** (application layer growth)
4. **Content delivery** (streaming, gaming, social media)
5. **Edge computing** (autonomous vehicles, IoT, AR/VR)
6. **Crypto mining** (cyclical, opportunistic power buyer)

## Competitive Moat Assessment

| Moat Type | Signal | Measurement |
|-----------|--------|-------------|
| **Power Access** | Secured utility capacity, substation agreements | MW of contracted power > current usage |
| **Land Position** | Owned campuses in constrained metros | Developable MW on owned land |
| **Interconnection Density** | Network-rich facilities, peering exchanges | # of networks, cross-connects per facility |
| **Customer Relationships** | Multi-year hyperscaler MSAs, expansion options | WALE, renewal rate, expansion pipeline |
| **Operational Expertise** | Industry-leading PUE, uptime SLA track record | PUE <1.2, 99.999%+ uptime |
| **Capital Access** | Investment-grade rating, low cost of debt | BBB+ or better, spread to benchmark |
| **Permitting Relationships** | Track record of approvals in constrained markets | Time to permit vs market average |

## Valuation Framework

### Key Multiples
| Multiple | Premium Range | Fair Value | Discount Range |
|----------|--------------|------------|----------------|
| **EV/EBITDA** | 25-35x (scarcity + AI growth) | 18-25x | <15x (commodity, high leverage) |
| **P/AFFO** | 30-40x (growth REITs) | 22-30x | <18x |
| **EV/MW (installed)** | >$15M/MW (premium ecosystem) | $8-15M/MW | <$6M/MW (wholesale commodity) |
| **Price/NAV** | >1.3x (growth premium) | 1.0-1.3x | <0.9x (distressed or over-leveraged) |

### Valuation Considerations
- **Development value**: NAV should include pipeline at risk-adjusted stabilized yield, not just operating assets
- **Power scarcity premium**: Markets with grid constraints justify higher EV/MW (supply cannot respond quickly)
- **AI demand optionality**: Facilities with high-density capability command valuation premium even if not yet leased
- **Interest rate sensitivity**: DC REITs trade inversely to long-term rates; 100bp rate move = 5-10% valuation impact

## Red Flags Specific to Data Centers

- **Speculative development >50% of pipeline with <30% pre-leased**: Oversupply risk if demand cools
- **Single hyperscaler >40% of revenue**: Customer concentration + renegotiation leverage at renewal
- **PUE >1.5 with no retrofit plan**: Legacy fleet becoming uncompetitive, higher opex per MW
- **Land bank in unconstrained markets only**: No scarcity premium, race-to-bottom pricing
- **Rising construction costs without proportional rent increases**: Margin compression on new builds
- **Short WALE (<3 years) in a rising supply market**: Re-leasing risk at lower rates
- **No liquid cooling capability or roadmap**: Will lose AI workloads to competitors
- **Debt maturity wall within 24 months in rising rate environment**: Refinancing at higher cost
- **Water-intensive cooling in drought-prone regions**: Regulatory/operational risk (Arizona, parts of Texas)
