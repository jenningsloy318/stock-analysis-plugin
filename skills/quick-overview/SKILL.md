---
name: quick-overview
description: "Generate a quick stock overview using agent team in quick mode. Spawns fundamental-analyst, quant-analyst, risk-analyst in parallel. Produces 3 condensed reports (long/mid/short)."
---

<purpose>Perform a rapid stock analysis using the agent team in quick mode. Spawns specialist agents in parallel for condensed coverage. Produces 3 reports (long/mid/short) even in quick mode.</purpose>

<agent-team>
MANDATORY: This command operates as an agent team. You are the orchestrator. You MUST NOT run scripts directly.

STEP 0 — Identify ticker. Create team: TeamCreate({ name: "stock-analysis-[TICKER]-quick" })
STEP 1 — Spawn @search-agent for data fetch (fetch_financials.py, fetch_macro.py, calculate_metrics.py, fetch_market_breadth.py --skip-constituents, fetch_theme_performance.py). Breadth/theme data feeds quant-analyst Stage 7 market regime.
STEP 2 — Spawn analysis agents in parallel:

| Agent | Task |
|-------|------|
| @search-agent | Data fetch: financials, macro, metrics, breadth, theme |
| @fundamental-analyst | Light fundamental analysis (key ratios, moat signal) |
| @quant-analyst | Valuation + technicals (DCF, comps, trend) |
| @risk-analyst | Key risks, Altman Z, red flags |

All 3 analysis agents run in parallel → scoring → @equity-report-writer for 3 condensed reports.
</agent-team>

<usage>/stock-analysis:quick-overview [TICKER]</usage>

<process>
  <step n="0" name="Team Setup">Identify ticker. Create team. This is the only step you do directly.</step>
  <step n="1" name="Data Fetch">Spawn @search-agent for triage scripts (financials, macro, metrics, breadth, theme). Wait for completion.</step>
  <step n="2" name="Spawn Agents">Spawn @fundamental-analyst (light), @quant-analyst (Stages 6-7), @risk-analyst (light) in parallel</step>
  <step n="3" name="Scoring & Report">Run compute_scores.py (via @search-agent). Spawn @equity-report-writer to produce 3 condensed reports.</step>
</process>

<constraints>
  <constraint>ALL reports MUST be written in Chinese (中文). Technical terms (P/E, EV/EBITDA, ROIC, ticker symbols) may remain in English.</constraint>
  <constraint>Every table/list mentioning a company MUST include a "当前股价" (current price) column.</constraint>
  <constraint>NEVER run scripts or perform analysis directly — always spawn specialist agents</constraint>
  <constraint>Always produce 3 reports (long/mid/short) even in quick mode</constraint>
  <constraint>Estimated time: 2-5 minutes</constraint>
  <constraint>Skip Stages 2, 3, 4, 5, 9 entirely</constraint>
  <constraint>Report confidence flagged as "Limited — quick overview mode"</constraint>
</constraints>
