---
name: compare
description: "Compare multiple stocks using agent team. Spawns quant-analyst and fundamental-analyst per ticker for consistent scoring."
---

<purpose>Perform comparative analysis across 2-5 stocks using agent team. Spawns specialist agents for each ticker to ensure consistent scoring methodology, then merges results into comparison table.</purpose>

<agent-team>
MANDATORY: This command operates as an agent team. You are the orchestrator. You MUST NOT run scripts directly.

STEP 0 — Confirm all tickers valid, resolve ambiguous names. Create team: TeamCreate({ name: "stock-analysis-compare" })
STEP 1 — Spawn @search-agent for data fetch (fetch_financials.py, calculate_metrics.py, fetch_theme_performance.py for each ticker). Theme data provides sector rotation context for cross-stock comparison.
STEP 2 — Spawn scoring agents:

| Agent | Task |
|-------|------|
| @search-agent | Data fetch: financials, metrics, theme performance for each ticker |
| @quant-analyst | Valuation scoring for each ticker (run in parallel) |
| @fundamental-analyst | Financial health scoring for each ticker (run in parallel) |

Max 3 agents concurrent. Orchestrator merges scores into comparison table.
</agent-team>

<usage>/stock-analysis:compare [TICKER1],[TICKER2],[TICKER3]...</usage>

<process>
  <step n="0" name="Team Setup">Confirm all tickers valid, resolve ambiguous names. Create team. This is the only step you do directly.</step>
  <step n="1" name="Data Fetch">Spawn @search-agent to run fetch_financials.py, calculate_metrics.py, and fetch_theme_performance.py for each ticker. Wait for completion.</step>
  <step n="2" name="Spawn Agents">Spawn @quant-analyst and @fundamental-analyst for each ticker in parallel</step>
  <step n="3" name="Comparison">Merge agent scores into side-by-side comparison table (in Chinese), rank by composite</step>
</process>

<constraints>
  <constraint>ALL output MUST be written in Chinese (中文). Technical terms (P/E, EV/EBITDA, ROIC, ticker symbols) may remain in English.</constraint>
  <constraint>Every comparison table MUST include a "当前股价" (current price) column for each stock.</constraint>
  <constraint>Prefer growth-stage companies (成长型公司) with price under $100 (US) or ¥100 (A-shares) when suggesting comparables.</constraint>
  <constraint>NEVER run scripts or perform deep analysis directly — delegate scoring to sub-agents</constraint>
  <constraint>Maximum 5 stocks per comparison</constraint>
  <constraint>All stocks should share GICS sector alignment (warn if mixed sectors)</constraint>
  <constraint>Use identical valuation methodology across all stocks</constraint>
</constraints>
