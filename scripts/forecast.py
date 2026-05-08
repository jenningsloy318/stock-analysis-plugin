#!/usr/bin/env python3
"""Time-series forecasting for revenue, EPS, and FCF.

Usage:
    forecast.py ./reports/AAPL/raw-data.json
    forecast.py raw-data.json --horizon 5 --output ./reports/[TICKER]/forecast.json
    forecast.py raw-data.json --method arima --confidence 0.80

Fits ARIMA and ETS models to financial time series extracted from the
raw financial data JSON (output of fetch_financials.py). Produces
forecast distributions with confidence intervals.

Replaces the single constant growth-rate assumption in DCF with
data-derived projections that include uncertainty bands.
"""

import argparse
import json
import os
import sys
import warnings
from datetime import datetime, timezone
from typing import Any

import numpy as np

# Suppress statsmodels warnings about convergence
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

try:
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    from statsmodels.tsa.stattools import adfuller
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False


# ---------------------------------------------------------------------------
# Data extraction
# ---------------------------------------------------------------------------

def extract_series(financials: dict, field_path: list[str]) -> list[float]:
    """Extract a time series of values from nested financial data.

    field_path: e.g., ["income_statement", "revenue"]
    Returns list of annual values (most recent first).
    """
    data = financials
    for key in field_path:
        data = data.get(key, {})
        if not data:
            return []

    if isinstance(data, list):
        entries = data
    elif isinstance(data, dict):
        # Already in {period, value} format?
        entries = data
    else:
        return []

    values = []
    for entry in entries:
        if isinstance(entry, dict):
            val = entry.get("value")
            if val is not None:
                values.append(float(val))
        elif isinstance(entry, (int, float)):
            values.append(float(entry))

    # Reverse to chronological order (oldest first) for time-series models
    values.reverse()
    return values


# ---------------------------------------------------------------------------
# Stationarity test
# ---------------------------------------------------------------------------

def test_stationarity(series: list[float]) -> dict:
    """Augmented Dickey-Fuller test for stationarity."""
    if len(series) < 5:
        return {"stationary": False, "p_value": None, "note": "Insufficient data"}

    try:
        result = adfuller(series, autolag="AIC")
        p_value = result[1]
        return {
            "stationary": p_value < 0.05,
            "adf_statistic": round(result[0], 4),
            "p_value": round(p_value, 4),
            "critical_values": {k: round(v, 4) for k, v in result[4].items()},
        }
    except Exception as e:
        return {"stationary": False, "p_value": None, "error": str(e)}


# ---------------------------------------------------------------------------
# ARIMA forecast
# ---------------------------------------------------------------------------

def forecast_arima(series: list[float], horizon: int = 5,
                   confidence: float = 0.80) -> dict:
    """Fit ARIMA model and produce forecasts with confidence intervals."""
    if len(series) < 5:
        return {"method": "ARIMA", "error": "Insufficient data (need ≥5 observations)"}

    try:
        # Auto-select ARIMA order (simplified grid search)
        best_aic = float("inf")
        best_order = (1, 1, 1)
        best_model = None

        # Try common orders
        orders = [(0, 1, 0), (1, 1, 0), (0, 1, 1), (1, 1, 1), (2, 1, 1), (1, 1, 2)]

        for order in orders:
            try:
                model = ARIMA(series, order=order)
                fitted = model.fit()
                if fitted.aic < best_aic:
                    best_aic = fitted.aic
                    best_order = order
                    best_model = fitted
            except Exception:
                continue

        if best_model is None:
            return {"method": "ARIMA", "error": "Could not fit any ARIMA model"}

        # Forecast
        forecast_result = best_model.get_forecast(steps=horizon)
        forecast_mean = forecast_result.predicted_mean
        alpha = 1.0 - confidence
        conf_int = forecast_result.conf_int(alpha=alpha)

        forecasts = []
        for i in range(horizon):
            forecasts.append({
                "period": i + 1,
                "mean": round(float(forecast_mean.iloc[i]), 2) if i < len(forecast_mean) else None,
                "lower": round(float(conf_int.iloc[i, 0]), 2) if i < len(conf_int) else None,
                "upper": round(float(conf_int.iloc[i, 1]), 2) if i < len(conf_int) else None,
            })

        return {
            "method": "ARIMA",
            "order": list(best_order),
            "aic": round(best_aic, 2),
            "horizon": horizon,
            "confidence_level": confidence,
            "last_observed": round(float(series[-1]), 2) if series else None,
            "forecasts": forecasts,
            "implied_cagr": round(
                (forecasts[-1]["mean"] / series[-1]) ** (1 / horizon) - 1, 4
            ) if series and series[-1] > 0 and forecasts[-1]["mean"] else None,
        }

    except Exception as e:
        return {"method": "ARIMA", "error": str(e)}


