# Stock Analysis Plugin — Agent Team

## Cross-Platform Support

| Platform | Agent Location | Format | Delegation |
|----------|---------------|--------|------------|
| **Claude Code** | `agents/*.md` | YAML frontmatter + XML tags | `Agent` tool with `subagent_type` |
| **Codex** | `.codex/agents/*.toml` | TOML with `developer_instructions` | Skill-embedded orchestration |

## Orchestrator (Team Lead)

**team-lead** — Unified pipeline coordinator following super-dev team-lead pattern:
- XML-tagged: `<constraints>` with `<constraint-group>`, `<process>`, `<agent-spawn-fields>`, `<quality-gates>`
- NEVER analyzes directly — only spawns, coordinates, and quality-gates
- Manages 25 stages (20 work + 5 validation gates); delegates per-company analysis to company-orchestrators

## Company Orchestrator (Context Isolation Layer)

**company-orchestrator** — Per-company deep-dive manager:
- Spawned by team-lead via async pool (max 4 concurrent — next company spawns as soon as any prior orchestrator finishes; no batch-edge stalls)
- Independently manages ALL stages 5-15 for a single company in its own context window
- Uses dependency-aware wave scheduling internally (3 concurrent analysts max)
- Returns structured completion summary to team-lead upon finishing
- Prevents team-lead context exhaustion when analyzing 10-20 companies

## Specialist Agents (20 agents, 25 stages)

| Agent | Stage(s) | Purpose | Per-Company |
|-------|----------|---------|-------------|
| **data-collector** | 1 | Shared data: macro, RS, breadth, themes | No |
| **sector-screener** | 2, 3 | Sub-industry scoring + deep-dive | No |
| **company-screener** | 4 | Company filtering, scoring, ranking | No |
| **company-orchestrator** | 5-15 | Per-company analysis coordinator | Yes |
| **fundamental-analyst** | 5, 6 | Financial health + earnings quality | Yes |
| **industry-analyst** | 7 | Porter, TAM, moat, competitive | Yes |
| **supply-chain-analyst** | 8 | Supply chain mapping, HHI, disruption | Yes |
| **macro-analyst** | 9 | Dalio, Four-Box, geopolitics, FX | Yes |
| **quant-analyst** | 10, 11 | Valuation + market regime/technicals | Yes |
| **risk-analyst** | 12 | Scenario analysis, forensic, kill switch | Yes |
| **alt-data-analyst** | 13 | Digital footprint, NLP, channel checks | Yes |
| **catalyst-analyst** | 14 | Catalyst calendar, PEAD, event study | Yes |
| **china-market-analyst** | 15 | A-share policy, northbound, margin | Yes (conditional) |
| **scorer** | 16 | Deterministic scoring + cross-check | No |
| **report-validator** | 1.5, 4.5, 16.5, 17.5, 18.5 | Independent validation at 5 checkpoints | No |
| **screening-report-writer** | 17 | Screening overview reports | No |
| **equity-report-writer** | 17, 18 | Per-company deep-dive + best picks | No |
| **roadmap-walker** | walk | Top-down chain decomposition for `--mode walk THEME` (replaces stages 2-16.5) | No |
| **search-agent** | all | Multi-source financial web search | No |
| **market-daily-orchestrator** | daily | Daily market macro report | No |

## Stage Map

### 25-Stage Pipeline (20 work stages + 5 validation gates)

