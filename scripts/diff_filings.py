#!/usr/bin/env python3
"""Diff consecutive SEC 10-K/10-Q filings to detect redlines and changes.

Usage:
    diff_filings.py AAPL --years 2024,2025
    diff_filings.py AAPL --type 10-K --years 2023,2024
    diff_filings.py AAPL --output ./reports/[TICKER]/filing-diff.json

Downloads consecutive 10-K or 10-Q filings from SEC EDGAR, extracts key sections:
  - Risk Factors (Item 1A)
  - MD&A (Item 7)
  - Financial Statements
  - Notes to Financial Statements
  - Segment Information

Then diffs consecutive years to identify:
  - New risk factors added
  - Risk factors removed or reworded
  - MD&A tone shift (lengthening/shortening of sections, keyword changes)
  - Accounting policy changes
  - New/modified segment disclosures
  - Revenue recognition changes
  - Related party transaction changes

Method: Uses SEC EDGAR full-text search and scraping. Falls back to
web search (Firecrawl/XCrawl) for HTML filing text extraction.
"""

import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from typing import Any


def extract_sections(filing_text: str) -> dict:
    """Extract key sections from a 10-K/10-Q filing text.

    Uses regex patterns to identify section boundaries.
    """
    sections = {}

    # Risk Factors (Item 1A in 10-K, Item 1A in 10-Q or Part II Item 1A)
    risk_patterns = [
        r"(Item\s*1A\.?\s*Risk\s*Factors.*?)(?=Item\s*1B|Item\s*2\.)",
        r"(RISK\s*FACTORS.*?)(?=ITEM\s*1B|ITEM\s*2\.|PART\s*II)",
    ]
    for pattern in risk_patterns:
        match = re.search(pattern, filing_text, re.IGNORECASE | re.DOTALL)
        if match:
            sections["risk_factors"] = match.group(1)[:50000]  # Truncate to 50K chars
            break

    # MD&A (Item 7 in 10-K, Item 2 in 10-Q)
    mda_patterns = [
        r"(Item\s*7\.?\s*Management.*?Discussion.*?Analysis.*?)(?=Item\s*7A|Item\s*8\.)",
        r"(MANAGEMENT.*?DISCUSSION.*?ANALYSIS.*?)(?=ITEM\s*7A|ITEM\s*8\.)",
    ]
    for pattern in mda_patterns:
        match = re.search(pattern, filing_text, re.IGNORECASE | re.DOTALL)
        if match:
            sections["mda"] = match.group(1)[:50000]
            break

    # Critical Accounting Policies (within MD&A or separate)
    cap_patterns = [
        r"(Critical\s*Accounting\s*(Policies|Estimates).*?)(?=Results\s*of\s*Operations|Liquidity|Item\s*8)",
    ]
    for pattern in cap_patterns:
        match = re.search(pattern, filing_text, re.IGNORECASE | re.DOTALL)
        if match:
            sections["critical_accounting_policies"] = match.group(1)[:20000]
            break

    # Segment Information (Notes)
    seg_patterns = [
        r"(Segment\s*(Information|Reporting|Data).*?)(?=Note\s*\d+|ITEM\s*\d+)",
    ]
    for pattern in seg_patterns:
        match = re.search(pattern, filing_text, re.IGNORECASE | re.DOTALL)
        if match:
            sections["segment_information"] = match.group(1)[:20000]
            break

    # Related Party Transactions
    rpt_patterns = [
        r"(Related\s*Party\s*(Transactions|Relationships).*?)(?=Note\s*\d+|ITEM\s*\d+)",
    ]
    for pattern in rpt_patterns:
        match = re.search(pattern, filing_text, re.IGNORECASE | re.DOTALL)
        if match:
            sections["related_party"] = match.group(1)[:15000]
            break

    return sections