# ---------------------------------------------------------------------------
# ETS (Exponential Smoothing) forecast
# ---------------------------------------------------------------------------

def forecast_ets(series: list[float], horizon: int = 5,
                 confidence: float = 0.80) -> dict:
    """Fit Holt-Winters exponential smoothing model and forecast."""
    if len(series) < 4:
        return {"method": "ETS", "error": "Insufficient data (need ≥4 observations)"}

    try:
        # Try additive trend, no seasonality (annual data rarely has seasonality)
        model = ExponentialSmoothing(
            series,
            trend="add",
            seasonal=None,
            initialization_method="estimated",
        )
        fitted = model.fit()

        # Forecast
        forecast_mean = fitted.forecast(horizon)

        # Approximate confidence intervals using residual std
        residuals = fitted.resid
        if len(residuals) > 1:
            residual_std = np.std(residuals)
            z_score = 1.28 if confidence == 0.80 else 1.645 if confidence == 0.90 else 1.96
        else:
            residual_std = 0
            z_score = 1.28

        forecasts = []
        for i in range(horizon):
            mean_val = float(forecast_mean.iloc[i]) if i < len(forecast_mean) else None
            margin = residual_std * z_score * np.sqrt(i + 1)  # Wider as horizon grows
            forecasts.append({
                "period": i + 1,
                "mean": round(mean_val, 2) if mean_val is not None else None,
                "lower": round(mean_val - margin, 2) if mean_val is not None else None,
                "upper": round(mean_val + margin, 2) if mean_val is not None else None,
            })

        return {
            "method": "ETS (Holt-Winters, additive trend)",
            "aic": round(fitted.aic, 2) if hasattr(fitted, "aic") else None,
            "horizon": horizon,
            "confidence_level": confidence,
            "last_observed": round(float(series[-1]), 2) if series else None,
            "forecasts": forecasts,
            "implied_cagr": round(
                (forecasts[-1]["mean"] / series[-1]) ** (1 / horizon) - 1, 4
            ) if series and series[-1] > 0 and forecasts[-1]["mean"] else None,
            "residual_std": round(float(residual_std), 2),
        }

    except Exception as e:
        return {"method": "ETS", "error": str(e)}


# ---------------------------------------------------------------------------
# Naive forecast (constant growth fallback)
# ---------------------------------------------------------------------------

def forecast_naive(series: list[float], horizon: int = 5) -> dict:
    """Simple constant-CAGR forecast as fallback when models fail."""
    if len(series) < 2:
        return {"method": "Naive (constant CAGR)", "error": "Insufficient data"}

    cagr = (series[-1] / series[0]) ** (1 / (len(series) - 1)) - 1 if series[0] > 0 else 0

    forecasts = []
    last = series[-1]
    for i in range(horizon):
        last = last * (1 + cagr)
        forecasts.append({
            "period": i + 1,
            "mean": round(last, 2),
            "lower": round(last * 0.7, 2),   # ±30% ad-hoc band
            "upper": round(last * 1.3, 2),
        })

    return {
        "method": "Naive (constant CAGR)",
        "historical_cagr": round(cagr, 4),
        "horizon": horizon,
        "last_observed": round(float(series[-1]), 2) if series else None,
        "forecasts": forecasts,
        "implied_cagr": round(cagr, 4),
    }


# ---------------------------------------------------------------------------
# Combined forecast
# ---------------------------------------------------------------------------

