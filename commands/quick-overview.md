---
name: quick-overview
description: "Generate a quick stock overview with reduced stages. Runs Stages 1+6+7+8 in parallel and produces a Mid-term format report."
---

<purpose>Perform a rapid stock analysis using only the most critical stages (Fundamentals, Valuation, Risk) in parallel. Produces a condensed Mid-term format report suitable for initial screening or time-constrained decisions.</purpose>

<usage>/stock-analysis:quick-overview [TICKER]</usage>

<process>
  <step n="1" name="Triage">Identify ticker, check current price and market data</step>
  <step n="2" name="Parallel Stages">Spawn fundamental-analyst (Stage 1 light), quant-analyst (Stages 6-7), risk-analyst (Stage 8 light) in parallel</step>
  <step n="3" name="Scoring">Run compute_scores.py before report generation</step>
  <step n="4" name="Report">Generate condensed Mid-term format report from stage summaries</step>
</process>

<constraints>
  <constraint>Estimated time: 1-3 minutes</constraint>
  <constraint>Skip Stages 2, 3, 4, 5, 9 entirely</constraint>
  <constraint>Stage 1: summary only (1.1 Financial Health)</constraint>
  <constraint>Stage 8: Light mode (8.2 quantification + 8.4 catalysts only)</constraint>
  <constraint>Report confidence automatically flagged as "Limited — quick overview mode"</constraint>
</constraints>
