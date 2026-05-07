---
name: compare
description: "Compare multiple stocks across key dimensions. Produces a side-by-side comparison table with relative rankings."
---

<purpose>Perform comparative analysis across 2-5 stocks on the same key dimensions (financials, moat, valuation, risk). Produces a structured comparison table highlighting relative strengths/weaknesses and ranking stocks by composite score.</purpose>

<usage>/stock-analysis:compare [TICKER1],[TICKER2],[TICKER3]...</usage>

<process>
  <step n="1" name="Validate">Confirm all tickers are valid, resolve ambiguous names</step>
  <step n="2" name="Data Fetch">Run fetch_financials.py and calculate_metrics.py for each ticker</step>
  <step n="3" name="Dimension Scoring">Score each stock on: Financial Health, Moat Quality, Valuation Attractiveness, Growth Trajectory, Risk Profile (1-10 each)</step>
  <step n="4" name="Comparison Table">Generate side-by-side table with key metrics and scores</step>
  <step n="5" name="Ranking">Rank stocks by composite score with methodology explanation</step>
</process>

<constraints>
  <constraint>Maximum 5 stocks per comparison</constraint>
  <constraint>All stocks should share GICS sector alignment (warn if mixed sectors)</constraint>
  <constraint>Use identical valuation methodology across all stocks for fair comparison</constraint>
  <constraint>State clearly which dimensions each stock wins/loses on</constraint>
</constraints>