def forecast_series(series: list[float], horizon: int = 5,
                    confidence: float = 0.80, method: str = "auto") -> dict:
    """Forecast a single time series with the best available method."""
    if not series or len(series) < 2:
        return {"error": "Insufficient data", "observations": len(series)}

    result = {
        "observations": len(series),
        "historical_values": [round(v, 2) for v in series],
    }

    # Stationarity test
    if STATSMODELS_AVAILABLE and len(series) >= 5:
        result["stationarity_test"] = test_stationarity(series)

    if method == "arima" and STATSMODELS_AVAILABLE:
        result["forecast"] = forecast_arima(series, horizon, confidence)
        if "error" in result["forecast"]:
            result["forecast"] = forecast_ets(series, horizon, confidence)
    elif method == "ets" and STATSMODELS_AVAILABLE:
        result["forecast"] = forecast_ets(series, horizon, confidence)
        if "error" in result["forecast"]:
            result["forecast"] = forecast_arima(series, horizon, confidence)
    elif method == "naive":
        result["forecast"] = forecast_naive(series, horizon)
    else:
        # Auto: try ARIMA first, then ETS, then naive
        if STATSMODELS_AVAILABLE:
            arima_result = forecast_arima(series, horizon, confidence)
            if "error" not in arima_result:
                result["forecast"] = arima_result
            else:
                ets_result = forecast_ets(series, horizon, confidence)
                if "error" not in ets_result:
                    result["forecast"] = ets_result
                else:
                    result["forecast"] = forecast_naive(series, horizon)
        else:
            result["forecast"] = forecast_naive(series, horizon)

    return result


# ---------------------------------------------------------------------------
# Ensemble forecast (combine multiple methods)
# ---------------------------------------------------------------------------

