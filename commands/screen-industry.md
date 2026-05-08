---
name: screen-industry
description: "Run top-down industry screening using GICS Level 4 (Sub-Industry) as the default classification unit. Identifies the most attractive sub-industries across all sectors, performs deep-dive analysis, and produces a ranked watchlist of the most promising stocks. Designed as a precursor to /stock-analysis:analyze for deep dives on top picks."
---

<purpose>Invoke the industry-screening-orchestrator agent team to perform top-down sector-to-sub-industry-to-company screening using GICS Level 4 (163 sub-industries) as the default atomic screening unit. The orchestrator spawns specialized screener agents — it NEVER performs deep screening directly.</purpose>

<agent-team>
MANDATORY: This command operates as an agent team. You are the orchestrator (industry-screening team lead).

STEP 0 — Create team IMMEDIATELY as the FIRST action (before ANY scripts):
  Claude Code: TeamCreate({ name: "industry-screening-[TIMESTAMP]" })
  Gemini CLI: Team is implicit.

STEP 1 — Spawn data-fetch agent for setup scripts:
  Claude Code: Agent({ subagent_type: "stock-analysis:search-agent", team_name: "industry-screening-[TIMESTAMP]", prompt: "Run screening data fetch..." })
  Gemini CLI: @search-agent Run screening data fetch...

STEP 2+ — Spawn screening agents:
  Claude Code: Agent({ subagent_type: "industry-screening:<agent-name>", team_name: "industry-screening-[TIMESTAMP]", prompt: "..." })
  Gemini CLI: @<agent-name> <task description>

| Agent | Phases | Spawn When |
|-------|--------|------------|
| @search-agent | 0 (data fetch) | Initial setup: macro, RS, persist |
| @sector-screener | 1, 2 | Sector ranking, sub-industry deep-dive analysis |
| @company-screener | 3 | Company filtering, scoring, and ranking within an industry |
| @screening-report-writer | 4 | Synthesizes phase summaries into 3 final screening reports |

Parallel execution (max 3 concurrent):
- Phase 1: Up to 3 @sector-screener agents (sector batches)
- Phase 2: Up to 2 @sector-screener agents (deep-dive on top sub-industries)
- Phase 3: 1-2 @company-screener agents (normal or split by market cap tier)
- Phase 4: 1 @screening-report-writer agent

ENFORCEMENT: The orchestrator MUST NOT run scripts directly. ALL work delegated to sub-agents.
</agent-team>

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
  <step n="0" name="Team Creation (orchestrator)">Create agent team immediately. Identify screening scope.</step>
  <step n="1" name="Spawn Data Fetch">Spawn @search-agent to run macro fetch, RS computation, persist init. Terminate after completion.</step>
  <step n="2" name="Spawn Screeners">Spawn @sector-screener agents for two-pass analysis: score sectors, rank Level 4 sub-industries. Produce unified sub-industry leaderboard.</step>
  <step n="3" name="Spawn Deep Dive">Spawn @sector-screener in deep-dive mode for top 2-3 sub-industries. Validate thesis and map complete company universe.</step>
  <step n="4" name="Spawn Company Screener">Spawn @company-screener for selected sub-industry. Apply quantitative filters, produce ranked watchlist.</step>
  <step n="5" name="Spawn Report Writer & Cleanup">Spawn @screening-report-writer to synthesize all phase summaries into 3 final reports (long/mid/short). Then cleanup: delete ALL intermediate files (phase*.md, sector_rs.json, sub_industry_rs.json, etc.) — only 3 final reports remain. Terminate all agents. Delete team.</step>
</process>

<constraints>
  <constraint>ALL reports MUST be written in Chinese (中文). Technical terms (P/E, EV/EBITDA, ROIC, ticker symbols) may remain in English. GICS names include both English and Chinese. Source citations remain in original language.</constraint>
  <constraint>NEVER perform Phase 1-4 screening/analysis directly — always spawn specialist agents</constraint>
  <constraint>DEFAULT: Always screen at GICS Level 4 (Sub-Industry) granularity</constraint>
  <constraint>Designed as a precursor — after screening, offer to deep-dive top picks with /stock-analysis:analyze</constraint>
  <constraint>All reports saved to ./reports/screening/[SUB_INDUSTRY_CODE]_[long|mid|short]_[YYYY-MM-DD].md (3 files per run)</constraint>
  <constraint>At least 10 companies must pass filters for a valid watchlist</constraint>
  <constraint>Macro data within 30 days freshness; sector data within 90 days</constraint>
  <constraint>Context eviction enforced after each phase completion</constraint>
  <constraint>Reference `references/gics_taxonomy.md` for all GICS classifications</constraint>
</constraints>
