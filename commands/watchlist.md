---
name: watchlist
description: "Check status of previously analyzed stocks using agent team. Spawns search-agent for current data, compares against prior targets."
---

<purpose>Review previously generated reports using agent team. Spawns search-agent for current price/news data, compares against prior targets, checks catalyst timelines, and verifies kill switch conditions.</purpose>

<agent-team>
MANDATORY: This command operates as an agent team. You are the orchestrator.

Delegate current data gathering to sub-agent:
  Claude Code: Agent({ subagent_type: "stock-analysis:search-agent", prompt: "..." })
  Gemini CLI: @search-agent <task>

| Agent | Task |
|-------|------|
| @search-agent | Fetch current prices, news, catalyst updates for each watchlist ticker |

Orchestrator reads existing reports, delegates data fetch, then compiles status.
</agent-team>

<usage>/stock-analysis:watchlist [TICKER|all]</usage>

<process>
  <step n="1" name="Scan Reports (orchestrator direct)">Read ./reports/ directory for all existing analysis reports</step>
  <step n="2" name="Spawn Agent">Spawn @search-agent for current price, news, and catalyst data</step>
  <step n="3" name="Status Check (orchestrator direct)">Compare current data to bull/base/bear targets, check kill switches</step>
  <step n="4" name="Summary (orchestrator direct)">Output watchlist table with status indicators</step>
</process>

<constraints>
  <constraint>ALL output MUST be written in Chinese (中文). Technical terms (ticker symbols, metric names) may remain in English.</constraint>
  <constraint>Only works if reports exist in ./reports/ from prior analyses</constraint>
  <constraint>Flag any report older than 90 days as "STALE — re-analysis recommended"</constraint>
  <constraint>If kill switch condition is approaching, highlight with warning</constraint>
  <constraint>If price has moved beyond bear case target, flag as "THESIS AT RISK"</constraint>
</constraints>
