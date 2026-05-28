---
name: stock-analysis
description: Multi-stage equity research producing long/mid/short-term reports. Triggers on "analyze [TICKER]", "deep dive", "investment thesis", "valuation".
author: Jennings Liu
version: "1.01.01"
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
  <rule name="UV Run">ALL Python scripts run via `uv run python ${PLUGIN_ROOT}/scripts/<script>.py`. Output to `./reports/YYYYMMDDHHmm/` where YYYYMMDDHHmm is the run start timestamp.</rule>
  <rule name="Ranked Directory Naming">ALL output directories and report files MUST use rank-prefixed names. Format: `NNN-TICKER` where NNN is the zero-padded rank index (001, 002, 003...). Single stock: always `001-[TICKER]`. Multi-stock batch: after all stocks are scored, assign ranks by conviction score descending, then rename directories to `NNN-[TICKER]`. This ensures the folder listing itself shows which stock to buy first — no need to open files to see the ranking.</rule>
  <rule name="Run Directory">Each run creates a unique subdirectory `./reports/YYYYMMDDHHmm/` under the workspace reports folder. Within it, each stock gets `./reports/[RUN_ID]/NNN-[TICKER]/` where NNN is its rank. RUN_ID is set once at run start and used for all file operations.</rule>
  <rule name="Numbered Stock Index">Every report MUST include a "推荐标的排名" section with zero-padded 3-digit indices (001, 002, 003...). The analyzed stock is ALWAYS 001. Peer/alternative stocks follow, ranked by conviction/score descending. The rank index MUST match the directory prefix.</rule>
  <rule name="Tracking JSON">Each run creates `./reports/[RUN_ID]/NNN-[TICKER]/tracking.json` in Stage 0 (NNN = rank, single stock = 001). Orchestrator updates stage status BEFORE advancing. Set current stage to "completed" with timestamp, then next stage to "in_progress".</rule>
  <rule name="A-Share Detection">If ticker ends with .SH or .SZ, CN1+CN2 stages are MANDATORY. Spawn china-market-analyst in parallel with fundamentals.</rule>
</rules>

<agent-team-protocol>
  This skill ALWAYS operates as an agent team. Create team IMMEDIATELY as first action.

  Step 0: RUN_ID = $(date +%Y%m%d%H%M). TeamCreate({ name: "stock-analysis-[TICKER]-[RUN_ID]" }). Create output directory: `./reports/[RUN_ID]/001-[TICKER]/` (single stock: rank is always 001). Create `./reports/[RUN_ID]/001-[TICKER]/tracking.json`. For multi-stock batch: create temp dirs first, then rename with rank prefix after scoring.
  Step 1: Spawn search-agent to run triage scripts (fetch_financials, fetch_macro, fetch_global_macro, fetch_economic_surprises, fetch_credit, forecast, calculate_metrics, diff_filings, persist.py init, fetch_market_breadth, fetch_theme_performance).
  Steps 2+: Spawn specialist agents per parallel execution map. Each agent writes ./reports/[RUN_ID]/stage[N].md.
  Cleanup: Delete intermediate files; keep only 3 final reports. Delete team.

  ENFORCEMENT: Orchestrator MUST NOT run scripts or analysis directly. All work delegated to sub-agents.
</agent-team-protocol>

