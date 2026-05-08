# Data Source Matrix

Use this matrix before running stock-analysis or industry-screening. The goal is coverage by dimension, source quality, and freshness, not volume of citations.

## Source Tiers

| Tier | Use | Examples | Completion Rule |
|------|-----|----------|-----------------|
| Tier 0 | Market prices and tradable instruments | Exchange/finance tool, yfinance, Polygon/Alpaca when configured | Required for current price, market cap, beta, technicals, and options-sensitive reports |
| Tier 1 | Primary filings and official statistics | SEC EDGAR submissions/companyfacts, company IR filings, FRED/Federal Reserve, BEA, BLS, Treasury FiscalData, CFTC COT, FINRA short interest, EIA, FDA, FDIC/OCC | Blocking for any claim directly supported by these datasets |
| Tier 2 | Audited or institutionally curated secondary data | Exchange filings outside the US, S&P/FactSet/Capital IQ if available, ETF issuer holdings, rating agency releases, consensus providers, reputable industry reports | Allowed when Tier 1 does not cover the dimension; must be labeled |
| Tier 3 | Directional alternative data | Google Trends, Similarweb snippets, app-store ranks, Glassdoor public pages, Reddit/social sentiment, patents, hiring pages, channel-check summaries | Never decisive alone; requires convergence with at least one Tier 1 or Tier 2 signal |

## Coverage Requirements By Dimension

| Dimension | Minimum Sources | Freshness Target | Notes |
|-----------|-----------------|------------------|-------|
| Current price, volume, options | 1 Tier 0 source | Same day for short-term, 7 days for mid/long | Quote staleness must be explicit in reports |
| Financial statements | SEC/company filings plus script output | Latest 10-K/10-Q or local market equivalent | For non-US companies, use exchange filings and label accounting standard |
| Segment and geography | Latest annual report, 10-K/20-F/40-F, investor presentation | Latest annual filing; update if material 8-K/6-K exists | Required for multi-segment valuation and geopolitical exposure |
| Management and governance | DEF 14A/proxy, Form 4, board/company filings | Proxy within 15 months; Form 4 within 90 days | If no recent Form 4 exists, state "No recent Form 4 found" instead of failing |
| Macro | FRED/Fed plus BEA/BLS/Treasury where relevant | 30 days for monthly/daily series; latest quarter for GDP | Use regional official sources for non-US issuers |
| Credit and liquidity | FRED spreads, Treasury, company debt notes, ratings releases | 7 days for spreads; latest filing for maturity schedule | Mandatory for levered companies and financials |
| Positioning and flow | CFTC COT, FINRA short interest, ETF holdings/flows, 13F/13D/13G | 7 days for COT, latest settlement for short interest, latest quarter for 13F | Distinguish short interest from short-sale volume |
| Industry structure | GICS/NAICS mapping, BEA industry data, reputable industry report | 90 days for market data; 12 months for structural reports | Require both top-down and bottom-up TAM sanity checks |
| Company screening universe | GICS/ETF holdings/exchange lists plus web verification | 90 days | Missing companies must be reported as universe risk |
| Alternative data | At least 3 independent directional signals | 30 days for social/search/app; 12 months for patents | Mark as directional and non-representative |
| Capital structure & returns | yfinance shares/buyback data, SEC filings (10-K cash flow statement), proxy | Latest filing for buyback data; 90 days for share count | Required for capital allocation scoring and SBC dilution flag |
| Private market / M&A | yfinance fundamentals, web search for precedent transactions, 13D filings | 90 days for fundamentals; 12 months for M&A comps | LBO floor is computed deterministically; precedent transactions need web search |
| Technical structure (Weinstein) | yfinance weekly OHLCV (2yr), SPY benchmark | Same day for short-term; 7 days otherwise | Required for Stage 6 Weinstein classification and CANSLIM L-factor |
| ESG & carbon risk | yfinance sustainability fields, sector benchmarks, GICS emission intensity tables | 90 days for ESG scores; 12 months for carbon intensity | Required for long-term risk assessment in carbon-intensive sectors (GICS 10, 15, 20, 55) |
| International market adjustments | akshare (China), EDINET/TDnet (Japan), BSE/NSE (India), DART/KRX (Korea) | 90 days for structural metrics; 30 days for flows | Required when primary listing is non-US or >20% revenue from covered markets |
| Volatility & tail risk | yfinance daily returns (2yr), GARCH model output, Student-t fitting | 7 days for short-term; 30 days otherwise | Required for enhanced risk metrics and position sizing |
| Supply chain concentration | yfinance geographic segments, GICS sector chokepoint mapping, revenue HHI | 90 days for segments; 12 months for structural | Required for industry analysis (Stage 3) and operational due diligence |
| Earnings quality | Financial statements (income, cash flow, balance sheet), 3-5yr history | Latest filing | Required for forensic accounting and fundamental quality assessment |
| Liquidity & microstructure | yfinance daily OHLCV (1yr), bid-ask when available, shares outstanding | 7 days for short-term; 30 days otherwise | Required for position sizing constraints and market impact estimation |
| Short interest & squeeze | yfinance short interest, float shares, institutional holdings, catalyst calendar | 7 days for short-term; 14 days otherwise | Required for short-term positioning analysis and squeeze risk scoring |
| Activist & governance catalysts | yfinance institutional holders, insider transactions, 13D/proxy filings | 30 days for institutional; 90 days for proxy | Required for governance catalyst identification and proxy fight probability |
| Tail risk & drawdowns | yfinance daily returns (2yr), portfolio positions, correlation matrix | 7 days for short-term; 30 days otherwise | Required for portfolio-level risk assessment and position sizing |

