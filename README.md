# Stock Analysis Plugin

Multi-stage institutional equity research plugin for **Claude Code** and **OpenAI Codex**. A single unified skill — `stock-analysis` — produces long/mid/short-term reports synthesizing methodologies from 14 investment frameworks (Buffett, Munger, Dalio, Soros, Lynch, Fisher, Marks, Druckenmiller, Greenblatt, Burry, ARK, Mauboussin, Damodaran, Taleb, Graham).

## Installation

### Claude Code

```bash
claude plugin marketplace add jenningsloy318/stock-analysis-plugin
claude plugin install stock-analysis@stock-analysis
```

### OpenAI Codex

```bash
codex plugin marketplace add jenningsloy318/stock-analysis-plugin
```


## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Setup

```bash
# Install dependencies with uv (creates .venv automatically)
uv sync

# Run scripts via uv
uv run python scripts/fetch_financials.py AAPL --years 5
```

Or with pip:

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
pip install -r scripts/requirements.txt
```

### API Keys

Set as environment variables. The scripts read them at runtime.

| Key | Required | Purpose | Get Key |
|-----|----------|---------|---------|
| `FRED_API_KEY` | Yes | Macro indicators (GDP, CPI, rates, ISM Services PMI, JOLTS, LEI, C&I Loans) | [fred.stlouisfed.org](https://fred.stlouisfed.org/docs/api/api_key.html) |
| `FINNHUB_API_KEY` | Yes | Sentiment, insider, earnings, analyst, estimate revisions | [finnhub.io](https://finnhub.io/) |
| `REDDIT_CLIENT_ID` | No | Social sentiment (Reddit) | [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps) |
| `REDDIT_CLIENT_SECRET` | No | Social sentiment (Reddit) | Same as above |
| `FMP_API_KEY` | No | Financial data fallback | [financialmodelingprep.com](https://financialmodelingprep.com/) |
| `POLYGON_API_KEY` | No | Real-time data fallback | [polygon.io](https://polygon.io/) |

**No API key required for:** `fetch_cot.py` (CFTC public data), `fetch_technicals.py` (yfinance), `fetch_alternatives.py` (public web data).

```bash
export FRED_API_KEY="your-key"
export FINNHUB_API_KEY="your-key"
```


## Commands

One unified skill with 5 modes. Dispatch by **explicit `--mode` flag** (authoritative) OR **natural-language trigger phrase**. The `--mode` flag always overrides trigger phrases when both present.

### stock-analysis (5 modes)

| Mode | Flag | Positional / args | Trigger phrases | What it does |
|------|------|-------------------|-----------------|--------------|
| **pipeline** *(default)* | `--mode pipeline` *(or omit)* | `--top-industry 5 --total-company 10` | "find best stocks", "top stocks", "全面筛选" | Screen 163 sub-industries → pick top companies → deep-dive each |
| **screen** | `--mode screen` | `--top-industry 30` | "screen sectors", "筛选行业", "best industries" | Sub-industry screening + company watchlist, no deep-dive |
| **analyze** | `--mode analyze` | `TICKER [TICKER...]` (positional) | "analyze AAPL", "deep dive TSLA", "investment thesis NVDA", "DCF AMD" | Full 11-stage deep-dive on specific ticker(s) |
| **compare** | `--mode compare` | `T1,T2[,T3,...]` (comma-list) | "compare AAPL,MSFT,GOOGL", "NVDA vs AMD" | Side-by-side 2-5 stocks, ranked by composite score |
| **walk** | `--mode walk` | `THEME` (quoted multi-word) | "walk the chain for [theme]", "chokepoint analysis [theme]", "瓶颈分析" | Top-down chain decomposition: anchor demand roadmap → walk supply chain → score chokepoints → rank candidates by asymmetry composite. Universal (AI infra, EV, robotics, defense, solar, biopharma, grid, semi capex, materials). |

**Dispatch order** (Stage 0): `--mode <name>` > trigger phrase > default(pipeline). Mode names: `pipeline | screen | analyze | compare | walk`.

**Invocation examples**:

```
# Flag form (explicit, scriptable)
stock-analysis                                                  # pipeline (default)
stock-analysis --top-industry 5 --total-company 12                           # pipeline
stock-analysis --mode pipeline --top-industry 5 --total-company 12           # pipeline (explicit)
stock-analysis --mode screen --top-industry 30                               # screen 30 sub-industries
stock-analysis --mode analyze NVDA                              # single deep-dive
stock-analysis --mode analyze NVDA AMD INTC                     # multi-ticker deep-dive
stock-analysis --mode compare NVDA,AMD,INTC                     # comparison
stock-analysis --mode walk "humanoid robotics"                  # bottleneck walk
stock-analysis --mode walk "AI optical interconnect" --top-industry 7