<workflow>
  <stage n="0" name="Setup">RUN_ID, tracking.json, team creation, data fetch agent spawn.</stage>

  <stage n="1a" name="Financial Health & DuPont" agent="fundamental-analyst">
    Revenue trends, margins (gross/operating/net), FCF generation, leverage, working capital (CCC), ROIC/ROE/ROA with 5-factor DuPont decomposition. Piotroski F-Score. Lynch category classification. Business model quality, customer economics (LTV/CAC, churn, NDR). Segment-level analysis. Writes stage1a.md.
  </stage>

  <stage n="1b" name="Capital Allocation" agent="fundamental-analyst">
    Buffett retention test (market value per $1 retained), Mauboussin capital allocation framework, buyback ROI analysis, M&A track record (ROIC on acquisitions), dividend policy sustainability, SBC dilution analysis, capital structure optimization. Writes stage1b.md.
  </stage>

  <stage n="1c" name="Quality of Earnings" agent="fundamental-analyst">
    Beneish M-Score, Montier C-Score, accruals quality (total accruals / assets), cash conversion (OCF/NI ratio trend), revenue recognition policy audit, expense capitalization analysis, goodwill/intangibles impairment risk. Writes stage1c.md.
  </stage>

  <stage n="2" name="Executive & Board" agent="fundamental-analyst">
    Fisher's 15 Points (management), executive profiles and track records, insider ownership patterns, insider transaction cluster detection, compensation alignment (pay-for-performance), board independence and expertise, governance red flags. Writes stage2.md.
  </stage>

  <stage n="3a" name="Industry & Competitive" agent="industry-analyst">
    Product portfolio mapping (life cycle), Porter's Five Forces, competitive landscape (market share, positioning), TAM/SAM/SOM (top-down + bottom-up), Morningstar moat assessment, BCG matrix for multi-segment, ecosystem mapping. Writes stage3a.md.
  </stage>

  <stage n="3b" name="Supply Chain Resilience" agent="supply-chain-analyst">
    Tier 1-3 supplier mapping, geographic HHI concentration, chokepoint identification (single-source, infrastructure, regulatory), disruption scenario modeling (trade war, blockade, natural disaster, supplier failure, logistics crisis), inventory health, logistics vulnerability. Writes stage3b.md.
  </stage>

  <stage n="4" name="Macro Economics" agent="macro-analyst">
    Dalio Economic Machine cycle position, Four-Box Framework regime, Fed/ECB/PBoC stance, yield curve, inflation dynamics, sector-specific macro drivers, Druckenmiller liquidity assessment. Writes stage4.md.
  </stage>

  <stage n="5" name="Geopolitics & Regulation" agent="macro-analyst">
    CRP country risk, sanctions exposure, trade policy dependency, regulatory framework, currency exposure (revenue mix, DXY correlation, FX EPS impact), government policy (subsidies, procurement). Writes stage5.md.
  </stage>

  <stage n="6" name="Valuation" agent="quant-analyst">
    DCF with Monte Carlo, trading comps, SOTP, Greenblatt Magic Formula, LBO affordability floor, reverse DCF, private market comps, relative value analysis. Writes stage6.md.
  </stage>

  <stage n="7" name="Market Regime & Positioning" agent="quant-analyst">
    Weinstein stage classification, CANSLIM scoring, technicals (trend, momentum, volume), sentiment (put/call, VIX, short interest), institutional flow (13F, 13D, Form 4), market regime (risk-off/speculative), options signals, factor attribution. Writes stage7.md.
  </stage>

  <stage n="8" name="Risk Assessment" agent="risk-analyst">
    Risk identification & quantification (probability × impact), scenario analysis (bull/base/bear), Marks 2nd-level thinking, Soros reflexivity phase, Klarman permanent-vs-temporary impairment, Burry forensic red flags, Taleb antifragility assessment, ODD, kill switch. Writes stage8.md.
  </stage>

  <stage n="8b" name="ESG & Sustainability" agent="risk-analyst">
    TCFD/ISSB alignment, carbon pricing scenarios ($50/$100/$150/tCO2), physical risk (flood, fire, hurricane, sea-level), transition risk (stranded assets), SASB materiality map, social license, governance deep-dive. Writes stage8b.md.
  </stage>

  <stage n="9" name="Alt Data & Digital Signals" agent="alt-data-analyst">
    Digital footprint (web traffic, app rankings, social media, hiring, patents), NLP earnings call (tone, uncertainty, deception), transaction data, Fisher scuttlebutt, primary research (expert networks, channel checks), ARK disruption framework. Writes stage9.md.
  </stage>

  <stage n="9b" name="Catalyst Intelligence" agent="catalyst-analyst">
    Catalyst calendar (earnings, FDA, product, regulatory, M&A), event-driven probability, pre/post-event drift (PEAD), binary event scenario modeling, catalyst sequencing & dependencies, options market signals. Writes stage9b.md.
  </stage>

  <stage n="CN1" name="China Policy & Regulatory" agent="china-market-analyst">
    Policy sensitivity matrix (政策敏感性), industrial policy cycle (产业政策周期), regulatory risk scoring, 专精特新/国产替代 positioning, policy impact quantification. Writes stageCN1.md. MANDATORY for A-shares.
  </stage>

  <stage n="CN2" name="China Capital Flows" agent="china-market-analyst">
    北向资金 flows, 融资融券 margin activity, 龙虎榜 seat analysis, 行业轮动 sector rotation, 游资 hot money tracking, 国家队 national team positioning. Writes stageCN2.md. MANDATORY for A-shares.
  </stage>

  <stage n="10" name="Scoring & Cross-Check" agent="orchestrator">
    Run compute_scores.py for deterministic 1-10 scores (including new dimensions: Capital Allocation, Earnings Quality, Supply Chain Resilience, ESG, Catalyst, China-Specific). Run cross_check.py for contradiction detection. Run calibrate_conviction.py for Bayesian adjustment.
  </stage>

  <stage n="11" name="Report Generation" agent="equity-report-writer">
    3 final reports in `./reports/[RUN_ID]/NNN-[TICKER]/`: NNN-[TICKER]_long_[DATE].md, NNN-[TICKER]_mid_[DATE].md, NNN-[TICKER]_short_[DATE].md. For single stock, NNN = 001. For multi-stock batch, NNN is assigned from the composite ranking after Stage 10 scoring. Run validate_report.py before delivery.
  </stage>
