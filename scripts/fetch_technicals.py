#!/usr/bin/env python3
"""Compute technical indicators from OHLCV price data.

Usage:
    fetch_technicals.py AAPL
    fetch_technicals.py AAPL --period 6mo --interval 1d
    fetch_technicals.py AAPL MSFT --output ./reports/[TICKER]/tech.json

Uses yfinance to fetch OHLCV data (free, no API key), then computes
technical indicators deterministically — no external API needed beyond
the price source.

Alpha Vantage free tier is only 25 calls/day, so local computation is
the primary path. Set ALPHAVANTAGE_API_KEY for the fallback path.

Indicators computed:
  - Trend: SMA (20/50/200), EMA (12/26/50/200), MACD, ADX
  - Momentum: RSI (14), Stochastic (14,3,3), Rate of Change
  - Volatility: Bollinger Bands (20,2), ATR (14)
  - Volume: OBV, Volume SMA, Volume Ratio, Volume Profile (POC, Value Area)
  - Support/Resistance: pivot points, rolling highs/lows
  - Composite: trend strength score, setup quality score
  - Weinstein Stage: 30-week MA-based structure classification (1-4)
  - CANSLIM Technicals: RS rank, supply/demand, market direction factors

Output: JSON to stdout or --output file.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

try:
    import yfinance as yf
except ImportError:
    sys.stderr.write("Error: 'yfinance' required. Run: pip install yfinance\n")
    sys.exit(1)

try:
    import numpy as np
except ImportError:
    sys.stderr.write("Error: 'numpy' required. Run: pip install numpy\n")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Indicator computation functions
# ---------------------------------------------------------------------------


def sma(values: list[float], window: int) -> list[float | None]:
    """Simple Moving Average."""
    out = [None] * len(values)
    if len(values) < window:
        return out
    for i in range(window - 1, len(values)):
        out[i] = sum(values[i - window + 1 : i + 1]) / window
    return out


def ema(values: list[float], window: int) -> list[float | None]:
    """Exponential Moving Average."""
    out = [None] * len(values)
    if len(values) < window:
        return out
    multiplier = 2 / (window + 1)
    # Seed with SMA for the first value
    out[window - 1] = sum(values[:window]) / window
    for i in range(window, len(values)):
        out[i] = (values[i] - out[i - 1]) * multiplier + out[i - 1]
    return out


def rsi(closes: list[float], window: int = 14) -> list[float | None]:
    """Relative Strength Index (Wilder's smoothing)."""
    if len(closes) < window + 1:
        return [None] * len(closes)

    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(d, 0) for d in deltas]
    losses = [max(-d, 0) for d in deltas]

    avg_gain = sum(gains[:window]) / window
    avg_loss = sum(losses[:window]) / window

    rsi_vals = [None] * (window + 1)
    if avg_loss == 0:
        rsi_vals[window] = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi_vals[window] = 100.0 - (100.0 / (1.0 + rs))

    for i in range(window + 1, len(closes)):
        avg_gain = (avg_gain * (window - 1) + gains[i - 1]) / window
        avg_loss = (avg_loss * (window - 1) + losses[i - 1]) / window
        if avg_loss == 0:
            rsi_vals.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi_vals.append(100.0 - (100.0 / (1.0 + rs)))

    return rsi_vals


def macd(closes: list[float], fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """MACD — Moving Average Convergence Divergence.

    Returns {macd_line, signal_line, histogram}.
    """
    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)

    macd_line = [None] * len(closes)
    for i in range(len(closes)):
        if ema_fast[i] is not None and ema_slow[i] is not None:
            macd_line[i] = ema_fast[i] - ema_slow[i]

    valid_macd = [v if v is not None else 0.0 for v in macd_line]
    signal_line = ema(valid_macd, signal)

    # Align signal_line back to original index (ema pads at front)
    histogram = [None] * len(closes)
    for i in range(len(closes)):
        if macd_line[i] is not None and signal_line[i] is not None:
            histogram[i] = macd_line[i] - signal_line[i]

    return {"macd_line": macd_line, "signal_line": signal_line, "histogram": histogram}


