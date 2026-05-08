# Fintech & Payments Deep-Dive

## Industry Structure

### Value Chain Segments
| Segment | Description | Key Players | Moat Source |
|---------|------------|-------------|-------------|
| **Card Networks** | Transaction routing, settlement rails | V, MA, AXP, DFS | Two-sided network effects, ubiquity |
| **Payment Processors** | Gateway, authorization, fraud | PYPL, ADYEN, FIS, FISV, GPN | Scale economics, merchant lock-in |
| **Acquirers/ISOs** | Merchant onboarding, POS | SQ (Block), TOST, CLVR | Distribution, software bundling |
| **Issuers/Neobanks** | Card issuance, deposit accounts | SoFi, Chime, Nu Holdings, Revolut | CAC efficiency, cross-sell |
| **BNPL** | Point-of-sale credit, installments | AFRM, Klarna, Afterpay (Block) | Merchant integration, consumer habit |
| **Crypto Exchanges** | Digital asset trading, custody | COIN, Binance, Kraken | Liquidity depth, regulatory license |
| **Embedded Finance** | BaaS, API-based financial products | Marqeta, Galileo (SoFi), Unit | Platform integrations, API stickiness |
| **Infrastructure/Plumbing** | Core banking, ledger, compliance | Plaid, MX, Stripe, Adyen | Developer adoption, data aggregation |

### Network Effects & Platform Dynamics
- **Two-sided networks (card schemes)**: Merchant acceptance drives cardholder adoption and vice versa. Once critical mass is reached, switching costs become insurmountable.
- **Data network effects**: More transactions → better fraud models → lower losses → lower pricing → more merchants. Virtuous cycle.
- **Platform stacking**: Payments → lending → deposits → insurance → investing. Each product lowers blended CAC.
- **Embedded finance multiplier**: Non-financial platforms (Shopify, Uber) embedding payments/lending create new distribution that bypasses traditional channels.

## Key Fintech Metrics

### Payments (Networks, Processors, Acquirers)

| Metric | Formula/Definition | Bullish Threshold | Bearish Threshold |
|--------|-------------------|-------------------|-------------------|
| **TPV (Total Payment Volume)** | Gross dollar volume processed | >20% YoY growth | <10% or decelerating 3+ quarters |
| **Take Rate** | Net Revenue / TPV | Stable or expanding | Declining >10bp/year (pricing pressure) |
| **Revenue Growth** | YoY net revenue change | >15% | <8% |
| **Transaction Growth** | YoY transaction count change | >15% (volume-driven growth) | <5% (saturation) |
| **Cost per Transaction** | Processing cost / Total transactions | Declining trend (scale) | Rising (complexity, fraud) |
| **Gross Margin** | Net revenue - network/interchange fees / Net revenue | >65% (processor) >75% (network) | <55% |
| **Op Margin** | Operating income / Net revenue | >30% (at scale) | <15% (sub-scale or heavy investment) |
| **FCF Conversion** | FCF / Net Income | >80% | <50% (capex-heavy, SBC-heavy) |

### Neobanks & Digital Banks

| Metric | Formula/Definition | Bullish Threshold | Bearish Threshold |
|--------|-------------------|-------------------|-------------------|
| **Deposits per User** | Total deposits / Active accounts | >$5,000 (primary bank) | <$1,000 (side account) |
| **Revenue per User (ARPU)** | Total revenue / Active users | >$80/year | <$30/year |
| **Net Interest Margin (NIM)** | (Interest income - Interest expense) / Avg earning assets | >3.5% | <2.0% |
| **Cross-Sell Ratio** | Products per customer | >3 products | <1.5 products |
| **Net Revenue Retention** | Revenue from prior-year cohort / Prior-year revenue | >115% | <95% |
| **Credit Loss / Revenue** | Net charge-offs / Total revenue | <15% | >30% (credit quality deteriorating) |
| **Funding Cost** | Interest expense / Average deposits | <200bp above Fed Funds | >350bp above Fed Funds |
| **Active User Growth** | YoY growth in monthly active users | >25% | <10% |