## Freshness SLA

| Data Class | Max Freshness | Blocks Stage? |
|------------|---------------|---------------|
| Quote, options, technicals | Same day for short-term; 7 days otherwise | Yes for short-term and valuation |
| News and catalysts | 7 days | Yes for short-term and event-driven mid-term |
| Macro daily/weekly series | 30 days | Yes for Stages 4, 7 and screening Phase 0 |
| Financial statements | Latest reported quarter/year | Yes for Stages 1, 6, 8 and company screening |
| Insider/Form 4 | 90 days if activity exists | No if no filing exists; annotate |
| Sector valuation/growth | 90 days | Yes for broad screening |
| Industry reports/TAM | 12 months | No, but confidence drops if older |
| Patents/governance/proxy | 12-15 months | Yes for long-term management or innovation claims |

## Source Quorum Rules

1. A numeric investment claim needs one Tier 1/Tier 0 source or two independent Tier 2 sources.
2. A qualitative thesis claim needs at least two independent sources, unless it is directly stated in a company filing.
3. Alternative data can support direction, timing, or divergence only after convergence scoring.
4. If sources conflict, preserve the conflict in the report and assign lower confidence.
5. If a critical source is unavailable, write "Data not available" and lower confidence instead of substituting an unverifiable proxy.

## Non-US Coverage

For non-US companies, replace US-only sources with local equivalents:

| Dimension | Preferred Sources |
|-----------|-------------------|
| Filings | Local exchange filings, annual report, 20-F/40-F/6-K if SEC-listed ADR |
| Macro | Central bank, national statistics office, IMF/OECD/World Bank where official local APIs are unavailable |
| Rates and currency | Local central bank, Treasury/sovereign yield data, FX market data |
| Industry | Local industry regulator, trade body, exchange sector classification, regional government statistics |
| Governance | Local proxy/annual meeting materials, exchange governance filings |

## Sector-Specific Add-Ons

| Sector | Required Add-Ons |
|--------|------------------|
| Banks | Regulatory capital, CET1, NIM, loan loss provisions, deposit beta, unrealized securities losses, FDIC/OCC/Fed data where available |
| Insurance | Combined ratio, reserves, float yield, catastrophe exposure, solvency capital |
| REITs | FFO/AFFO, occupancy, lease maturities, cap rates, debt maturity schedule |
| Energy | Production volumes, reserves, decline rates, realized prices, hedges, EIA commodity data |
| Biotech/Pharma | Pipeline phase probabilities, trial readouts, FDA calendar, patent cliff, payer/reimbursement risk |
| SaaS/Software | ARR, NRR/GRR, CAC payback, rule of 40, RPO, churn, seat expansion, cloud gross margin |
| Semiconductors | Node exposure, wafer starts, utilization, inventory days, customer concentration, export controls |
| Industrials | Backlog, book-to-bill, capacity utilization, input costs, order cycle |
| Consumer | Same-store sales, traffic, basket size, inventory turns, promotion intensity |

