---
name: context-management
description: "Rules for managing context window during multi-stage analysis: progressive disclosure, eviction protocol, and parallel execution limits"
---

<purpose>Prevent context exhaustion during multi-stage analysis by enforcing progressive reference loading, stage-level data eviction, and parallel execution caps.</purpose>

<directives>
  <directive name="Progressive Loading">Load reference files on-demand per stage. Only one reference file active at a time. Drop previous stage's reference before loading next.</directive>
  <directive name="Stage Eviction">After each stage: write summary to ./reports/[TICKER]/stage[N].md. Drop raw data (SEC filings, full transcripts, raw financials, full search results). Retain only: key metrics table, stage scores, 3-sentence narrative per sub-section.</directive>
  <directive name="Context Budget">Maximum active context: <80% of window. If approaching limit, offload intermediate data to temp files. At Stage 9, read all temp files to synthesize.</directive>
  <directive name="Parallel Limits">Max concurrent sub-agents: 3. Long-term: Stages 1-3 parallel. Mid-term: Stages 4-6 parallel. Short-term: Stages 6+8 paired.</directive>
  <directive name="Reference Loading Schedule">frameworks_value_growth.md: Stages 1-3. frameworks_macro_quant.md: Stages 4-6. frameworks_risk_alt.md: Stages 7-8. institutional_odd.md: Stage 7 ODD section. sector_metrics.md: Stage 1 after GICS identification. equity_report_templates.md: Stage 9.</directive>
</directives>

<checklist>
  - [ ] Only one reference file loaded at a time
  - [ ] Raw data dropped after each stage summary written
  - [ ] Stage summaries written to ./reports/ before eviction
  - [ ] Active context <80% of window at all times
  - [ ] Parallel agents capped at 3
</checklist>
