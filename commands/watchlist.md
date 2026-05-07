---
name: watchlist
description: "Check status of previously analyzed stocks. Shows price changes vs targets, catalyst updates, and kill switch status."
---

<purpose>Review previously generated reports in ./reports/ and provide a status update: current price vs targets, catalyst timeline progress, kill switch proximity, and whether the original thesis remains intact or needs revision.</purpose>

<usage>/stock-analysis:watchlist [TICKER|all]</usage>

<process>
  <step n="1" name="Scan Reports">Read ./reports/ directory for all existing analysis reports</step>
  <step n="2" name="Current Data">Fetch current price for each ticker via finance tool</step>
  <step n="3" name="Status Check">Compare current price to bull/base/bear targets from original report</step>
  <step n="4" name="Catalyst Review">Check if any catalysts from the report have materialized</step>
  <step n="5" name="Kill Switch Check">Verify kill switch conditions are NOT triggered</step>
  <step n="6" name="Summary Table">Output watchlist table with status indicators</step>
</process>

<constraints>
  <constraint>Only works if reports exist in ./reports/ from prior analyses</constraint>
  <constraint>Flag any report older than 90 days as "STALE — re-analysis recommended"</constraint>
  <constraint>If kill switch condition is approaching, highlight with warning</constraint>
  <constraint>If price has moved beyond bear case target, flag as "THESIS AT RISK"</constraint>
</constraints>
