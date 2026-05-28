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
- Manages 19 stages with dependency-aware wave scheduling across companies

## Specialist Agents (17 agents, 19 stages)

| Agent | Stage(s) | Purpose | Per-Company |
|-------|----------|---------|-------------|
| **data-collector** | 1 | Shared data: macro, RS, breadth, themes | No |
| **sector-screener** | 2, 3 | Sub-industry scoring + deep-dive | No |
| **company-screener** | 4 | Company filtering, scoring, ranking | No |
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
| **screening-report-writer** | 17 | Screening overview reports | No |
| **equity-report-writer** | 17 | Per-company deep-dive reports | No |
| **search-agent** | all | Multi-source financial web search | No |
| **market-daily-orchestrator** | daily | Daily market macro report | No |

## Stage Map

### 18-Stage Pipeline

```
Stage 0:  Setup (orchestrator)
Stage 1:  Data Collection (data-collector)
Stage 2:  Sub-Industry Screening (sector-screener ×3 parallel)
Stage 3:  Sub-Industry Deep-Dive (sector-screener ×4 parallel waves)
Stage 4:  Company Screening (company-screener ×3 parallel)
Stage 5:  Financial Health (fundamental-analyst)          ← per-company
Stage 6:  Earnings Quality (fundamental-analyst)          ← per-company, depends 5
Stage 7:  Industry & Competitive (industry-analyst)       ← per-company
Stage 8:  Supply Chain (supply-chain-analyst)             ← per-company, depends 7
Stage 9:  Macro & Geopolitics (macro-analyst)             ← per-company
Stage 10: Valuation (quant-analyst)                       ← per-company, depends 5+7
Stage 11: Market Regime (quant-analyst)                   ← per-company, depends 10
Stage 12: Risk Assessment (risk-analyst)                  ← per-company, depends 10
Stage 13: Alt Data (alt-data-analyst)                     ← per-company
Stage 14: Catalyst (catalyst-analyst)                     ← per-company, depends 13
Stage 15: A-Share (china-market-analyst)                  ← per-company, conditional .SH/.SZ
Stage 16: Scoring & Cross-Check (scorer)
Stage 17: Report Generation (report writers ×parallel)
Stage 18: Best Picks Highlight (equity-report-writer) (report writers ×parallel)
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
| **pipeline** (default) | 0→1→2→3→4→5-15→16→17 | — |
| **screen** | 0→1→2→3→4→17(screening) | 5-16 |
| **analyze** | 0→1→5-15→16→17 | 2-4 |
| **compare** | 0→1→5-15→16(rank)→17(compare) | 2-4 |

### Cross-Company Wave Scheduling

With max 4 concurrent agents and M companies, stages pipeline across companies:
```
T1: [5,7,9,13] → [6,8,10,14] → [11,12] → [15]
T2: [5,7,9,13] → [6,8,10,14] → [11,12] → [15]
T3: [5,7,9,13] → ...

Slot utilization:
[T1:5, T1:7, T1:9, T1:13] → [T1:6, T1:8, T1:10, T1:14] → [T1:11, T1:12, T2:5, T2:7] → ...
```

## Platform-Specific Notes

### Claude Code
The orchestrator uses the `Agent` tool to spawn sub-agents with `subagent_type` and `team_name`. Agents can nest (sub-agents may call search-agent).

### Codex
Agent definitions in `.codex/agents/` use TOML format. Orchestration is skill-embedded — the SKILL.md contains coordination logic.