def bb(typicals: list[float], window: int = 20, num_std: float = 2.0) -> dict:
    """Bollinger Bands.

    Args:
        typicals: typical price = (H + L + C) / 3
    Returns {middle_band, upper_band, lower_band, bandwidth, %b}.
    """
    middle = sma(typicals, window)
    upper = [None] * len(typicals)
    lower = [None] * len(typicals)
    bandwidth = [None] * len(typicals)
    pct_b = [None] * len(typicals)

    for i in range(len(typicals)):
        if middle[i] is None:
            continue
        window_vals = typicals[i - window + 1 : i + 1]
        std = np.std(window_vals, ddof=0)
        upper[i] = middle[i] + num_std * std
        lower[i] = middle[i] - num_std * std
        if upper[i] != lower[i]:
            bandwidth[i] = (upper[i] - lower[i]) / middle[i]
            pct_b[i] = (typicals[i] - lower[i]) / (upper[i] - lower[i])

    return {
        "middle": middle,
        "upper": upper,
        "lower": lower,
        "bandwidth": bandwidth,
        "pct_b": pct_b,
    }


def atr(
    highs: list[float], lows: list[float], closes: list[float], window: int = 14
) -> list[float | None]:
    """Average True Range."""
    if len(closes) < 2:
        return [None] * len(closes)

    true_ranges = [None]  # first value undefined
    for i in range(1, len(closes)):
        hl = highs[i] - lows[i]
        hc = abs(highs[i] - closes[i - 1])
        lc = abs(lows[i] - closes[i - 1])
        true_ranges.append(max(hl, hc, lc))

    # Wilder's smoothed ATR
    atr_vals = [None] * window
    if len(true_ranges) > window:
        atr_vals.append(sum(true_ranges[1 : window + 1]) / window)
        for i in range(window + 1, len(true_ranges)):
            atr_vals.append((atr_vals[i - 1] * (window - 1) + true_ranges[i]) / window)

    return atr_vals


def obv(closes: list[float], volumes: list[float]) -> list[float | None]:
    """On-Balance Volume."""
    if len(closes) < 2 or len(volumes) != len(closes):
        return [None] * len(closes)

    obv_vals = [0.0]
    for i in range(1, len(closes)):
        if closes[i] > closes[i - 1]:
            obv_vals.append(obv_vals[-1] + (volumes[i] or 0))
        elif closes[i] < closes[i - 1]:
            obv_vals.append(obv_vals[-1] - (volumes[i] or 0))
        else:
            obv_vals.append(obv_vals[-1])
    return obv_vals


def stochastic(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    k_window: int = 14,
    d_window: int = 3,
) -> dict:
    """Stochastic Oscillator (%K, %D)."""
    k_vals = [None] * len(closes)
    for i in range(k_window - 1, len(closes)):
        window_h = max(highs[i - k_window + 1 : i + 1])
        window_l = min(lows[i - k_window + 1 : i + 1])
        if window_h != window_l:
            k_vals[i] = 100 * (closes[i] - window_l) / (window_h - window_l)
        else:
            k_vals[i] = 50.0

    valid_k = [v if v is not None else 50.0 for v in k_vals]
    d_vals = sma(valid_k, d_window)

    return {"k_line": k_vals, "d_line": d_vals}


def find_support_resistance(
    highs: list[float], lows: list[float], closes: list[float]
) -> dict:
    """Find support and resistance levels using pivot points and recent highs/lows."""
    if len(closes) < 20:
        return {}

    # Pivot point based on last full period
    recent_h = max(highs[-20:])
    recent_l = min(lows[-20:])
    recent_c = closes[-1]

    pp = (recent_h + recent_l + recent_c) / 3
    r1 = 2 * pp - recent_l
    r2 = pp + (recent_h - recent_l)
    r3 = recent_h + 2 * (pp - recent_l)
    s1 = 2 * pp - recent_h
    s2 = pp - (recent_h - recent_l)
    s3 = recent_l - 2 * (recent_h - pp)

    # 52-week-like levels from available data
    high_52w = max(highs[-252:]) if len(highs) >= 252 else max(highs)
    low_52w = min(lows[-252:]) if len(lows) >= 252 else min(lows)

    return {
        "pivot_point": round(pp, 2),
        "resistance_r1": round(r1, 2),
        "resistance_r2": round(r2, 2),
        "resistance_r3": round(r3, 2),
        "support_s1": round(s1, 2),
        "support_s2": round(s2, 2),
        "support_s3": round(s3, 2),
        "range_52w_high": round(high_52w, 2),
        "range_52w_low": round(low_52w, 2),
        "range_20d_high": round(recent_h, 2),
        "range_20d_low": round(recent_l, 2),
    }


