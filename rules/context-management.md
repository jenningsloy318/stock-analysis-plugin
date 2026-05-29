---
name: context-management
description: "Rules for managing context window during multi-stage analysis: progressive disclosure, eviction protocol, and parallel execution limits"
---

<purpose>Prevent context exhaustion during the 25-stage pipeline by enforcing progressive reference loading, stage-level data eviction, async-pool parallelism, and per-company context isolation via company-orchestrator agents.</purpose>

<directives>
  <directive name="Progressive Loading">Load reference files on-demand per stage. Only one reference file active at a time. Drop previous stage's reference before loading next.</directive>
  <directive name="Stage Eviction">After each stage: write summary to `./reports/[RUN_ID]/NNN-[TICKER]/stage[N].md` (per-company stages 5-15) or `./reports/[RUN_ID]/stage[N].md` (shared stages 1-4, 16-19). Drop raw data (SEC filings, full transcripts, raw financials, full search results). Retain only: key metrics table, stage scores, 3-sentence narrative per sub-section.</directive>
  <directive name="Context Budget">Maximum active context: <80% of window. If approaching limit, offload intermediate data to temp files. At Stage 16 (scoring) and Stage 17 (report writing), read stage summaries — never raw data.</directive>
  <directive name="Parallel Limits">Cap company-orchestrator agents at 4 concurrent (async pool — next spawns when any prior finishes). Within a company-orchestrator, cap analyst agents at 3 concurrent per wave. Sector-screener Stage 2 runs in 3 parallel batches of ~54 sub-industries; Stage 3 caps at 4 parallel deep-dives.</directive>
  <directive name="Per-Company Isolation">For stages 5-15, team-lead delegates to company-orchestrator agents (one per company). Each orchestrator owns its own context window — team-lead receives only a compressed COMPANY_ORCHESTRATOR_COMPLETE summary (~1-1.5k tokens) and never sees per-company raw data.</directive>
  <directive name="Reference Loading Schedule">
    - frameworks_value_growth.md: Stages 5, 6, 7
    - frameworks_macro_quant.md: Stages 9, 10, 11
    - frameworks_risk_alt.md: Stages 12, 13
    - frameworks_narrative_structure.md: Stages 10, 14
    - frameworks_taleb_graham.md: Stage 12 (kill switch / fragility)
    - frameworks_behavioral.md: Stage 13 (alt data + reflexivity)
    - frameworks_bottleneck_investing.md: Stages 8, 10 (Step 3c), and walk mode
    - institutional_odd.md: Stage 12 (operational due diligence)
    - sector_metrics.md: Stages 1-4 (after GICS identification)
    - equity_report_templates.md: Stage 17 (per-company reports)
    - screening_report_templates.md: Stage 17 (screening reports)
    - international_markets.md: Stage 9, 15 (non-US companies)
  </directive>
</directives>

<checklist>
  - [ ] Only one reference file loaded at a time per stage
  - [ ] Raw data dropped after each stage summary written
  - [ ] Stage summaries written to `./reports/[RUN_ID]/NNN-[TICKER]/stage[N].md` before eviction
  - [ ] Active context <80% of window at all times
  - [ ] Company-orchestrators capped at 4 concurrent (async pool, not synchronous batches)
  - [ ] Analyst agents within an orchestrator capped at 3 concurrent per wave
  - [ ] team-lead never holds per-company raw data — only compressed orchestrator summaries
</checklist>
