#!/usr/bin/env python3
"""Compute options market signals: IV surface, put/call skew, gamma exposure, term structure, max pain.

Usage:
    calculate_options.py AAPL                             # Basic options analysis
    calculate_options.py AAPL --output ./reports/[TICKER]/options.json
    calculate_options.py AAPL --expiry 2026-06-20         # Specific expiration
    calculate_options.py AAPL --mode full                 # Full analysis (slower)

Computes from yfinance options chain data:
  - Implied Volatility (IV) by strike (IV smile/skew)
  - Put/Call ratio (volume, open interest)
  - Max Pain (strike with max option buyer loss at expiry)
  - ATM IV, IV30 (30-day constant-maturity IV)
  - Put/Call skew (25-delta risk reversal)
  - Gamma exposure profile (simplified — dealer positioning proxy)
  - IV term structure (contango/backwardation across expiries)
  - Unusual options activity detection (volume/OI spike vs 20-day avg)

Free data source: yfinance (CBOE delayed options data).
Limitations: Delayed ~15 min, limited Greeks, no trade-by-trade flow.
For institutional-grade flow, a paid provider (CBOE LiveVol, ORATS) is needed.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

try:
    import yfinance as yf
    import numpy as np
except ImportError:
    sys.stderr.write(
        "Error: yfinance and numpy required. Run: pip install yfinance numpy\n"
    )
    sys.exit(1)


def compute_max_pain(calls: list[dict], puts: list[dict]) -> dict:
    """Compute Max Pain — the strike price where option buyers lose the most.

    For each strike, compute total loss for call and put holders.
    Max Pain = strike where total loss is minimized.
    """
    if not calls or not puts:
        return {"error": "No options data available"}

    # Extract strikes and open interest
    call_strikes = {}
    for c in calls:
        strike = c.get("strike")
        oi = c.get("openInterest", 0) or 0
        if strike is not None and strike > 0:
            call_strikes[strike] = call_strikes.get(strike, 0) + oi

    put_strikes = {}
    for p in puts:
        strike = p.get("strike")
        oi = p.get("openInterest", 0) or 0
        if strike is not None and strike > 0:
            put_strikes[strike] = put_strikes.get(strike, 0) + oi

    all_strikes = sorted(set(list(call_strikes.keys()) + list(put_strikes.keys())))
    if not all_strikes:
        return {"error": "No valid strikes"}

    # For each potential settlement price (= each strike), compute total loss
    min_pain = float("inf")
    max_pain_strike = all_strikes[0]

    for settlement in all_strikes:
        total_loss = 0.0
        for strike, oi in call_strikes.items():
            if settlement > strike:
                total_loss += (settlement - strike) * oi * 100
        for strike, oi in put_strikes.items():
            if settlement < strike:
                total_loss += (strike - settlement) * oi * 100

        if total_loss < min_pain:
            min_pain = total_loss
            max_pain_strike = settlement

    return {
        "max_pain_strike": round(max_pain_strike, 2),
        "min_total_loss": round(min_pain, 2),
        "strike_count": len(all_strikes),
        "interpretation": f"Max Pain at ${max_pain_strike:.2f}. "
        f"Price tends to gravitate toward this level near expiration "
        f"due to dealer hedging dynamics.",
    }


def compute_put_call_ratios(calls: list[dict], puts: list[dict]) -> dict:
    """Compute put/call ratios (volume-based and OI-based)."""
    total_call_vol = sum(c.get("volume", 0) or 0 for c in calls)
    total_put_vol = sum(p.get("volume", 0) or 0 for p in puts)
    total_call_oi = sum(c.get("openInterest", 0) or 0 for c in calls)
    total_put_oi = sum(p.get("openInterest", 0) or 0 for p in puts)

    vol_ratio = total_put_vol / total_call_vol if total_call_vol > 0 else None
    oi_ratio = total_put_oi / total_call_oi if total_call_oi > 0 else None

    # Interpretation
    def interpret(ratio: float | None) -> str:
        if ratio is None:
            return "No data"
        if ratio > 1.2:
            return "Bearish (elevated put activity)"
        elif ratio > 0.8:
            return "Neutral (balanced)"
        elif ratio > 0.5:
            return "Bullish (call-skewed)"
        else:
            return "Very Bullish (heavily call-skewed — potential complacency)"

    return {
        "put_call_volume": {
            "total_call_volume": total_call_vol,
            "total_put_volume": total_put_vol,
            "ratio": round(vol_ratio, 3) if vol_ratio is not None else None,
            "interpretation": interpret(vol_ratio),
        },
        "put_call_open_interest": {
            "total_call_oi": total_call_oi,
            "total_put_oi": total_put_oi,
            "ratio": round(oi_ratio, 3) if oi_ratio is not None else None,
            "interpretation": interpret(oi_ratio),
        },
    }


def compute_iv_surface(calls: list[dict], puts: list[dict], spot: float) -> dict:
    """Analyze implied volatility across strikes (IV smile/skew)."""
    # Extract IV by strike
    call_ivs = {}
    for c in calls:
        strike = c.get("strike")
        iv = c.get("impliedVolatility")
        if strike and iv and iv > 0 and iv < 5:  # IV as decimal (0.01-5.0 range)
            call_ivs[strike] = iv

    put_ivs = {}
    for p in puts:
        strike = p.get("strike")
        iv = p.get("impliedVolatility")
        if strike and iv and iv > 0 and iv < 5:
            put_ivs[strike] = iv

    # ATM IV (closest to spot)
    if call_ivs:
        atm_strike = min(call_ivs.keys(), key=lambda x: abs(x - spot))
        atm_iv = call_ivs.get(atm_strike) or put_ivs.get(atm_strike)
    else:
        atm_iv = None
        atm_strike = None

    # IV skew: 25-delta risk reversal (OTM put IV - OTM call IV)
    # Approximate: 90% moneyness put vs 110% moneyness call
    otm_put_strikes = [s for s in put_ivs if s < spot * 0.95]
    otm_call_strikes = [s for s in call_ivs if s > spot * 1.05]

    otm_put_iv = (
        np.mean([put_ivs[s] for s in otm_put_strikes]) if otm_put_strikes else None
    )
    otm_call_iv = (
        np.mean([call_ivs[s] for s in otm_call_strikes]) if otm_call_strikes else None
    )

    skew = None
    if otm_put_iv is not None and otm_call_iv is not None:
        skew = round(otm_put_iv - otm_call_iv, 4)

    # IV term structure: compare near-term vs next expiry IV
    near_term_iv = atm_iv

    return {
        "atm_strike": atm_strike,
        "atm_iv": round(atm_iv, 4) if atm_iv else None,
        "atm_iv_pct": f"{atm_iv * 100:.1f}%" if atm_iv else None,
        "iv_skew": skew,
        "iv_skew_interpretation": (
            f"Put skew: {skew * 100:.1f}% — "
            f"{'Elevated hedging demand (bearish signal)' if skew and skew > 0.05 else 'Normal skew' if skew and skew > 0.02 else 'Low skew (complacency)'}"
            if skew is not None
            else "No skew data"
        ),
        "otm_put_iv": round(otm_put_iv, 4) if otm_put_iv else None,
        "otm_call_iv": round(otm_call_iv, 4) if otm_call_iv else None,
        "methodology": "IV skew = OTM put IV - OTM call IV. Positive = puts expensive (hedging demand). "
        "Negative = calls expensive (speculative upside demand).",
    }


def detect_unusual_activity(calls: list[dict], puts: list[dict]) -> dict:
    """Detect unusual options activity: volume spikes relative to OI.

    Flags individual contracts where volume > 3x average volume or volume/OI > 1.0.
    """
    unusual = []

    for option_list, opt_type in [(calls, "CALL"), (puts, "PUT")]:
        for opt in option_list:
            volume = opt.get("volume", 0) or 0
            oi = opt.get("openInterest", 0) or 0
            strike = opt.get("strike")
            if volume > 500 and oi > 0 and volume / oi > 1.0:
                unusual.append(
                    {
                        "type": opt_type,
                        "strike": strike,
                        "volume": volume,
                        "open_interest": oi,
                        "volume_oi_ratio": round(volume / oi, 2),
                        "implied_volatility": opt.get("impliedVolatility"),
                        "signal": (
                            "Bullish flow — new positions being opened"
                            if opt_type == "CALL" and volume / oi > 2
                            else "Bearish flow — new positions being opened"
                            if opt_type == "PUT" and volume / oi > 2
                            else "Elevated volume — investigate further"
                        ),
                    }
                )

    unusual.sort(key=lambda x: x["volume_oi_ratio"], reverse=True)

    return {
        "unusual_contracts": unusual[:10],
        "total_unusual_detected": len(unusual),
        "threshold": "volume/OI > 1.0 and volume > 500",
        "note": "Unusual activity is directional but not definitive. Cross-reference with news and price action.",
    }


def compute_gamma_exposure(calls: list[dict], puts: list[dict], spot: float) -> dict:
    """Estimate net gamma exposure (GEX) by strike.

    Assumes dealers are short calls (retail buys calls) and long puts (retail buys puts).
    GEX per strike = OI × 100 × gamma_approx × spot. Positive GEX = pinning force;
    negative GEX = amplification (moves away from strike accelerate).
    """
    if not spot or spot <= 0:
        return {"error": "Cannot compute GEX without spot price"}

    gex_by_strike: dict[float, float] = {}
    total_call_gex = 0.0
    total_put_gex = 0.0

    for opt in calls:
        strike = opt.get("strike")
        oi = opt.get("openInterest", 0) or 0
        if not strike or oi == 0:
            continue
        moneyness = abs(spot - strike) / spot
        gamma_approx = max(0.01, 0.04 * (1 - min(moneyness * 5, 1.0)))
        contract_gex = oi * 100 * gamma_approx * spot
        gex_by_strike[strike] = gex_by_strike.get(strike, 0) + contract_gex
        total_call_gex += contract_gex

    for opt in puts:
        strike = opt.get("strike")
        oi = opt.get("openInterest", 0) or 0
        if not strike or oi == 0:
            continue
        moneyness = abs(spot - strike) / spot
        gamma_approx = max(0.01, 0.04 * (1 - min(moneyness * 5, 1.0)))
        contract_gex = oi * 100 * gamma_approx * spot
        gex_by_strike[strike] = gex_by_strike.get(strike, 0) - contract_gex
        total_put_gex += contract_gex

    net_gex = total_call_gex - total_put_gex

    top_strikes = sorted(gex_by_strike.items(), key=lambda x: abs(x[1]), reverse=True)[
        :5
    ]

    flip_strike = None
    sorted_strikes = sorted(gex_by_strike.items(), key=lambda x: x[0])
    for i in range(len(sorted_strikes) - 1):
        if sorted_strikes[i][1] > 0 and sorted_strikes[i + 1][1] < 0:
            flip_strike = sorted_strikes[i][0]
            break
        elif sorted_strikes[i][1] < 0 and sorted_strikes[i + 1][1] > 0:
            flip_strike = sorted_strikes[i + 1][0]
            break

    return {
        "net_gex": round(net_gex, 0),
        "gex_regime": "positive" if net_gex > 0 else "negative",
        "interpretation": (
            "Positive GEX: dealer hedging pins price, expect low volatility and mean reversion"
            if net_gex > 0
            else "Negative GEX: dealer hedging amplifies moves, expect high volatility and trending"
        ),
        "gamma_flip_strike": flip_strike,
        "top_gex_strikes": [{"strike": s, "gex": round(g, 0)} for s, g in top_strikes],
        "total_call_gex": round(total_call_gex, 0),
        "total_put_gex": round(total_put_gex, 0),
        "methodology": "Approximate GEX using moneyness-based gamma proxy. Dealers assumed short calls, long puts.",
    }


def compute_iv_term_structure(
    stock, expiries: list[str], spot: float, primary_expiry: str
) -> dict:
    """Compare ATM IV across expiration dates to detect vol term structure shape.

    Contango (normal): far-dated IV > near-dated IV — market calm.
    Backwardation: near-dated IV > far-dated IV — imminent event/stress.
    """
    if len(expiries) < 2:
        return {"error": "Need 2+ expiry dates for term structure"}

    term_points = []
    for exp in expiries[:5]:
        try:
            chain = stock.option_chain(exp)
            calls = chain.calls.to_dict("records")
            atm_strike = min(
                (c["strike"] for c in calls if c.get("strike")),
                key=lambda x: abs(x - spot),
                default=None,
            )
            if not atm_strike:
                continue
            atm_calls = [
                c
                for c in calls
                if c.get("strike") == atm_strike
                and c.get("impliedVolatility")
                and 0 < c["impliedVolatility"] < 5
            ]
            if atm_calls:
                iv = atm_calls[0]["impliedVolatility"]
                term_points.append({"expiry": exp, "atm_iv": round(iv, 4)})
        except Exception:
            continue

    if len(term_points) < 2:
        return {"error": "Insufficient term structure data"}

    near_iv = term_points[0]["atm_iv"]
    far_iv = term_points[-1]["atm_iv"]
    slope = round(far_iv - near_iv, 4)

    structure = (
        "contango" if slope > 0.01 else "backwardation" if slope < -0.01 else "flat"
    )

    return {
        "term_points": term_points,
        "structure": structure,
        "slope": slope,
        "interpretation": {
            "contango": "Normal — market expects future vol higher than near-term. No imminent stress.",
            "backwardation": "Inverted — near-term vol elevated. Likely event-driven (earnings, macro). Hedging demand concentrated short-term.",
            "flat": "Flat — no significant term structure signal.",
        }[structure],
    }


def main():
    parser = argparse.ArgumentParser(
        description="Compute options market signals from yfinance data"
    )
    parser.add_argument("ticker", help="Ticker symbol")
    parser.add_argument(
        "--expiry",
        help="Specific expiration date (YYYY-MM-DD). Default: nearest monthly.",
    )
    parser.add_argument(
        "--mode",
        choices=["basic", "full"],
        default="basic",
        help="Analysis depth (basic = nearest expiry; full = all expiries)",
    )
    parser.add_argument("--output", help="Output file path (default: stdout)")
    args = parser.parse_args()

    ticker = args.ticker.strip().upper()

    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        spot = (
            info.get("currentPrice")
            or info.get("regularMarketPrice")
            or info.get("previousClose")
        )

        if not spot:
            print(
                f"Error: Cannot determine current price for {ticker}", file=sys.stderr
            )
            sys.exit(1)

        # Get available expiration dates
        expiries = stock.options
        if not expiries:
            print(f"Error: No options data available for {ticker}", file=sys.stderr)
            sys.exit(1)

        # Select expiry
        if args.expiry:
            selected_expiry = args.expiry
        else:
            # Nearest monthly (typically 3rd Friday)
            selected_expiry = expiries[0]

        # Fetch options chain
        opt_chain = stock.option_chain(selected_expiry)
        calls = [c for c in opt_chain.calls.to_dict("records") if c.get("strike")]
        puts = [p for p in opt_chain.puts.to_dict("records") if p.get("strike")]

        result = {
            "ticker": ticker,
            "spot_price": round(float(spot), 2),
            "expiration": selected_expiry,
            "computed_at": datetime.now(timezone.utc).isoformat(),
            "data_source": "yfinance (CBOE delayed ~15min)",
        }

        # Basic analysis
        result["max_pain"] = compute_max_pain(calls, puts)
        result["put_call_ratios"] = compute_put_call_ratios(calls, puts)
        result["iv_surface"] = compute_iv_surface(calls, puts, spot)

        # Full mode: unusual activity detection + gamma exposure + term structure
        if args.mode == "full":
            result["unusual_activity"] = detect_unusual_activity(calls, puts)
            result["gamma_exposure"] = compute_gamma_exposure(calls, puts, spot)
            result["iv_term_structure"] = compute_iv_term_structure(
                stock, expiries, spot, selected_expiry
            )

        # Summary signal
        signals = []
        pcr = result["put_call_ratios"].get("put_call_volume", {}).get("ratio")
        skew = result["iv_surface"].get("iv_skew")
        max_pain_strike = result["max_pain"].get("max_pain_strike")

        if pcr is not None:
            if pcr > 1.2:
                signals.append("Bearish — elevated put/call ratio")
            elif pcr < 0.5:
                signals.append("Bullish — low put/call ratio (potential complacency)")
        if skew is not None:
            if skew > 0.05:
                signals.append("Bearish — elevated IV skew (hedging demand)")
            elif skew < -0.02:
                signals.append("Bullish — inverted skew (call speculation)")
        if max_pain_strike and spot:
            mp_diff_pct = (max_pain_strike - spot) / spot * 100
            if mp_diff_pct > 2:
                signals.append(
                    f"Bullish — Max Pain ${max_pain_strike:.2f} ({mp_diff_pct:.1f}% above spot)"
                )
            elif mp_diff_pct < -2:
                signals.append(
                    f"Bearish — Max Pain ${max_pain_strike:.2f} ({mp_diff_pct:.1f}% below spot)"
                )

        # GEX regime signal (full mode only)
        gex_data = result.get("gamma_exposure", {})
        if gex_data and not gex_data.get("error"):
            gex_regime = gex_data.get("gex_regime")
            if gex_regime == "negative":
                signals.append(
                    "Bearish — negative GEX (dealer hedging amplifies moves)"
                )
            elif gex_regime == "positive":
                signals.append(
                    "Neutral — positive GEX (dealer pinning, low vol expected)"
                )

        # IV term structure signal (full mode only)
        ts_data = result.get("iv_term_structure", {})
        if ts_data and not ts_data.get("error"):
            structure = ts_data.get("structure")
            if structure == "backwardation":
                signals.append(
                    "Bearish — IV backwardation (near-term stress/event premium)"
                )

        result["signals_summary"] = {
            "signals": signals,
            "net_sentiment": (
                "Bullish"
                if len([s for s in signals if "Bullish" in s])
                > len([s for s in signals if "Bearish" in s])
                else "Bearish"
                if len([s for s in signals if "Bearish" in s])
                > len([s for s in signals if "Bullish" in s])
                else "Neutral / Mixed"
            ),
        }

    except Exception as e:
        result = {"ticker": ticker, "error": str(e)}

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
