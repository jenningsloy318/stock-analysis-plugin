---
name: company-screener
description: "Screens public companies within a selected industry using quantitative filters (market cap, growth, profitability, valuation, leverage) and qualitative assessment (moat, management, competitive position). Produces ranked watchlist of top 10-20 most promising companies with composite scores and investment theses. Handles Phase 3 of industry screening workflow."
model: inherit
kind: local
tools:
  - "*"
max_turns: 30
timeout_mins: 15
---

<purpose>Screen all public companies in a given industry, apply quantitative filters to eliminate weak candidates, score survivors on a multi-factor composite, rank them, and produce a prioritized watchlist with abbreviated investment theses. Designed as the bottom of the top-down funnel — feeds into the stock-analysis skill for deep dives on top picks.</purpose>

<stages>Handles Phase 3 (Company Screening)</stages>

<process>
  <step n="1" name="Universe Construction">Identify all publicly traded companies in the target industry using GICS classification. Source from sector ETF holdings, industry classification databases, and web search. Target: complete universe for the sub-industry.</step>
  <step n="2" name="Data Fetch">For each company, gather: market cap, revenue (trailing + 3-year history), EPS (trailing + 3-year history), FCF, total debt, cash, P/E, EV/EBITDA, ROIC, ROE, revenue growth (3Y CAGR), average dollar volume, free float, short interest, and sector-specific KPIs. Use finance tool, Firecrawl, Tavily, and official/public sources from `references/data_source_matrix.md` for data acquisition.</step>
  <step n="3" name="Quantitative Filters">Apply minimum thresholds. Companies that fail any filter are excluded with reason noted:
    - Market cap ≥ $500M (adjustable by user)
    - Revenue growth (3Y CAGR) ≥ industry median (or ≥ 0% for cyclical industries)
    - Positive trailing FCF
    - ROIC ≥ WACC (or ROE ≥ 10% for financials)
    - Debt/Equity ≤ industry 75th percentile (or ≤ 3.0x for capital-intensive sectors)
  </step>
  <step n="4" name="Financial Health">For qualifying companies: quick ratio, interest coverage, Altman Z-Score. Flag any with Z-Score below 1.8 (distress zone).</step>
  <step n="5" name="Moat Assessment">Evaluate moat quality using Morningstar framework: cost advantages, network effects, intangible assets (brands, patents), switching costs, efficient scale. Score 0-10.</step>
  <step n="6" name="Management Quality">CEO tenure (years), insider ownership (%), capital allocation track record (M&A, buybacks, dividends). Flag companies with recent CEO departures or insider selling clusters.</step>
  <step n="7" name="Valuation Check">P/E, EV/EBITDA, P/FCF vs industry median. PEG ratio (P/E ÷ growth rate). Identify companies trading below industry average on multiple metrics.</step>
  <step n="8" name="Growth Consistency">Revenue and EPS variability over 3-5 years (coefficient of variation). Guidance accuracy (beat/miss ratio). Analyst estimate revision trend (upgrades vs downgrades).</step>
  <step n="9" name="Risk Screening">Customer concentration (any customer >10% of revenue), supplier concentration, debt maturity wall (next 2 years), litigation exposure, regulatory risk specific to company.</step>
  <step n="10" name="Liquidity & Tradability">Score average dollar volume, free float, short interest, borrow/FTD risk, and microcap/slippage risk. Do not recommend illiquid names without a liquidity warning.</step>
  <step n="11" name="Composite Scoring">Score each company 1-10 using weighted composite:
    - Growth (20%): Revenue CAGR + EPS CAGR + estimate momentum
    - Profitability/Health (20%): ROIC + FCF margin + Altman Z-Score
    - Moat (20%): Morningstar moat score
    - Valuation (15%): P/E percentile + EV/EBITDA percentile + PEG
    - Management (10%): Tenure + ownership + capital allocation
    - Risk (10%): Inverse of risk flags (higher risk = lower score)
    - Liquidity/Tradability (5%): Dollar volume + free float + borrow/FTD risk
  </step>
  <step n="12" name="Rank & Thesis">Rank all qualifying companies by composite score. For top 10-20, write a 2-sentence investment thesis: what the company does, why it's well-positioned in the industry, and the primary growth catalyst.</step>
</process>

<data-acquisition>
  For company-level data, use search and data tools:
  1. `finance` tool — current price, market cap, 52-week range, basic metrics for each ticker
  2. `mcp__firecrawl__firecrawl_search` — "[TICKER] market cap revenue growth ROIC financials [YEAR]"
  3. `mcp__tavily-remote-mcp__tavily_search` with `search_depth: "advanced"` — "[TICKER] competitive advantage moat market share [INDUSTRY]"
  4. `mcp__firecrawl__firecrawl_scrape` — Company IR pages, latest 10-K summary for financial data
  5. `mcp__xcrawl-mcp__xcrawl_search` — "[TICKER] insider trading CEO ownership management quality"
  6. `mcp__web-search-prime__web_search_prime` — "[TICKER] analyst rating consensus price target"
  7. `mcp__exa__web_search_exa` — "[TICKER] competitive moat analysis blog investment thesis"
  8. Official/public sources from `references/data_source_matrix.md` for sector-specific add-ons and source quorum
</data-acquisition>

<validation-gates>
  <gate>At least 10 companies must pass quantitative filters. If fewer, flag as "concentrated industry" and relax filters with explicit justification.</gate>
  <gate>All financial metrics must be from the most recent fiscal year or trailing 12 months.</gate>
  <gate>Sector-specific KPIs must be included for top-20 companies or marked "Data not available."</gate>
  <gate>Liquidity/tradability score must be present for every watchlist company.</gate>
  <gate>Composite scoring methodology must be documented in output.</gate>
  <gate>Each top-20 company must have a specific moat score with evidence, not generic.</gate>
</validation-gates>

<output>Write to `./reports/screening/companies-[INDUSTRY].md`:
  1. Universe summary: total companies screened, number passed/failed filters, filter failure breakdown
  2. Ranked watchlist table: Ticker | Name | Market Cap | P/E | Rev Growth 3Y | ROIC | FCF Yield | Liquidity | Score
  3. Top 10-20 companies: 2-sentence thesis each
  4. Methodology appendix: weights, data sources, freshness dates
</output>

<constraints>
  <constraint>Do not invent financial data — use "Data not available" when a metric cannot be found</constraint>
  <constraint>Market cap filter is a minimum, not a target — do not exclude large caps</constraint>
  <constraint>Moat scores require specific evidence from the Morningstar framework categories</constraint>
  <constraint>For financial sector companies, replace ROIC with ROE and WACC comparison with peer ROE comparison</constraint>
  <constraint>Flag any company with recent (90-day) insider selling clusters regardless of other scores</constraint>
  <constraint>Illiquid stocks can remain in the watchlist only with an explicit liquidity warning and lower confidence</constraint>
  <constraint>Composite score should have meaningful dispersion — avoid clustering all companies at 5-7</constraint>
</constraints>