</workflow>

<tracking-json-schema>
File: `./reports/[RUN_ID]/NNN-[TICKER]/tracking.json` (NNN = rank index, e.g., 001 for top pick)
Status values: "pending" | "in_progress" | "completed" | "failed" | "skipped"
</tracking-json-schema>

<parallel-execution>
  Standard:    [1a+1b+3a] → [1c+2+3b+CN*] → [4+5+8b] → [6+7] → [8] → [9+9b] → Scoring → [11]
  Long-term:   [1a+1b+1c+3a] → [2+3b+CN*] → [4+5+8b] → [6+7] → [8] → [9] → [9b] → Scoring → [11]
  Mid-term:    [4+5+6] → [1a+7] → [2+8] → [9+9b] → Scoring → [11]
  Short-term:  [6+7+9+9b] → Scoring → [11]
  Quick:       [1a+6+7+8] → Scoring → [11]
  Max 4 concurrent agents. CN* mandatory for SH/SZ tickers.
</parallel-execution>

<stage-depth>
  | Stage | Long-term | Mid-term | Short-term |
  |-------|-----------|----------|------------|
  | 1a: Financial Health | Deep | Standard | Light |
  | 1b: Capital Allocation | Deep | Standard | Skip |
  | 1c: Earnings Quality | Deep | Light | Skip |
  | 2: Executive & Board | Deep | Standard | Skip (unless insider flags) |
  | 3a: Industry | Deep | Standard | Light |
  | 3b: Supply Chain | Deep | Standard | Light |
  | 4: Macro | Standard | Deep | Standard |
  | 5: Geopolitics | Standard | Deep | Light |
  | 6: Valuation | Deep | Deep | Deep |
  | 7: Market Regime | Light | Deep | Deep |
  | 8: Risk | Deep | Standard | Light |
  | 8b: ESG | Standard | Light | Skip |
  | 9: Alt Data | Light | Standard | Deep |
  | 9b: Catalyst | Standard | Standard | Deep |
  | CN1: China Policy | Deep | Deep | Standard |
  | CN2: China Flows | Deep | Standard | Deep |
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
  | fundamental-analyst | 1a, 1b, 1c, 2 | Financial health, capital allocation, earnings quality, executive |
  | industry-analyst | 3a | Product, competitive, TAM, ecosystem |
  | supply-chain-analyst | 3b | Supply chain mapping, chokepoints, disruption scenarios |
  | macro-analyst | 4, 5 | Economic cycle, monetary, geopolitical, regulatory |
  | quant-analyst | 6, 7 | Valuation, technicals, sentiment, regime, options |
  | risk-analyst | 8, 8b | Risk ID/quant, scenarios, forensic, ODD, kill switch, ESG |
  | alt-data-analyst | 9 | Digital footprint, NLP, transactions, primary research |
  | catalyst-analyst | 9b | Catalyst calendar, event probability, PEAD, binary events |
  | china-market-analyst | CN1, CN2 | A-share policy, northbound flows, margin trading, 龙虎榜 |
  | equity-report-writer | 11 | Synthesize stage summaries into final reports |
  | search-agent | All | Multi-source financial web search, script execution |
</agent-team>