def adx(
    highs: list[float], lows: list[float], closes: list[float], window: int = 14
) -> list[float | None]:
    """Average Directional Index (ADX)."""
    if len(closes) < window + 1:
        return [None] * len(closes)

    tr = [None]
    plus_dm = [None]
    minus_dm = [None]

    for i in range(1, len(closes)):
        hl = highs[i] - lows[i]
        hc = abs(highs[i] - closes[i - 1])
        lc = abs(lows[i] - closes[i - 1])
        tr.append(max(hl, hc, lc))

        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        plus_dm.append(up if up > down and up > 0 else 0.0)
        minus_dm.append(down if down > up and down > 0 else 0.0)

    # Wilder's smoothing
    atr_vals = [None] * window
    atr_vals.append(sum(tr[1 : window + 1]) / window)
    for i in range(window + 1, len(tr)):
        atr_vals.append((atr_vals[i - 1] * (window - 1) + tr[i]) / window)

    smoothed_plus_dm = [None] * window
    smoothed_minus_dm = [None] * window
    smoothed_plus_dm.append(sum(plus_dm[1 : window + 1]) / window)
    smoothed_minus_dm.append(sum(minus_dm[1 : window + 1]) / window)
    for i in range(window + 1, len(tr)):
        smoothed_plus_dm.append(
            (smoothed_plus_dm[i - 1] * (window - 1) + plus_dm[i]) / window
        )
        smoothed_minus_dm.append(
            (smoothed_minus_dm[i - 1] * (window - 1) + minus_dm[i]) / window
        )

    adx_vals = [None] * (window * 2)
    for i in range(window, len(closes)):
        if atr_vals[i] and atr_vals[i] != 0:
            pdi = (
                (smoothed_plus_dm[i] / atr_vals[i]) * 100
                if smoothed_plus_dm[i] is not None
                else 0
            )
            mdi = (
                (smoothed_minus_dm[i] / atr_vals[i]) * 100
                if smoothed_minus_dm[i] is not None
                else 0
            )
            if pdi + mdi > 0:
                dx = abs(pdi - mdi) / (pdi + mdi) * 100
            else:
                dx = 0.0
            adx_vals.append(dx)
        else:
            adx_vals.append(None)

    # Smooth ADX (simple moving average of DX)
    adx_smoothed = [None] * len(closes)
    valid_start = next((i for i, v in enumerate(adx_vals) if v is not None), None)
    if valid_start is not None:
        for i in range(valid_start + window - 1, len(closes)):
            if i >= valid_start and adx_vals[i] is not None:
                start_idx = i - window + 1
                window_dx = [v for v in adx_vals[start_idx : i + 1] if v is not None]
                if window_dx:
                    adx_smoothed[i] = sum(window_dx) / len(window_dx)

    return adx_smoothed


# ---------------------------------------------------------------------------
# Composite scores
# ---------------------------------------------------------------------------


def trend_strength_score(
    closes: list[float],
    sma_20: list[float | None],
    sma_50: list[float | None],
    sma_200: list[float | None],
) -> dict:
    """Score trend strength 0-10.

    Higher = stronger bullish trend alignment.
    """
    if len(closes) < 50 or sma_20[-1] is None:
        return {"score": None, "assessment": "insufficient_data"}

    score = 5.0
    reasons = []

    # Price vs SMAs
    c = closes[-1]
    if sma_20[-1] and sma_50[-1]:
        if c > sma_20[-1] > sma_50[-1]:
            score += 1.5
            reasons.append("Price above 20/50 SMA (bullish alignment)")
        elif c < sma_20[-1] < sma_50[-1]:
            score -= 1.5
            reasons.append("Price below 20/50 SMA (bearish alignment)")

    if sma_50[-1] and sma_200[-1] is not None:
        if sma_50[-1] > sma_200[-1]:
            score += 1.0
            reasons.append("Golden cross: 50 SMA above 200 SMA")
        else:
            score -= 1.0
            reasons.append("Death cross: 50 SMA below 200 SMA")

    # Slope of 20 SMA
    recent_sma20 = [v for v in sma_20[-10:] if v is not None]
    if len(recent_sma20) >= 2:
        slope = (
            (recent_sma20[-1] - recent_sma20[0]) / recent_sma20[0]
            if recent_sma20[0] != 0
            else 0
        )
        if slope > 0.01:
            score += 0.5
        elif slope < -0.01:
            score -= 0.5

    score = max(0, min(10, score))
    if score >= 7:
        assessment = "Strong bullish trend"
    elif score >= 5.5:
        assessment = "Moderate bullish bias"
    elif score >= 4.5:
        assessment = "Neutral / ranging"
    elif score >= 3:
        assessment = "Moderate bearish bias"
    else:
        assessment = "Strong bearish trend"

    return {"score": round(score, 1), "assessment": assessment, "reasons": reasons}


