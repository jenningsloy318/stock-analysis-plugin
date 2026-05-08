---
name: quick-overview
description: "Generate a quick stock overview using agent team in quick mode. Spawns fundamental-analyst, quant-analyst, risk-analyst in parallel. Produces 3 condensed reports (long/mid/short)."
---

<purpose>Perform a rapid stock analysis using the agent team in quick mode. Spawns specialist agents in parallel for condensed coverage. Produces 3 reports (long/mid/short) even in quick mode.</purpose>

<agent-team>
MANDATORY: This command operates as an agent team. You are the orchestrator.

After Triage & data fetch, spawn sub-agents in parallel:
  Claude Code: Agent({ subagent_type: "stock-analysis:<agent-name>", prompt: "..." })
  Gemini CLI: @<agent-name> <task>

| Agent | Task |
|-------|------|
| @fundamental-analyst | Light fundamental analysis (key ratios, moat signal) |
| @quant-analyst | Valuation + technicals (DCF, comps, trend) |
| @risk-analyst | Key risks, Altman Z, red flags |

All 3 agents run in parallel → scoring → @equity-report-writer for 3 condensed reports.
</agent-team>

<usage>/stock-analysis:quick-overview [TICKER]</usage>

<process>
  <step n="1" name="Triage (orchestrator direct)">Identify ticker, run fetch_financials.py, fetch_macro.py, calculate_metrics.py</step>
  <step n="2" name="Spawn Agents">Spawn @fundamental-analyst (light), @quant-analyst (Stages 6-7), @risk-analyst (light) in parallel</step>
  <step n="3" name="Scoring (orchestrator direct)">Run compute_scores.py</step>
  <step n="4" name="Spawn Report Writer">Spawn @equity-report-writer to produce 3 condensed reports</step>
</process>

<constraints>
  <constraint>NEVER perform analysis directly — always spawn specialist agents</constraint>
  <constraint>Always produce 3 reports (long/mid/short) even in quick mode</constraint>
  <constraint>Estimated time: 2-5 minutes</constraint>
  <constraint>Skip Stages 2, 3, 4, 5, 9 entirely</constraint>
  <constraint>Report confidence flagged as "Limited — quick overview mode"</constraint>
</constraints>