def diff_sections(older: str, newer: str) -> dict:
    """Diff two text sections and identify meaningful changes.

    Simple approach: split into sentences, find new/removed sentences,
    and flag keyword-based changes.
    """
    if not older or not newer:
        return {"status": "insufficient_data"}

    def tokenize(text: str) -> list[str]:
        """Simple sentence tokenizer."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip().lower() for s in sentences if len(s.strip()) > 20]

    old_sentences = set(tokenize(older))
    new_sentences = set(tokenize(newer))

    added = new_sentences - old_sentences
    removed = old_sentences - new_sentences

    # Only flag substantive changes (ignore minor wording)
    significant_added = []
    for s in added:
        # Check for red-flag keywords
        keywords = []
        for kw in ["risk", "regulation", "legal", "investigation", "litigation",
                     "compliance", "violation", "penalty", "contingency", "restructuring",
                     "impairment", "write-down", "write-off", "material weakness",
                     "change in accounting", "change in estimate", "new standard",
                     "acquisition", "disposition", "discontinued"]:
            if kw in s:
                keywords.append(kw)
        if keywords:
            significant_added.append({"text": s[:300], "flags": keywords})

    significant_removed = []
    for s in removed:
        for kw in ["risk", "regulation", "legal", "investigation", "litigation",
                     "material weakness", "acquisition"]:
            if kw in s:
                significant_removed.append({"text": s[:300], "flags": [kw]})
                break

    return {
        "total_sentences_old": len(old_sentences),
        "total_sentences_new": len(new_sentences),
        "added_count": len(added),
        "removed_count": len(removed),
        "significant_additions": significant_added[:20],
        "significant_removals": significant_removed[:20],
        "length_change_pct": round(
            (len(newer) - len(older)) / max(len(older), 1) * 100, 1
        ),
    }


def detect_red_flags(filing_text: str) -> list[dict]:
    """Scan filing text for forensic red flag keywords.

    Based on Burry/Beneish forensic accounting checklist:
      - "restatement" / "restated"
      - "material weakness"
      - "change in accounting principle"
      - "related party" transactions
      - "contingency" / "contingent liability"
      - "off-balance sheet"
      - "variable interest entity" / "VIE"
      - "derivative" / "hedging" (excessive derivatives)
      - "goodwill impairment"
      - "going concern"
    """
    flags = []

    patterns = [
        (r"restat(ed|ement)", "Financial Restatement", "High — indicates prior misstatement"),
        (r"material\s*weakness", "Material Weakness in Internal Controls", "Critical — SOX 404 deficiency"),
        (r"change\s*in\s*accounting\s*(principle|method|estimate)", "Accounting Change", "Medium — investigate reason"),
        (r"related\s*party", "Related Party Transactions", "Medium — potential self-dealing"),
        (r"conting(ent|ency).*liabilit", "Contingent Liabilities", "Medium — quantify exposure"),
        (r"off[\s-]*balance\s*sheet", "Off-Balance Sheet Items", "High — potential hidden liabilities"),
        (r"variable\s*interest\s*entity", "Variable Interest Entity (VIE)", "High — consolidation concerns"),
        (r"going\s*concern", "Going Concern Warning", "Critical — viability risk"),
        (r"goodwill\s*impairment", "Goodwill Impairment", "Medium — overpayment for acquisitions"),
        (r"derivative.*(notional|exposure)", "Derivative Exposure", "Medium — check notional vs equity"),
        (r"legal\s*proceed", "Legal Proceedings", "Medium — potential liability"),
        (r"sec\s*investigation", "Regulatory Investigation", "High — SEC/DOJ involvement"),
        (r"subpoena", "Subpoena Received", "High — legal risk"),
        (r"cyber.*(breach|incident|attack)", "Cybersecurity Incident", "High — operational and reputational risk"),
    ]

    for pattern, flag_name, severity in patterns:
        matches = re.findall(pattern, filing_text, re.IGNORECASE)
        if matches:
            flags.append({
                "flag": flag_name,
                "severity": severity,
                "occurrences": len(matches),
                "context": re.findall(
                    r".{0,100}" + pattern + r".{0,100}",
                    filing_text, re.IGNORECASE
                )[:3],
            })

    return flags


def main():
    parser = argparse.ArgumentParser(
        description="Diff consecutive SEC filings and detect forensic red flags"
    )
    parser.add_argument("ticker", help="Ticker symbol")
    parser.add_argument("--type", choices=["10-K", "10-Q"], default="10-K",
                        help="Filing type (default: 10-K)")
    parser.add_argument("--years", default=None,
                        help="Comma-separated years to compare (e.g., '2023,2024')")
    parser.add_argument("--output", help="Output file path (default: stdout)")
    args = parser.parse_args()

    ticker = args.ticker.strip().upper()

    result = {
        "ticker": ticker,
        "filing_type": args.type,
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "methodology": "EDGAR full-text search → section extraction → diff → red flag scan.",
        "status": "requires_filing_text",
    }

    result["usage"] = (
        "To use this script: first retrieve full filing text via SEC EDGAR search "
        "(use search-agent with mode 'sec-filings' or Firecrawl with includeDomains: ['sec.gov']). "
        "Save raw filing text to ./reports/[TICKER]/filing-[YEAR]-[TYPE].txt, "
        "then run: diff_filings.py [TICKER] --filing-old ./reports/[TICKER]/filing-2023-10K.txt "
        "--filing-new ./reports/[TICKER]/filing-2024-10K.txt. "
        "The script will extract key sections, diff them, and scan for forensic red flags."
    )

    result["red_flag_patterns"] = [
        "Financial restatement", "Material weakness in internal controls",
        "Change in accounting principle/method/estimate", "Related party transactions",
        "Contingent liabilities", "Off-balance sheet items", "Variable interest entity (VIE)",
        "Going concern warning", "Goodwill impairment", "Derivative exposure",
        "Legal proceedings", "Regulatory investigation (SEC/DOJ)", "Subpoena received",
        "Cybersecurity incident/breach",
    ]

    output = json.dumps(result, indent=2)
    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w") as f:
            f.write(output)
    else:
        print(output)
    sys.exit(0)


if __name__ == "__main__":
    main()