```
Stage 0:    Setup (team-lead) — TeamCreate stock-analysis-[RUN_ID]
Stage 1:    Data Collection (data-collector)
Stage 1.5:  Data Validation (report-validator) — data-freshness
Stage 2:    Sub-Industry Screening (sector-screener ×3 parallel)
Stage 3:    Sub-Industry Deep-Dive (sector-screener ×4 parallel waves)
Stage 4:    Company Screening (company-screener ×3 parallel)
Stage 4.5:  Screening Validation (report-validator) — screening-completeness
Stage 5:    Financial Health (fundamental-analyst)          ← per-company
Stage 6:    Earnings Quality (fundamental-analyst)          ← per-company, depends 5
Stage 7:    Industry & Competitive (industry-analyst)       ← per-company
Stage 8:    Supply Chain (supply-chain-analyst)             ← per-company, depends 7
Stage 9:    Macro & Geopolitics (macro-analyst)             ← per-company
Stage 10:   Valuation (quant-analyst)                       ← per-company, depends 5+7
Stage 11:   Market Regime (quant-analyst)                   ← per-company, depends 10
Stage 12:   Risk Assessment (risk-analyst)                  ← per-company, depends 10
Stage 13:   Alt Data (alt-data-analyst)                     ← per-company
Stage 14:   Catalyst (catalyst-analyst)                     ← per-company, depends 13
Stage 15:   A-Share (china-market-analyst)                  ← per-company, conditional .SH/.SZ
Stage 16:   Scoring & Cross-Check (scorer)
Stage 16.5: Score Validation (report-validator) — score-consistency
Stage 17:   Report Generation (report writers ×parallel)
Stage 17.5: Report Validation (report-validator) — report-quality
Stage 18:   Best Picks Highlight (equity-report-writer)
Stage 18.5: Best Picks Validation (report-validator) — best-picks-completeness
Stage 19:   Cleanup (team-lead) — TeamDelete + remove temp files
```

### Dependency DAG (Per-Company Stages 5-15)

```
Wave 1: [5 + 7 + 9 + 13]  ← all independent, 4 agents
Wave 2: [6 + 8 + 10 + 14] ← 6←5, 8←7, 10←5+7, 14←13
Wave 3: [11 + 12]         ← 11←10, 12←10
Wave 4: [15]              ← all deps, A-share only
```

### Mode Routing

| Mode | Stages Run | Skip |
|------|-----------|------|
| **pipeline** (default) | 0→1→1.5→2→3→4→4.5→5-15→16→16.5→17→17.5→18→18.5→19 | — |
| **screen** | 0→1→1.5→2→3→4→4.5→17→17.5→18→18.5→19 | 5-16.5 |
| **analyze** | 0→1→1.5→5-15→16→16.5→17→17.5→18→18.5→19 | 2-4.5 |
| **compare** | 0→1→1.5→5-15→16(rank)→16.5→17→17.5→18→18.5→19 | 2-4.5 |

### Cross-Company Orchestrator Async Pool

With max 4 concurrent company-orchestrators and M companies:
```
Initial:  spawn company-orch(001), (002), (003), (004) in parallel (run_in_background=true)
Async:    when ANY orchestrator finishes (whichever first), immediately spawn the next pending company
          - pool stays saturated at min(4, remaining) at all times
          - no batch-edge stalls (slow company doesn't block fast ones)
Loop:     until queue empty AND pool empty

Each orchestrator internally: Wave1[5,7,9,13] → Wave2[6,8,10,14] → Wave3[11,12] → Wave4[15]
20-30% wall-clock speedup vs synchronous batches on heterogeneous runtimes.

Team-lead turns for 20 companies: ~11 (vs 220+ without orchestrators)
Each orchestrator has its own 40-turn budget and independent context window.
```

### Walk Mode (Top-down Chain Decomposition)

Triggered by `--mode walk "THEME"` (e.g., `--mode walk "humanoid robotics"`).
- team-lead spawns ONE roadmap-walker agent (replaces stages 2-16.5)
- Walker performs Steps 1-6 of references/frameworks_bottleneck_investing.md:
  roadmap anchor → chain decomposition → chokepoint scoring → candidate selection
  → score_bottleneck_asymmetry.py → walk.md synthesis
- Outputs: walk_roadmap.json, walk_chain.json, walk_candidates.json, walk.md
- Then jumps to Stage 17 (reports) → 17.5 → 18 (best picks) → 18.5 → 19 (cleanup)
- SKIPS the screening pipeline AND per-company deep-dive

## Platform-Specific Notes

### Claude Code
The orchestrator uses the `Agent` tool to spawn sub-agents with `subagent_type` and `team_name`. Agents can nest (sub-agents may call search-agent).

### Codex
Agent definitions in `.codex/agents/` use TOML format. Orchestration is skill-embedded — the SKILL.md contains coordination logic.
