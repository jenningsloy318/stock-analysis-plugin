#!/usr/bin/env python3
"""Compute sector relative strength rankings against S&P 500.

Usage:
    compute_sector_rs.py                          # all 11 sectors vs SPY
    compute_sector_rs.py --sectors XLK,XLF,XLE    # specific sector ETFs
    compute_sector_rs.py --benchmark SPY --period 1y
    compute_sector_rs.py --output ./reports/screening/sector-rs.json

Uses sector ETF price data (yfinance) to compute:
  - Relative strength (RS) ratio: sector ETF / benchmark
  - RS momentum across 1M, 3M, 6M, 12M timeframes
  - RS ranking (percentile vs all sectors)
  - RS direction (improving/deteriorating)
  - Composite RS score for sector rotation

This feeds the 20% RS weight in short-term industry screening and the
10% RS weight in mid-term screening.
"""

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Any

try:
    import yfinance as yf
    import numpy as np
except ImportError:
    sys.stderr.write("Error: yfinance and numpy required. Run: pip install yfinance numpy\n")
    sys.exit(1)


# GICS sector → ETF mapping
SECTOR_ETFS = {
    "Technology": "XLK",
    "Financials": "XLF",
    "Healthcare": "XLV",
    "Consumer Discretionary": "XLY",
    "Communication Services": "XLC",
    "Industrials": "XLI",
    "Energy": "XLE",
    "Consumer Staples": "XLP",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Materials": "XLB",
}


