---
name: stock-analyze
description: "Run full multi-stage equity research analysis on a stock ticker. Always produces all 3 report types (Long-term, Mid-term, Short-term) automatically."
---

<purpose>Invoke the stock-analyst orchestrator agent team to perform full multi-stage equity research. Always produces all 3 report horizons (long/mid/short) from a single data-collection pass. The orchestrator spawns specialized analyst agents for each stage — it NEVER performs deep analysis directly.</purpose>

<agent-team>
MANDATORY: This command operates as an agent team. You are the orchestrator (stock-analyst team lead).

After Step 0 (Triage), spawn sub-agents for ALL analysis stages using:
  Claude Code: Agent({ subagent_type: "stock-analysis:<agent-name>", prompt: "..." })
  Gemini CLI: @<agent-name> <task description>

| Agent | Stages | Spawn When |
|-------|--------|------------|
| @fundamental-analyst | 1-2 | Company financials, moat, executive/insider analysis |
| @industry-analyst | 3 | Competitive landscape, Porter's Five Forces, TAM/SAM |
| @macro-analyst | 4-5 | Economic cycle, monetary policy, geopolitics |
| @quant-analyst | 6-7 | Valuation (DCF, comps), technicals, market regime |
| @risk-analyst | 8 | Risk quantification, scenarios, forensic red flags |
| @alt-data-analyst | 9 | Web traffic, app data, NLP earnings, social sentiment |
| @search-agent | All | Financial web search when specialist agents need data |
| @equity-report-writer | 10 | Synthesize stage summaries into final 3 reports |

Parallel execution (max 3 concurrent):
- Full run: [1+2+3] → [4+5] → [6+7] → [8] → [9] → Scoring → [10]
- Quick: [1+6+7+8] → Scoring → [10]
</agent-team>

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
  <step n="1" name="Triage (orchestrator direct)">Identify ticker, check earnings calendar, create output directory, run initial scripts (fetch_financials.py, fetch_macro.py, calculate_metrics.py, forecast.py)</step>
  <step n="2" name="Spawn Agents">Spawn analyst sub-agents per parallel execution rules — each writes its stage summary to ./reports/[TICKER]/stage[N].md</step>
  <step n="3" name="Scoring (orchestrator direct)">Run compute_scores.py for deterministic component scores, then cross_check.py for contradiction detection</step>
  <step n="4" name="Spawn Report Writer">Spawn @equity-report-writer to synthesize stage summaries into 3 final reports (long/mid/short)</step>
  <step n="5" name="Quality Gate (orchestrator direct)">Run validate_report.py, verify fact integrity for each report</step>
</process>

<constraints>
  <constraint>NEVER perform Stages 1-9 analysis directly — always spawn specialist agents</constraint>
  <constraint>If earnings within 14 days, warn user before proceeding</constraint>
  <constraint>If earnings within 3 days, recommend waiting unless user overrides</constraint>
  <constraint>All reports saved to ./reports/[TICKER]/[TICKER]_[long|mid|short]_[YYYY-MM-DD].md (3 files)</constraint>
  <constraint>Context eviction enforced after each stage completion</constraint>
</constraints>
