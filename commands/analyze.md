---
name: analyze
description: "Run full multi-stage equity research analysis on a stock ticker. Always produces all 3 report types (Long-term, Mid-term, Short-term) automatically."
---

<purpose>Invoke the stock-analyst orchestrator to perform full multi-stage equity research. Always produces all 3 report horizons (long/mid/short) from a single data-collection pass. Spawns specialized analyst agents for each stage and produces institutional-grade reports.</purpose>

<usage>/stock-analysis:analyze [TICKER] [options]</usage>

<options>
  --quick                        Quick overview mode (reduced stages, still produces 3 reports)
</options>

<defaults>
  - Always produces 3 reports: long-term, mid-term, short-term
  - No need to specify horizon — all 3 generated automatically
  - One shared data-collection pass; reports diverge at scoring/synthesis
</defaults>

<process>
  <step n="1" name="Triage">Identify ticker, check earnings calendar, create output directory</step>
  <step n="2" name="Data Fetch">Run scripts: fetch_financials.py, fetch_macro.py, calculate_metrics.py, forecast.py, fetch_credit.py</step>
  <step n="3" name="Stage Execution">Spawn analyst agents per parallel execution rules (all stages run once, feeding all 3 report types)</step>
  <step n="4" name="Report Generation">Spawn equity-report-writer to synthesize stage summaries into 3 final reports (long/mid/short)</step>
  <step n="5" name="Quality Gate">Run pre-delivery checklist, validate fact integrity for each report</step>
</process>

<constraints>
  <constraint>If earnings within 14 days, warn user before proceeding</constraint>
  <constraint>If earnings within 3 days, recommend waiting unless user overrides</constraint>
  <constraint>All reports saved to ./reports/[TICKER]/[TICKER]_[long|mid|short]_[YYYY-MM-DD].md (3 files)</constraint>
  <constraint>Context eviction enforced after each stage completion</constraint>
</constraints>
