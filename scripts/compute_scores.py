#!/usr/bin/env python3
"""Compute deterministic 1-10 component scores from script outputs.

Usage:
    compute_scores.py \
        --metrics ./reports/AAPL/metrics.json \
        --macro ./reports/macro.json \
        --technicals ./reports/[TICKER]/tech.json \
        --alternatives ./reports/[TICKER]/alt-data.json \
        --sentiment ./reports/[TICKER]/sentiment.json \
        --capital-structure ./reports/[TICKER]/capital_structure.json \
        --report-type long \
        [--gics-sector 45] \
        [--output ./reports/[TICKER]/scores.json]

Produces reproducible, rubric-based 1-10 scores for 11 conviction
components: Financial Health, Moat Quality, Management Quality, Valuation
Attractiveness, Macro Tailwind, Risk Profile, Alternative Alignment,
Technical Setup, Capital Structure, Weinstein Alignment, and CANSLIM.

Then computes the final conviction rating using the per-report-type
weighted formulas, applying override rules (component ≤3 caps at Hold,
3+ missing components forces Low confidence).
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Scoring utilities
# ---------------------------------------------------------------------------


def _clamp(score: float, lo: float = 1.0, hi: float = 10.0) -> float:
    return max(lo, min(hi, round(score, 1)))


def _score_from_percentile(
    value: float | None,
    bullish_25: float,
    bullish_75: float,
    bearish_25: float,
    bearish_75: float,
    higher_is_better: bool = True,
) -> float | None:
    """Map a value to 1-10 using percentile-style thresholds.

    bullish_25/75: thresholds where score transitions from 5→7.5→10
    bearish_25/75: thresholds where score transitions from 5→2.5→1
    """
    if value is None:
        return None
    if higher_is_better:
        if value >= bullish_75:
            return 9.0 + (value - bullish_75) / (bullish_75 * 2)  # 9-10 range
        elif value >= bullish_25:
            return 6.0 + 3.0 * (value - bullish_25) / (bullish_75 - bullish_25)
        elif value >= bearish_75:
            return 4.0 + 2.0 * (value - bearish_75) / (bullish_25 - bearish_75)
        elif value >= bearish_25:
            return 1.5 + 2.5 * (value - bearish_25) / (bearish_75 - bearish_25)
        else:
            return 1.0
    else:
        # Lower is better (e.g., debt/equity)
        if value <= bearish_25:
            return 9.0 + (bearish_25 - value) / max(bearish_25 * 2, 0.01)
        elif value <= bearish_75:
            return 6.0 + 3.0 * (bearish_75 - value) / (bearish_75 - bearish_25)
        elif value <= bullish_25:
            return 4.0 + 2.0 * (bullish_25 - value) / (bullish_25 - bearish_75)
        elif value <= bullish_75:
            return 1.5 + 2.5 * (bullish_75 - value) / (bullish_75 - bullish_25)
        else:
            return 1.0


# ---------------------------------------------------------------------------
# 1. Financial Health Score (1-10)
# ---------------------------------------------------------------------------


def compute_financial_health(metrics: dict, sector: int | None = None) -> dict:
    """Score financial health from computed metrics.

    Weights: Margin quality (25%), ROE/ROIC (20%), Leverage (20%),
             FCF generation (20%), Growth stability (15%).
    """
    ratios = metrics.get("ratios", {})
    reasons: list[str] = []
    sub_scores: dict[str, float | None] = {}
    weights: dict[str, float] = {
        "margin_quality": 0.25,
        "roe_roic": 0.20,
        "leverage": 0.20,
        "fcf_generation": 0.20,
        "growth_stability": 0.15,
    }

    # --- Margin Quality ---
    op_margin = ratios.get("operating_margin")
    net_margin = ratios.get("net_margin")
    score_margin = None
    if op_margin is not None:
        # Sector-adjusted thresholds
        if sector in (45, 50):  # Tech, Comm Services
            score_margin = _score_from_percentile(op_margin, 0.20, 0.35, 0.10, 0.05)
        elif sector == 35:  # Health Care
            score_margin = _score_from_percentile(op_margin, 0.25, 0.40, 0.12, 0.05)
        elif sector == 30:  # Consumer Staples
            score_margin = _score_from_percentile(op_margin, 0.15, 0.25, 0.08, 0.03)
        else:
            score_margin = _score_from_percentile(op_margin, 0.15, 0.25, 0.08, 0.03)
        if score_margin:
            reasons.append(
                f"Operating margin: {op_margin:.1%} → sub-score {score_margin:.1f}"
            )
    sub_scores["margin_quality"] = score_margin

    # --- ROE / ROIC ---
    roe = ratios.get("roe")
    dupont = ratios.get("dupont", {})
    score_roe = None
    if roe is not None:
        # Penalize leverage-driven ROE
        leverage_driven = dupont.get("interpretation", {}).get("leverage_driven", False)
        if leverage_driven:
            score_roe = _score_from_percentile(roe, 0.20, 0.35, 0.10, 0.05)
            reasons.append(
                f"ROE: {roe:.1%} (leverage-driven → penalized) → sub-score {score_roe:.1f}"
            )
        else:
            score_roe = _score_from_percentile(roe, 0.12, 0.20, 0.06, 0.02)
            reasons.append(
                f"ROE: {roe:.1%} (operationally-driven) → sub-score {score_roe:.1f}"
            )
    sub_scores["roe_roic"] = score_roe

    # --- Leverage ---
    debt_to_equity = ratios.get("debt_to_equity")
    net_debt = ratios.get("net_debt")
    score_leverage = None
    if debt_to_equity is not None:
        # Lower is better
        score_leverage = _score_from_percentile(
            debt_to_equity, 0.5, 1.5, 0.3, 0.8, higher_is_better=False
        )
        if score_leverage:
            reasons.append(
                f"Debt/Equity: {debt_to_equity:.2f} → sub-score {score_leverage:.1f}"
            )
    elif net_debt is not None:
        # Approximate from net debt
        adj_leverage = 1.0 if net_debt > 0 else 0.3
        score_leverage = _score_from_percentile(
            adj_leverage, 0.5, 1.5, 0.3, 0.8, higher_is_better=False
        )
    sub_scores["leverage"] = score_leverage

    # --- FCF Generation ---
    fcf_yield = ratios.get("fcf_yield")
    ocf_to_ni = ratios.get("ocf_to_ni")
    score_fcf = None
    signals = []
    if fcf_yield is not None:
        fcf_score = _score_from_percentile(fcf_yield, 0.03, 0.08, 0.01, 0.0)
        signals.append(f"FCF yield: {fcf_yield:.1%}")
    else:
        fcf_score = 5.0
    if ocf_to_ni is not None:
        if ocf_to_ni < 0.7:
            fcf_score = min(fcf_score or 5.0, 3.0)
            signals.append(f"OCF/NI: {ocf_to_ni:.2f} (poor quality)")
    if signals:
        score_fcf = _clamp(fcf_score or 5.0)
        reasons.append(f"FCF signals: {'; '.join(signals)} → sub-score {score_fcf:.1f}")
    sub_scores["fcf_generation"] = score_fcf

    # --- Growth Stability ---
    rev_cagr = ratios.get("revenue_cagr_5yr")
    ni_cagr = ratios.get("ni_cagr_5yr")
    fcf_cagr = ratios.get("fcf_cagr_5yr")
    score_growth = None
    if rev_cagr is not None and ni_cagr is not None:
        avg_growth = (rev_cagr + ni_cagr) / 2
        # High growth good, but negative is bad, and extreme growth unsustainable
        if avg_growth > 0.30:
            gscore = 7.0  # High but flag as potentially unsustainable
        elif avg_growth > 0.15:
            gscore = 8.5
        elif avg_growth > 0.08:
            gscore = 7.0
        elif avg_growth > 0.03:
            gscore = 5.5
        elif avg_growth > 0:
            gscore = 4.0
        else:
            gscore = 2.0
        # Stability: if NI CAGR and FCF CAGR diverge wildly, penalize
        if fcf_cagr is not None and rev_cagr is not None:
            divergence = abs(rev_cagr - fcf_cagr)
            if divergence > 0.15:
                gscore -= 1.5
                reasons.append(f"Revenue/FCF growth divergence: {divergence:.1%}")
        score_growth = _clamp(gscore)
        reasons.append(
            f"Avg revenue/NI CAGR: {avg_growth:.1%} → sub-score {score_growth:.1f}"
        )
    sub_scores["growth_stability"] = score_growth

    # Composite
    valid = {k: v for k, v in sub_scores.items() if v is not None}
    if not valid:
        return {
            "score": None,
            "assessment": "insufficient_data",
            "sub_scores": sub_scores,
            "reasons": reasons,
        }

    total = sum(valid[k] * weights[k] for k in valid)
    total /= sum(weights[k] for k in valid)
    final = _clamp(total)

    if final >= 7.5:
        assessment = (
            "Excellent — expanding margins, strong FCF, low leverage, consistent growth"
        )
    elif final >= 6.0:
        assessment = "Good — healthy but not exceptional across all dimensions"
    elif final >= 4.5:
        assessment = "Adequate — mixed signals, some metrics below sector norms"
    elif final >= 3.0:
        assessment = "Weak — multiple metrics concerning, warrants caution"
    else:
        assessment = "Poor — significant financial distress indicators"

    return {
        "score": final,
        "assessment": assessment,
        "sub_scores": sub_scores,
        "sub_score_weights": weights,
        "reasons": reasons,
        "methodology": "Financial Health = Margin(25%) + ROE(20%) + Leverage(20%) + FCF(20%) + Growth(15%)",
    }


# ---------------------------------------------------------------------------
# 2. Moat Quality Score (1-10)
# ---------------------------------------------------------------------------


def compute_moat_quality(metrics: dict, sector: int | None = None) -> dict:
    """Score competitive moat from quantitative proxies.

    Since true moat analysis requires qualitative assessment, this provides
    quantitative proxies that the LLM agent can adjust ±2 points based on
    qualitative search findings.
    """
    ratios = metrics.get("ratios", {})
    reasons: list[str] = []
    sub_scores: dict[str, float | None] = {}

    # --- Pricing Power (via margin stability/level) ---
    op_margin = ratios.get("operating_margin")
    net_margin = ratios.get("net_margin")
    score_pricing = None
    if op_margin is not None:
        if op_margin > 0.30:
            score_pricing = 9.0
        elif op_margin > 0.20:
            score_pricing = 7.5
        elif op_margin > 0.10:
            score_pricing = 5.5
        elif op_margin > 0.05:
            score_pricing = 4.0
        else:
            score_pricing = 2.0
        reasons.append(
            f"Operating margin {op_margin:.1%} → pricing power proxy {score_pricing:.1f}"
        )
    sub_scores["pricing_power"] = score_pricing

    # --- Returns on Capital (moat durability proxy) ---
    roe = ratios.get("roe")
    score_returns = None
    if roe is not None:
        if roe > 0.25:
            score_returns = 9.0
        elif roe > 0.18:
            score_returns = 7.5
        elif roe > 0.12:
            score_returns = 6.0
        elif roe > 0.08:
            score_returns = 4.5
        elif roe > 0:
            score_returns = 3.0
        else:
            score_returns = 1.0
        reasons.append(f"ROE {roe:.1%} → capital return proxy {score_returns:.1f}")
    sub_scores["returns_on_capital"] = score_returns

    # --- Revenue Growth Consistency (moat trajectory proxy) ---
    rev_cagr = ratios.get("revenue_cagr_5yr")
    score_growth = None
    if rev_cagr is not None:
        if rev_cagr > 0.20:
            score_growth = 8.5
        elif rev_cagr > 0.12:
            score_growth = 7.5
        elif rev_cagr > 0.06:
            score_growth = 6.0
        elif rev_cagr > 0.02:
            score_growth = 5.0
        elif rev_cagr > -0.02:
            score_growth = 3.5
        else:
            score_growth = 2.0
        reasons.append(
            f"5yr revenue CAGR {rev_cagr:.1%} → growth proxy {score_growth:.1f}"
        )
    sub_scores["growth_consistency"] = score_growth

    # --- Sector premium (tech/healthcare get structural moat bonus) ---
    sector_bonus = 0.0
    if sector in (45, 35):  # Tech, Healthcare
        sector_bonus = 0.5
        reasons.append(f"GICS {sector}: sector structural moat bonus +{sector_bonus}")

    valid = {k: v for k, v in sub_scores.items() if v is not None}
    if not valid:
        return {
            "score": None,
            "assessment": "insufficient_data",
            "sub_scores": sub_scores,
            "reasons": reasons,
        }

    weights = {
        "pricing_power": 0.35,
        "returns_on_capital": 0.35,
        "growth_consistency": 0.30,
    }
    total = sum(valid[k] * weights[k] for k in valid) / sum(weights[k] for k in valid)
    total += sector_bonus
    final = _clamp(total)

    if final >= 7.5:
        assessment = (
            "Wide moat — sustained high returns, pricing power, consistent growth"
        )
    elif final >= 6.0:
        assessment = "Narrow moat — competitive advantages present but not dominant"
    elif final >= 4.0:
        assessment = "No moat — returns near cost of capital, undifferentiated"
    else:
        assessment = "Moat erosion — declining returns, competitive pressure evident"

    return {
        "score": final,
        "assessment": assessment,
        "sub_scores": sub_scores,
        "reasons": reasons,
        "adjustable": True,
        "adjustment_range": [-2.0, 2.0],
        "adjustment_note": "LLM agent may adjust ±2.0 based on qualitative moat analysis (Morningstar framework findings)",
        "methodology": "Moat = PricingPower(35%) + Returns(35%) + Growth(30%) + SectorBonus",
    }


# ---------------------------------------------------------------------------
# 3. Management Quality Score (1-10)
# ---------------------------------------------------------------------------


def compute_management_quality(metrics: dict, sentiment: dict | None = None) -> dict:
    """Score management quality from quantitative proxies.

    Adjustable ±2.0 by LLM agent based on qualitative leadership assessment.
    """
    ratios = metrics.get("ratios", {})
    reasons: list[str] = []
    sub_scores: dict[str, float | None] = {}

    # --- Capital Allocation (ROIC vs WACC spread proxy via ROE) ---
    roe = ratios.get("roe")
    score_capital = None
    if roe is not None:
        if roe > 0.20:
            score_capital = 8.5
        elif roe > 0.14:
            score_capital = 7.0
        elif roe > 0.10:
            score_capital = 5.5
        elif roe > 0.05:
            score_capital = 4.0
        else:
            score_capital = 2.0
        reasons.append(f"ROE {roe:.1%} → capital allocation proxy {score_capital:.1f}")
    sub_scores["capital_allocation"] = score_capital

    # --- Insider Activity ---
    score_insider = 5.0  # Neutral default
    if sentiment:
        insider = sentiment.get("insider", {})
        summary = insider.get("summary", {})
        buys = summary.get("buys_count", 0)
        sells = summary.get("sells_count", 0)
        clusters = insider.get("cluster_detection") or []

        if buys > sells * 2 and any(
            c.get("type") == "cluster_buying" for c in clusters
        ):
            score_insider = 9.0
            reasons.append(
                f"Strong insider buying: {buys} buys vs {sells} sells with cluster"
            )
        elif buys > sells:
            score_insider = 7.0
            reasons.append(f"Net insider buying: {buys} buys vs {sells} sells")
        elif sells > buys * 3:
            score_insider = 2.0
            reasons.append(f"Heavy insider selling: {sells} sells vs {buys} buys")
        elif sells > buys:
            score_insider = 4.0
            reasons.append(f"Net insider selling: {sells} sells vs {buys} buys")
        if any(c.get("type") == "cluster_buying" for c in clusters):
            reasons.append("Cluster buying detected — strong bullish signal")
        if any(c.get("type") == "cluster_selling" for c in clusters):
            reasons.append("Cluster selling detected — bearish signal")
            score_insider = min(score_insider, 3.0)
    sub_scores["insider_activity"] = score_insider

    # --- Guidance Accuracy (earnings beat streak proxy) ---
    score_guidance = 5.0
    if sentiment:
        earnings = sentiment.get("earnings", {})
        beat_streak = earnings.get("beat_streak", 0)
        if beat_streak >= 4:
            score_guidance = 9.0
            reasons.append(f"Consistent earnings beats: {beat_streak}-quarter streak")
        elif beat_streak >= 2:
            score_guidance = 7.0
            reasons.append(f"Recent earnings beats: {beat_streak}-quarter streak")
        elif beat_streak == 1:
            score_guidance = 6.0
        else:
            # Check for misses
            surprises = earnings.get("past_surprises", [])
            misses = sum(
                1
                for s in surprises
                if s.get("surprise") is not None and s["surprise"] < 0
            )
            if misses >= 2:
                score_guidance = 3.0
                reasons.append(f"{misses} earnings misses in recent quarters")
    sub_scores["guidance_accuracy"] = score_guidance

    # --- Shareholder returns (buyback + dividend) ---
    score_shareholder = 5.0
    # No direct buyback data in current scripts; leave as neutral
    sub_scores["shareholder_returns"] = score_shareholder

    weights = {
        "capital_allocation": 0.40,
        "insider_activity": 0.35,
        "guidance_accuracy": 0.25,
    }
    valid = {k: v for k, v in sub_scores.items() if k != "shareholder_returns"}
    if not valid:
        return {
            "score": None,
            "assessment": "insufficient_data",
            "sub_scores": sub_scores,
            "reasons": reasons,
        }

    total = sum(valid[k] * weights[k] for k in valid) / sum(weights[k] for k in valid)
    final = _clamp(total)

    if final >= 7.5:
        assessment = "Excellent — strong capital allocation, insider alignment, consistent delivery"
    elif final >= 6.0:
        assessment = "Good — competent management with some areas for improvement"
    elif final >= 4.0:
        assessment = "Adequate — mixed signals, some governance concerns"
    else:
        assessment = "Poor — significant management concerns or misalignment"

    return {
        "score": final,
        "assessment": assessment,
        "sub_scores": sub_scores,
        "reasons": reasons,
        "adjustable": True,
        "adjustment_range": [-2.0, 2.0],
        "adjustment_note": "LLM agent may adjust ±2.0 based on qualitative leadership assessment (Fisher's 15 points, Glassdoor trends, CEO track record)",
        "methodology": "Management = CapitalAlloc(40%) + Insider(35%) + Guidance(25%)",
    }


# ---------------------------------------------------------------------------
# 4. Valuation Attractiveness Score (1-10)
# ---------------------------------------------------------------------------


def compute_valuation(metrics: dict) -> dict:
    """Score valuation attractiveness from DCF, comps, and reverse DCF."""
    reasons: list[str] = []
    sub_scores: dict[str, float | None] = {}

    # --- DCF Margin of Safety ---
    dcf = metrics.get("dcf_valuation", {})
    dcf_value = dcf.get("per_share_value")
    ratios = metrics.get("ratios", {})
    pe = ratios.get("pe_ratio")
    score_dcf = None
    if dcf_value and pe:
        # Approximate current price from P/E * EPS
        eps = ratios.get("eps")
        if eps:
            current_price = pe * eps
            mos = (
                (dcf_value - current_price) / current_price if current_price > 0 else 0
            )
            if mos > 0.30:
                score_dcf = 9.5
            elif mos > 0.15:
                score_dcf = 8.0
            elif mos > 0.05:
                score_dcf = 6.5
            elif mos > -0.05:
                score_dcf = 5.0
            elif mos > -0.15:
                score_dcf = 3.5
            elif mos > -0.30:
                score_dcf = 2.0
            else:
                score_dcf = 1.0
            reasons.append(
                f"DCF margin of safety: {mos:.1%} → sub-score {score_dcf:.1f}"
            )
    sub_scores["dcf_mos"] = score_dcf

    # --- P/E vs history / sector ---
    score_pe = None
    if pe and pe > 0:
        if pe < 10:
            score_pe = 9.0
        elif pe < 15:
            score_pe = 7.5
        elif pe < 20:
            score_pe = 6.0
        elif pe < 25:
            score_pe = 5.0
        elif pe < 35:
            score_pe = 3.5
        elif pe < 50:
            score_pe = 2.0
        else:
            score_pe = 1.0
        reasons.append(f"P/E: {pe:.1f} → sub-score {score_pe:.1f}")
    sub_scores["pe_level"] = score_pe

    # --- PEG Ratio (Lynch) ---
    peg = ratios.get("peg_ratio")
    score_peg = None
    if peg is not None:
        if peg < 0.8:
            score_peg = 9.0
        elif peg < 1.2:
            score_peg = 7.5
        elif peg < 1.8:
            score_peg = 6.0
        elif peg < 2.5:
            score_peg = 4.5
        else:
            score_peg = 2.5
        reasons.append(f"PEG: {peg:.2f} → sub-score {score_peg:.1f}")
    sub_scores["peg_ratio"] = score_peg

    # --- FCF Yield vs Risk-Free ---
    fcf_yield = ratios.get("fcf_yield")
    score_fcf_yield = None
    if fcf_yield is not None:
        if fcf_yield > 0.08:
            score_fcf_yield = 9.0
        elif fcf_yield > 0.05:
            score_fcf_yield = 7.5
        elif fcf_yield > 0.03:
            score_fcf_yield = 5.5
        elif fcf_yield > 0.01:
            score_fcf_yield = 3.5
        else:
            score_fcf_yield = 1.5
        reasons.append(f"FCF yield: {fcf_yield:.1%} → sub-score {score_fcf_yield:.1f}")
    sub_scores["fcf_yield"] = score_fcf_yield

    # --- Reverse DCF ---
    rev_dcf = metrics.get("reverse_dcf", {})
    implied_growth = rev_dcf.get("implied_growth_rate")
    rev_cagr = ratios.get("revenue_cagr_5yr")
    score_reverse = None
    if implied_growth is not None and rev_cagr is not None:
        gap = implied_growth - rev_cagr
        if gap < -0.05:
            score_reverse = 9.0  # Market underpricing growth
        elif gap < 0:
            score_reverse = 7.0
        elif gap < 0.05:
            score_reverse = 5.0
        elif gap < 0.10:
            score_reverse = 3.0
        else:
            score_reverse = 1.5  # Market pricing unrealistic growth
        reasons.append(
            f"Reverse DCF implied growth {implied_growth:.1%} vs historical {rev_cagr:.1%} → sub-score {score_reverse:.1f}"
        )
    sub_scores["reverse_dcf"] = score_reverse

    weights = {
        "dcf_mos": 0.30,
        "pe_level": 0.15,
        "peg_ratio": 0.20,
        "fcf_yield": 0.20,
        "reverse_dcf": 0.15,
    }
    valid = {k: v for k, v in sub_scores.items() if v is not None}
    if not valid:
        return {
            "score": None,
            "assessment": "insufficient_data",
            "sub_scores": sub_scores,
            "reasons": reasons,
        }

    total = sum(valid[k] * weights[k] for k in valid) / sum(weights[k] for k in valid)
    final = _clamp(total)

    if final >= 7.5:
        assessment = (
            "Significantly undervalued — large margin of safety, attractive multiples"
        )
    elif final >= 6.0:
        assessment = "Moderately undervalued — reasonable price for quality"
    elif final >= 4.5:
        assessment = "Fairly valued — price near intrinsic, no margin of safety"
    elif final >= 3.0:
        assessment = "Moderately overvalued — premium pricing, limited upside"
    else:
        assessment = (
            "Significantly overvalued — extreme multiples, unrealistic growth priced in"
        )

    return {
        "score": final,
        "assessment": assessment,
        "sub_scores": sub_scores,
        "reasons": reasons,
        "methodology": "Valuation = DCF_MoS(30%) + PE(15%) + PEG(20%) + FCF_Yield(20%) + ReverseDCF(15%)",
    }


# ---------------------------------------------------------------------------
# 5. Macro Tailwind Score (1-10)
# ---------------------------------------------------------------------------


def compute_macro_tailwind(macro: dict, metrics: dict | None = None) -> dict:
    """Score macro environment favorability.

    10 = strong tailwinds, 1 = strong headwinds, 5 = neutral.
    """
    summary = macro.get("macro_summary", {})
    indicators = macro.get("indicators", {})
    reasons: list[str] = []
    sub_scores: dict[str, float | None] = {}

    # --- Dalio Regime ---
    regime = summary.get("macro_regime", "unknown")
    if regime == "goldilocks":
        score_regime = 8.5
        reasons.append(
            "Goldilocks regime (rising growth + stable inflation) — optimal for equities"
        )
    elif regime == "reflation":
        score_regime = 6.5
        reasons.append(
            "Reflation regime (rising growth + rising inflation) — favorable but watch rates"
        )
    elif regime == "deflation":
        score_regime = 4.0
        reasons.append(
            "Deflationary regime (falling growth + low inflation) — challenging for equities"
        )
    elif regime == "stagflation":
        score_regime = 2.0
        reasons.append(
            "Stagflation regime (falling growth + rising inflation) — worst for equities"
        )
    else:
        score_regime = 5.0
        reasons.append("Unknown/ambiguous macro regime")
    sub_scores["dalio_regime"] = score_regime

    # --- Yield Curve ---
    key_levels = summary.get("key_levels", {})
    inverted = key_levels.get("yield_curve_inverted", False)
    spread = key_levels.get("ten_two_spread")
    if inverted:
        score_yc = 2.5
        spread_str = f"{spread:.2f}%" if spread is not None else "N/A"
        reasons.append(f"Yield curve inverted ({spread_str}) — recession signal active")
    elif spread is not None and spread < 0.5:
        score_yc = 4.0
        reasons.append(f"Yield curve flat ({spread:.2f}%) — caution")
    else:
        score_yc = 6.5
        spread_str = f"{spread:.2f}%" if spread is not None else "data unavailable"
        reasons.append(f"Yield curve normal ({spread_str}) — no recession signal")
    sub_scores["yield_curve"] = score_yc

    # --- PMI ---
    pmi = key_levels.get("ism_pmi")
    if pmi is not None:
        if pmi > 55:
            score_pmi = 8.0
            reasons.append(f"PMI {pmi:.1f} — strong expansion")
        elif pmi > 50:
            score_pmi = 6.0
            reasons.append(f"PMI {pmi:.1f} — mild expansion")
        elif pmi > 45:
            score_pmi = 4.0
            reasons.append(f"PMI {pmi:.1f} — contraction warning")
        else:
            score_pmi = 2.0
            reasons.append(f"PMI {pmi:.1f} — significant contraction")
        sub_scores["pmi"] = score_pmi

    # --- Recession Risk ---
    recession = summary.get("recession_risk", "unknown")
    if recession == "low":
        score_recession = 7.5
    elif recession == "elevated":
        score_recession = 4.5
    elif recession == "high":
        score_recession = 2.0
    else:
        score_recession = 5.0
    reasons.append(f"Recession risk: {recession}")
    sub_scores["recession_risk"] = score_recession

    # --- Fed Direction ---
    ff_rate = key_levels.get("fed_funds_rate")
    # Compare to 6-month trend in macro data
    fed_data = indicators.get("DFF", {}).get("data", [])
    if len(fed_data) >= 2:
        recent = fed_data[0].get("value", 0) or 0
        prior_6m = fed_data[min(5, len(fed_data) - 1)].get("value", 0) or 0
        if recent < prior_6m * 0.9:
            # Fed cutting → bullish
            score_fed = 8.0
            reasons.append("Fed cutting rates — accommodative")
        elif recent > prior_6m * 1.05:
            score_fed = 3.0
            reasons.append("Fed hiking rates — restrictive")
        else:
            score_fed = 5.5
            reasons.append("Fed on hold — neutral")
    else:
        score_fed = 5.0
    sub_scores["fed_direction"] = score_fed

    weights = {
        "dalio_regime": 0.30,
        "yield_curve": 0.20,
        "pmi": 0.15,
        "recession_risk": 0.20,
        "fed_direction": 0.15,
    }
    valid = {k: v for k, v in sub_scores.items() if v is not None}
    if not valid:
        return {
            "score": None,
            "assessment": "insufficient_data",
            "sub_scores": sub_scores,
            "reasons": reasons,
        }

    total = sum(valid[k] * weights[k] for k in valid) / sum(weights[k] for k in valid)
    final = _clamp(total)

    if final >= 7.0:
        assessment = (
            "Strong macro tailwinds — expansionary, accommodative, low recession risk"
        )
    elif final >= 5.5:
        assessment = "Mild tailwinds — generally favorable with some caution areas"
    elif final >= 4.0:
        assessment = "Mixed — some headwinds offsetting tailwinds"
    elif final >= 2.5:
        assessment = "Headwinds dominating — multiple macro concerns"
    else:
        assessment = "Strong headwinds — recessionary signals, restrictive policy"

    return {
        "score": final,
        "assessment": assessment,
        "sub_scores": sub_scores,
        "reasons": reasons,
        "methodology": "Macro = DalioRegime(30%) + YieldCurve(20%) + PMI(15%) + RecessionRisk(20%) + FedDirection(15%)",
    }


# ---------------------------------------------------------------------------
# 6. Risk Profile Score (1-10)
# ---------------------------------------------------------------------------


def compute_risk_profile(metrics: dict) -> dict:
    """Score risk profile. Higher = lower risk (safer)."""
    reasons: list[str] = []
    sub_scores: dict[str, float | None] = {}
    ratios = metrics.get("ratios", {})

    # --- Altman Z-Score ---
    altman = metrics.get("altman_zscore", {})
    zscore = altman.get("zscore")
    zone = altman.get("zone", "")
    score_altman = None
    if zscore is not None:
        if zone == "Safe":
            score_altman = 9.0
            reasons.append(f"Altman Z: {zscore:.2f} (Safe zone)")
        elif zone == "Grey":
            score_altman = 5.0
            reasons.append(f"Altman Z: {zscore:.2f} (Grey zone — monitor)")
        else:
            score_altman = 2.0
            reasons.append(
                f"Altman Z: {zscore:.2f} (Distress zone — elevated bankruptcy risk)"
            )
    sub_scores["altman_z"] = score_altman

    # --- Beneish M-Score ---
    beneish = metrics.get("beneish_mscore", {})
    mscore = beneish.get("mscore")
    flagged = beneish.get("flag", False)
    score_beneish = None
    if flagged:
        score_beneish = 2.0
        reasons.append(f"Beneish M-Score: {mscore:.2f} (> -1.78 → manipulation risk)")
    elif mscore is not None:
        score_beneish = 8.0
        reasons.append(f"Beneish M-Score: {mscore:.2f} (clean)")
    sub_scores["beneish_m"] = score_beneish

    # --- Leverage ---
    debt_eq = ratios.get("debt_to_equity")
    score_leverage = None
    if debt_eq is not None:
        if debt_eq < 0.5:
            score_leverage = 9.0
        elif debt_eq < 1.0:
            score_leverage = 7.5
        elif debt_eq < 2.0:
            score_leverage = 5.0
        elif debt_eq < 3.5:
            score_leverage = 3.0
        else:
            score_leverage = 1.5
        reasons.append(f"Debt/Equity: {debt_eq:.2f} → sub-score {score_leverage:.1f}")
    sub_scores["leverage"] = score_leverage

    # --- FCF / OCF quality ---
    ocf_to_ni = ratios.get("ocf_to_ni")
    score_cf_quality = None
    if ocf_to_ni is not None:
        if ocf_to_ni > 1.2:
            score_cf_quality = 9.0
        elif ocf_to_ni > 0.9:
            score_cf_quality = 7.0
        elif ocf_to_ni > 0.7:
            score_cf_quality = 5.0
        else:
            score_cf_quality = 2.5
        reasons.append(f"OCF/NI: {ocf_to_ni:.2f} → sub-score {score_cf_quality:.1f}")
    sub_scores["cash_flow_quality"] = score_cf_quality

    # --- EPS Growth stability ---
    ni_cagr = ratios.get("ni_cagr_5yr")
    score_earnings_stability = None
    if ni_cagr is not None:
        if ni_cagr > 0.10:
            score_earnings_stability = 8.0
        elif ni_cagr > 0.03:
            score_earnings_stability = 6.0
        elif ni_cagr > -0.05:
            score_earnings_stability = 4.0
        else:
            score_earnings_stability = 2.0
    sub_scores["earnings_stability"] = score_earnings_stability

    weights = {
        "altman_z": 0.25,
        "beneish_m": 0.25,
        "leverage": 0.20,
        "cash_flow_quality": 0.20,
        "earnings_stability": 0.10,
    }
    valid = {k: v for k, v in sub_scores.items() if v is not None}
    if not valid:
        return {
            "score": None,
            "assessment": "insufficient_data",
            "sub_scores": sub_scores,
            "reasons": reasons,
        }

    total = sum(valid[k] * weights[k] for k in valid) / sum(weights[k] for k in valid)
    final = _clamp(total)

    if final >= 7.5:
        assessment = (
            "Low risk — strong balance sheet, clean forensic signals, quality earnings"
        )
    elif final >= 6.0:
        assessment = "Moderate risk — manageable but some areas warrant monitoring"
    elif final >= 4.0:
        assessment = "Elevated risk — multiple concerns, hedge or reduce position"
    else:
        assessment = (
            "High risk — active red flags, potential for permanent capital loss"
        )

    # Red flag detection
    red_flags = []
    if flagged:
        red_flags.append("Beneish M-Score flagged (> -1.78)")
    if zone == "Distress":
        red_flags.append("Altman Z in Distress zone (< 1.81)")
    if ocf_to_ni is not None and ocf_to_ni < 0.7:
        red_flags.append(f"Poor OCF/NI quality ({ocf_to_ni:.2f})")
    if debt_eq is not None and debt_eq > 3.5:
        red_flags.append(f"Excessive leverage ({debt_eq:.2f})")

    return {
        "score": final,
        "assessment": assessment,
        "sub_scores": sub_scores,
        "reasons": reasons,
        "red_flags": red_flags,
        "red_flag_count": len(red_flags),
        "override": len(red_flags) >= 3,  # 3+ red flags → no Buy rating
        "methodology": "Risk = AltmanZ(25%) + BeneishM(25%) + Leverage(20%) + CFQuality(20%) + EarnStability(10%)",
    }


# ---------------------------------------------------------------------------
# 7. Alternative Alignment Score (1-10)
# ---------------------------------------------------------------------------


def compute_alternative_alignment(alternatives: dict) -> dict:
    """Score alternative data alignment with reported fundamentals.

    Higher = alternative data confirms/exceeds reported trends.
    """
    alt_data = alternatives.get("alternative_data", {})
    reasons: list[str] = []
    sub_scores: dict[str, float | None] = {}
    null_count = 0
    total_sources = 0

    # --- Web Traffic ---
    web = alt_data.get("web", {})
    total_sources += 1
    if (
        web
        and web.get("source") != "unavailable_paywall"
        and web.get("search_interest_trend")
    ):
        trend = web.get("search_interest_trend")
        if trend == "rising":
            sub_scores["web_traffic"] = 8.0
        elif trend == "stable":
            sub_scores["web_traffic"] = 6.0
        elif trend == "declining":
            sub_scores["web_traffic"] = 3.0
        else:
            sub_scores["web_traffic"] = 5.0
        reasons.append(f"Web search interest: {trend}")
    else:
        null_count += 1

    # --- Social Sentiment ---
    social = alt_data.get("social", {})
    total_sources += 1
    if social and social.get("reddit_sentiment_score") is not None:
        sent = social["reddit_sentiment_score"]
        if sent > 0.3:
            sub_scores["social_sentiment"] = 8.5
        elif sent > 0.1:
            sub_scores["social_sentiment"] = 7.0
        elif sent > -0.1:
            sub_scores["social_sentiment"] = 5.0
        elif sent > -0.3:
            sub_scores["social_sentiment"] = 3.0
        else:
            sub_scores["social_sentiment"] = 1.5
        reasons.append(f"Reddit sentiment: {sent:.3f}")
    else:
        # Try Finnhub social as fallback
        null_count += 1

    # --- Patents ---
    patents = alt_data.get("patents", {})
    total_sources += 1
    if patents and patents.get("recent_patents", 0) > 0:
        count = patents.get("recent_patents", 0)
        if count > 50:
            sub_scores["innovation"] = 9.0
        elif count > 20:
            sub_scores["innovation"] = 7.5
        elif count > 5:
            sub_scores["innovation"] = 6.0
        else:
            sub_scores["innovation"] = 4.0
        reasons.append(f"Recent patents: {count}")
    else:
        null_count += 1

    # --- Glassdoor ---
    glassdoor = alt_data.get("glassdoor", {})
    total_sources += 1
    if glassdoor and glassdoor.get("overall_rating") is not None:
        rating = glassdoor["overall_rating"]
        if rating > 4.0:
            sub_scores["employee_sentiment"] = 8.5
        elif rating > 3.5:
            sub_scores["employee_sentiment"] = 6.5
        elif rating > 3.0:
            sub_scores["employee_sentiment"] = 5.0
        else:
            sub_scores["employee_sentiment"] = 3.0
        reasons.append(f"Glassdoor rating: {rating}")
    else:
        null_count += 1

    # --- Hiring ---
    total_sources += 1
    hiring = alt_data.get("hiring", {})
    if hiring and hiring.get("source") != "unavailable_paywall":
        pass  # Would score if data available
    else:
        null_count += 1

    # --- Transactions ---
    total_sources += 1
    txn = alt_data.get("transactions", {})
    if txn and txn.get("source") != "unavailable_paywall":
        pass
    else:
        null_count += 1

    sub_score_weights = {
        "web_traffic": 0.20,
        "social_sentiment": 0.20,
        "innovation": 0.20,
        "employee_sentiment": 0.20,
        "hiring": 0.10,
        "transactions": 0.10,
    }
    valid = {k: v for k, v in sub_scores.items()}
    if not valid:
        return {
            "score": None,
            "assessment": "insufficient_data",
            "sub_scores": sub_scores,
            "reasons": reasons,
            "data_availability": f"{total_sources - null_count}/{total_sources} sources",
        }

    total = sum(valid[k] * sub_score_weights.get(k, 0.17) for k in valid)
    total /= sum(sub_score_weights.get(k, 0.17) for k in valid)
    final = _clamp(total)

    if final >= 7.0:
        assessment = "Alternative data confirms/exceeds reported trends"
    elif final >= 5.0:
        assessment = "Mixed — some alt signals align, some neutral"
    elif final >= 3.5:
        assessment = "Alternative data diverging negative — potential early warning"
    else:
        assessment = "Significant negative divergence — investigate further"

    return {
        "score": final,
        "assessment": assessment,
        "sub_scores": sub_scores,
        "reasons": reasons,
        "data_availability": f"{total_sources - null_count}/{total_sources} sources",
        "methodology": "AltAlign = Web(20%) + Social(20%) + Innovation(20%) + Employee(20%) + Hiring(10%) + Txn(10%)",
    }


# ---------------------------------------------------------------------------
# 8. Technical Setup Score (1-10)
# ---------------------------------------------------------------------------


def compute_technical_setup(technicals: dict) -> dict:
    """Score technical setup quality from computed indicators."""
    # Handle per-ticker structure from fetch_technicals.py
    if not technicals:
        return {"score": None, "assessment": "insufficient_data"}

    # Find the first ticker's data
    ticker_data = None
    for key, val in technicals.items():
        if isinstance(val, dict) and "trend_strength" in val:
            ticker_data = val
            break

    if not ticker_data:
        return {"score": None, "assessment": "insufficient_data"}

    trend = ticker_data.get("trend_strength", {})
    momentum = ticker_data.get("momentum", {})
    setup_quality = ticker_data.get("setup_quality")
    volume = ticker_data.get("volume", {})
    reasons: list[str] = []

    # Use pre-computed composite if available
    if setup_quality is not None:
        final = _clamp(setup_quality)
        reasons.append(f"Pre-computed setup quality: {setup_quality}")
    else:
        # Combine trend + momentum scores
        t_score = trend.get("score", 5.0) or 5.0
        m_score = momentum.get("score", 5.0) or 5.0
        final = _clamp((t_score + m_score) / 2)
        reasons.append(f"Trend: {t_score}, Momentum: {m_score} → composite {final}")

    if trend.get("assessment"):
        reasons.append(f"Trend: {trend['assessment']}")
    if momentum.get("assessment"):
        reasons.append(f"Momentum: {momentum['assessment']}")
    if volume.get("assessment"):
        reasons.append(f"Volume: {volume['assessment']}")

    if final >= 7.0:
        assessment = "Strong technical setup — trend + momentum aligned bullishly"
    elif final >= 5.5:
        assessment = "Moderate setup — positive bias but not all signals confirming"
    elif final >= 4.5:
        assessment = "Neutral — range-bound or mixed signals"
    elif final >= 3.0:
        assessment = "Weak setup — bearish bias, negative momentum"
    else:
        assessment = "Broken setup — strong bearish trend, distribution"

    return {
        "score": final,
        "assessment": assessment,
        "trend_score": trend.get("score"),
        "momentum_score": momentum.get("score"),
        "reasons": reasons,
        "methodology": "Technical = avg(TrendScore, MomentumScore); adjusted for volume signals",
    }


# ---------------------------------------------------------------------------
# 9. Capital Structure Score (1-10)
# ---------------------------------------------------------------------------


def compute_capital_structure(capital_data: dict) -> dict:
    """Score capital structure and shareholder returns quality.

    Higher = better capital allocation (buybacks at discount, low dilution,
    optimal leverage, strong total capital return).
    """
    if not capital_data:
        return {"score": None, "assessment": "insufficient_data"}

    reasons: list[str] = []
    sub_scores: dict[str, float | None] = {}

    # --- Buyback Effectiveness ---
    buyback = capital_data.get("buyback_analysis", {})
    buyback_roi = buyback.get("buyback_roi_annualized")
    score_buyback = None
    if buyback_roi is not None:
        if buyback_roi > 0.15:
            score_buyback = 9.0
        elif buyback_roi > 0.08:
            score_buyback = 7.5
        elif buyback_roi > 0.0:
            score_buyback = 5.5
        elif buyback_roi > -0.10:
            score_buyback = 3.5
        else:
            score_buyback = 1.5
        reasons.append(
            f"Buyback ROI: {buyback_roi:.1%} → sub-score {score_buyback:.1f}"
        )
    sub_scores["buyback_effectiveness"] = score_buyback

    # --- SBC Dilution ---
    sbc = capital_data.get("sbc_dilution", {})
    sbc_pct = sbc.get("sbc_to_revenue")
    score_sbc = None
    if sbc_pct is not None:
        if sbc_pct < 0.02:
            score_sbc = 9.0
        elif sbc_pct < 0.05:
            score_sbc = 7.0
        elif sbc_pct < 0.10:
            score_sbc = 5.0
        elif sbc_pct < 0.15:
            score_sbc = 3.0
        else:
            score_sbc = 1.5
        reasons.append(f"SBC/Revenue: {sbc_pct:.1%} → sub-score {score_sbc:.1f}")
    sub_scores["sbc_dilution"] = score_sbc

    # --- Total Capital Return ---
    cap_return = capital_data.get("capital_return", {})
    total_yield = cap_return.get("total_capital_return_yield")
    score_return = None
    if total_yield is not None:
        if total_yield > 0.06:
            score_return = 9.0
        elif total_yield > 0.04:
            score_return = 7.5
        elif total_yield > 0.02:
            score_return = 6.0
        elif total_yield > 0.0:
            score_return = 4.5
        else:
            score_return = 2.5
        reasons.append(
            f"Total capital return yield: {total_yield:.1%} → sub-score {score_return:.1f}"
        )
    sub_scores["total_return"] = score_return

    # --- Leverage Optimality (distance from optimal WACC point) ---
    structure = capital_data.get("capital_structure", {})
    wacc_current = structure.get("wacc_current")
    wacc_sensitivity = structure.get("wacc_sensitivity", [])
    score_leverage_opt = None
    if wacc_current is not None and wacc_sensitivity:
        min_wacc = min(
            (s.get("wacc", 1.0) for s in wacc_sensitivity), default=wacc_current
        )
        gap = wacc_current - min_wacc
        if gap < 0.005:
            score_leverage_opt = 9.0
        elif gap < 0.01:
            score_leverage_opt = 7.0
        elif gap < 0.02:
            score_leverage_opt = 5.0
        else:
            score_leverage_opt = 3.0
        reasons.append(
            f"WACC gap from optimal: {gap:.2%} → sub-score {score_leverage_opt:.1f}"
        )
    sub_scores["leverage_optimality"] = score_leverage_opt

    weights = {
        "buyback_effectiveness": 0.30,
        "sbc_dilution": 0.25,
        "total_return": 0.25,
        "leverage_optimality": 0.20,
    }
    valid = {k: v for k, v in sub_scores.items() if v is not None}
    if not valid:
        return {
            "score": None,
            "assessment": "insufficient_data",
            "sub_scores": sub_scores,
            "reasons": reasons,
        }

    total = sum(valid[k] * weights[k] for k in valid) / sum(weights[k] for k in valid)
    final = _clamp(total)

    if final >= 7.5:
        assessment = "Excellent capital allocation — buybacks at discount, low dilution, strong returns"
    elif final >= 6.0:
        assessment = "Good — generally shareholder-friendly capital decisions"
    elif final >= 4.0:
        assessment = (
            "Adequate — mixed capital allocation, some dilution or misallocation"
        )
    else:
        assessment = (
            "Poor — value-destructive buybacks, excessive SBC, or suboptimal leverage"
        )

    return {
        "score": final,
        "assessment": assessment,
        "sub_scores": sub_scores,
        "reasons": reasons,
        "methodology": "CapStructure = Buyback(30%) + SBC(25%) + TotalReturn(25%) + LeverageOpt(20%)",
    }


# ---------------------------------------------------------------------------
# 10. Weinstein Stage Alignment Score (1-10)
# ---------------------------------------------------------------------------


def compute_weinstein_alignment(technicals: dict) -> dict:
    """Score Weinstein stage alignment for timing purposes.

    Stage 2 (advancing) = highest score for longs.
    Stage 4 (declining) = lowest score for longs.
    """
    if not technicals:
        return {"score": None, "assessment": "insufficient_data"}

    ticker_data = None
    for key, val in technicals.items():
        if isinstance(val, dict) and "weinstein" in val:
            ticker_data = val
            break

    if not ticker_data or "weinstein" not in ticker_data:
        return {"score": None, "assessment": "No Weinstein data available"}

    weinstein = ticker_data["weinstein"]
    stage = weinstein.get("stage")
    stage_name = weinstein.get("stage_name", "")
    slope = weinstein.get("30wma_slope", 0)

    reasons: list[str] = []
    score = 5.0

    if stage == 2:
        score = 9.0 if slope > 0.002 else 7.5
        reasons.append(f"Weinstein Stage 2 (Advancing) — 30WMA slope: {slope:.4f}")
    elif stage == 1:
        score = 5.5
        reasons.append("Weinstein Stage 1 (Basing) — accumulation phase")
    elif stage == 3:
        score = 3.5
        reasons.append("Weinstein Stage 3 (Topping) — distribution phase")
    elif stage == 4:
        score = 1.5
        reasons.append("Weinstein Stage 4 (Declining) — avoid or short")

    # Relative strength bonus/penalty
    rs = ticker_data.get("relative_strength", {})
    composite_rs = rs.get("composite_rs")
    if composite_rs is not None:
        if composite_rs > 1.1:
            score = min(10.0, score + 1.0)
            reasons.append(
                f"RS composite {composite_rs:.2f} > 1.1 — outperforming market"
            )
        elif composite_rs < 0.9:
            score = max(1.0, score - 1.0)
            reasons.append(
                f"RS composite {composite_rs:.2f} < 0.9 — underperforming market"
            )

    final = _clamp(score)

    if final >= 7.0:
        assessment = f"Stage {stage} ({stage_name}) — favorable for long positions"
    elif final >= 5.0:
        assessment = f"Stage {stage} ({stage_name}) — neutral, wait for confirmation"
    else:
        assessment = f"Stage {stage} ({stage_name}) — unfavorable for new longs"

    return {
        "score": final,
        "assessment": assessment,
        "stage": stage,
        "stage_name": stage_name,
        "reasons": reasons,
        "methodology": "Weinstein Stage scoring: S2=9, S1=5.5, S3=3.5, S4=1.5 ± RS adjustment",
    }


# ---------------------------------------------------------------------------
# 11. CANSLIM Score (1-10)
# ---------------------------------------------------------------------------


def compute_canslim(
    metrics: dict, technicals: dict, sentiment: dict | None = None
) -> dict:
    """Score O'Neil CANSLIM criteria (7 factors → 1-10).

    C = Current quarterly EPS growth
    A = Annual EPS growth
    N = New (highs, products, management)
    S = Supply/Demand (volume + float)
    L = Leader/Laggard (relative strength)
    I = Institutional sponsorship
    M = Market direction
    """
    ratios = metrics.get("ratios", {})
    reasons: list[str] = []
    factors: dict[str, float | None] = {}

    # C — Current quarterly EPS growth (>25% is passing)
    eps_growth_q = ratios.get("eps_growth_qoq")
    if eps_growth_q is not None:
        if eps_growth_q > 0.40:
            factors["C"] = 10.0
        elif eps_growth_q > 0.25:
            factors["C"] = 8.0
        elif eps_growth_q > 0.15:
            factors["C"] = 6.0
        elif eps_growth_q > 0.0:
            factors["C"] = 4.0
        else:
            factors["C"] = 2.0
        reasons.append(f"C: Quarterly EPS growth {eps_growth_q:.0%}")
    else:
        factors["C"] = None

    # A — Annual EPS growth (>25% for 3yr)
    ni_cagr = ratios.get("ni_cagr_5yr") or ratios.get("ni_cagr_3yr")
    if ni_cagr is not None:
        if ni_cagr > 0.25:
            factors["A"] = 9.0
        elif ni_cagr > 0.15:
            factors["A"] = 7.0
        elif ni_cagr > 0.08:
            factors["A"] = 5.0
        elif ni_cagr > 0.0:
            factors["A"] = 3.5
        else:
            factors["A"] = 1.5
        reasons.append(f"A: Annual EPS CAGR {ni_cagr:.0%}")
    else:
        factors["A"] = None

    # N — New highs (price near 52wk high)
    ticker_data = None
    for key, val in (technicals or {}).items():
        if isinstance(val, dict) and (
            "price_52w_position" in val or "trend_strength" in val
        ):
            ticker_data = val
            break

    if ticker_data:
        pos_52w = ticker_data.get("price_52w_position")
        if pos_52w is not None:
            if pos_52w > 0.90:
                factors["N"] = 9.0
                reasons.append(
                    f"N: Price at {pos_52w:.0%} of 52-week range — new high territory"
                )
            elif pos_52w > 0.75:
                factors["N"] = 7.0
            elif pos_52w > 0.50:
                factors["N"] = 5.0
            else:
                factors["N"] = 3.0
                reasons.append(
                    f"N: Price at {pos_52w:.0%} of 52-week range — not near highs"
                )
        else:
            factors["N"] = None
    else:
        factors["N"] = None

    # S — Supply/demand (volume trend)
    if ticker_data:
        volume_data = ticker_data.get("volume", {})
        vol_ratio = volume_data.get("volume_vs_avg")
        if vol_ratio is not None:
            if vol_ratio > 1.5:
                factors["S"] = 8.5
            elif vol_ratio > 1.0:
                factors["S"] = 6.5
            elif vol_ratio > 0.7:
                factors["S"] = 4.5
            else:
                factors["S"] = 3.0
        else:
            factors["S"] = None
    else:
        factors["S"] = None

    # L — Leader (relative strength)
    if ticker_data:
        rs = ticker_data.get("relative_strength", {})
        composite = rs.get("composite_rs")
        if composite is not None:
            if composite > 1.20:
                factors["L"] = 9.5
            elif composite > 1.05:
                factors["L"] = 7.5
            elif composite > 0.95:
                factors["L"] = 5.0
            elif composite > 0.80:
                factors["L"] = 3.0
            else:
                factors["L"] = 1.5
            reasons.append(f"L: RS composite {composite:.2f}")
        else:
            factors["L"] = None
    else:
        factors["L"] = None

    # I — Institutional sponsorship (from sentiment/insider)
    if sentiment:
        analyst = sentiment.get("analyst", {})
        total_analysts = 0
        rec_trends = analyst.get("recommendation_trends", [])
        if rec_trends:
            latest = rec_trends[0]
            total_analysts = sum(
                latest.get(k, 0)
                for k in ["strongBuy", "buy", "hold", "sell", "strongSell"]
            )
        if total_analysts > 20:
            factors["I"] = 8.0
        elif total_analysts > 10:
            factors["I"] = 6.5
        elif total_analysts > 5:
            factors["I"] = 5.0
        else:
            factors["I"] = 3.5
        reasons.append(f"I: {total_analysts} analysts covering")
    else:
        factors["I"] = None

    # M — Market direction (simplified: use market RS if available)
    factors["M"] = 5.0  # Neutral default; agent overrides based on macro

    valid = {k: v for k, v in factors.items() if v is not None}
    if len(valid) < 3:
        return {
            "score": None,
            "assessment": "insufficient_data",
            "factors": factors,
            "reasons": reasons,
        }

    avg = sum(valid.values()) / len(valid)
    final = _clamp(avg)

    pass_count = sum(1 for v in valid.values() if v >= 6.0)
    fail_count = sum(1 for v in valid.values() if v < 4.0)

    if final >= 7.5:
        assessment = f"Strong CANSLIM — {pass_count}/{len(valid)} factors passing"
    elif final >= 6.0:
        assessment = f"Moderate CANSLIM — {pass_count}/{len(valid)} factors passing"
    elif final >= 4.5:
        assessment = f"Weak CANSLIM — only {pass_count}/{len(valid)} factors passing, {fail_count} failing"
    else:
        assessment = f"CANSLIM fail — {fail_count}/{len(valid)} factors failing"

    return {
        "score": final,
        "assessment": assessment,
        "factors": factors,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "reasons": reasons,
        "methodology": "CANSLIM = avg(C,A,N,S,L,I,M) where each factor scored 1-10",
    }


# ---------------------------------------------------------------------------
# Framework divergence detection
# ---------------------------------------------------------------------------


def detect_framework_divergence(scores: dict) -> dict:
    """Detect when component scores strongly disagree, indicating analytical tension.

    Flags pairs of components where one is bullish (≥7.5) and the other is
    bearish (≤3.5). These divergences require human investigation.
    """
    components = [
        "financial_health",
        "moat_quality",
        "management_quality",
        "valuation_attractiveness",
        "macro_tailwind",
        "risk_profile",
        "alternative_alignment",
        "technical_setup",
        "capital_structure",
        "weinstein_alignment",
        "canslim",
    ]

    score_values = {}
    for comp in components:
        obj = scores.get(comp, {})
        s = obj.get("score") if isinstance(obj, dict) else None
        if s is not None:
            score_values[comp] = s

    divergences = []

    # Known meaningful divergence pairs
    tension_pairs = [
        ("financial_health", "valuation_attractiveness", "Value trap or recovery?"),
        ("moat_quality", "technical_setup", "Moat intact but market disagrees?"),
        ("macro_tailwind", "financial_health", "Strong company in weak macro?"),
        ("alternative_alignment", "financial_health", "Alt data sees deterioration?"),
        ("management_quality", "risk_profile", "Good management but high risk?"),
        ("valuation_attractiveness", "technical_setup", "Cheap but in downtrend?"),
        ("weinstein_alignment", "moat_quality", "Technical stage conflicts moat?"),
    ]

    for comp_a, comp_b, question in tension_pairs:
        a = score_values.get(comp_a)
        b = score_values.get(comp_b)
        if a is None or b is None:
            continue
        spread = abs(a - b)
        if spread >= 4.0 and ((a >= 7.5 and b <= 3.5) or (b >= 7.5 and a <= 3.5)):
            divergences.append(
                {
                    "pair": [comp_a, comp_b],
                    "scores": [a, b],
                    "spread": round(spread, 1),
                    "investigation_prompt": question,
                    "severity": "high" if spread >= 5.0 else "moderate",
                }
            )

    # Overall dispersion (standard deviation of available scores)
    if len(score_values) >= 4:
        values = list(score_values.values())
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        dispersion = variance**0.5
    else:
        dispersion = None

    return {
        "divergences": divergences,
        "divergence_count": len(divergences),
        "score_dispersion": round(dispersion, 2) if dispersion else None,
        "high_conviction_signal": len(divergences) == 0 and (dispersion or 0) < 1.5,
        "investigation_required": len(divergences) > 0,
    }


# ---------------------------------------------------------------------------
# Final conviction computation
# ---------------------------------------------------------------------------


def compute_conviction(scores: dict, report_type: str) -> dict:
    """Compute final conviction rating from component scores.

    Applies per-report-type weights and override rules.
    """
    weights = {
        "long": {
            "financial_health": 0.15,
            "moat_quality": 0.20,
            "management_quality": 0.15,
            "valuation_attractiveness": 0.20,
            "capital_structure": 0.10,
            "macro_tailwind": 0.05,
            "risk_profile": 0.10,
            "weinstein_alignment": 0.05,
        },
        "mid": {
            "financial_health": 0.10,
            "moat_quality": 0.10,
            "management_quality": 0.10,
            "valuation_attractiveness": 0.20,
            "macro_tailwind": 0.20,
            "risk_profile": 0.10,
            "weinstein_alignment": 0.10,
            "canslim": 0.10,
        },
        "short": {
            "valuation_attractiveness": 0.10,
            "macro_tailwind": 0.10,
            "risk_profile": 0.10,
            "alternative_alignment": 0.25,
            "technical_setup": 0.20,
            "weinstein_alignment": 0.15,
            "canslim": 0.10,
        },
        "quick": {
            "financial_health": 0.20,
            "valuation_attractiveness": 0.30,
            "risk_profile": 0.20,
            "technical_setup": 0.15,
            "weinstein_alignment": 0.15,
        },
    }

    wt = weights.get(report_type, weights["mid"])

    # Gather component scores
    component_scores = {}
    for comp in wt:
        key_map = {
            "financial_health": "financial_health",
            "moat_quality": "moat_quality",
            "management_quality": "management_quality",
            "valuation_attractiveness": "valuation_attractiveness",
            "capital_structure": "capital_structure",
            "macro_tailwind": "macro_tailwind",
            "risk_profile": "risk_profile",
            "alternative_alignment": "alternative_alignment",
            "technical_setup": "technical_setup",
            "weinstein_alignment": "weinstein_alignment",
            "canslim": "canslim",
        }
        score_obj = scores.get(key_map[comp], {})
        component_scores[comp] = score_obj.get("score")

    # Count missing
    missing = [k for k, v in component_scores.items() if v is None]
    low_components = [
        k for k, v in component_scores.items() if v is not None and v <= 3.0
    ]

    # Compute weighted average with available components
    available = {k: v for k, v in component_scores.items() if v is not None}
    if not available:
        return {
            "conviction": None,
            "rating": "Unable to rate",
            "confidence": "No data",
            "error": "No component scores available",
        }

    total_weight = sum(wt[k] for k in available)
    conviction = sum(available[k] * wt[k] for k in available) / total_weight

    # Apply override rules
    overrides = []
    confidence = "High"

    # Rule: any component ≤3 caps at Hold
    if low_components:
        conviction = min(conviction, 5.9)
        overrides.append(
            f"Component(s) ≤3 ({', '.join(low_components)}) → capped at Hold (5.9)"
        )

    # Rule: 3+ missing components → Low confidence
    if len(missing) >= 3:
        confidence = "Low"
        overrides.append(f"{len(missing)} missing components → Low confidence")

    # Rule: framework divergence reduces confidence
    divergence = scores.get("framework_divergence", {})
    if divergence.get("divergence_count", 0) >= 2:
        if confidence == "High":
            confidence = "Medium"
        overrides.append(
            f"{divergence['divergence_count']} framework divergences → confidence capped at Medium"
        )

    # Rule: red flag override
    risk_obj = scores.get("risk_profile", {})
    if risk_obj.get("override"):
        conviction = min(conviction, 3.9)
        overrides.append("3+ forensic red flags → capped at Sell (3.9)")

    conviction = round(conviction, 1)

    # Rating
    if conviction >= 9.0:
        rating = "Strong Buy"
    elif conviction >= 7.5:
        rating = "Buy"
    elif conviction >= 6.0:
        rating = "Hold / Accumulate"
    elif conviction >= 4.0:
        rating = "Hold / Reduce"
    elif conviction >= 2.0:
        rating = "Sell"
    else:
        rating = "Strong Sell"

    # Lollapalooza bonus
    lollapalooza = False
    # Check for 3+ high-score components (>7.5)
    high_components = [
        k for k, v in component_scores.items() if v is not None and v >= 7.5
    ]
    if len(high_components) >= 3:
        lollapalooza = True
        conviction = min(10.0, conviction + 1.5)
        overrides.append(
            f"Lollapalooza Effect detected ({len(high_components)} strong components) → +1.5 bonus"
        )

    return {
        "conviction": round(conviction, 1),
        "rating": rating,
        "confidence": confidence,
        "component_scores": component_scores,
        "missing_components": missing,
        "low_components": low_components,
        "overrides": overrides,
        "lollapalooza_detected": lollapalooza,
        "methodology": f"Conviction = Σ(component × weight) for {report_type}-term report. Override rules applied.",
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Compute deterministic component scores and conviction rating"
    )
    parser.add_argument("--metrics", help="Path to calculate_metrics.py output JSON")
    parser.add_argument("--macro", help="Path to fetch_macro.py output JSON")
    parser.add_argument("--technicals", help="Path to fetch_technicals.py output JSON")
    parser.add_argument(
        "--alternatives", help="Path to fetch_alternatives.py output JSON"
    )
    parser.add_argument("--sentiment", help="Path to fetch_sentiment.py output JSON")
    parser.add_argument(
        "--report-type",
        choices=["long", "mid", "short", "quick"],
        default="mid",
        help="Report type for conviction weighting",
    )
    parser.add_argument(
        "--gics-sector", type=int, help="GICS sector code (e.g., 45 for Tech)"
    )
    parser.add_argument(
        "--capital-structure", help="Path to fetch_capital_structure.py output JSON"
    )
    parser.add_argument("--liquidity", help="Path to compute_liquidity.py output JSON")
    parser.add_argument(
        "--short-interest", help="Path to fetch_short_interest.py output JSON"
    )
    parser.add_argument(
        "--activist", help="Path to fetch_activist_exposure.py output JSON"
    )
    parser.add_argument("--output", help="Output file path (default: stdout)")
    parser.add_argument(
        "--ticker", default="UNKNOWN", help="Ticker symbol for output labeling"
    )
    args = parser.parse_args()

    # Load inputs
    metrics = {}
    macro = {}
    technicals = {}
    alternatives = {}
    sentiment = {}
    capital_data = {}

    if args.metrics:
        with open(args.metrics) as f:
            metrics = json.load(f)
    if args.macro:
        with open(args.macro) as f:
            macro = json.load(f)
    if args.technicals:
        with open(args.technicals) as f:
            technicals = json.load(f)
    if args.alternatives:
        with open(args.alternatives) as f:
            alternatives = json.load(f)
    if args.sentiment:
        with open(args.sentiment) as f:
            raw_sent = json.load(f)
            if args.ticker in raw_sent:
                sentiment = raw_sent[args.ticker]
            elif raw_sent:
                sentiment = list(raw_sent.values())[0]
    if args.capital_structure:
        with open(args.capital_structure) as f:
            capital_data = json.load(f)

    liquidity_data = {}
    if args.liquidity:
        with open(args.liquidity) as f:
            liquidity_data = json.load(f)

    short_interest_data = {}
    if args.short_interest:
        with open(args.short_interest) as f:
            short_interest_data = json.load(f)

    activist_data = {}
    if args.activist:
        with open(args.activist) as f:
            activist_data = json.load(f)

    scores = {
        "ticker": args.ticker,
        "report_type": args.report_type,
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }

    # Compute each component score
    scores["financial_health"] = compute_financial_health(metrics, args.gics_sector)
    scores["moat_quality"] = compute_moat_quality(metrics, args.gics_sector)
    scores["management_quality"] = compute_management_quality(metrics, sentiment)
    scores["valuation_attractiveness"] = compute_valuation(metrics)
    scores["macro_tailwind"] = compute_macro_tailwind(macro, metrics)
    scores["risk_profile"] = compute_risk_profile(metrics)
    scores["alternative_alignment"] = compute_alternative_alignment(alternatives)
    scores["technical_setup"] = compute_technical_setup(technicals)
    scores["capital_structure"] = compute_capital_structure(capital_data)
    scores["weinstein_alignment"] = compute_weinstein_alignment(technicals)
    scores["canslim"] = compute_canslim(metrics, technicals, sentiment)

    # Framework divergence detection
    scores["framework_divergence"] = detect_framework_divergence(scores)

    # Conviction
    scores["conviction"] = compute_conviction(scores, args.report_type)

    # Liquidity-adjusted position sizing
    if liquidity_data:
        liq_score = liquidity_data.get("liquidity_score", 10.0)
        warnings = liquidity_data.get("warnings", [])
        pos_sizing = liquidity_data.get("position_sizing", {})
        scores["liquidity"] = {
            "score": liq_score,
            "rating": liquidity_data.get("liquidity_rating", "Unknown"),
            "days_to_liquidate": pos_sizing.get("days_to_liquidate"),
            "market_impact_bps": pos_sizing.get("estimated_slippage_bps"),
            "liquidity_constrained": pos_sizing.get("liquidity_constrained", False),
            "warnings": warnings,
        }
        conv = scores["conviction"]
        if liq_score < 4.0:
            conv["position_size_cap"] = "micro_cap_max_2pct"
            conv["liquidity_note"] = (
                "Liquidity score <4: max position 2% AUM regardless of conviction"
            )
        elif liq_score < 6.0:
            conv["position_size_cap"] = "small_cap_max_4pct"
            conv["liquidity_note"] = "Liquidity score <6: max position 4% AUM"
        else:
            conv["position_size_cap"] = "standard"

    # Short interest integration
    if short_interest_data:
        squeeze = short_interest_data.get("squeeze_analysis", {})
        positioning = short_interest_data.get("positioning", {})
        si = short_interest_data.get("short_interest", {})
        scores["short_interest"] = {
            "short_pct_float": si.get("short_pct_float"),
            "days_to_cover": squeeze.get("days_to_cover"),
            "squeeze_score": squeeze.get("squeeze_score"),
            "squeeze_risk_level": squeeze.get("squeeze_risk_level"),
            "momentum_vs_short": squeeze.get("momentum_vs_short"),
            "effective_free_float_pct": positioning.get("effective_free_float_pct"),
        }
        # For short-term reports, high squeeze score boosts conviction
        conv = scores["conviction"]
        sq_score = squeeze.get("squeeze_score", 0)
        if args.report_type == "short" and sq_score >= 7.0:
            conv["squeeze_catalyst"] = True
            conv["squeeze_note"] = (
                f"Squeeze score {sq_score:.1f}/10 — short-term upside catalyst"
            )
        elif sq_score >= 8.0:
            conv.setdefault("catalysts", []).append(
                f"High squeeze potential ({sq_score:.1f}/10)"
            )

    # Activist exposure integration
    if activist_data:
        activist_exp = activist_data.get("activist_exposure", {})
        insider = activist_data.get("insider_activity", {})
        scores["activist_exposure"] = {
            "activist_presence_score": activist_exp.get("activist_presence_score"),
            "proxy_fight_probability": activist_exp.get("proxy_fight_probability"),
            "activists_detected": activist_exp.get("activists_detected", []),
            "insider_confidence_ratio": insider.get("insider_confidence_ratio"),
            "cluster_selling_detected": insider.get("cluster_selling_detected"),
        }
        conv = scores["conviction"]
        presence = activist_exp.get("activist_presence_score", 0)
        if presence >= 7:
            conv.setdefault("catalysts", []).append(
                f"Activist involvement (score {presence}/10) — potential catalyst"
            )
        if insider.get("cluster_selling_detected"):
            conv.setdefault("warnings", []).append(
                "Insider cluster selling detected — management confidence flag"
            )

    output = json.dumps(scores, indent=2)
    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w") as f:
            f.write(output)
    else:
        print(output)
    sys.exit(0)


if __name__ == "__main__":
    main()
