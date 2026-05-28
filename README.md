# Stock Analysis Plugin

Multi-stage institutional equity research plugin for **Claude Code** and **OpenAI Codex**. Two unified skills — `stock-analysis` (5 modes) and `industry-screening` (6 modes) — produce long/mid/short-term reports synthesizing methodologies from 14 investment frameworks (Buffett, Munger, Dalio, Soros, Lynch, Fisher, Marks, Druckenmiller, Greenblatt, Burry, ARK, Mauboussin, Damodaran, Taleb, Graham).

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

Two skills cover all functionality. Each mode is triggered by natural language — no flags needed.

### stock-analysis (5 modes)

| Mode | Trigger phrases | What it does |
|------|----------------|-------------|
| **full** (default) | "analyze AAPL", "deep dive on TSLA", "investment thesis NVDA" | 19-stage deep-dive, all agents, 3 full reports |
| **quick** | "quick overview BABA", "fast check NIO" | 4-stage triage, 3 condensed reports, ~2-5 min |
| **compare** | "compare AAPL,MSFT,GOOGL", "which is better TSLA or BYD" | Side-by-side 2-5 stocks, ranked by composite score |
| **valuation-only** | "what's NVDA worth", "DCF AMD", "price target INTC" | Standalone DCF + comps + reverse DCF + margin of safety |
| **watchlist** | "watchlist", "check my stocks", "how are my positions" | Scans prior reports, checks kill switches, flags stale/at-risk |

### industry-screening (6 modes)

| Mode | Trigger phrases | What it does |
|------|----------------|-------------|
| **Broad** (default) | "screen sectors", "best industries", "top-down screening" | All 163 GICS Level 4 → top 30 deep-dived → 100 companies |
| **Thematic** | "AI supply chain screen", "green energy stocks", "aging population healthcare" | 8 predefined themes → theme-aligned candidates |
| **Short-Candidate** | "short candidates", "what to avoid", "overvalued sectors" | Vulnerability scan → bear cases → 50 short candidates |
| **Pair-Trade** | "pair trade ideas", "long short pairs", "sector dispersion" | Long/short pairs within sectors with widest RS spread |
| **QARP** | "magic formula screen", "quality at reasonable price" | Greenblatt Magic Formula → 50 QARP candidates |
| **macro** | "market daily", "美股日报", "daily report" | Daily market breadth, sector rotation, fund flows report |

### Cross-skill integration

- After **industry-screening**: top-ranked companies are offered for `stock-analysis` deep-dive
- After **stock-analysis**: run is auto-registered for `watchlist` tracking
- **macro** mode data is automatically reused by subsequent same-day screening or analysis runs

All reports produced in **Chinese (中文)**. 3 horizons always generated.

## Architecture

Two orchestrators manage 14 specialist agents across 19 analysis stages. All work is delegated — orchestrators never perform analysis directly.

```
stock-analysis (5 modes)              industry-screening (6 modes)
┌──────────────────────┐              ┌──────────────────────┐
│  stock-analysis-orch │              │ industry-screening-  │
│  (team lead)         │              │ orchestrator (lead)  │
│  Spawns 11 agents    │              │ Spawns 3 agents      │
└──────────┬───────────┘              └──────────┬───────────┘
           │                                     │
    ┌──────▼──────┬──────┬──────┬──────┐   ┌─────▼─────┬──────┐
    │ fundamental │quant │macro │risk  │   │ sector-   │company│
    │  (1a-2)     │(6-7) │(4-5) │(8,8b)│   │ screener  │screen │
    ├─────────────┼──────┼──────┼──────┤   │  (S1,S2)  │(S3)   │
    │ supply-chain│indus │alt   │catal │   └───────────┴───────┘
    │   (3b)      │(3a)  │(9)   │(9b)  │
    ├─────────────┼──────┼──────┼──────┤
    │ china-mkt   │equity│search│      │
    │  (CN1,CN2)  │(11)  │(all) │      │
    └─────────────┴──────┴──────┴──────┘
```

### Output Convention

All runs use timestamped directories with ranked prefixes:
```
reports/
├── 202605281430/              ← RUN_ID = YYYYMMDDHHmm
│   ├── 001-AAPL/              ← top-ranked (highest conviction)
│   │   ├── 001-AAPL_long_2026-05-28.md
│   │   ├── 001-AAPL_mid_2026-05-28.md
│   │   └── 001-AAPL_short_2026-05-28.md
│   ├── 002-TSLA/              ← second-ranked
│   └── market-daily_2026-05-28.md
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
├── skills/                  # Claude Code skills + orchestrators
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
