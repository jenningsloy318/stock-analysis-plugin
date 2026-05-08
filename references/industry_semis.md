# Semiconductors & Hardware Deep-Dive

## Industry Structure

### Value Chain Segments
| Segment | Description | Key Players | Cycle Sensitivity |
|---------|------------|-------------|-------------------|
| **EDA/IP** | Design software & IP blocks | SNPS, CDNS, ARM | Low (subscription/royalty) |
| **Fabless** | Chip design, outsourced manufacturing | NVDA, AMD, QCOM, AVGO, MRVL | Moderate (end-demand driven) |
| **Foundry** | Contract manufacturing | TSM, Samsung, IFS (INTC) | High (capacity utilization) |
| **IDM** | Design + manufacturing | INTC, Samsung, STM, TXN | High (fixed-cost leverage) |
| **Equipment** | Fab tools & metrology | ASML, AMAT, LRCX, KLAC | Very High (WFE cycle) |
| **OSAT** | Packaging & test | ASE, Amkor, JCET | High (unit volume) |

### Technology Node Exposure
Identify which process nodes the company or its foundry partners depend on:
- **Leading edge (<5nm)**: AI/GPU, smartphone AP, HPC. High growth, high capex, concentrated supply (TSMC dominant).
- **Mature (28nm-90nm)**: Auto, industrial, analog, MCU. Stable demand, overcapacity risk.
- **Legacy (>90nm)**: Power, discrete, sensors. Commodity-like, price competition.

### Capex Intensity & Cyclicality
Semiconductor capex as % of revenue is the key cycle indicator:
| Phase | WFE Capex YoY | Utilization | Inventory Days | Signal |
|-------|--------------|-------------|----------------|--------|
| Early Upturn | +10-20% | 75-85% | Below avg | Bullish — capacity tightens |
| Mid Cycle | +20-30% | 85-95% | Normal | Neutral — balanced |
| Late Cycle | +30%+ | >95% | Rising | Caution — over-ordering risk |
| Downturn | -10 to -30% | <75% | Above avg | Bearish — correction phase |

## Key Semiconductor Metrics

| Metric | Formula/Definition | Bullish Threshold | Bearish Threshold |
|--------|-------------------|-------------------|-------------------|
| **Revenue Growth** | YoY revenue change | >15% | <5% or negative |
| **Gross Margin** | (Revenue - COGS) / Revenue | >55% (fabless >60%) | <45% |
| **Op Margin** | Operating Income / Revenue | >30% | <20% |
| **Inventory Days** | Inventory / (COGS/365) | <90 days (declining) | >120 days (rising) |
| **Capex / Revenue** | Capital Expenditure / Revenue | 8-15% (sustaining) | >25% (overbuilding) or <5% (underinvesting) |
| **FCF Yield** | FCF / Market Cap | >5% (value entry) | <2% (peak cycle) |
| **R&D / Revenue** | R&D Expense / Revenue | >15% (innovation lead) | <8% (underinvesting in future nodes) |

### Segment-Specific KPIs

**Foundry:**
| Metric | Bullish | Bearish |
|--------|---------|---------|
| Utilization Rate | >90% | <75% |
| ASP Trend | Rising (node migration) | Declining (price competition) |
| Customer Concentration | Diversified top-5 | >60% from single customer |
| CapEx / Depreciation | >1.5x (capacity expansion) | <0.8x (underinvesting) |

**Equipment:**
| Metric | Bullish | Bearish |
|--------|---------|---------|
| Book-to-Bill | >1.15 | <0.90 |
| Backlog Coverage | >3 quarters | <1 quarter |
| Service Revenue % | >25% (recurring) | <15% (lumpy) |
| China Exposure | <25% of revenue | >40% (export control risk) |

