---
name: industry-screening
description: Top-down GICS Level 4 sub-industry screening funnel. Produces ranked watchlists. Triggers on "screen sectors", "best industries", "top-down screening", "sector rotation".
author: Jennings Liu
version: "1.0.49"
license: MIT
---

# Industry Screening — Top-Down Sub-Industry Funnel (GICS Level 4)

## Overview

Industry-screening-orchestrator (team lead) spawns specialist screener agents in parallel. NEVER performs analysis directly. Uses GICS Level 4 (Sub-Industry, 163 classifications) as the ONLY screening unit. Reports present flat sub-industry leaderboards — no Level 1/2/3 grouping as standalone sections (those appear only as context within Level 4 entries).

**Report language:** Chinese (中文). Technical terms in English. GICS names: "Semiconductors (半导体)".
**Price filter:** US < $100, China A-shares < ¥100. Filter before watchlist ranking.

## Script Execution

<platform-paths>
  PLUGIN_ROOT:
    claude: ${CLAUDE_PLUGIN_ROOT}
    gemini: ${extensionPath}
  PLUGIN_DATA:
    claude: ${CLAUDE_PLUGIN_DATA}
    gemini: ${extensionPath}/data
</platform-paths>

All Python scripts run via `uv run python ${PLUGIN_ROOT}/scripts/<script>.py`. Output to `./reports/screening/`.

## Agent Team Activation

This skill ALWAYS operates as an agent team. Create team IMMEDIATELY as first action.

**Step 0:** `TeamCreate({ name: "industry-screening-[TIMESTAMP]" })`
**Step 1:** Spawn `search-agent` to run setup scripts (fetch_macro, fetch_economic_surprises, compute_sector_rs, persist.py init). Terminate after completion.
**Steps 2+:** Spawn screener agents per parallel execution map. Each writes phase summaries. Terminate each after completion.
**Cleanup:** Delete intermediate files; keep only 3 final reports. Delete team.

ENFORCEMENT: Orchestrator MUST NOT run scripts or analysis directly. All work delegated to sub-agents.

## Workflow

### Phase 0: Setup (orchestrator)
1. Determine scope: all sectors / specific sector / theme. Default: ask user.
2. All 3 horizons produced automatically (long/mid/short).
3. Run macro fetch + economic surprises + sector/sub-industry RS + persist.py init + source coverage plan.
4. Load `references/gics_taxonomy.md`, `references/data_source_matrix.md`.

### Phase 1: Sub-Industry Screening
Spawn up to 3 `sector-screener` agents in parallel (batched by parent sector). Each screens all sub-industries in its batch via two-pass analysis:
- **Pass 1:** Growth, Profitability, Valuation, Macro Fit, Innovation, Regulatory, Capital Flows, Relative Strength, Cyclicality, Constituent Quality, Supply/Demand Cycle
- **Pass 2:** Rank sub-industries within above-median sectors by RS, growth, structural attractiveness, concentration, investable depth

Orchestrator synthesizes batch outputs into unified **sub-industry leaderboard** (top 15-20, flat ranked, no sector grouping). Composite weights per horizon:

| Dimension | Long-term | Mid-term | Short-term |
|-----------|-----------|----------|------------|
| Growth | 25% | 20% | 10% |
| Profitability | 20% | 15% | 5% |
| Valuation | 10% | 15% | 10% |
| Macro Fit | 10% | 15% | 10% |
| Innovation | 15% | 10% | 5% |
| Regulatory | 5% | 5% | 5% |
| Capital Flows | 5% | 5% | 20% |
| Relative Strength | 5% | 10% | 20% |
| Cyclicality | 5% | 5% | 5% |
| Constituent Quality | 0% | 0% | 10% |
| Supply/Demand Cycle | 0% | 0% | 0% |

### Phase 2: Sub-Industry Deep Dive
Spawn 1 `sector-screener` per top sub-industry (max 2 parallel). Each analyzes: sub-industry definition, company universe, competitive dynamics (Porter), growth catalysts, barriers to entry, TAM, key players, supply chain, life cycle, profit pool, adoption curve. Writes `./reports/screening/deepdive-[CODE]-[NAME].md`.

### Phase 3: Company Screening
Spawn 1-2 `company-screener` agents. Screen all public companies in selected sub-industry with quantitative filters (market cap >$500M, revenue growth >median, positive FCF, ROIC>WACC). Composite score: Growth (20%), Profitability (20%), Moat (20%), Valuation (15%), Management (10%), Risk (10%), Liquidity (5%). Writes `./reports/screening/companies-[CODE].md`.

### Phase 4: Reports
Spawn `screening-report-writer`. Pre-compute filenames: `[SUB_INDUSTRY_CODE]_long_[DATE].md`, etc. Agent synthesizes all phase summaries, produces 3 horizon reports. Structure: Executive Summary → Macro Context → Sub-Industry Leaderboard → Deep Dive → Company Watchlist → Next Actions → Risks → Methodology Appendix.

## Parallel Execution

```
Broad:  [S1 batch A + S1 batch B + S1 batch C] → [S2 top A + S2 top B] → [S3] → Report
Single: [S1] → [S2] → [S3] → Report
Theme:  [S1 themed] → [S2] → [S3] → Report
```
Max 3 concurrent agents.

## Phase Depth Allocation

| Phase | Broad Screen | Single Sector | Thematic |
|-------|-------------|---------------|----------|
| 1: Sub-Industry Screening | Full (3 batches) | Light (1 sector) | Medium (3-5 sectors) |
| 2: Deep Dive | Top 2-3 sub-industries | Top 2 | Top 2 |
| 3: Company Screening | Top 1-2 sub-industries | Top 1-2 | Top 1-2 |
| 4: Report | Full | Full | Full |

## Context Eviction Protocol

After each phase: write phase summary → `persist.py save` → drop raw data from context. If context >80%, offload more.

## Pre-Delivery Checklist

Verify: macro ≤30d fresh, sub-industry data ≤90d fresh, leaderboard ≥10 sub-industries, NO Level 1/2/3 standalone sections, selected sub-industry has structural thesis with GICS code, watchlist ≥10 companies, all metrics cited with source+date, Chinese report, no invented data.

## Agent Team

| Agent | Phases | Purpose |
|-------|--------|---------|
| sector-screener | 1, 2 | Sector ranking, sub-industry deep-dive |
| company-screener | 3 | Company filtering, scoring, ranking |
| screening-report-writer | 4 | Synthesize phases into final reports |
| search-agent | All | Financial web search, script execution |

## Integration with stock-analysis

After screening: "Top-ranked companies can be deep-dived with the stock-analysis skill. Run full equity research on any ticker?" Macro context and industry thesis feed directly into stock-analysis Stages 4 and 3.
