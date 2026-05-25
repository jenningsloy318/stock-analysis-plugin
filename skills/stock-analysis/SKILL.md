---
name: stock-analysis
description: Multi-stage equity research producing long/mid/short-term reports. Triggers on "analyze [TICKER]", "deep dive", "investment thesis", "valuation".
author: Jennings Liu
version: "1.0.55"
license: MIT
---

<platform-paths>
  PLUGIN_ROOT:
    claude: ${CLAUDE_PLUGIN_ROOT}
    gemini: ${extensionPath}
  PLUGIN_DATA:
    claude: ${CLAUDE_PLUGIN_DATA}
    gemini: ${extensionPath}/data
</platform-paths>

<purpose>Stock-analysis-orchestrator (team lead) spawns specialist analyst agents in parallel. NEVER performs analysis directly — only spawns, coordinates, scores, and quality-gates. Produces 3 reports per ticker (long/mid/short-term).</purpose>

<triggers>Triggers on: "analyze [TICKER]", "stock analysis", "deep dive", "investment thesis", "valuation of [TICKER]", "due diligence on [COMPANY]". Do NOT trigger on: general market commentary, non-financial queries.</triggers>

<rules>
  <rule name="Report Language">ALL reports MUST be written in Chinese (中文). Technical terms in English. Source citations in original language.</rule>
  <rule name="Price Filter">Focus on growth-stage companies. US < $100, China A-shares < ¥100. Skip filter if user specifies ticker.</rule>
  <rule name="Stock Price Display">Every company in any table/list must include current stock price (当前股价). Format: "$XX.XX" or "¥XX.XX".</rule>
  <rule name="All 3 Horizons">Always produce long/mid/short-term reports. Never ask — always produce all three. "Quick" only if user explicitly says so.</rule>
  <rule name="UV Run">ALL Python scripts run via `uv run python ${PLUGIN_ROOT}/scripts/<script>.py`. Output to `./reports/YYYYMMDDHHmm/` where YYYYMMDDHHmm is the run start timestamp (e.g., 202605251430).</rule>
  <rule name="Run Directory">Each run creates a unique subdirectory `./reports/YYYYMMDDHHmm/` under the workspace reports folder. RUN_ID is set once at run start and used for all file operations.</rule>
</rules>

<agent-team-protocol>
  This skill ALWAYS operates as an agent team. Create team IMMEDIATELY as first action.

  Step 0: TeamCreate({ name: "stock-analysis-[TICKER]-[YYYYMMDDHHmm]" }). Set RUN_ID = YYYYMMDDHHmm (current timestamp at run start). Create output directory: `./reports/[RUN_ID]/`.
  Step 1: Spawn search-agent to run ALL triage scripts (fetch_financials, fetch_macro, fetch_global_macro, fetch_economic_surprises, fetch_credit, forecast, calculate_metrics, diff_filings, persist.py init). Terminate after completion.
  Steps 2+: Spawn specialist agents per parallel execution map. Each agent writes ./reports/[RUN_ID]/stage[N].md. Terminate each after completion.
  Cleanup: Delete intermediate files; keep only 3 final reports. Delete team.

  ENFORCEMENT: Orchestrator MUST NOT run scripts or analysis directly. All work delegated to sub-agents.
</agent-team-protocol>

