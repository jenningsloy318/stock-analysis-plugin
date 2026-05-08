# Stock Analysis Plugin

Multi-stage institutional equity research plugin for **Claude Code**, **OpenAI Codex**, and **Gemini CLI**. Produces long-term, mid-term, and short-term stock analysis reports synthesizing methodologies from Buffett, Dalio, Soros, Lynch, Fisher, Marks, Druckenmiller, Greenblatt, Burry, and ARK.

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

### Gemini CLI

```bash
gemini extensions install https://github.com/jenningsloy318/stock-analysis-plugin
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

**Gemini CLI**: API keys are configured during extension install via `gemini extensions config stock-analysis`. Keys are stored securely in the system keychain.

## Commands

### Gemini CLI

| Command | Description |
|---------|-------------|
| `/stock-analysis:analyze [TICKER]` | Full multi-stage equity research (all 3 horizons) |
| `/stock-analysis:quick-overview [TICKER]` | Rapid 3-stage analysis (1-3 min) |
| `/stock-analysis:compare [T1],[T2],[T3]` | Side-by-side stock comparison |
| `/stock-analysis:valuation [TICKER]` | Standalone valuation (DCF, comps, relative) |
| `/stock-analysis:watchlist [TICKER\|all]` | Status check on prior analyses |
| `/industry-screening:screen [SCOPE]` | Top-down GICS Level 4 sub-industry screening |

### Claude Code

| Command | Description |
|---------|-------------|
| `/stock-analyze [TICKER]` | Full multi-stage equity research (all 3 horizons) |
| `/quick-overview [TICKER]` | Rapid 3-stage analysis (1-3 min) |
| `/compare [T1],[T2],[T3]` | Side-by-side stock comparison |
| `/valuation [TICKER]` | Standalone valuation (DCF, comps, relative) |
| `/watchlist [TICKER\|all]` | Status check on prior analyses |
| `/screen-industry [SCOPE]` | Top-down GICS Level 4 sub-industry screening |

### OpenAI Codex

Codex uses the same commands as Claude Code via skill-embedded orchestration.

All commands produce **3 reports** (long-term, mid-term, short-term) automatically — no need to specify horizon. Reports are written in **Chinese (中文)**.

## Architecture

The `stock-analysis-orchestrator` acts as team lead — it spawns specialist sub-agents for all analysis work, never performing deep analysis directly. Agent definitions in `agents/` are shared by both Claude Code and Gemini CLI.

```
┌─────────────────────────────────────────────────────────────┐
│               stock-analysis-orchestrator                     │
│                  (Team Lead / Orchestrator)                   │
│         Spawns specialists, manages parallel execution        │
└─────────────┬───────────────────────────────┬───────────────┘
              │                               │
    ┌─────────▼─────────┐          ┌─────────▼─────────┐
    │ fundamental-analyst│          │  industry-analyst  │
    │  Stages 1-2       │          │  Stage 3           │
    └───────────────────┘          └────────────────────┘
              │                               │
    ┌─────────▼─────────┐          ┌─────────▼─────────┐
    │   macro-analyst    │          │   quant-analyst    │
    │  Stages 4-5       │          │  Stages 6-7        │
    └───────────────────┘          └────────────────────┘
              │                               │
    ┌─────────▼─────────┐          ┌─────────▼─────────┐
    │   risk-analyst     │          │  alt-data-analyst  │
    │  Stage 8           │          │  Stage 9           │
    └───────────────────┘          └────────────────────┘
              │                               │
              └───────────────┬───────────────┘
                    ┌─────────▼─────────┐
                    │ equity-report-writer│
                    │   Stage 10-11     │
                    └───────────────────┘
```

### Cross-Platform Agent Team

| Platform | Agent Location | Delegation |
|----------|---------------|------------|
| Claude Code | `agents/*.md` | `Agent` tool with `subagent_type` |
| Gemini CLI | `agents/*.md` (shared) | Auto-delegation or `@agent-name` |
| Codex | `.codex/agents/*.toml` | Skill-embedded orchestration |

### Parallel Execution

| Report Type | Parallel Groups | Est. Time |
|-------------|-----------------|-----------|
| Long-term | [1+2+3] → [4+5] → [6+7] → [8] → [9] → Scoring → [10-11] | 8-15 min |
| Mid-term | [4+5+6] → [1+7] → [2+8] → [9] → Scoring → [10-11] | 5-10 min |
| Short-term | [6+7+9] → Scoring → [10-11] | 2-5 min |
| Quick | [1+6+7+8] → Scoring → [10-11] | 1-3 min |

## Directory Structure

```
stock-analysis-plugin/
├── .claude-plugin/          # Claude Code manifests
├── .codex-plugin/           # OpenAI Codex manifest
├── .codex/                  # Codex agent configs (TOML)
├── gemini-extension.json    # Gemini CLI manifest
├── CLAUDE.md                # Plugin rules & philosophy
├── GEMINI.md                # → symlink to CLAUDE.md
├── AGENTS.md                # Agent index
├── agents/                  # Specialist agent definitions (MD)
├── commands/                # Slash commands (Claude .md + Gemini .toml)
├── skills/                  # Main orchestrator skill
├── scripts/                 # Python analysis scripts
├── references/              # Analysis framework docs
├── rules/                   # Modular quality guidelines
└── docs/                    # Requirements & design docs
```

## Analyst Methodologies

| Framework | Trader | Applied To |
|-----------|--------|------------|
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

## Report Types

- **Long-term (1-3+ years)**: Intrinsic value, moat durability, management quality
- **Mid-term (1-12 months)**: Catalysts, relative value, cycle positioning
- **Short-term (days-weeks)**: Technical setup, sentiment, alternative data signals

## License

MIT