### BNPL / Lending Fintechs

| Metric | Formula/Definition | Bullish Threshold | Bearish Threshold |
|--------|-------------------|-------------------|-------------------|
| **GMV (Gross Merchandise Value)** | Total purchase volume financed | >30% YoY growth | <10% |
| **Revenue as % of GMV** | Net revenue / GMV | >7% (healthy monetization) | <4% (thin margins) |
| **Delinquency Rate (30+ days)** | 30+ day past due / Total receivables | <3% | >6% |
| **Net Charge-Off Rate** | Annual NCOs / Average receivables | <5% | >10% |
| **Unit Economics (RLTC)** | Revenue Less Transaction Costs / GMV | >3% | <0% (losing money per transaction) |
| **Funding Diversification** | # of warehouse/ABS facilities | >5 diversified sources | <2 concentrated sources |
| **Merchant Repeat Rate** | % of volume from returning merchants | >80% | <50% (high churn) |

### Crypto Exchanges

| Metric | Formula/Definition | Bullish Threshold | Bearish Threshold |
|--------|-------------------|-------------------|-------------------|
| **Trading Volume** | Total spot + derivatives volume | Growing with market share gains | Declining share even in bull market |
| **Blended Take Rate** | Net trading revenue / Trading volume | >20bp (retail-heavy) | <5bp (institutional race to zero) |
| **Subscription/Services Revenue %** | Non-trading revenue / Total revenue | >30% (diversified) | <10% (trading-volume dependent) |
| **Assets on Platform** | Total custodied assets | Growing > crypto market cap growth | Outflows |
| **Regulatory Licenses** | # of jurisdictions with full licenses | >20 major markets | <5 or pending enforcement actions |

## Unit Economics Framework

### CAC & LTV by Sub-Segment

| Sub-Segment | Typical CAC | Target LTV/CAC | Payback Period |
|-------------|-------------|----------------|----------------|
| Card Networks | N/A (bank partners) | N/A | Perpetual moat |
| Payment Processors | $500-2,000/merchant | >5x | 12-18 months |
| Neobanks (consumer) | $30-80/user | >6x | 18-24 months |
| Neobanks (SMB) | $200-500/business | >8x | 12-18 months |
| BNPL | $10-30/consumer + merchant integration | >4x | 6-12 months |
| Crypto Exchange | $50-200/funded account | >3x | Variable (cycle-dependent) |
| Embedded Finance (BaaS) | $5,000-50,000/platform partner | >10x | 24-36 months |

### Path to Profitability Checkpoints
1. **Gross profit positive**: Revenue exceeds direct costs (interchange, fraud, processing)
2. **Contribution margin positive**: Gross profit exceeds variable S&M (CAC)
3. **EBITDA positive**: Contribution profit exceeds fixed costs (R&D, G&A)
4. **GAAP profitable**: EBITDA exceeds SBC, D&A, interest
5. **Rule of 40**: Revenue growth % + FCF margin % exceeds 40

## Regulatory Landscape

### Key Regulatory Dimensions
| Regulation | Impact | Affected Segments |
|------------|--------|-------------------|
| **Durbin Amendment** | Caps debit interchange for banks >$10B assets | Issuers, networks, neobanks at scale |
| **CFPB Open Banking (1033)** | Mandates data portability | Aggregators, neobanks (benefit), incumbents (risk) |
| **State-by-State Licensing** | Money transmitter licenses required per state | Payments, crypto, lending |
| **Basel III Endgame** | Higher capital requirements for bank partners | BaaS, embedded finance, BNPL |
| **Interchange Regulation (global)** | EU/UK cap at 0.2-0.3%, Australia flat cap | Networks, processors with international exposure |
| **Bank charter requirements** | OCC/state bank charter for deposit-taking | Neobanks seeking primary bank status |
| **Crypto (MiCA, SEC)** | Securities classification, custody rules | Exchanges, DeFi, stablecoin issuers |
| **BNPL (Truth in Lending)** | Disclosure requirements, credit reporting mandates | BNPL providers |