# Phrase form (natural)
"find best stocks"                                              # → pipeline
"screen sectors for top 10 industries"                          # → screen
"deep dive NVDA"                                                # → analyze
"compare NVDA vs AMD"                                           # → compare
"walk the chain for rare-earth permanent magnets"               # → walk
```

### Parameters

| Parameter | Default | Range | Used by | Description |
|-----------|---------|-------|---------|-------------|
| `--top-industry` | 5 (pipeline) / 30 (screen) / 7 (walk) | 1-163 (pipeline, screen) / 1-20 (walk) | pipeline, screen, walk | Number of top sub-industries (pipeline/screen) or candidate companies (walk). Walk caps at 20 because candidates are individual companies in chokepoint layers, not GICS sub-industries. |
| `--total-company` | 10 | 1-40 | pipeline | Total companies to deep-dive, selected by score across ALL sub-industries (not quota per sub-industry). Cap raised to 40 — performance-driven, raise only if you can wait (40 companies × 11 stages = 440 agent runs minimum). |

Company distribution: top M companies are selected by score across ALL top-N sub-industries — not equally distributed. Higher-scoring sub-industries naturally contribute more companies.

### How the Pipeline Works

```
Stage 0:    Setup — TeamCreate stock-analysis-[RUN_ID] + tracking
Stage 1:    Data Collection (shared data fetched ONCE)
Stage 1.5:  Data Validation ✓
Stage 2:    Screen all 163 GICS Level 4 → top N sub-industries
Stage 3:    Deep-dive sub-industries + screen companies → top M
Stage 4:    Company Screening
Stage 4.5:  Screening Validation ✓
Stage 5-15: Analysis branches (max 4 parallel)
  For each company: fundamentals → industry → macro → valuation → risk → alt-data
Stage 16:   Scoring & cross-check
Stage 16.5: Score Validation ✓
Stage 17:   Report generation (3 horizons × each output)
Stage 17.5: Report Validation ✓
Stage 18:   Best Picks highlight summary
Stage 18.5: Best Picks Validation ✓
Stage 19:   Cleanup — TeamDelete + remove temp files
```

All reports produced in **Chinese (中文)**. 3 horizons always generated.

## Architecture

One orchestrator manages 20 specialist agents across 25 pipeline stages (20 work + 5 independent validation gates). All work is delegated — the orchestrator never performs analysis directly. The `report-validator` agent independently validates data freshness, screening completeness, scoring consistency, and report quality at 5 checkpoints.

```
stock-analysis (5 modes: pipeline / screen / analyze / compare / walk)
┌────────────────────────────────────────────────────────────┐
│  team-lead (unified team lead)           │
│  Routes mode → delegates to specialist agents              │
└──────────┬─────────────────────────────────────────────────┘
           │
    ┌──────▼──────┬──────────┬──────────┬──────────┐
    │ Screening   │ Analysis Branches (max 4 parallel)       │
    │             │          │          │          │
    │ sector-     │fundament │ industry │ quant-   │
    │ screener    │analyst   │ analyst  │ analyst  │
    │ company-    │macro-    │ supply-  │ risk-    │
    │ screener    │analyst   │ chain    │ analyst  │
    │ screening-  │ alt-data-│ analyst  │ catalyst-│
    │ report-     │analyst   │          │ analyst  │
    │ writer      │          │ china-   │          │
    │             │          │ market   │          │
    └─────────────┴──────────┴──────────┴──────────┘
           │
    equity-report-writer + search-agent (shared)
```

### Output Convention

All runs use timestamped directories with ranked prefixes:
```
reports/
├── 202605281430/              ← RUN_ID = YYYYMMDDHHmm
│   ├── SCREEN_long_2026-05-28.md    ← screening overview
│   ├── SCREEN_mid_2026-05-28.md
│   ├── SCREEN_short_2026-05-28.md
│   ├── 001-AAPL/              ← top-ranked company
│   │   ├── 001-AAPL_long_2026-05-28.md
│   │   ├── 001-AAPL_mid_2026-05-28.md
│   │   └── 001-AAPL_short_2026-05-28.md
│   └── 002-TSLA/              ← second-ranked company
```

## Directory Structure

```
stock-analysis-plugin/
├── .claude-plugin/          # Claude Code manifests
├── .codex-plugin/           # OpenAI Codex manifest
├── .codex/                  # Codex agent configs (TOML)
├── plugin.json              # Antigravity plugin manifest
├── CLAUDE.md                # Plugin rules & philosophy
├── AGENTS.md                # Agent index
├── agents/                  # Specialist agent definitions (MD)
├── skills/                  # Unified skill
├── scripts/                 # Python analysis scripts
├── references/              # Analysis framework docs
├── rules/                   # Modular quality guidelines
└── docs/                    # Requirements & design docs
```

## Analyst Methodologies (14 Frameworks)

| Framework | Thinker | Applied To |
|-----------|---------|------------|
| Four Filters + Margin of Safety | Buffett/Munger | Long-term moat & value |
| 15 Points + Scuttlebutt | Fisher | Growth quality assessment |
| Six Categories + PEG | Lynch | Stock classification |
| Economic Machine + Four-Box | Dalio | Macro regime positioning |
| Reflexivity Model | Soros | Self-reinforcing dynamics |
| Macro-Micro Integration | Druckenmiller | Position sizing & timing |
| Magic Formula | Greenblatt | Relative value screening |
| SEC Deep-Dive + Forensics | Burry | Accounting red flags |
| Second-Level Thinking | Marks | Risk assessment & cycle |
| Disruption + Wright's Law | ARK | Technology S-curve |
| Expectations Investing + CAP | Mauboussin | Reverse DCF, capital allocation |
| Narrative-to-Numbers | Damodaran | Story → model translation |
| Antifragility + Via Negativa | Taleb | Optionality, fragility scoring |
| Deep Value + Net-Nets | Graham | Margin of safety, acquirer's multiple |

## Report Types

- **Long-term (1-3+ years)**: Intrinsic value, moat durability, management quality
- **Mid-term (1-12 months)**: Catalysts, relative value, cycle positioning
- **Short-term (days-weeks)**: Technical setup, sentiment, alternative data signals

## License

MIT
