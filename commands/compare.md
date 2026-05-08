---
name: compare
description: "Compare multiple stocks using agent team. Spawns quant-analyst and fundamental-analyst per ticker for consistent scoring."
---

<purpose>Perform comparative analysis across 2-5 stocks using agent team. Spawns specialist agents for each ticker to ensure consistent scoring methodology, then merges results into comparison table.</purpose>

<agent-team>
MANDATORY: This command operates as an agent team. You are the orchestrator.

After data fetch, delegate scoring to sub-agents:
  Claude Code: Agent({ subagent_type: "stock-analysis:<agent-name>", prompt: "..." })
  Gemini CLI: @<agent-name> <task>

| Agent | Task |
|-------|------|
| @quant-analyst | Valuation scoring for each ticker (run in parallel) |
| @fundamental-analyst | Financial health scoring for each ticker (run in parallel) |

Max 3 agents concurrent. Orchestrator merges scores into comparison table.
</agent-team>

<usage>/stock-analysis:compare [TICKER1],[TICKER2],[TICKER3]...</usage>

<process>
  <step n="1" name="Validate (orchestrator direct)">Confirm all tickers are valid, resolve ambiguous names</step>
  <step n="2" name="Data Fetch (orchestrator direct)">Run fetch_financials.py and calculate_metrics.py for each ticker</step>
  <step n="3" name="Spawn Agents">Spawn @quant-analyst and @fundamental-analyst for each ticker in parallel</step>
  <step n="4" name="Comparison (orchestrator direct)">Merge agent scores into side-by-side comparison table, rank by composite</step>
</process>

<constraints>
  <constraint>NEVER perform deep analysis directly — delegate scoring to sub-agents</constraint>
  <constraint>Maximum 5 stocks per comparison</constraint>
  <constraint>All stocks should share GICS sector alignment (warn if mixed sectors)</constraint>
  <constraint>Use identical valuation methodology across all stocks</constraint>
</constraints>
