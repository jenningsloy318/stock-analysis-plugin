#!/usr/bin/env python3
"""Portfolio context: correlation analysis, position sizing, risk contribution.

Usage:
    portfolio_context.py AAPL --portfolio '{"AAPL":0.15,"MSFT":0.10,"SPY":0.25}'
    portfolio_context.py AAPL --portfolio-file /tmp/portfolio.json
    portfolio_context.py AAPL --portfolio '{"AAPL":0.2}' --risk-free 0.04

Computes:
  - Correlation of new position with existing portfolio
  - Marginal risk contribution
  - Portfolio variance impact
  - Recommended position size relative to existing exposure
  - Diversification benefit score
  - Factor exposure overlap
"""

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone
from typing import Any

try:
    import numpy as np
    import yfinance as yf
except ImportError:
    sys.stderr.write("Error: numpy and yfinance required.\n")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Correlation analysis
# ---------------------------------------------------------------------------

def fetch_returns(tickers: list[str], period: str = "1y") -> dict[str, list[float]]:
    """Fetch daily returns for a list of tickers."""
    returns = {}
    for t in tickers:
        try:
            stock = yf.Ticker(t)
            hist = stock.history(period=period)
            if hist.empty or len(hist) < 20:
                returns[t] = []
                continue
            closes = hist["Close"].values
            daily_returns = [(closes[i] - closes[i - 1]) / closes[i - 1]
                             for i in range(1, len(closes))]
            returns[t] = daily_returns
        except Exception:
            returns[t] = []
    return returns


def compute_correlation(returns_a: list[float], returns_b: list[float]) -> float | None:
    """Compute Pearson correlation between two return series."""
    if len(returns_a) < 20 or len(returns_b) < 20:
        return None
    min_len = min(len(returns_a), len(returns_b))
    a = returns_a[-min_len:]
    b = returns_b[-min_len:]
    if len(a) < 2:
        return None
    corr = np.corrcoef(a, b)[0, 1]
    return round(float(corr), 4) if not math.isnan(corr) else None


# ---------------------------------------------------------------------------
# Portfolio risk metrics
# ---------------------------------------------------------------------------

def compute_portfolio_metrics(new_ticker: str, new_weight: float,
                               portfolio: dict[str, float],
                               returns: dict[str, list[float]],
                               risk_free: float = 0.04) -> dict:
    """Compute portfolio risk metrics with the new position."""
    all_tickers = list(portfolio.keys()) + [new_ticker]
    all_weights = [portfolio.get(t, 0) for t in all_tickers[:-1]] + [new_weight]

    # Normalize weights (existing portfolio is (1 - new_weight))
    remaining = 1.0 - new_weight
    normalized = [w * remaining for w in all_weights[:-1]] + [new_weight]

    # Extract aligned return series
    min_len = min(len(returns.get(t, [])) for t in all_tickers if returns.get(t, []))
    if min_len < 20:
        return {"error": "Insufficient price history (need ≥20 days)"}

    aligned = {}
    for t in all_tickers:
        r = returns.get(t, [])
        if len(r) >= min_len:
            aligned[t] = r[-min_len:]

    if not aligned:
        return {"error": "No aligned return data"}

    # Covariance matrix
    tickers_available = [t for t in all_tickers if t in aligned]
    n = len(tickers_available)
    returns_matrix = np.array([aligned[t] for t in tickers_available])
    cov_matrix = np.cov(returns_matrix)

    # Portfolio variance and std
    weights_arr = np.array([normalized[i] for i, t in enumerate(all_tickers) if t in tickers_available])

    port_variance = weights_arr @ cov_matrix @ weights_arr
    port_std = math.sqrt(max(0, port_variance))

    # Annualized volatility
    ann_std = port_std * math.sqrt(252)
    ann_return = 0  # Can't predict returns, just risk

    # Sharpe ratio (approximate, using 0 expected return)
    sharpe = -risk_free / ann_std if ann_std > 0 else 0

    # Marginal risk contribution of new position
    # MRC_i = w_i * (Σw)_i / σ_p
    new_idx = tickers_available.index(new_ticker) if new_ticker in tickers_available else -1
    mrc = None
    if new_idx >= 0 and port_std > 0:
        marginal_cov = cov_matrix[new_idx] @ weights_arr
        mrc = new_weight * marginal_cov / port_std

    # Correlation of new ticker with existing portfolio
    if new_ticker in tickers_available and len(tickers_available) > 1:
        existing_returns = np.zeros(min_len)
        existing_weights_sum = 0
        for i, t in enumerate(tickers_available):
            if t != new_ticker:
                existing_returns += aligned[t] * normalized[i]
                existing_weights_sum += normalized[i]
        if existing_weights_sum > 0:
            existing_returns /= existing_weights_sum
            port_corr = np.corrcoef(aligned[new_ticker], existing_returns)[0, 1]
        else:
            port_corr = None
    else:
        port_corr = None

    # Diversification benefit
    # DB = 1 - (portfolio_var / weighted_avg_individual_var)
    individual_vars = np.diag(cov_matrix)
    weighted_avg_var = weights_arr @ individual_vars
    diversification = 1 - (port_variance / weighted_avg_var) if weighted_avg_var > 0 else 0

    # Correlation matrix for display
    corr_summary = {}
    for i, t1 in enumerate(tickers_available):
        for j, t2 in enumerate(tickers_available):
            if i < j:
                if cov_matrix[i, i] > 0 and cov_matrix[j, j] > 0:
                    corr = cov_matrix[i, j] / math.sqrt(cov_matrix[i, i] * cov_matrix[j, j])
                    corr_summary[f"{t1}_vs_{t2}"] = round(float(corr), 4)

    return {
        "portfolio_std_annualized": round(float(ann_std), 4),
        "portfolio_variance": round(float(port_variance), 6),
        "diversification_benefit": round(float(diversification), 4),
        "correlation_with_portfolio": round(float(port_corr), 4) if port_corr is not None else None,
        "marginal_risk_contribution": round(float(mrc), 6) if mrc is not None else None,
        "existing_holdings": len(tickers_available) - 1,
        "correlation_matrix": corr_summary,
        "concentration_warning": (
            "High concentration risk — new position highly correlated with portfolio"
            if port_corr and abs(port_corr) > 0.8
            else "Moderate correlation — provides some diversification"
            if port_corr and abs(port_corr) > 0.5
            else "Low correlation — good diversification candidate"
            if port_corr is not None
            else None
        ),
    }