def forecast_ensemble(series: list[float], horizon: int = 5,
                      confidence: float = 0.80) -> dict:
    """Produce ensemble forecast combining ARIMA, ETS, and naive methods.

    Weights: ARIMA 0.4, ETS 0.4, Naive 0.2 when all available.
    """
    methods = {}

    if STATSMODELS_AVAILABLE:
        methods["arima"] = forecast_arima(series, horizon, confidence)
        methods["ets"] = forecast_ets(series, horizon, confidence)
    methods["naive"] = forecast_naive(series, horizon)

    # Compute ensemble mean
    ensemble_forecasts = []
    weights = {"arima": 0.4, "ets": 0.4, "naive": 0.2}

    for i in range(horizon):
        weighted_sum = 0.0
        total_weight = 0.0
        for name, result in methods.items():
            if "forecasts" in result and i < len(result["forecasts"]):
                mean_val = result["forecasts"][i].get("mean")
                if mean_val is not None:
                    w = weights.get(name, 0.2)
                    weighted_sum += mean_val * w
                    total_weight += w

        if total_weight > 0:
            ensemble_mean = weighted_sum / total_weight
        else:
            ensemble_mean = None

        # Ensemble lower = min of lower bounds
        lower_vals = []
        upper_vals = []
        for name, result in methods.items():
            if "forecasts" in result and i < len(result["forecasts"]):
                lo = result["forecasts"][i].get("lower")
                hi = result["forecasts"][i].get("upper")
                if lo is not None:
                    lower_vals.append(lo)
                if hi is not None:
                    upper_vals.append(hi)

        ensemble_lower = min(lower_vals) if lower_vals else None
        ensemble_upper = max(upper_vals) if upper_vals else None

        ensemble_forecasts.append({
            "period": i + 1,
            "mean": round(ensemble_mean, 2) if ensemble_mean is not None else None,
            "lower": round(ensemble_lower, 2) if ensemble_lower is not None else None,
            "upper": round(ensemble_upper, 2) if ensemble_upper is not None else None,
        })

    last_val = series[-1] if series else 1
    ensemble_cagr = (
        (ensemble_forecasts[-1]["mean"] / last_val) ** (1 / horizon) - 1
        if last_val > 0 and ensemble_forecasts[-1]["mean"] else None
    )

    return {
        "method": "Ensemble (ARIMA + ETS + Naive)",
        "horizon": horizon,
        "confidence_level": confidence,
        "last_observed": round(float(last_val), 2) if series else None,
        "ensemble_forecasts": ensemble_forecasts,
        "ensemble_cagr": round(ensemble_cagr, 4) if ensemble_cagr is not None else None,
        "individual_methods": {
            name: {
                "method": result.get("method", name),
                "cagr": result.get("implied_cagr"),
                "error": result.get("error"),
            }
            for name, result in methods.items()
        },
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Time-series forecasting for financial data"
    )
    parser.add_argument("input", help="Path to raw financial data JSON")
    parser.add_argument("--horizon", type=int, default=5, help="Forecast horizon in years (default: 5)")
    parser.add_argument("--confidence", type=float, default=0.80, help="Confidence level (default: 0.80)")
    parser.add_argument("--method", choices=["auto", "arima", "ets", "naive", "ensemble"],
                        default="ensemble", help="Forecast method (default: ensemble)")
    parser.add_argument("--output", help="Output file path (default: stdout)")
    args = parser.parse_args()

    if not STATSMODELS_AVAILABLE and args.method in ("arima", "ets", "auto"):
        print("Warning: statsmodels not installed. Falling back to naive forecast.",
              file=sys.stderr)
        print("Install: pip install statsmodels", file=sys.stderr)
        args.method = "naive"

    with open(args.input) as f:
        raw_data = json.load(f)

    # Extract the first ticker's data
    ticker = list(raw_data.keys())[0] if raw_data else "UNKNOWN"
    data = raw_data.get(ticker, {})
    financials = data.get("financials", {})

    # Extract series
    revenue = extract_series(financials, ["income_statement", "revenue"])
    net_income = extract_series(financials, ["income_statement", "net_income"])
    operating_income = extract_series(financials, ["income_statement", "operating_income"])
    fcf = extract_series(financials, ["cash_flow", "free_cash_flow"])
    ocf = extract_series(financials, ["cash_flow", "operating_cash_flow"])

    result = {
        "ticker": ticker,
        "forecast_date": datetime.now(timezone.utc).isoformat(),
        "data_source": data.get("source", "unknown"),
        "horizon_years": args.horizon,
        "confidence_level": args.confidence,
        "forecast_method": args.method,
    }

    # Forecast each series
    for name, series in [
        ("revenue", revenue),
        ("net_income", net_income),
        ("operating_income", operating_income),
        ("free_cash_flow", fcf),
        ("operating_cash_flow", ocf),
    ]:
        if len(series) >= 2:
            if args.method == "ensemble":
                result[name] = forecast_ensemble(series, args.horizon, args.confidence)
            else:
                result[name] = forecast_series(series, args.horizon, args.confidence, args.method)
        else:
            result[name] = {"error": "Insufficient data", "observations": len(series)}

    # Growth rate comparison table
    growth_table = {}
    for name, forecast_data in result.items():
        if isinstance(forecast_data, dict) and "ensemble_cagr" in forecast_data:
            growth_table[name] = {
                "ensemble_cagr": forecast_data["ensemble_cagr"],
                "individual_cagrs": forecast_data.get("individual_methods", {}),
            }
        elif isinstance(forecast_data, dict) and "forecast" in forecast_data:
            fc = forecast_data["forecast"]
            if isinstance(fc, dict):
                growth_table[name] = {"cagr": fc.get("implied_cagr")}

    result["growth_rate_summary"] = growth_table

    # Recommended DCF inputs
    if "free_cash_flow" in result and isinstance(result["free_cash_flow"], dict):
        fcf_data = result["free_cash_flow"]
        ensemble_cagr = fcf_data.get("ensemble_cagr")
        if ensemble_cagr is not None:
            result["dcf_recommendations"] = {
                "fcf_growth_rate": round(ensemble_cagr, 4),
                "growth_rate_source": "Ensemble forecast (ARIMA + ETS + Naive)",
                "growth_rate_lower": round(
                    fcf_data["ensemble_forecasts"][-1]["lower"] / fcf_data["last_observed"]
                    ** (1 / args.horizon) - 1, 4
                ) if fcf_data.get("ensemble_forecasts") and fcf_data["last_observed"] > 0 else None,
                "growth_rate_upper": round(
                    fcf_data["ensemble_forecasts"][-1]["upper"] / fcf_data["last_observed"]
                    ** (1 / args.horizon) - 1, 4
                ) if fcf_data.get("ensemble_forecasts") and fcf_data["last_observed"] > 0 else None,
                "note": "Use these growth rates in DCF instead of single constant assumption."
                        " Lower/upper provide a range for sensitivity analysis.",
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