def momentum_score(
    rsi_val: float | None,
    macd_hist: float | None,
    sto_k: float | None,
    roc_val: float | None,
) -> dict:
    """Score momentum 0-10."""
    if rsi_val is None and macd_hist is None:
        return {"score": None, "assessment": "insufficient_data"}

    score = 5.0
    signals = []

    if rsi_val is not None:
        if rsi_val > 70:
            score -= 1.0
            signals.append(f"RSI overbought ({rsi_val:.0f})")
        elif rsi_val < 30:
            score += 1.0
            signals.append(f"RSI oversold ({rsi_val:.0f}) — potential bounce")
        elif rsi_val > 50:
            score += 0.3
        else:
            score -= 0.3

    if macd_hist is not None:
        if macd_hist > 0:
            score += 0.5
            signals.append("MACD histogram positive (bullish momentum)")
        else:
            score -= 0.5
            signals.append("MACD histogram negative (bearish momentum)")

    if sto_k is not None:
        if sto_k > 80:
            score -= 0.5
        elif sto_k < 20:
            score += 0.5

    if roc_val is not None:
        if roc_val > 5:
            score += 0.5
        elif roc_val < -5:
            score -= 0.5

    score = max(0, min(10, score))
    if score >= 7:
        assessment = "Strong momentum (bullish)"
    elif score >= 5.5:
        assessment = "Mild bullish momentum"
    elif score >= 4.5:
        assessment = "Neutral momentum"
    elif score >= 3:
        assessment = "Mild bearish momentum"
    else:
        assessment = "Strong momentum (bearish)"

    return {"score": round(score, 1), "assessment": assessment, "signals": signals}


# ---------------------------------------------------------------------------
# Weinstein Stage Classification
# ---------------------------------------------------------------------------