**Fabless:**
| Metric | Bullish | Bearish |
|--------|---------|---------|
| Design Win Pipeline | 3+ ramping products | <2 new products |
| ASP Trend (per product gen) | Increasing | Flat or declining |
| Customer Diversification | >3 major customers | >50% from single customer |
| Time to Market | Leading competitor by 6+ months | Trailing competitor |

### Memory-Specific (if applicable)
| Metric | Bullish | Bearish |
|--------|---------|---------|
| Bit Growth | >15% YoY | <5% YoY |
| ASP/GB | Rising QoQ | Declining QoQ |
| Inventory at Customers | <4 weeks | >8 weeks |
| Capex Cut Announcements | Major producers cutting | All adding capacity |

## Competitive Moat in Semiconductors

| Moat Type | Signal | Measurement |
|-----------|--------|-------------|
| **Architecture/Design** | Proprietary ISA, GPU CUDA lock-in, FPGA toolchain | Developer ecosystem size, software stack depth |
| **Process Technology** | Leading node access, proprietary packaging | Transistor density, power efficiency vs peers |
| **Manufacturing Scale** | Fab scale, yield rates, equipment access | Cost per transistor, die per wafer, yield % |
| **IP Portfolio** | Patent thicket, cross-licensing, standard-essential patents | Patent count × citation quality, royalty revenue |
| **Switching Costs** | Design-in cycle (12-24 months), qualification requirements, socket exclusivity | Design win retention rate |
| **Customer Relationships** | Long-term agreements, co-development, capacity reservations | Revenue visibility >2 years |

## Key Risks

### Structural
- **Moore's Law slowing**: Cost per transistor no longer declining → rising design costs
- **Geopolitical fragmentation**: US-China export controls bifurcating supply chains
- **TSMC concentration**: >90% of leading-edge capacity at one company and one island
- **Talent scarcity**: Global shortage of semiconductor engineers

### Cyclical
- **Double-ordering**: Customers order from multiple foundries during shortages, then cancel
- **Capacity overshoot**: All producers adding capacity simultaneously → glut
- **Inventory correction**: 2-4 quarter destocking cycles after over-ordering

### Technology
- **AI disruption**: GPU → custom ASIC → in-house silicon at hyperscalers
- **Architecture shifts**: x86 → ARM → RISC-V
- **Chiplet/advanced packaging**: Shifts value from node shrinks to integration

## Valuation Framework

### Key Multiples
- **P/E (NTM)**: 15-25x range typical. Above 25x = premium growth. Below 12x = cyclical trough.
- **EV/EBITDA**: 8-15x typical. Equipment trades at lower multiples. Fabless at premium.
- **P/B**: Relevant for memory and equipment at cycle troughs. Buy signal when P/B < 1.0 at trough.
- **P/S**: Only use for early-stage fabless with depressed margins. Apply 3-8x range.

### Cycle-Aware Valuation
- **Peak earnings**: Use mid-cycle EPS, not trailing peak. Trailing P/E looks cheap at cycle peaks.
- **Trough earnings**: Asset-heavy semis should be bought at high P/E (depressed earnings), sold at low P/E.
- **Book value**: For memory and equipment, tangible book value provides a floor at cycle troughs.

### The Memory Cycle Playbook
1. Monitor: DRAM/NAND spot prices (weekly), producer capex announcements, inventory days
2. Buy signal: All producers cutting capex + prices below cash cost + P/B < 1.0
3. Sell signal: All producers adding capacity + prices rising + P/B > 2.5

## Red Flags Specific to Semis

- **Channel inventory building while reported revenue growing**: Demand-pull vs channel-stuffing
- **Customer concentration >50%**: Apple, Nvidia, or hyperscaler single-customer risk
- **US entity list / export control exposure**: Any revenue from Huawei, SMIC, or restricted entities
- **Process node transition delays**: 2+ quarter slip on next node = competitive gap
- **Insider selling at cycle peaks**: Cluster selling by fabless CEOs near revenue peaks
- **Goodwill-heavy balance sheet from acquisitions**: Check goodwill/total assets >30%