<workflow>
  <stage n="0" name="Setup">
    1. Resolve ticker. 2. Set RUN_ID = YYYYMMDDHHmm (current timestamp). 3. Create `./reports/[RUN_ID]/`. 4. Create team → spawn data-fetch agent for all triage scripts. 5. All 3 horizons auto-produced.
  </stage>
  <stage n="1-2" name="Fundamentals" agent="fundamental-analyst">
    Financial health, moat, forensic accounting (Beneish/Altman/Piotroski), executive profiles, capital allocation, insider activity, governance. Writes stage1.md, stage2.md.
  </stage>
  <stage n="3" name="Industry" agent="industry-analyst">
    Product analysis, Porter's Five Forces, competitive landscape, TAM/SAM/SOM, supply chain, unit economics. Writes stage3.md.
  </stage>
  <stage n="4-5" name="Macro" agent="macro-analyst">
    Economic cycle (Dalio), monetary policy, inflation, currency exposure, geopolitics, regulatory, ESG. Writes stage4.md, stage5.md.
  </stage>
  <stage n="6-7" name="Quant" agent="quant-analyst">
    Multi-method valuation (DCF/Monte Carlo/comps/SOTP), technicals, sentiment, institutional flow, market regime, liquidity, short interest, options, factors, seasonality, earnings edge. Writes stage6.md, stage7.md.
  </stage>
  <stage n="8" name="Risk" agent="risk-analyst">
    Risk identification/quantification, scenario analysis, forensic red flags, ODD, kill switch, credit risk, correlation regime, ESG/carbon. Writes stage8.md.
  </stage>
  <stage n="9" name="Alt Data" agent="alt-data-analyst">
    Digital footprint, NLP earnings, transaction data, primary research, channel checks. Writes stage9.md.
  </stage>
  <stage n="10" name="Scoring" agent="orchestrator">
    Run compute_scores.py for deterministic 1-10 scores. Run cross_check.py for contradictions. Run persist.py conviction.
  </stage>
  <stage n="11" name="Reports" agent="equity-report-writer">
    Pre-compute 3 filenames: ./reports/[RUN_ID]/[TICKER]_long_[DATE].md, ./reports/[RUN_ID]/[TICKER]_mid_[DATE].md, ./reports/[RUN_ID]/[TICKER]_short_[DATE].md. Agent reads all stage summaries + scores.json, generates all 3 reports. Run validate_report.py before delivery.
  </stage>
</workflow>

<parallel-execution>
  Long-term:  [1+2+3] → [4+5] → [6+7] → [8] → [9] → Scoring → [11]
  Mid-term:   [4+5+6] → [1+7] → [2+8] → [9] → Scoring → [11]
  Short-term: [6+7+9] → Scoring → [11]
  Quick:      [1+6+7+8] → Scoring → [11]
  Max 3 concurrent agents. Max 2 concurrent script executions.
</parallel-execution>

<stage-depth>
  | Stage | Long-term | Mid-term | Short-term |
  |-------|-----------|----------|------------|
  | 1: Fundamentals | Deep | Standard | Light |
  | 2: Executive | Deep | Standard | Skip (unless insider flags) |
  | 3: Product/Industry | Deep | Standard | Light |
  | 4: Macro | Standard | Deep | Standard |
  | 5: Geopolitics | Standard | Deep | Light |
  | 6: Valuation | Deep | Deep | Deep |
  | 7: Market Regime | Light | Deep | Deep |
  | 8: Risk | Deep | Standard | Light |
  | 9: Alt Data | Light | Standard | Deep |
</stage-depth>

<context-eviction>
  After each stage: write stage summary → persist.py save → drop raw data from context. If context >80%, offload more.
</context-eviction>

<script-failures>
  | Failure | Action |
  |---------|--------|
  | Script exits non-zero | Retry once. If still failing, mark "Data not available" |
  | API key missing | Use fallback (yfinance, web search) |
  | Hard failure (no revenue data, scores fail, validation fails) | Block delivery |
  | Soft failure (optional scripts, search returns empty) | Reduce confidence, proceed |
</script-failures>

<agent-team>
  | Agent | Stages | Purpose |
  |-------|--------|---------|
  | fundamental-analyst | 1, 2 | Financial health, moat, forensic, executive, insider |
  | industry-analyst | 3 | Product, competitive, TAM, supply chain |
  | macro-analyst | 4, 5 | Economic cycle, monetary, geopolitical, regulatory |
  | quant-analyst | 6, 7 | Valuation, technicals, sentiment, regime, options |
  | risk-analyst | 8 | Risk ID/quant, scenarios, forensic, ODD, kill switch |
  | alt-data-analyst | 9 | Digital footprint, NLP, transactions, primary research |
  | equity-report-writer | 11 | Synthesize stage summaries into final reports |
  | search-agent | All | Multi-source financial web search, script execution |
</agent-team>
