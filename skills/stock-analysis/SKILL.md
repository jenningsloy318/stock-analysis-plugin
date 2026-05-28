---
name: stock-analysis
description: Multi-stage equity research producing long/mid/short-term reports. Supports full deep-dive, quick overview, multi-stock comparison, standalone valuation, and watchlist monitoring. Triggers on "analyze [TICKER]", "deep dive", "investment thesis", "valuation", "compare", "quick overview", "watchlist".
author: Jennings Liu
version: "1.02.01"
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

<purpose>Stock-analysis-orchestrator (team lead) spawns specialist analyst agents in parallel. NEVER performs analysis directly — only spawns, coordinates, scores, and quality-gates. Produces 3 reports per ticker (long/mid/short-term). Supports 5 modes: full, quick, compare, valuation-only, watchlist.</purpose>

<triggers>Triggers on: "analyze [TICKER]", "stock analysis", "deep dive", "investment thesis", "valuation of [TICKER]", "due diligence on [COMPANY]", "compare [T1],[T2]", "quick overview [TICKER]", "watchlist", "check my stocks". Do NOT trigger on: general market commentary, industry screening requests (use industry-screening).</triggers>

<modes>
  <mode name="full" default="true">
    <description>Complete 19-stage deep-dive analysis. All specialist agents, all frameworks. 3 full horizon reports. ~15-30 min.</description>
    <trigger>"analyze [TICKER]", "deep dive", "stock analysis", "investment thesis", "due diligence"</trigger>
    <stages>0→1a+1b+3a→1c+2+3b+CN*→4+5+8b→6+7→8→9+9b→10→11</stages>
    <max-agents>4</max-agents>
  </mode>

  <mode name="quick">
    <description>Rapid triage: fundamental-analyst + quant-analyst + risk-analyst in parallel. 4 dimensions only (Financial Health, Moat, Valuation, Risk). 3 condensed reports with lower confidence ceiling. ~2-5 min.</description>
    <trigger>"quick overview [TICKER]", "quick analysis", "fast check"</trigger>
    <stages>0→1a+6+7+8→10→11</stages>
    <max-agents>3</max-agents>
    <confidence-cap>Medium (skipped stages: capital allocation, supply chain, ESG, catalyst, China, industry deep-dive)</confidence-cap>
  </mode>

  <mode name="compare">
    <description>Side-by-side comparison of 2-5 stocks. Spawns quant-analyst + fundamental-analyst per ticker in parallel. Merges scores into ranked comparison table. ~5-10 min.</description>
    <trigger>"compare [T1],[T2],[T3]", "which is better [T1] or [T2]", "stock comparison"</trigger>
    <process>
      1. Validate tickers (all should share GICS sector alignment)
      2. Spawn search-agent for data fetch (financials, metrics, theme performance for each ticker)
      3. Spawn quant-analyst + fundamental-analyst per ticker in parallel (max 4 concurrent)
      4. Merge scores into side-by-side comparison table ranked by composite
      5. Top-ranked stock is offered for full deep-dive
    </process>
    <constraints>
      - Max 5 stocks per comparison
      - Identical valuation methodology across all stocks
      - ALL output in Chinese (中文)
      - Include 当前股价 column for every stock
    </constraints>
  </mode>

  <mode name="valuation-only">
    <description>Standalone valuation: DCF + comps + reverse DCF + margin of safety. Spawns quant-analyst only. ~2-3 min.</description>
    <trigger>"valuation of [TICKER]", "what's [TICKER] worth", "price target [TICKER]", "DCF [TICKER]"</trigger>
    <process>
      1. Spawn search-agent for fetch_financials, calculate_metrics, forecast, fetch_peer_universe, fetch_theme_performance
      2. Spawn quant-analyst for full valuation (DCF, comps, SOTP, LBO floor, reverse DCF)
      3. Present: intrinsic value range, margin of safety, fair value verdict
    </process>
    <quick-revaluation>
      When a prior full analysis exists (30-90 days old):
      1. Reuse last DCF assumptions from scores.json
      2. Update only: current price, market cap, peer multiples
      3. Recompute margin of safety and flag conviction changes
    </quick-revaluation>
  </mode>

  <mode name="watchlist">
    <description>Check status of previously analyzed stocks. Auto-discovers prior reports from ranked directories. Compares current price to targets, checks kill switches, flags stale reports. ~1-3 min.</description>
    <trigger>"watchlist", "check my stocks", "portfolio status", "how are my stocks doing"</trigger>
    <auto-discovery>
      Scans `./reports/*/NNN-[TICKER]/` to find all prior analyses.
      For each: reads long-term report → extracts conviction, targets, kill switches, catalyst dates.
    </auto-discovery>
    <status-categories>
      - ON TRACK: Price within base-bull range → no action
      - TARGET REACHED: Price at/above bull case → offer profit-taking or target update
      - KILL SWITCH APPROACHING: Trigger condition nearing → flag with specific values
      - THESIS AT RISK: Price below bear case → offer full re-analysis
      - STALE (>90 days): Report expired → offer re-analysis
    </status-categories>
  </mode>
