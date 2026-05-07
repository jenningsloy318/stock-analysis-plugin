---
name: valuation
description: "Run standalone valuation analysis (Stage 6 only). Quick DCF, comps, and relative value without full research."
---

<purpose>Perform standalone valuation analysis without running the full multi-stage workflow. Computes DCF (with sensitivity table), trading comps, relative value metrics, and technical levels. Useful for quick price checks or updating valuations on previously analyzed stocks.</purpose>

<usage>/stock-analysis:valuation [TICKER]</usage>

<process>
  <step n="1" name="Data Fetch">Run fetch_financials.py and calculate_metrics.py for the ticker</step>
  <step n="2" name="DCF">5-10yr FCF projections, WACC, terminal value, sensitivity table, reverse DCF</step>
  <step n="3" name="Trading Comps">Identify 3-5 peers, compare EV/EBITDA, P/E, P/FCF, PEG</step>
  <step n="4" name="Relative Value">Current multiples vs 5-year history and peers</step>
  <step n="5" name="Technical Levels">Key support/resistance, trend assessment</step>
  <step n="6" name="Summary">Intrinsic value range, margin of safety, fair value verdict</step>
</process>

<constraints>
  <constraint>This is Stage 6 only — no fundamental, macro, or risk analysis</constraint>
  <constraint>Results should be interpreted alongside a full analysis for investment decisions</constraint>
  <constraint>DCF sensitivity table is mandatory — must show WACC vs terminal growth matrix</constraint>
</constraints>
