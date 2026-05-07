## Plugin versioning rule (MUST follow)
- Every modification MUST include a patch version bump in ALL platform manifests simultaneously:
  - `.claude-plugin/plugin.json`
  - `.claude-plugin/marketplace.json` (the plugin entry version)
  - `.codex-plugin/plugin.json`
  - `gemini-extension.json`
- Bump the patch level (e.g., 1.0.0 → 1.0.1) and include ALL four files in the same commit
- ALL four manifest versions MUST always match each other

## Analysis Philosophy (MUST follow)

- **Data integrity first**: Never invent financial figures. If data is unavailable, state "Data not available" — never guess.
- **Methodology transparency**: Every conclusion must be traceable to a specific analytical framework (Buffett, Dalio, Soros, Lynch, Fisher, Marks, Druckenmiller, Greenblatt, Burry, or ARK).
- **Second-level thinking**: Always ask "what's priced in?" not just "what's happening?"
- **Multi-dimensional analysis**: Cover all critical factors that move stock prices (fundamentals + macro + technicals + alternative data).
- **Progressive disclosure**: Load reference files on-demand per analysis stage. Drop raw data after each stage summary is written.
- **Source attribution**: Every data claim must use `[Source: ... | Retrieved: ... | Fact/Interpretation/Speculation]` format.

## Agent Orchestration (MUST follow)

- The main `stock-analysis` skill acts as the coordinator — it spawns specialized agents for parallel stage execution.
- Agents: `fundamental-analyst`, `industry-analyst`, `macro-analyst`, `quant-analyst`, `risk-analyst`, `alt-data-analyst`, `report-writer`.
- The coordinator NEVER performs deep analysis directly — it delegates to specialist agents and synthesizes results.
- Parallel execution rules:
  - Long-term: Stages 1-3 can run in parallel
  - Mid-term: Stages 4-6 can run in parallel
  - Short-term: Stages 6+8 can pair
- Cap parallel sub-agents at 3.

## Script Execution (MUST follow)

- Python scripts in `scripts/` perform deterministic calculations (DCF, ratios, scores) — no LLM involvement in math.
- Scripts are called via `exec_shell` / `Bash` tool.
- Required environment: Python 3.10+, dependencies in `scripts/requirements.txt`.
- API keys: `FRED_API_KEY` (macro) and `FINNHUB_API_KEY` (sentiment/insider/earnings) are recommended. All other keys are optional with functional fallbacks.

## Report Quality Gates (MUST follow)

- Pre-delivery checklist must pass before any report is delivered:
  - All Tier 1 data sources within Max Freshness
  - No [STALE] flags on critical metrics
  - At least 1 framework divergence acknowledged
  - Kill switch defined for each report type
  - Methodology attribution present for all major conclusions
  - 5 random fact checks passed (hallucination protocol)
- If any gate fails, report must carry: "INCOMPLETE ANALYSIS — [reason]"

## Context Window Management (MUST follow)

- After each stage: write stage summary to `/tmp/stock-analysis-[TICKER]-stage[N].md`
- Drop raw data from context (SEC filings, full transcripts, raw financials)
- Retain only: key metrics table, stage scores, 3-sentence narrative per sub-section
- Maximum active context at any point: <80% of the context window
