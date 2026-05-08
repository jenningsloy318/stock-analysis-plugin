---
name: data-integrity
description: "Rules for data source verification, freshness enforcement, and source attribution in stock analysis reports"
---

<purpose>Enforce data integrity standards across all analysis stages. Ensures financial figures are verifiable, sources are properly attributed, and stale data is flagged.</purpose>

<directives>
  <directive name="Source Matrix">Load `references/data_source_matrix.md` before data acquisition. It defines source tiers, freshness windows, source quorum rules, non-US substitutions, and sector-specific add-ons.</directive>
  <directive name="Source Tiering">Tier 0: live/tradable market data. Tier 1 (blocking): official filings/statistics such as SEC/company filings, FRED/Fed, BEA, BLS, Treasury, CFTC COT, FINRA short interest, EIA, FDA, FDIC/OCC. Tier 2 (annotated): institutional holdings, ratings releases, analyst consensus, peer financial databases, industry reports. Tier 3 (directional only): web traffic, app analytics, social sentiment, patents, hiring, channel checks.</directive>
  <directive name="Source Quorum">Numeric investment claims require one Tier 0/Tier 1 source or two independent Tier 2 sources. Alternative data cannot be decisive unless it converges with Tier 1/Tier 2 evidence.</directive>
  <directive name="Freshness Enforcement">Every data point must carry a retrieved_at timestamp and source_date/report_period where available. Data exceeding Max Freshness is annotated [STALE: X days]. Blocking Tier 0/Tier 1 data past Max Freshness blocks the stage or lowers confidence explicitly.</directive>
  <directive name="Attribution Format">Every claim: [Source: ... | Retrieved: YYYY-MM-DD | Fact/Interpretation/Speculation]. Paraphrased quotes tagged [Paraphrased].</directive>
  <directive name="No Fabrication">Never invent financial figures. Never guess management comments. Never fabricate peer data. State "Data not available" instead.</directive>
  <directive name="Unit Consistency">Always state units (billions/millions/thousands), currency, accounting standard, and fiscal period. Verify consistent usage throughout report.</directive>
  <directive name="Date Consistency">Verify fiscal year boundaries. "Q4 2025" may not mean calendar Q4. Always check period-end date.</directive>
  <directive name="Conflict Preservation">If reliable sources disagree, report both values/views, identify the likely reason for the difference, and lower confidence until resolved.</directive>
</directives>

<checklist>
  - [ ] All Tier 1 sources within Max Freshness
  - [ ] Source matrix loaded and coverage assessed by dimension
  - [ ] Source quorum met for numeric investment claims
  - [ ] No fabricated figures (trace every number to source)
  - [ ] Source attribution format applied to all claims
  - [ ] Units, currency, accounting standard, and fiscal period stated on every financial figure
  - [ ] Fiscal year/quarter dates verified against company calendar
  - [ ] Stale data flagged with [STALE: X days] annotation
  - [ ] Conflicting sources preserved and confidence adjusted
</checklist>