</modes>

<rules>
  <rule name="Report Language">ALL reports MUST be written in Chinese (中文). Technical terms in English. Source citations in original language.</rule>
  <rule name="Price Filter">Focus on growth-stage companies. US < $100, China A-shares < ¥100. Skip filter if user specifies ticker.</rule>
  <rule name="Stock Price Display">Every company in any table/list must include current stock price (当前股价). Format: "$XX.XX" or "¥XX.XX".</rule>
  <rule name="All 3 Horizons">Always produce long/mid/short-term reports. Never ask — always produce all three.</rule>
  <rule name="UV Run">ALL Python scripts run via `uv run python ${PLUGIN_ROOT}/scripts/<script>.py`.</rule>
  <rule name="Ranked Directory Naming">ALL output directories and report files MUST use rank-prefixed names. Format: `NNN-TICKER`. Single stock: `001-[TICKER]`. Compare mode: rank after scoring.</rule>
  <rule name="Run Directory">Each run creates `./reports/YYYYMMDDHHmm/`. Within it: `NNN-[TICKER]/` per stock.</rule>
  <rule name="Numbered Stock Index">Every report MUST include "推荐标的排名" with 001, 002, 003 indices matching directory prefix.</rule>
  <rule name="Tracking JSON">Each run creates `./reports/[RUN_ID]/NNN-[TICKER]/tracking.json`. Update BEFORE advancing stages.</rule>
  <rule name="A-Share Detection">If ticker ends with .SH or .SZ, CN1+CN2 stages are MANDATORY (full mode only).</rule>
</rules>

<agent-team-protocol>
  This skill ALWAYS operates as an agent team. Create team IMMEDIATELY as first action.
  Modes affect which agents are spawned and how many stages run. Full mode uses all 11 specialist agents.
  Quick mode uses fundamental-analyst + quant-analyst + risk-analyst.
  Compare mode uses fundamental-analyst + quant-analyst per ticker.
  Valuation-only mode uses quant-analyst.
  Watchlist mode uses search-agent only.
  ENFORCEMENT: Orchestrator MUST NOT run scripts or analysis directly.
</agent-team-protocol>

