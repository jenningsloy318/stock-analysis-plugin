---
name: valuation
description: "Run standalone valuation analysis using agent team. Spawns quant-analyst for DCF, comps, and relative value."
---

<purpose>Perform standalone valuation analysis using agent team. Spawns quant-analyst for DCF, trading comps, relative value, and technical levels. Useful for quick price checks or updating valuations.</purpose>

<agent-team>
MANDATORY: This command operates as an agent team. You are the orchestrator.

After data fetch, delegate valuation analysis to sub-agent:
  Claude Code: Agent({ subagent_type: "stock-analysis:quant-analyst", prompt: "..." })
  Gemini CLI: @quant-analyst <task>

| Agent | Task |
|-------|------|
| @quant-analyst | Full valuation: DCF, trading comps, relative value, technicals |

Orchestrator runs data scripts, then delegates analysis to @quant-analyst.
</agent-team>

<usage>/stock-analysis:valuation [TICKER]</usage>

<process>
  <step n="1" name="Data Fetch (orchestrator direct)">Run fetch_financials.py, calculate_metrics.py, forecast.py, fetch_peer_universe.py</step>
  <step n="2" name="Spawn Agent">Spawn @quant-analyst for full valuation analysis</step>
  <step n="3" name="Summary (orchestrator direct)">Present valuation verdict: intrinsic value range, margin of safety, fair value</step>
</process>

<constraints>
  <constraint>NEVER perform valuation analysis directly — delegate to @quant-analyst</constraint>
  <constraint>DCF sensitivity table mandatory (WACC vs terminal growth matrix)</constraint>
  <constraint>Results should be combined with full analysis for investment decisions</constraint>
</constraints>