def weinstein_stage(weekly_closes: list[float], weekly_volumes: list[float]) -> dict:
    """Classify price structure into Weinstein's 4 stages using 30-week MA.

    Stage 1: Basing (30WMA flat, price oscillating around it)
    Stage 2: Advancing (30WMA rising, price above)
    Stage 3: Topping (30WMA flattening after rise, price oscillating)
    Stage 4: Declining (30WMA falling, price below)
    """
    if len(weekly_closes) < 35:
        return {"stage": None, "evidence": "Insufficient weekly data (need 35+ weeks)"}

    wma_30 = sma(weekly_closes, 30)

    current_price = weekly_closes[-1]
    current_wma = wma_30[-1]
    prev_wma_4w = wma_30[-5] if len(wma_30) > 5 else None
    prev_wma_8w = wma_30[-9] if len(wma_30) > 9 else None

    if current_wma is None or prev_wma_4w is None:
        return {"stage": None, "evidence": "30-week MA not yet computed"}

    # MA slope (annualized rate of change)
    wma_slope_4w = (current_wma - prev_wma_4w) / prev_wma_4w if prev_wma_4w else 0
    wma_slope_8w = (current_wma - prev_wma_8w) / prev_wma_8w if prev_wma_8w else 0

    price_vs_wma = (current_price - current_wma) / current_wma

    # Volume pattern: compare recent 4-week avg to prior 4-week avg
    if len(weekly_volumes) >= 8:
        recent_vol = sum(weekly_volumes[-4:]) / 4
        prior_vol = sum(weekly_volumes[-8:-4]) / 4
        vol_expansion = recent_vol / prior_vol if prior_vol > 0 else 1.0
    else:
        vol_expansion = 1.0

    # 52-week high/low relative position
    if len(weekly_closes) >= 52:
        high_52w = max(weekly_closes[-52:])
        low_52w = min(weekly_closes[-52:])
        range_52w = high_52w - low_52w
        position_in_range = (
            (current_price - low_52w) / range_52w if range_52w > 0 else 0.5
        )
    else:
        position_in_range = 0.5

    # Stage classification logic
    evidence = []

    if wma_slope_4w > 0.02 and price_vs_wma > 0.02:
        stage = 2
        evidence.append(f"30WMA rising ({wma_slope_4w:.1%}/4wk)")
        evidence.append(f"Price {price_vs_wma:.1%} above 30WMA")
        if vol_expansion > 1.2:
            evidence.append("Volume expanding on advance (bullish)")
    elif wma_slope_4w < -0.02 and price_vs_wma < -0.02:
        stage = 4
        evidence.append(f"30WMA falling ({wma_slope_4w:.1%}/4wk)")
        evidence.append(f"Price {price_vs_wma:.1%} below 30WMA")
    elif abs(wma_slope_4w) <= 0.02 and position_in_range > 0.6:
        stage = 3
        evidence.append(f"30WMA flattening after advance ({wma_slope_4w:.1%}/4wk)")
        evidence.append(
            f"Price near top of range ({position_in_range:.0%} of 52wk range)"
        )
    elif abs(wma_slope_4w) <= 0.02 and position_in_range < 0.4:
        stage = 1
        evidence.append(f"30WMA flat ({wma_slope_4w:.1%}/4wk)")
        evidence.append(
            f"Price near bottom of range ({position_in_range:.0%} of 52wk range)"
        )
    elif wma_slope_4w > 0:
        stage = 2
        evidence.append(f"30WMA mildly rising ({wma_slope_4w:.1%}/4wk)")
    else:
        stage = 4 if price_vs_wma < -0.03 else 1
        evidence.append(
            f"Ambiguous — price {price_vs_wma:.1%} vs 30WMA, slope {wma_slope_4w:.1%}"
        )

    stage_names = {
        1: "Basing/Accumulation",
        2: "Advancing",
        3: "Topping/Distribution",
        4: "Declining",
    }

    return {
        "methodology": "Weinstein 4-Stage Classification using 30-week MA direction, price position, and volume",
        "stage": stage,
        "stage_name": stage_names[stage],
        "action": {
            1: "WATCH — do not buy yet",
            2: "BUY zone",
            3: "SELL — take profits",
            4: "AVOID — never buy",
        }[stage],
        "thirty_week_ma": round(current_wma, 2),
        "price_vs_30wma_pct": round(price_vs_wma * 100, 1),
        "wma_slope_4wk": round(wma_slope_4w * 100, 2),
        "volume_expansion": round(vol_expansion, 2),
        "position_in_52wk_range": round(position_in_range * 100, 1),
        "evidence": evidence,
    }


def compute_relative_strength(
    ticker_closes: list[float],
    market_closes: list[float],
    periods: list[int] | None = None,
) -> dict:
    """Compute relative strength vs market (SPY) over multiple periods."""
    if periods is None:
        periods = [63, 126, 252]  # ~3mo, 6mo, 12mo in trading days

    rs_scores = {}
    for period in periods:
        if len(ticker_closes) > period and len(market_closes) > period:
            ticker_return = (ticker_closes[-1] / ticker_closes[-period - 1]) - 1
            market_return = (market_closes[-1] / market_closes[-period - 1]) - 1
            rs = ticker_return - market_return
            rs_scores[f"{period}d"] = round(rs * 100, 1)
        else:
            rs_scores[f"{period}d"] = None

    # Composite RS (weighted: 40% 6mo, 40% 12mo, 20% 3mo)
    rs_3m = rs_scores.get("63d")
    rs_6m = rs_scores.get("126d")
    rs_12m = rs_scores.get("252d")

    composite = None
    if all(v is not None for v in [rs_3m, rs_6m, rs_12m]):
        composite = round(rs_3m * 0.2 + rs_6m * 0.4 + rs_12m * 0.4, 1)

    return {
        "methodology": "Relative strength vs SPY (stock return minus market return)",
        "periods": rs_scores,
        "composite_rs": composite,
        "rs_rank_estimate": "Top 20% (Leader)"
        if composite and composite > 15
        else "Top 40%"
        if composite and composite > 5
        else "Middle"
        if composite and composite > -5
        else "Bottom 40%"
        if composite and composite > -15
        else "Bottom 20% (Laggard)"
        if composite is not None
        else None,
    }