# ---------------------------------------------------------------------------
# Position sizing recommendation
# ---------------------------------------------------------------------------

def recommend_position_size(conviction: float, portfolio_corr: float | None,
                             sharpe: float, max_single: float = 0.20) -> dict:
    """Recommend position size based on conviction and portfolio context.

    Uses a combination of:
    - Conviction score (1-10) → base allocation
    - Portfolio correlation → diversification adjustment
    - Maximum single-position cap
    """
    if conviction is None:
        return {"recommended_size": None, "error": "Conviction score required"}

    # Base size from conviction
    if conviction >= 9.0:
        base = 0.12
    elif conviction >= 7.5:
        base = 0.08
    elif conviction >= 6.0:
        base = 0.05
    elif conviction >= 4.0:
        base = 0.02
    else:
        base = 0.0  # Don't allocate to low-conviction ideas

    # Diversification adjustment
    if portfolio_corr is not None:
        if abs(portfolio_corr) < 0.3:
            base *= 1.3  # Low correlation → size up
        elif abs(portfolio_corr) > 0.7:
            base *= 0.6  # High correlation → size down

    # Cap at maximum
    recommended = min(base, max_single)

    # Kelly criterion overlay (simplified)
    # f* = edge / odds
    # Edge ≈ conviction - 5 (shift to -4 to +5 range)
    edge = (conviction - 5.0) / 5.0  # -1 to +1
    if edge > 0:
        # Rough odds: assume 3:1 risk/reward for high conviction
        odds = 3.0 if conviction >= 7.5 else 2.0 if conviction >= 6.0 else 1.5
        kelly = edge / odds
        kelly_quarter = kelly * 0.25
    else:
        kelly_quarter = 0.0

    return {
        "recommended_size": round(recommended, 4),
        "recommended_size_pct": f"{recommended:.1%}",
        "base_allocation": round(base, 4),
        "quarter_kelly": round(kelly_quarter, 4),
        "max_position_cap": max_single,
        "methodology": "Base from conviction × diversification adjustment, capped at max. Quarter-Kelly overlay.",
    }


# ---------------------------------------------------------------------------
# Factor exposure overlap
# ---------------------------------------------------------------------------

FACTOR_PROXIES = {
    "market_beta": "SPY",
    "value": "VTV",
    "growth": "VUG",
    "small_cap": "IWM",
    "momentum": "MTUM",
    "quality": "QUAL",
    "low_vol": "USMV",
    "dividend": "VYM",
}


