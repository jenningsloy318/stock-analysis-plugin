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
- Required API keys (free tier sufficient):
  - `FRED_API_KEY` — macro indicators ([get key](https://fred.stlouisfed.org/docs/api/api_key.html))
  - `FINNHUB_API_KEY` — sentiment/insider/earnings ([get key](https://finnhub.io/))
- Optional API keys:
  - `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET` — social sentiment
  - `FMP_API_KEY` — financial data fallback
  - `ALPHAVANTAGE_API_KEY` — technical indicators fallback

```bash
pip install -r scripts/requirements.txt
```

## Commands

| Command | Description |
|---------|-------------|
| `/stock-analysis:analyze [TICKER]` | Full multi-stage equity research |
| `/stock-analysis:quick-overview [TICKER]` | Rapid 3-stage analysis (1-3 min) |
| `/stock-analysis:compare [T1],[T2],[T3]` | Side-by-side stock comparison |
| `/stock-analysis:watchlist [TICKER\|all]` | Status check on prior analyses |
| `/stock-analysis:valuation [TICKER]` | Standalone valuation (Stage 6 only) |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     stock-analyst                             │
│                  (Central Orchestrator)                       │
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
    │  Stages 4-5       │          │  Stage 6           │
    └───────────────────┘          └────────────────────┘
              │                               │
    ┌─────────▼─────────┐          ┌─────────▼─────────┐
    │   risk-analyst     │          │  alt-data-analyst  │
    │  Stage 7           │          │  Stage 8           │
    └───────────────────┘          └────────────────────┘
              │                               │
              └───────────────┬───────────────┘
                    ┌─────────▼─────────┐
                    │   report-writer    │
                    │   Stage 9          │
                    └───────────────────┘
```

### Parallel Execution

| Report Type | Parallel Groups | Est. Time |
|-------------|-----------------|-----------|
| Long-term | [1+2+3] → [4+5] → [6] → [7] → [8] → [9] | 8-15 min |
| Mid-term | [4+5+6] → [1+7] → [2+8] → [9] | 5-10 min |
| Short-term | [6+8] → [9] | 2-5 min |
| Quick | [1+6+7] → [9] | 1-3 min |

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
├── commands/                # Claude Code slash commands
├── gemini-commands/         # Gemini CLI commands (TOML)
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
