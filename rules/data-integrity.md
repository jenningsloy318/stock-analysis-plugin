---
name: data-integrity
description: "Rules for data source verification, freshness enforcement, and source attribution in stock analysis reports"
---

<purpose>Enforce data integrity standards across all analysis stages. Ensures financial figures are verifiable, sources are properly attributed, and stale data is flagged.</purpose>

<directives>
  <directive name="Source Tiering">Tier 1 (blocking): SEC filings, financial statements, current price, macro indicators, insider transactions. Tier 2 (annotated): institutional holdings, short interest, analyst consensus, peer financials. Tier 3 (optional): web traffic, app analytics, social sentiment, patents.</directive>
  <directive name="Freshness Enforcement">Every data point must carry a retrieved_at timestamp. Data exceeding Max Freshness annotated [STALE: X days]. Tier 1 sources at 2x Max Freshness block the stage.</directive>
  <directive name="Attribution Format">Every claim: [Source: ... | Retrieved: YYYY-MM-DD | Fact/Interpretation/Speculation]. Paraphrased quotes tagged [Paraphrased].</directive>
  <directive name="No Fabrication">Never invent financial figures. Never guess management comments. Never fabricate peer data. State "Data not available" instead.</directive>
  <directive name="Unit Consistency">Always state units (billions/millions/thousands). Verify consistent usage throughout report.</directive>
  <directive name="Date Consistency">Verify fiscal year boundaries. "Q4 2025" may not mean calendar Q4. Always check period-end date.</directive>
</directives>

<checklist>
  - [ ] All Tier 1 sources within Max Freshness
  - [ ] No fabricated figures (trace every number to source)
  - [ ] Source attribution format applied to all claims
  - [ ] Units stated on every financial figure
  - [ ] Fiscal year/quarter dates verified against company calendar
  - [ ] Stale data flagged with [STALE: X days] annotation
</checklist>