def compute_factor_exposure(ticker: str) -> dict:
    """Estimate factor exposures by correlation to factor ETFs."""
    exposures = {}
    ticker_returns = fetch_returns([ticker], "6mo").get(ticker, [])

    if len(ticker_returns) < 20:
        return {"error": "Insufficient data for factor analysis"}

    # Fetch factor ETF returns
    factor_tickers = list(set(FACTOR_PROXIES.values()))
    factor_returns = fetch_returns(factor_tickers, "6mo")

    for factor_name, etf in FACTOR_PROXIES.items():
        etf_rets = factor_returns.get(etf, [])
        if etf_rets:
            corr = compute_correlation(ticker_returns, etf_rets)
            exposures[factor_name] = corr

    # Dominant factors
    if exposures:
        significant = {k: v for k, v in exposures.items() if v is not None and abs(v) > 0.5}
        dominant = sorted(significant.items(), key=lambda x: -abs(x[1]))
    else:
        dominant = []

    return {
        "factor_exposures": exposures,
        "dominant_factors": [{"factor": d[0], "correlation": d[1]} for d in dominant[:3]],
        "interpretation": (
            f"Stock primarily driven by: {', '.join(d[0] for d in dominant[:3])}"
            if dominant
            else "No dominant factor exposure detected"
        ),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Portfolio context: correlation, sizing, risk contribution"
    )
    parser.add_argument("ticker", help="Ticker to analyze in portfolio context")
    parser.add_argument("--portfolio", help='JSON portfolio: \'{"AAPL":0.15,"MSFT":0.10}\'')
    parser.add_argument("--portfolio-file", help="Path to portfolio JSON file")
    parser.add_argument("--conviction", type=float, help="Conviction score (1-10)")
    parser.add_argument("--risk-free", type=float, default=0.04, help="Risk-free rate (default: 0.04)")
    parser.add_argument("--output", help="Output file path (default: stdout)")
    args = parser.parse_args()

    ticker = args.ticker.strip().upper()

    # Load portfolio
    portfolio = {}
    if args.portfolio:
        try:
            portfolio = json.loads(args.portfolio)
        except json.JSONDecodeError as e:
            print(f"Error parsing portfolio JSON: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.portfolio_file:
        try:
            with open(args.portfolio_file) as f:
                portfolio = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading portfolio file: {e}", file=sys.stderr)
            sys.exit(1)

    result = {
        "ticker": ticker,
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "existing_portfolio": {k: f"{v:.1%}" for k, v in portfolio.items()} if portfolio else {},
    }

    # Fetch returns for ticker + portfolio holdings
    all_tickers = [ticker] + [t for t in portfolio.keys() if t != ticker]
    returns = fetch_returns(all_tickers)

    # Correlation of ticker with each portfolio holding
    correlations = {}
    for pt, pw in portfolio.items():
        if pt != ticker:
            corr = compute_correlation(returns.get(ticker, []), returns.get(pt, []))
            correlations[pt] = corr

    result["pairwise_correlations"] = correlations

    # Portfolio risk metrics
    if portfolio:
        # Default new weight: 5% if not specified
        new_weight = portfolio.get(ticker, 0.05)
        metrics = compute_portfolio_metrics(ticker, new_weight, portfolio, returns, args.risk_free)
        result["portfolio_risk"] = metrics

        # Position sizing
        if args.conviction is not None:
            port_corr = metrics.get("correlation_with_portfolio")
            sizing = recommend_position_size(args.conviction, port_corr, metrics.get("sharpe_ratio", 0))
            result["position_sizing"] = sizing

    # Factor exposure
    result["factor_exposure"] = compute_factor_exposure(ticker)

    # Summary
    warnings = []
    if correlations:
        high_corr = [(t, c) for t, c in correlations.items() if c is not None and abs(c) > 0.7]
        if high_corr:
            warnings.append(f"High correlation with existing holdings: {', '.join(t for t, _ in high_corr)}")

    result["portfolio_summary"] = {
        "warnings": warnings,
        "warning_count": len(warnings),
        "recommendation": (
            "Good diversification candidate — add to portfolio"
            if not warnings and result.get("position_sizing", {}).get("recommended_size", 0) > 0.03
            else "Moderate addition — size conservatively, monitor correlation"
            if not warnings
            else "Proceed with caution — high overlap with existing holdings"
        ),
    }

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
