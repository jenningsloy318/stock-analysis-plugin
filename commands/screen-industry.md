---
name: screen-industry
description: "Run top-down industry screening using GICS Level 4 (Sub-Industry) as the default classification unit. Identifies the most attractive sub-industries across all sectors, performs deep-dive analysis, and produces a ranked watchlist of the most promising stocks. Designed as a precursor to /stock-analysis:analyze for deep dives on top picks."
---

<purpose>Invoke the industry-screening-orchestrator to perform top-down sector-to-sub-industry-to-company screening using GICS Level 4 (163 sub-industries) as the default atomic screening unit. Ranks both sectors and sub-industries, deep-dives into the strongest sub-industry niches, screens all public companies in the selected sub-industry, and produces a ranked watchlist.</purpose>

<usage>/industry-screening:screen [SECTOR|all|theme] [options]</usage>

<options>
  --sector [SECTOR]             Focus on a specific GICS sector's sub-industries (skip broad ranking)
  --sub-industry [NAME|CODE]    Focus on a specific GICS Level 4 sub-industry directly
  --theme [THEME]               Screen sub-industries relevant to a theme (e.g., "AI", "clean energy")
  --min-cap [VALUE]             Minimum market cap filter in millions (default: 500)
  --top [N]                     Number of companies in watchlist (default: 15)
</options>

<defaults>
  - Screening granularity: GICS Level 4 (Sub-Industry) — always
  - All 3 horizons (long/mid/short) produced automatically — no need to specify
  - Phase 1 produces sub-industry leaderboard (sectors used internally only)
  - Phase 2 targets specific sub-industries by 8-digit GICS code
  - Level 1/2/3 data included as context within Level 4 sections
</defaults>

<process>
  <step n="1" name="Setup">Determine scope (all sectors / specific sector / theme / specific sub-industry), investment horizon, fetch macro context, compute sector RS AND sub-industry RS, create output directory</step>
  <step n="2" name="Sector & Sub-Industry Screening">Spawn sector-screener agents to perform two-pass analysis: score sectors, then rank all Level 4 sub-industries within top sectors. Produce unified sub-industry leaderboard.</step>
  <step n="3" name="Sub-Industry Deep Dive">Deep-dive on top sub-industries (by GICS Level 4 code) to validate thesis and map complete company universe</step>
  <step n="4" name="Company Screening">Screen all public companies in the selected sub-industry, apply quantitative filters, produce ranked watchlist</step>
  <step n="5" name="Report">Synthesize findings into 3 screening reports (long/mid/short) with sub-industry leaderboard, deep-dive thesis, company watchlist, and parent-level context</step>
</process>

<constraints>
  <constraint>DEFAULT: Always screen at GICS Level 4 (Sub-Industry) granularity</constraint>
  <constraint>Designed as a precursor — after screening, offer to deep-dive top picks with /stock-analysis:analyze</constraint>
  <constraint>All reports saved to ./reports/screening/[SUB_INDUSTRY_CODE]_[long|mid|short]_[YYYY-MM-DD].md (3 files per run)</constraint>
  <constraint>At least 10 companies must pass filters for a valid watchlist</constraint>
  <constraint>Macro data within 30 days freshness; sector data within 90 days</constraint>
  <constraint>Context eviction enforced after each phase completion</constraint>
  <constraint>Reference `references/gics_taxonomy.md` for all GICS classifications</constraint>
</constraints>
