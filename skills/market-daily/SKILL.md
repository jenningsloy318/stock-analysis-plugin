---
name: market-daily
description: "Generate daily US stock market macro report. Spawns market-daily-orchestrator agent to fetch breadth, theme performance, macro data, and synthesize a comprehensive daily report in Chinese."
---

<purpose>Daily US stock market macro report generation. Combines market breadth indicators, theme/style ETF performance, sector rotation data, macro environment, and institutional flows into a structured Chinese-language daily report suitable for pre-market review and trading preparation.</purpose>

<triggers>Triggers on: "market daily", "daily report", "美股日报", "market breadth", "market overview", "daily market", "今日市场".</triggers>

<agent-team>
MANDATORY: This command operates via the orchestrator agent. You MUST spawn @market-daily-orchestrator — never run scripts directly.

The orchestrator will:
1. Run fetch_theme_performance.py for sector/theme/style/index data
2. Run fetch_market_breadth.py for breadth indicators (VIX, credit, constituent breadth)
3. Run fetch_macro.py for macro context
4. Synthesize all data into a structured daily report in Chinese

Report sections produced:
- 0. 今日一句话总结 (One-sentence summary)
- 1. 大盘表现总览 (Index performance)
- 2. 板块与主题表现 (Sector & theme performance)
- 3. 市场宽度 (Market breadth)
- 4. 宏观环境 (Macro environment)
- 5. 资金流与情绪 (Fund flows & sentiment)
- 6. 技术面 (Technical analysis)
- 7. 板块轮动判断 (Sector rotation judgment)
- 8. 风险提示 (Risk alerts)
- 9. 明日观察清单 (Tomorrow's watchlist)
</agent-team>

<usage>/stock-analysis:market-daily</usage>

<process>
  <step n="0" name="Spawn Orchestrator">Spawn @market-daily-orchestrator agent. Pass no arguments — it auto-discovers today's date.</step>
  <step n="1" name="Wait for Report">Orchestrator runs all scripts and synthesizes report. Output goes to ./reports/[RUN_ID]/market-daily_[DATE].md</step>
</process>

<data-sources>
| Script | Data Provided |
|--------|--------------|
| `fetch_theme_performance.py` | 11 sector ETFs, 7 theme groups, 5 style factors, macro ETFs, specialty ETFs, indices, regime summary |
| `fetch_market_breadth.py` | S&P 500/Nasdaq 100 breadth (% above MAs, A/D, new highs/lows, McClellan), VIX term structure, credit spreads |
| `fetch_macro.py` | 2Y/10Y Treasury yields, Fed funds, CPI, employment, GDP, ISM, LEI from FRED |
</data-sources>

<output-format>
Report language: Chinese (中文). Technical terms in English.
Filename: `market-daily_[YYYY-MM-DD].md`
Location: `./reports/[RUN_ID]/`
</output-format>