def compute_rs(ticker: str, benchmark: str = "SPY", period: str = "2y") -> dict:
    """Compute relative strength for a sector ETF vs benchmark."""
    try:
        sector = yf.Ticker(ticker)
        bench = yf.Ticker(benchmark)

        sector_hist = sector.history(period=period)
        bench_hist = bench.history(period=period)

        if sector_hist.empty or bench_hist.empty:
            return {"error": f"No data for {ticker} or {benchmark}"}

        # Align dates
        common_dates = sector_hist.index.intersection(bench_hist.index)
        if len(common_dates) < 20:
            return {"error": f"Insufficient common trading days ({len(common_dates)})"}

        sector_close = sector_hist.loc[common_dates, "Close"].values
        bench_close = bench_hist.loc[common_dates, "Close"].values

        # RS ratio
        rs_ratio = sector_close / bench_close
        rs_ratio_normalized = rs_ratio / rs_ratio[0] * 100  # Base 100

        today = datetime.now().date()

        def price_at_days_ago(days: int) -> tuple:
            """Get price at approximate date N trading days ago."""
            if days >= len(sector_close):
                return None, None
            idx = len(sector_close) - 1 - days
            return float(sector_close[idx]), float(bench_close[idx])

        def compute_rs_change(trading_days: int) -> dict | None:
            """Compute RS change over a period."""
            s_now, b_now = sector_close[-1], bench_close[-1]
            if trading_days >= len(sector_close):
                return None
            s_past, b_past = sector_close[-1 - trading_days], bench_close[-1 - trading_days]
            if b_past == 0 or b_now == 0:
                return None

            rs_now = s_now / b_now
            rs_past = s_past / b_past
            rs_change = (rs_now / rs_past - 1) * 100

            sector_return = (s_now / s_past - 1) * 100
            bench_return = (b_now / b_past - 1) * 100
            excess_return = sector_return - bench_return

            return {
                "rs_change_pct": round(rs_change, 2),
                "sector_return_pct": round(sector_return, 2),
                "benchmark_return_pct": round(bench_return, 2),
                "excess_return_pct": round(excess_return, 2),
            }

        # Approximate trading day conversions
        periods = {
            "1M": 21,
            "3M": 63,
            "6M": 126,
            "12M": 252,
        }

        rs_data = {}
        for label, days in periods.items():
            change = compute_rs_change(days)
            if change:
                rs_data[label] = change

        # RS momentum: is RS accelerating or decelerating?
        rs_momentum = None
        if "1M" in rs_data and "3M" in rs_data:
            # Compare short-term RS change vs longer-term
            short = rs_data["1M"]["rs_change_pct"]
            long = rs_data["3M"]["rs_change_pct"]
            if short > 0 and long > 0:
                rs_momentum = "strong_positive" if short > long else "positive_stable"
            elif short > 0 > long:
                rs_momentum = "improving"
            elif short < 0 < long:
                rs_momentum = "deteriorating"
            elif short < 0 and long < 0:
                rs_momentum = "strong_negative" if short < long else "negative_stable"
            else:
                rs_momentum = "neutral"

        # Current RS ratio vs 1-year average
        if len(rs_ratio) >= 252:
            rs_1y_avg = np.mean(rs_ratio[-252:])
            rs_current = rs_ratio[-1]
            rs_vs_avg = (rs_current / rs_1y_avg - 1) * 100
        else:
            rs_vs_avg = None

        return {
            "ticker": ticker,
            "benchmark": benchmark,
            "period": period,
            "data_points": len(common_dates),
            "rs_data": rs_data,
            "rs_momentum": rs_momentum,
            "rs_vs_1y_avg_pct": round(rs_vs_avg, 2) if rs_vs_avg is not None else None,
            "latest_rs_ratio": round(float(rs_ratio[-1]), 6),
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        return {"error": str(e)}


def rank_sectors(rs_results: dict[str, dict]) -> dict:
    """Rank sectors by RS composite score."""
    scores = {}
    for sector, data in rs_results.items():
        if "error" in data:
            continue

        rs = data.get("rs_data", {})
        score = 0.0

        # Score: positive RS change = positive score
        weights = {"1M": 0.15, "3M": 0.30, "6M": 0.30, "12M": 0.25}

        for period, weight in weights.items():
            if period in rs:
                rs_change = rs[period]["rs_change_pct"]
                # Normalize: each 1% excess return = +0.5 points, capped at ±4
                period_score = min(4.0, max(-4.0, rs_change * 0.5))
                score += period_score * weight

        # Momentum bonus
        momentum = data.get("rs_momentum", "neutral")
        momentum_bonus = {
            "strong_positive": 1.5,
            "positive_stable": 0.8,
            "improving": 1.0,
            "neutral": 0.0,
            "deteriorating": -1.0,
            "negative_stable": -0.8,
            "strong_negative": -1.5,
        }
        score += momentum_bonus.get(momentum, 0)

        scores[sector] = {
            "ticker": data.get("ticker"),
            "composite_rs": round(score, 2),
            "rs_momentum": momentum,
            "rs_1m": rs.get("1M", {}).get("rs_change_pct"),
            "rs_3m": rs.get("3M", {}).get("rs_change_pct"),
            "rs_6m": rs.get("6M", {}).get("rs_change_pct"),
            "rs_12m": rs.get("12M", {}).get("rs_change_pct"),
        }

    # Rank by composite RS
    ranked = sorted(scores.items(), key=lambda x: x[1]["composite_rs"], reverse=True)

    # Percentile rank
    n = len(ranked)
    ranking = []
    for i, (sector, sdata) in enumerate(ranked):
        percentile = round((1 - i / max(n - 1, 1)) * 100, 1)
        entry = dict(sdata)
        entry["rank"] = i + 1
        entry["percentile"] = percentile
        ranking.append({"sector": sector, **entry})

    # Interpretation
    top_quartile = [r for r in ranking if r["percentile"] >= 75]
    bottom_quartile = [r for r in ranking if r["percentile"] <= 25]

    return {
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "sectors_ranked": len(ranking),
        "ranking": ranking,
        "top_quartile": [r["sector"] for r in top_quartile],
        "bottom_quartile": [r["sector"] for r in bottom_quartile],
        "methodology": "Composite RS = Σ(period RS × weight) + momentum bonus. "
                       "Weights: 1M=15%, 3M=30%, 6M=30%, 12M=25%. "
                       "RS change = % change in (sector ETF / SPY) over period.",
        "usage": "Feed top_quartile sectors to sector-screener for Phase 1 ranking. "
                 "RS is the single most predictive signal for sector rotation.",
    }


def main():
    parser = argparse.ArgumentParser(
        description="Compute sector relative strength rankings"
    )
    parser.add_argument("--sectors", help="Comma-separated sector ETF tickers (default: all 11 GICS)")
    parser.add_argument("--benchmark", default="SPY", help="Benchmark ticker (default: SPY)")
    parser.add_argument("--period", default="2y", help="Lookback period for RS calculation")
    parser.add_argument("--output", help="Output file path (default: stdout)")
    args = parser.parse_args()

    if args.sectors:
        etfs = {s.strip(): s.strip() for s in args.sectors.split(",")}
    else:
        etfs = SECTOR_ETFS

    results = {}
    for sector, ticker in etfs.items():
        data = compute_rs(ticker, args.benchmark, args.period)
        results[sector] = data

    ranking = rank_sectors(results)

    output = {
        "individual_results": results,
        "ranking": ranking,
    }

    result_json = json.dumps(output, indent=2)
    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w") as f:
            f.write(result_json)
    else:
        print(result_json)
    sys.exit(0)


if __name__ == "__main__":
    main()