### Regulatory Moat vs Regulatory Risk
- **Moat**: Fully licensed entities (bank charter, BitLicense, MTLs in 50 states) face less competition from new entrants
- **Risk**: Regulatory change can compress take rates (Durbin), force disclosure (BNPL), or restrict products (crypto)
- **Key question**: Is the company a regulatory beneficiary (barrier creator) or victim (margin compressor)?

## Competitive Dynamics

### Traditional Banks vs Fintechs vs Big Tech

| Dimension | Traditional Banks | Fintechs | Big Tech (AAPL, GOOG, AMZN) |
|-----------|------------------|----------|------------------------------|
| **Cost of Funds** | Lowest (insured deposits) | Higher (wholesale/fintech deposits) | Highest (balance sheet funded) |
| **Distribution** | Branch + digital | Digital-only | Embedded in ecosystem |
| **Regulation** | Heaviest (fully licensed) | Moderate (partner bank model) | Lightest (limited financial license) |
| **Technology** | Legacy core systems | Cloud-native | Best-in-class engineering |
| **Trust** | High (FDIC, brand) | Growing (younger demographics) | High (brand, but privacy concerns) |
| **Cross-Sell** | Broadest product set | Growing (2-4 products) | Ecosystem lock-in + adjacency |

### Competitive Threat Assessment
- **Big Tech entering payments**: Apple Pay, Google Pay, Amazon lending = distribution advantage without legacy costs
- **Banks fighting back**: JPM/Goldman investing $10B+/year in technology; Zelle challenging Venmo
- **Consolidation**: Sub-scale fintechs acquired for distribution (Afterpay→Block, Credit Karma→Intuit)
- **Verticalization**: Horizontal platforms losing to vertical-specific solutions (Toast for restaurants, Shopify for e-commerce)

## Valuation Framework

### Key Multiples by Sub-Segment
| Sub-Segment | Primary Multiple | Premium Range | Discount Range |
|-------------|-----------------|---------------|----------------|
| Card Networks | P/E (NTM) | 30-40x (growth + moat) | <25x (regulatory concern) |
| Payment Processors | EV/Revenue | 8-15x (high-growth) | 3-6x (mature, commoditized) |
| Neobanks (pre-profit) | EV/Revenue | 10-20x (rapid user growth) | <5x (decelerating) |
| Neobanks (profitable) | P/E | 25-40x | <15x |
| BNPL | EV/GMV | 3-8% of GMV | <1% of GMV |
| Crypto Exchanges | P/E (cycle-adjusted) | 20-30x mid-cycle | <10x peak earnings |

### Cycle Awareness
- **Interest rate sensitivity**: Neobanks benefit from higher rates (float income). BNPL suffers (higher funding costs, credit losses).
- **Consumer credit cycle**: Late-cycle = rising delinquencies for BNPL/lending fintechs. Look for reserve build acceleration.
- **Crypto cycle**: Exchange revenue is 80%+ correlated with crypto market cap. Use mid-cycle earnings for valuation.

## Red Flags Specific to Fintech

- **TPV growing but take rate compressing faster**: Revenue growth masking margin deterioration
- **Deposits per user flat or declining**: Users not deepening relationship (still a side account)
- **Credit losses rising faster than revenue growth**: Underwriting deteriorating to fuel growth
- **Regulatory action or consent order**: CFPB/OCC/state AG enforcement = existential risk for smaller players
- **Bank partner concentration**: Single sponsor bank relationship = key-man risk (if partner exits, business halts)
- **SBC >15% of revenue**: Dilution destroying shareholder value despite reported growth
- **Promotional pricing / cashback subsidies**: User growth fueled by unsustainable economics
- **Crypto exchange with declining non-trading revenue %**: Failure to diversify away from volatile trading fees
