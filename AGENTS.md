# Stock Analysis Plugin — Agent Team

## Cross-Platform Support

This plugin provides an agent team that works across both Claude Code and Gemini CLI:

| Platform | Agent Location | Format | Delegation |
|----------|---------------|--------|------------|
| **Claude Code** | `agents/*.md` | YAML frontmatter + markdown body | `Agent` tool with `subagent_type` |
| **Gemini CLI** | `agents/*.md` (extension root) | YAML frontmatter + markdown body | Auto-delegation or `@agent_name` |
| **Codex** | `.codex/agents/*.toml` | TOML with `developer_instructions` | Skill-embedded orchestration |

The `agents/` directory is shared between Claude and Gemini — both platforms read the same files. Gemini-specific fields (`kind`, `tools`, `max_turns`, `timeout_mins`) are ignored by Claude; Claude-specific content (XML body) is used as the system prompt by Gemini.

## Orchestrators

| Agent | Purpose |
|-------|---------|
| **stock-analyst** | Central coordinator for stock deep-dive analysis. Spawns specialists, manages parallel execution, enforces quality gates. Never performs deep analysis directly. |
| **industry-screening-orchestrator** | Central coordinator for top-down industry screening. Spawns sector-screener and company-screener agents, ranks sectors and companies, produces screening reports with watchlists. Never performs deep screening directly. |

## Specialist Agents

| Agent | Stages/Phases | Purpose |
|-------|---------------|---------|
| **fundamental-analyst** | 1, 2 | Financial health, moat, forensic accounting, executive profiles, insider activity |
| **industry-analyst** | 3 | Product analysis, Porter's Five Forces, competitive landscape, TAM/SAM/SOM, supply chain |
| **macro-analyst** | 4, 5 | Economic cycle (Dalio), monetary policy, inflation, geopolitics, regulatory, ESG |
| **quant-analyst** | 6, 7 | Multi-method valuation (DCF, comps, SOTP), technicals, sentiment, institutional flow, market regime & positioning (risk-off/speculative) |
| **risk-analyst** | 8 | Risk identification/quantification, scenario analysis, forensic red flags, ODD, kill switch |
| **alt-data-analyst** | 9 | Digital footprint, NLP earnings, transaction data, primary research, channel checks |
| **equity-report-writer** | 10 | Synthesizes stage summaries into final reports with conviction scoring |
| **search-agent** | All | Multi-source financial web search (Firecrawl, Tavily, Tinyfish, XCrawl, Exa) with provenance |
| **sector-screener** | S1, S2 | Sector growth/profitability/valuation analysis, sub-industry deep-dive, Porter's Five Forces, TAM, key player mapping |
| **company-screener** | S3 | Quantitative company filtering, multi-factor composite scoring, ranked watchlist generation with investment theses |
| **screening-report-writer** | S4 | Synthesizes screening phase summaries into final reports with conviction scoring and stock-analysis handoff |

## Parallel Execution Map

### Stock Analysis (deep-dive per ticker)
```
Long-term:   [1+2+3] → [4+5] → [6+7] → [8] → [9] → Scoring → [10]
Mid-term:    [4+5+6] → [1+7] → [2+8] → [9] → Scoring → [10]
Short-term:  [6+7+9] → Scoring → [10]
Quick:       [1+6+7+8] → Scoring → [10]
```

### Industry Screening (top-down funnel)
```
Broad:  [S1 batch A + S1 batch B + S1 batch C] → [S2 top sector A + S2 top sector B] → [S3] → Report
Single: [S1] → [S2] → [S3] → Report
Theme:  [S1 themed] → [S2] → [S3] → Report
```

Max concurrent agents: 3

## Platform-Specific Notes

### Claude Code

The orchestrator (`stock-analyst` or `industry-screening-orchestrator`) uses the `Agent` tool to spawn sub-agents with `subagent_type` matching the agent names. Agents can nest (sub-agents may call search-agent).

### Gemini CLI

The orchestrator auto-delegates to sub-agents based on their `description` field, or users can force delegation with `@agent_name` syntax. **Important**: Gemini sub-agents cannot call other sub-agents (single-level nesting only). The search-agent must be called directly by the orchestrator on behalf of specialists.

### Codex

Agent definitions in `.codex/agents/` use TOML format with `developer_instructions`. Orchestration is skill-embedded — the SKILL.md contains the coordination logic. Codex plugins do not have native agent team spawning; the agent files serve as configuration reference.
