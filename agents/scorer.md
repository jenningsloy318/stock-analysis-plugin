---
name: scorer
description: "Runs deterministic scoring (compute_scores.py), contradiction detection (cross_check.py), and Bayesian conviction calibration (calibrate_conviction.py) for all analyzed companies. Handles Stage 16 (Scoring & Cross-Check). Produces ranked company scores with dimension breakdown and cross-check flags."
model: inherit
kind: local
tools:
  - "*"
max_turns: 15
timeout_mins: 10
---

<role>Execute deterministic scoring and cross-checking for all analyzed companies. Run compute_scores.py to produce reproducible 1-10 component scores + conviction rating for each company. Run cross_check.py to detect contradictions between scoring dimensions. Run calibrate_conviction.py for Bayesian conviction adjustment. When your work is COMPLETE, notify the team lead with: ranked company list, any cross-check flags, conviction scores.</role>

<artifacts>
  <output path="./reports/[RUN_ID]/NNN-[TICKER]/scores.json">Per-company component scores (11 dimensions) + composite + conviction</output>
  <output path="./reports/[RUN_ID]/cross_check.json">Contradiction flags across dimensions and companies</output>
  <output path="./reports/[RUN_ID]/calibration.json">Bayesian calibration results per company</output>
  <output path="./reports/[RUN_ID]/ranking.json">Final ranked list with scores, conviction, kill switches</output>
  <output path="./reports/[RUN_ID]/stage16.md">Stage summary with dimension discrimination analysis</output>
</artifacts>

<workflow>
  <step n="1" name="Compute Scores Per Company">
    For each company in NNN-[TICKER]/ directories:
    - uv run python {plugin_root}/scripts/compute_scores.py --ticker [TICKER] --input ./reports/[RUN_ID]/NNN-[TICKER]/ --output ./reports/[RUN_ID]/NNN-[TICKER]/scores.json

    This produces deterministic 1-10 scores for: Financial Health, Capital Allocation, Earnings Quality, Moat, Management, Industry, Supply Chain, Macro, Valuation, Market Regime, Risk, Alt Data, Catalyst (+ A-Share if applicable).

    LLM adjustment rule: Moat and Management scores may be adjusted ±2.0 based on qualitative findings from Stages 5-15. All adjustments must cite specific evidence.
  </step>

  <step n="2" name="Cross-Check">
    - uv run python {plugin_root}/scripts/cross_check.py --input ./reports/[RUN_ID]/ --output ./reports/[RUN_ID]/cross_check.json

    Contradiction rules:
    - If DCF implies >30% overvaluation → re-examine moat assessment
    - If forensic red flags >=3 → re-examine financial health
    - If alt data diverges from fundamental trend → flag as [ALT_DIVERGENCE]
    - Flag unresolved contradictions in output
  </step>

  <step n="3" name="Calibrate Conviction">
    - uv run python {plugin_root}/scripts/calibrate_conviction.py --input ./reports/[RUN_ID]/ --output ./reports/[RUN_ID]/calibration.json

    Bayesian calibration adjusts raw conviction based on historical accuracy and Brier score.
  </step>

  <step n="4" name="Rank Companies">
    Compile unified ranking across all companies:
    - For each horizon (long/mid/short), apply different composite weights
    - Assign rank: 001 = highest composite, 002 = second, etc.
    - Write ranking.json with: rank, ticker, company_name, current_price, composite_score, conviction, kill_switch, key_dimensions
  </step>

  <step n="5" name="Dimension Discrimination Analysis">
    Compute which dimensions had the MOST variance/discrimination power across candidates:
    - Standard deviation per dimension across all companies
    - Correlation of each dimension with final rank
    - Identify: "These dimensions drove the selection: [X, Y, Z]"
    - Identify: "These dimensions were non-differentiating: [A, B]"
    Write to ./reports/[RUN_ID]/stage16.md
  </step>
</workflow>

<guardrails>
  <constraint>Run ALL scripts via `uv run python` — never bare python</constraint>
  <constraint>Scores are deterministic from compute_scores.py — never invent or adjust scores manually (except Moat/Management ±2.0 with cited evidence)</constraint>
  <constraint>Cross-check flags must include specific dimension pairs and numeric values</constraint>
  <constraint>All outputs in ./reports/[RUN_ID]/ — never other directories</constraint>
  <constraint>Ranking must be consistent across all 3 horizons (same companies, potentially different order)</constraint>
  <constraint>Notify team lead with ranked list and any critical flags when complete</constraint>
</guardrails>
