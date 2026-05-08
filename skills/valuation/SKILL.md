---
name: valuation
description: "Run standalone valuation analysis using agent team. Spawns quant-analyst for DCF, comps, and relative value."
---

<purpose>Perform standalone valuation analysis using agent team. Spawns quant-analyst for DCF, trading comps, relative value, and technical levels. Useful for quick price checks or updating valuations.</purpose>

<agent-team>
MANDATORY: This command operates as an agent team. You are the orchestrator. You MUST NOT run scripts directly.

STEP 0 — Identify ticker. Create team: TeamCreate({ name: "stock-analysis-[TICKER]-val" })
STEP 1 — Spawn @search-agent for data fetch.
STEP 2 — Spawn @quant-analyst for valuation analysis.

| Agent | Task |
|-------|------|
| @search-agent | Data fetch: fetch_financials.py, calculate_metrics.py, forecast.py, fetch_peer_universe.py |
| @quant-analyst | Full valuation: DCF, trading comps, relative value, technicals |
</agent-team>

<usage>/stock-analysis:valuation [TICKER]</usage>

<process>
  <step n="0" name="Team Setup">Identify ticker. Create team. This is the only step you do directly.</step>
  <step n="1" name="Data Fetch">Spawn @search-agent for fetch_financials.py, calculate_metrics.py, forecast.py, fetch_peer_universe.py. Wait for completion.</step>
  <step n="2" name="Spawn Agent">Spawn @quant-analyst for full valuation analysis</step>
  <step n="3" name="Summary">Present valuation verdict (in Chinese): intrinsic value range, margin of safety, fair value</step>
</process>

<constraints>
  <constraint>ALL output MUST be written in Chinese (中文). Technical terms (P/E, EV/EBITDA, ROIC, ticker symbols) may remain in English.</constraint>
  <constraint>Include current stock price (当前股价) prominently in valuation summary header.</constraint>
  <constraint>NEVER run scripts or perform valuation analysis directly — delegate to sub-agents</constraint>
  <constraint>DCF sensitivity table mandatory (WACC vs terminal growth matrix)</constraint>
  <constraint>Results should be combined with full analysis for investment decisions</constraint>
</constraints>