## IFRS vs US GAAP Reconciliation

When analyzing non-US companies reporting under IFRS, adjust for these key differences:

| Area | US GAAP | IFRS | Analysis Impact |
|------|---------|------|-----------------|
| **Revenue Recognition** | ASC 606 (similar to IFRS 15) | IFRS 15 | Largely converged. Watch for principal vs agent classification in marketplace/platform companies. |
| **Leases** | ASC 842: all leases on balance sheet | IFRS 16: all leases on balance sheet | Largely converged. Both capitalize operating leases now. |
| **Inventory** | LIFO permitted | LIFO prohibited | US companies using LIFO → inventory and COGS not comparable to IFRS peers. Adjust to FIFO for peer comparison. |
| **Goodwill** | Amortized over ≤10 years (private companies) or tested for impairment (public) | Tested for impairment only (no amortization) | Different impairment triggers and measurement. IFRS goodwill may be overstated. |
| **Development Costs** | Expensed (with narrow exceptions for software) | Capitalized if certain criteria met | IFRS companies may show higher assets and lower current expenses. Adjust for comparability. |
| **PP&E Revaluation** | Historical cost only | Revaluation model permitted | IFRS companies may show inflated asset values. Check if revaluation model is used. |
| **Extraordinary Items** | Permitted (rare) | Prohibited | IFRS income statements are cleaner — no below-the-line extraordinary classification. |
| **Cash Flow Statement** | Interest paid/received = operating; dividends paid = financing | Choice: interest/dividends can be operating or financing | Classification differences change OCF and FCF. Always check classification choices. |
| **Financial Instruments** | Complex (ASC 820 fair value hierarchy) | IFRS 9 (simpler classification) | Different hedge accounting and impairment models. |
| **Consolidation** | Variable interest entity (VIE) model | Control-based model (power + returns) | Different consolidation conclusions for SPVs, structured entities. |

### Analyst Adjustments Required

When comparing IFRS and US GAAP companies:

1. **Always state accounting standard in reports.** "FY2024 results (IFRS)" or "FY2024 (US GAAP)."
2. **Normalize inventory accounting.** If US peer uses LIFO, adjust to FIFO before comparing gross margins.
3. **Check for development cost capitalization.** IFRS tech/pharma companies may have higher assets. Subtract capitalized development from assets and add to expenses for comparability.
4. **Reconcile OCF.** IFRS companies with interest in financing cash flow → OCF overstated. Adjust to US GAAP OCF definition.
5. **Verify goodwill impairment.** IFRS impairment-only model → goodwill may be stale. Apply a simplified DCF reasonableness test.
6. **Watch segment reporting.** IFRS 8 is similar to ASC 280 but companies have more discretion in segment definition under IFRS.

### Non-US Filing Equivalents

| Country/Region | Filing Equivalent | Accounting Standard | Access |
|---------------|-------------------|---------------------|--------|
| **Canada** | SEDAR (sedar.com) | IFRS (public companies) | Free web |
| **UK** | Companies House | IFRS (UK-adopted) | Free web |
| **EU** | National registers + ESMA | IFRS (EU-adopted) | Free web (varies by country) |
| **Japan** | EDINET | JGAAP or IFRS (choice) | Free web |
| **China** | CSRC + SSE/SZSE | CAS (converging to IFRS) | akshare / free web |
| **India** | BSE/NSE + MCA | Ind AS (converged IFRS) | Free web |
| **Australia** | ASIC | IFRS (AASB) | Free web |
| **Brazil** | CVM | IFRS (CPC) | Free web |
| **Hong Kong** | HKEX | HKFRS (IFRS-equivalent) | Free web |
| **Singapore** | SGX | SFRS (IFRS-equivalent) | Free web |
| **ADR (US-listed foreign)** | SEC 20-F / 40-F | IFRS or home-country GAAP with reconciliation | SEC EDGAR |

## Report Confidence Mapping

| Coverage Result | Confidence Impact |
|-----------------|-------------------|
| All blocking dimensions pass, 0-1 stale non-critical sources | High confidence eligible |
| One blocking dimension unavailable but not central to thesis | Medium confidence maximum |
| Two or more blocking dimensions unavailable or stale | Low confidence maximum |
| Alternative-data-only thesis support | Low confidence maximum |
| Numeric claims fail fact check | Remove claim; rerun affected stage if material |
