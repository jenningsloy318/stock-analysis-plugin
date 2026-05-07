# Stock Analysis Plugin — Agents

## Orchestrator

| Agent | Purpose |
|-------|---------|
| **stock-analyst** | Central coordinator. Spawns specialists, manages parallel execution, enforces quality gates. Never performs deep analysis directly. |

## Specialist Agents

| Agent | Stages | Purpose |
|-------|--------|---------|
| **fundamental-analyst** | 1, 2 | Financial health, moat, forensic accounting, executive profiles, insider activity |
| **industry-analyst** | 3 | Product analysis, Porter's Five Forces, competitive landscape, TAM/SAM/SOM, supply chain |
| **macro-analyst** | 4, 5 | Economic cycle (Dalio), monetary policy, inflation, geopolitics, regulatory, ESG |
| **quant-analyst** | 6 | Multi-method valuation (DCF, comps, SOTP), technicals, sentiment, institutional flow |
| **risk-analyst** | 7 | Risk identification/quantification, scenario analysis, forensic red flags, ODD, kill switch |
| **alt-data-analyst** | 8 | Digital footprint, NLP earnings, transaction data, primary research, channel checks |
| **report-writer** | 9 | Synthesizes stage summaries into final reports with conviction scoring |
| **search-agent** | All | Multi-source financial web search (Firecrawl, Tavily, Tinyfish, XCrawl, Exa) with provenance |

## Parallel Execution Map

```
Long-term:   [1+2+3] → [4+5] → [6] → [7] → [8] → [9]
Mid-term:    [4+5+6] → [1+7] → [2+8] → [9]
Short-term:  [6+8] → [9]
Quick:       [1+6+7] → [9]
```

Max concurrent agents: 3
