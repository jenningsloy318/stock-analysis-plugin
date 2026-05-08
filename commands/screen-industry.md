---
name: screen-industry
description: "Run top-down industry screening to identify the most profitable and fastest-growing sectors, drill into the best sub-industries, and produce a ranked watchlist of the most promising stocks. Designed as a precursor to /stock-analysis:analyze for deep dives on top picks."
---

<purpose>Invoke the industry-screening-orchestrator to perform top-down sector-to-company screening. Identifies the most attractive sectors, drills into sub-industries, screens all public companies in the selected industry, and produces a ranked watchlist.</purpose>

<usage>/industry-screening:screen [SECTOR|all|theme] [options]</usage>

<options>
  --horizon [long|mid|short]   Investment horizon (affects weighting; default: mid)
  --sector [SECTOR]             Focus on a specific GICS sector (skip broad ranking)
  --theme [THEME]               Screen sectors relevant to a theme (e.g., "AI", "clean energy")
  --min-cap [VALUE]             Minimum market cap filter in millions (default: 500)
  --top [N]                     Number of companies in watchlist (default: 15)
</options>

<process>
  <step n="1" name="Setup">Determine scope (all sectors / specific sector / theme), investment horizon, fetch macro context, create output directory</step>
  <step n="2" name="Sector Screening">Spawn sector-screener agents to analyze and rank sectors by composite score</step>
  <step n="3" name="Industry Deep Dive">Deep-dive on top sectors to select the single best industry for stock selection</step>
  <step n="4" name="Company Screening">Screen all public companies in the selected industry, apply quantitative filters, produce ranked watchlist</step>
  <step n="5" name="Report">Synthesize findings into screening report with sector ranking, industry thesis, and company watchlist</step>
</process>

<constraints>
  <constraint>Designed as a precursor — after screening, offer to deep-dive top picks with /stock-analysis:analyze</constraint>
  <constraint>All reports saved to ./reports/screening/[SECTOR]_[INDUSTRY]_[YYYY-MM-DD].md</constraint>
  <constraint>At least 10 companies must pass filters for a valid watchlist</constraint>
  <constraint>Macro data within 30 days freshness; sector data within 90 days</constraint>
  <constraint>Context eviction enforced after each phase completion</constraint>
</constraints>