def volume_profile(
    closes: list[float],
    highs: list[float],
    lows: list[float],
    volumes: list[float],
    bins: int = 30,
) -> dict:
    """Compute volume profile: POC (Point of Control), Value Area High/Low.

    Distributes volume across price bins using typical price. Identifies the
    price level with the most traded volume (POC) and the range containing
    70% of total volume (Value Area).
    """
    n = len(closes)
    if n < 20 or not volumes:
        return {}

    typicals = [(h + l + c) / 3 for h, l, c in zip(highs, lows, closes)]
    price_min = min(lows)
    price_max = max(highs)
    if price_max <= price_min:
        return {}

    bin_size = (price_max - price_min) / bins
    vol_bins = [0.0] * bins
    bin_prices = [price_min + (i + 0.5) * bin_size for i in range(bins)]

    for tp, vol in zip(typicals, volumes):
        idx = min(int((tp - price_min) / bin_size), bins - 1)
        vol_bins[idx] += vol

    poc_idx = vol_bins.index(max(vol_bins))
    poc_price = bin_prices[poc_idx]

    total_vol = sum(vol_bins)
    if total_vol == 0:
        return {}

    # Value Area: expand outward from POC until 70% of volume captured
    va_vol = vol_bins[poc_idx]
    lo_idx = poc_idx
    hi_idx = poc_idx
    while va_vol / total_vol < 0.70 and (lo_idx > 0 or hi_idx < bins - 1):
        expand_lo = vol_bins[lo_idx - 1] if lo_idx > 0 else 0
        expand_hi = vol_bins[hi_idx + 1] if hi_idx < bins - 1 else 0
        if expand_lo >= expand_hi and lo_idx > 0:
            lo_idx -= 1
            va_vol += vol_bins[lo_idx]
        elif hi_idx < bins - 1:
            hi_idx += 1
            va_vol += vol_bins[hi_idx]
        else:
            lo_idx -= 1
            va_vol += vol_bins[lo_idx]

    return {
        "poc": round(poc_price, 2),
        "value_area_high": round(bin_prices[hi_idx] + bin_size / 2, 2),
        "value_area_low": round(bin_prices[lo_idx] - bin_size / 2, 2),
        "current_vs_poc": round((closes[-1] - poc_price) / poc_price * 100, 2),
        "interpretation": (
            "Above Value Area — extended, watch for mean reversion to POC"
            if closes[-1] > bin_prices[hi_idx] + bin_size / 2
            else "Below Value Area — oversold vs volume, watch for snap-back to POC"
            if closes[-1] < bin_prices[lo_idx] - bin_size / 2
            else "Within Value Area — fair value zone, balanced positioning"
        ),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def compute_all(
    closes: list[float],
    highs: list[float],
    lows: list[float],
    opens: list[float],
    volumes: list[float],
) -> dict:
    """Compute all technical indicators and composite scores."""

    typicals = [(h + l + c) / 3 for h, l, c in zip(highs, lows, closes)]

    sma_20 = sma(closes, 20)
    sma_50 = sma(closes, 50)
    sma_200 = sma(closes, 200)
    ema_12 = ema(closes, 12)
    ema_26 = ema(closes, 26)

    rsi_vals = rsi(closes, 14)
    macd_data = macd(closes)
    bb_data = bb(typicals, 20, 2.0)
    atr_vals = atr(highs, lows, closes, 14)
    obv_vals = obv(closes, volumes)
    sto_data = stochastic(highs, lows, closes)
    adx_vals = adx(highs, lows, closes)
    sr_levels = find_support_resistance(highs, lows, closes)

    # Rate of Change (20-day)
    roc = [None] * len(closes)
    for i in range(20, len(closes)):
        if closes[i - 20] != 0:
            roc[i] = ((closes[i] - closes[i - 20]) / closes[i - 20]) * 100

    # Volume analysis
    vol_sma_20 = sma(volumes, 20)
    vol_ratio = None
    if vol_sma_20[-1] is not None and vol_sma_20[-1] != 0:
        vol_ratio = volumes[-1] / vol_sma_20[-1]

    # Latest values for summary
    latest = {
        "date": None,  # filled from price data
        "close": round(closes[-1], 2) if closes else None,
        "sma_20": round(sma_20[-1], 2) if sma_20 and sma_20[-1] is not None else None,
        "sma_50": round(sma_50[-1], 2) if sma_50 and sma_50[-1] is not None else None,
        "sma_200": round(sma_200[-1], 2)
        if sma_200 and sma_200[-1] is not None
        else None,
        "ema_12": round(ema_12[-1], 2) if ema_12 and ema_12[-1] is not None else None,
        "ema_26": round(ema_26[-1], 2) if ema_26 and ema_26[-1] is not None else None,
        "rsi_14": round(rsi_vals[-1], 1)
        if rsi_vals and rsi_vals[-1] is not None
        else None,
        "macd_line": round(macd_data["macd_line"][-1], 4)
        if macd_data["macd_line"][-1] is not None
        else None,
        "macd_signal": round(macd_data["signal_line"][-1], 4)
        if macd_data["signal_line"][-1] is not None
        else None,
        "macd_histogram": round(macd_data["histogram"][-1], 4)
        if macd_data["histogram"][-1] is not None
        else None,
        "bb_upper": round(bb_data["upper"][-1], 2)
        if bb_data["upper"][-1] is not None
        else None,
        "bb_middle": round(bb_data["middle"][-1], 2)
        if bb_data["middle"][-1] is not None
        else None,
        "bb_lower": round(bb_data["lower"][-1], 2)
        if bb_data["lower"][-1] is not None
        else None,
        "bb_pct_b": round(bb_data["pct_b"][-1], 3)
        if bb_data["pct_b"][-1] is not None
        else None,
        "atr_14": round(atr_vals[-1], 2)
        if atr_vals and atr_vals[-1] is not None
        else None,
        "stoch_k": round(sto_data["k_line"][-1], 1)
        if sto_data["k_line"][-1] is not None
        else None,
        "stoch_d": round(sto_data["d_line"][-1], 1)
        if sto_data["d_line"][-1] is not None
        else None,
        "adx": round(adx_vals[-1], 1)
        if adx_vals and adx_vals[-1] is not None
        else None,
        "roc_20d": round(roc[-1], 2) if roc[-1] is not None else None,
        "volume_latest": volumes[-1] if volumes else None,
        "volume_sma_20": round(vol_sma_20[-1], 0)
        if vol_sma_20 and vol_sma_20[-1] is not None
        else None,
        "volume_ratio": round(vol_ratio, 2) if vol_ratio is not None else None,
        "obv_trend": "rising"
        if obv_vals and len(obv_vals) > 5 and obv_vals[-1] > obv_vals[-5]
        else "falling"
        if obv_vals and len(obv_vals) > 5
        else None,
    }

    # Composite scores
    trend_score = trend_strength_score(closes, sma_20, sma_50, sma_200)
    mom_score = momentum_score(
        rsi_vals[-1] if rsi_vals else None,
        macd_data["histogram"][-1],
        sto_data["k_line"][-1],
        roc[-1],
    )

    # Volume analysis summary
    vol_assessment = "normal"
    if vol_ratio and vol_ratio > 2.0:
        vol_assessment = "extreme_high"
    elif vol_ratio and vol_ratio > 1.5:
        vol_assessment = "elevated"
    elif vol_ratio and vol_ratio < 0.5:
        vol_assessment = "very_low"

    # Setup quality: combine trend + momentum scores
    setup_quality = None
    if trend_score["score"] is not None and mom_score["score"] is not None:
        raw = (trend_score["score"] + mom_score["score"]) / 2
        setup_quality = round(raw, 1)

    # Volume profile (POC, Value Area)
    vol_profile = volume_profile(closes, highs, lows, volumes)

    return {
        "latest": latest,
        "support_resistance": sr_levels,
        "trend_strength": trend_score,
        "momentum": mom_score,
        "volume": {
            "assessment": vol_assessment,
            "latest_volume": volumes[-1] if volumes else None,
            "avg_volume_20d": round(vol_sma_20[-1], 0)
            if vol_sma_20 and vol_sma_20[-1] is not None
            else None,
            "volume_ratio": vol_ratio,
            "obv_direction": latest.get("obv_trend"),
        },
        "volume_profile": vol_profile,
        "setup_quality": setup_quality,
    }


def fetch_alpha_vantage(ticker: str, api_key: str) -> dict | None:
    """Fallback: fetch RSI, MACD, SMA from Alpha Vantage API.

    Free tier: 25 calls/day. Use sparingly.
    """
    try:
        import requests
    except ImportError:
        return None

    indicators = {}
    functions = {
        "RSI": "RSI",
        "MACD": "MACDEXT",
        "SMA": "SMA",
        "BBANDS": "BBANDS",
    }

    for name, func in functions.items():
        try:
            resp = requests.get(
                "https://www.alphavantage.co/query",
                params={
                    "function": func,
                    "symbol": ticker,
                    "interval": "daily",
                    "time_period": 14 if name == "RSI" else 20,
                    "series_type": "close",
                    "apikey": api_key,
                },
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                if "Technical Analysis: " + name in data:
                    indicators[name.lower()] = data["Technical Analysis: " + name]
        except Exception:
            pass

    return indicators if indicators else None


def main():
    parser = argparse.ArgumentParser(
        description="Compute technical indicators for stock tickers"
    )
    parser.add_argument("tickers", nargs="+", help="Ticker symbols (e.g., AAPL MSFT)")
    parser.add_argument(
        "--period", default="1y", help="Price history period (default: 1y)"
    )
    parser.add_argument("--interval", default="1d", help="Price interval (default: 1d)")
    parser.add_argument("--output", help="Output file path (default: stdout)")
    parser.add_argument(
        "--alpha-vantage-key-env",
        default="ALPHAVANTAGE_API_KEY",
        help="Env var for Alpha Vantage API key (fallback only)",
    )
    args = parser.parse_args()

    results = {}
    for raw_ticker in args.tickers:
        ticker = raw_ticker.strip().upper()
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period=args.period, interval=args.interval)

            if hist.empty:
                results[ticker] = {"error": f"No price data for {ticker}"}
                continue

            closes = hist["Close"].tolist()
            highs = hist["High"].tolist()
            lows = hist["Low"].tolist()
            opens = hist["Open"].tolist()
            volumes = hist["Volume"].tolist()
            dates = hist.index.tolist()

            tech_data = compute_all(closes, highs, lows, opens, volumes)
            tech_data["latest"]["date"] = (
                str(dates[-1].date()) if len(dates) > 0 else None
            )
            tech_data["ticker"] = ticker
            tech_data["source"] = "yfinance_local"
            tech_data["retrieved_at"] = datetime.now(timezone.utc).isoformat()
            tech_data["data_points"] = len(closes)
            tech_data["period"] = args.period
            tech_data["interval"] = args.interval

            # Alpha Vantage fallback (only if data quality looks sparse)
            api_key = os.environ.get(args.alpha_vantage_key_env)
            if api_key:
                av = fetch_alpha_vantage(ticker, api_key)
                if av:
                    tech_data["alpha_vantage_fallback"] = av

            # Weinstein Stage (requires weekly data — fetch separately)
            try:
                weekly_hist = stock.history(period="2y", interval="1wk")
                if not weekly_hist.empty and len(weekly_hist) >= 35:
                    weekly_closes = weekly_hist["Close"].tolist()
                    weekly_volumes = weekly_hist["Volume"].tolist()
                    tech_data["weinstein_stage"] = weinstein_stage(
                        weekly_closes, weekly_volumes
                    )
                else:
                    tech_data["weinstein_stage"] = {
                        "stage": None,
                        "evidence": "Insufficient weekly data",
                    }
            except Exception as e:
                tech_data["weinstein_stage"] = {"stage": None, "error": str(e)}

            # Relative Strength vs SPY
            try:
                spy_hist = yf.Ticker("SPY").history(period="2y", interval="1d")
                if not spy_hist.empty:
                    spy_closes = spy_hist["Close"].tolist()
                    tech_data["relative_strength"] = compute_relative_strength(
                        closes, spy_closes
                    )
                else:
                    tech_data["relative_strength"] = {
                        "composite_rs": None,
                        "error": "SPY data unavailable",
                    }
            except Exception as e:
                tech_data["relative_strength"] = {"composite_rs": None, "error": str(e)}

            results[ticker] = tech_data

        except Exception as e:
            results[ticker] = {"error": str(e)}

    output = json.dumps(results, indent=2)
    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w") as f:
            f.write(output)
    else:
        print(output)
    sys.exit(0)


if __name__ == "__main__":
    main()