<workflow>
  <stage n="0" name="Setup">RUN_ID, tracking.json, team creation. Mode determines stage set.</stage>
  <stage n="1a" name="Financial Health & DuPont" agent="fundamental-analyst">DuPont 5-factor, Piotroski, Lynch categories. Writes stage1a.md.</stage>
  <stage n="1b" name="Capital Allocation" agent="fundamental-analyst">Buffett retention test, Mauboussin scorecard, SBC dilution. Writes stage1b.md. (full mode only)</stage>
  <stage n="1c" name="Quality of Earnings" agent="fundamental-analyst">Beneish M-Score, Montier C-Score, OCF/NI ratio. Writes stage1c.md. (full mode only)</stage>
  <stage n="2" name="Executive & Board" agent="fundamental-analyst">Fisher's 15 Points, insider clusters, compensation. Writes stage2.md.</stage>
  <stage n="3a" name="Industry & Competitive" agent="industry-analyst">Porter's Five Forces, TAM/SAM/SOM, moat. Writes stage3a.md.</stage>
  <stage n="3b" name="Supply Chain Resilience" agent="supply-chain-analyst">Tier 1-3 mapping, HHI, disruption scenarios. Writes stage3b.md. (full mode only)</stage>
  <stage n="4" name="Macro Economics" agent="macro-analyst">Dalio cycle, Four-Box, Fed stance. Writes stage4.md.</stage>
  <stage n="5" name="Geopolitics & Regulation" agent="macro-analyst">CRP risk, sanctions, currency exposure. Writes stage5.md.</stage>
  <stage n="6" name="Valuation" agent="quant-analyst">DCF+Monte Carlo, comps, SOTP, reverse DCF. Writes stage6.md.</stage>
  <stage n="7" name="Market Regime & Positioning" agent="quant-analyst">Weinstein, CANSLIM, sentiment, options. Writes stage7.md.</stage>
  <stage n="8" name="Risk Assessment" agent="risk-analyst">Scenario analysis, Marks, Burry, kill switch. Writes stage8.md.</stage>
  <stage n="8b" name="ESG & Sustainability" agent="risk-analyst">TCFD, carbon pricing, physical/transition risk. Writes stage8b.md. (full mode only)</stage>
  <stage n="9" name="Alt Data & Digital" agent="alt-data-analyst">Web traffic, NLP earnings, channel checks. Writes stage9.md.</stage>
  <stage n="9b" name="Catalyst Intelligence" agent="catalyst-analyst">Catalyst calendar, binary events, PEAD. Writes stage9b.md. (full mode only)</stage>
  <stage n="CN1" name="China Policy" agent="china-market-analyst">Policy sensitivity, 产业政策周期. Writes stageCN1.md. (A-share full mode only)</stage>
  <stage n="CN2" name="China Capital Flows" agent="china-market-analyst">北向资金, 融资融券, 龙虎榜. Writes stageCN2.md. (A-share full mode only)</stage>
  <stage n="10" name="Scoring & Cross-Check" agent="orchestrator">compute_scores.py, cross_check.py, calibrate_conviction.py.</stage>
  <stage n="11" name="Report Generation" agent="equity-report-writer">3 reports in `./reports/[RUN_ID]/NNN-[TICKER]/`. validate_report.py before delivery.</stage>
</workflow>

<parallel-execution>
  Full:        [1a+1b+3a] → [1c+2+3b+CN*] → [4+5+8b] → [6+7] → [8] → [9+9b] → Scoring → [11]
  Quick:       [1a+6+7+8] → Scoring → [11]
  Compare:     [quant-analyst + fundamental-analyst per ticker] → merge → rank
  Valuation:   [data fetch] → [quant-analyst] → verdict
  Watchlist:   [scan reports] → [fetch current data] → [status table]
  Max 4 concurrent agents.
</parallel-execution>

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

<integration>
  <produces>
    - 3 horizon reports → `./reports/[RUN_ID]/NNN-[TICKER]/NNN-[TICKER]_[horizon]_[DATE].md`
    - Stage summaries, scores, calibration, peers, kill switches
  </produces>
  <consumes-from-industry-screening>
    If invoked after screening, load: industry thesis → Stage 3a, macro context → Stage 4, supply chain → Stage 3b.
  </consumes-from-industry-screening>
  <consumes-from-market-daily>
    If market-daily report exists within 24h (via industry-screening --macro), reuse macro/breadth data.
  </consumes-from-market-daily>
  <handoff-to-watchlist>
    After reports delivered, run auto-registered for watchlist. Kill switch conditions are primary triggers.
  </handoff-to-watchlist>
</integration>
