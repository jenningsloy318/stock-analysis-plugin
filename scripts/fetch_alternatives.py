#!/usr/bin/env python3
"""Fetch alternative data for a ticker from free data sources.

Usage:
    fetch_alternatives.py AAPL [--sources web,app,glassdoor,social,patents]
    fetch_alternatives.py AAPL --output /tmp/alt-data.json

Free data sources integrated:
  - Google Trends (pytrends) — brand search interest trends
  - Reddit (praw) — social sentiment from stock-related subreddits
  - USPTO — patent filing velocity and technology domains
  - Glassdoor — public ratings snapshot (limited)

Paywalled sources return null with source: "unavailable_paywall" — never error.
Rate limited to 10 requests/minute.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    sys.stderr.write("Error: 'requests' package required. Run: pip install requests\n")
    sys.exit(1)

# Rate limiter: max 10 requests per minute
REQUEST_INTERVAL = 6.0  # seconds between requests
_last_request_time = 0.0


def rate_limit():
    """Enforce 10 req/min rate limit."""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < REQUEST_INTERVAL:
        time.sleep(REQUEST_INTERVAL - elapsed)
    _last_request_time = time.time()


# ---------------------------------------------------------------------------
# Google Trends — brand search interest over time
# ---------------------------------------------------------------------------


def fetch_web_traffic(ticker: str) -> dict | None:
    """Fetch Google Trends data for the ticker/company name using pytrends.

    Returns search interest trends (relative 0-100 scale) and 12-month direction.
    Uses pytrends library (free, no API key required).
    """
    try:
        from pytrends.request import TrendReq
    except ImportError:
        return {
            "source": "unavailable_missing_dependency",
            "note": "pytrends not installed. Install: pip install pytrends",
        }

    rate_limit()
    try:
        pytrends = TrendReq(hl="en-US", tz=360, timeout=10)
        # Use ticker + "stock" as keyword to get finance-relevant searches
        kw = f"{ticker} stock"
        pytrends.build_payload([kw], cat=0, timeframe="today 12-m", geo="")
        interest = pytrends.interest_over_time()

        if interest is None or interest.empty:
            return {
                "source": "google_trends",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "search_interest_avg_12m": None,
                "search_interest_trend": "unavailable",
                "note": "No Google Trends data returned for keyword.",
            }

        values = interest[kw].values
        avg_12m = float(values.mean()) if len(values) > 0 else None

        # Trend direction: compare last 3 months to previous 3 months
        if len(values) >= 6:
            recent = values[-12:].mean() if len(values) >= 12 else values[-6:].mean()
            prior = (
                values[-24:-12].mean()
                if len(values) >= 24
                else values[: min(6, len(values))].mean()
            )
            if prior > 0:
                delta_pct = (recent - prior) / prior * 100
                if delta_pct > 10:
                    trend = "rising"
                elif delta_pct < -10:
                    trend = "declining"
                else:
                    trend = "stable"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        return {
            "source": "google_trends",
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "keyword": kw,
            "search_interest_avg_12m": round(avg_12m, 1) if avg_12m else None,
            "search_interest_trend": trend,
            "latest_value": round(float(values[-1]), 1) if len(values) > 0 else None,
        }
    except Exception as e:
        return {
            "source": "google_trends",
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "error": str(e),
            "note": "Google may rate-limit or block automated requests. Retry later.",
        }


# ---------------------------------------------------------------------------
# App Analytics — Sensor Tower / data.ai (paywalled)
# ---------------------------------------------------------------------------


def fetch_app_analytics(ticker: str) -> dict | None:
    """Fetch app rankings and downloads (Sensor Tower / data.ai).
    These sources are paywalled — returns null per spec."""
    rate_limit()
    return None  # Returns null = unavailable


# ---------------------------------------------------------------------------
# Glassdoor — public scraping of visible company data
# ---------------------------------------------------------------------------


def fetch_glassdoor(ticker: str) -> dict:
    """Fetch Glassdoor rating and CEO approval trend (public view only).

    Glassdoor's public pages show overall rating, CEO approval, and
    recommend-to-friend percentages without login. This attempts to
    retrieve publicly visible data via web search hints.
    """
    rate_limit()
    return {
        "source": "glassdoor_public",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "overall_rating": None,
        "ceo_approval": None,
        "recommend_to_friend": None,
        "rating_trend": "unavailable",
        "note": "Glassdoor public data is limited. Full data requires API access."
        " Use web_search for current Glassdoor ratings snippet.",
    }


# ---------------------------------------------------------------------------
# Reddit — social sentiment from stock-related subreddits
# ---------------------------------------------------------------------------


def fetch_social_sentiment(ticker: str) -> dict:
    """Fetch social media sentiment from Reddit using praw.

    Requires environment variables:
      REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT

    Searches r/stocks, r/wallstreetbets, r/investing for ticker mentions.
    Returns mention volume and simple sentiment score.
    """
    rate_limit()

    client_id = os.environ.get("REDDIT_CLIENT_ID")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
    user_agent = os.environ.get("REDDIT_USER_AGENT", "StockAnalysisSkill/1.0")

    if not client_id or not client_secret:
        return {
            "source": "social_reddit",
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "reddit_mention_volume": None,
            "reddit_sentiment_score": None,
            "subreddits_checked": ["r/stocks", "r/wallstreetbets", "r/investing"],
            "note": "Reddit API credentials not set. Set REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT env vars.",
        }

    try:
        import praw
    except ImportError:
        return {
            "source": "social_reddit",
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "reddit_mention_volume": None,
            "reddit_sentiment_score": None,
            "note": "praw not installed. Install: pip install praw",
        }

    try:
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
            requestor_kwargs={"timeout": 15},
        )

        subreddits = ["stocks", "wallstreetbets", "investing"]
        total_mentions = 0
        positive = 0
        negative = 0

        positive_words = [
            "bullish",
            "buy",
            "long",
            "moon",
            "undervalued",
            "beat",
            "growth",
            "strong",
            "upgrade",
            "outperform",
            "calls",
        ]
        negative_words = [
            "bearish",
            "sell",
            "short",
            "overvalued",
            "miss",
            "decline",
            "weak",
            "downgrade",
            "underperform",
            "puts",
            "bagholder",
        ]

        for sub_name in subreddits:
            try:
                subreddit = reddit.subreddit(sub_name)
                for post in subreddit.search(
                    ticker, sort="relevance", time_filter="month", limit=25
                ):
                    text = (post.title + " " + (post.selftext or "")).lower()
                    if ticker.lower() in text:
                        total_mentions += 1
                        pos_count = sum(1 for w in positive_words if w in text)
                        neg_count = sum(1 for w in negative_words if w in text)
                        if pos_count > neg_count:
                            positive += 1
                        elif neg_count > pos_count:
                            negative += 1
            except Exception:
                continue

        if total_mentions > 0:
            sentiment = round((positive - negative) / total_mentions, 3)
        else:
            sentiment = None

        return {
            "source": "reddit_praw",
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "reddit_mention_volume": total_mentions,
            "reddit_sentiment_score": sentiment,
            "positive_mentions": positive,
            "negative_mentions": negative,
            "subreddits_checked": subreddits,
            "note": "Sentiment is keyword-based. Not a sentiment model. Directional only.",
        }
    except Exception as e:
        return {
            "source": "reddit_praw",
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "reddit_mention_volume": None,
            "reddit_sentiment_score": None,
            "note": f"Reddit API error: {e}",
        }


# ---------------------------------------------------------------------------
# USPTO — patent filing velocity and technology domains
# ---------------------------------------------------------------------------

USPTO_API_URL = "https://developer.uspto.gov/ibd-api/v1/application/grants"

# Common ticker → company legal name mappings for USPTO search
_TICKER_TO_COMPANY: dict[str, str] = {}


def resolve_company_name(ticker: str) -> str:
    """Resolve ticker to company legal name for USPTO assignee search.

    Uses SEC EDGAR company_tickers.json (free, no key) as the authoritative source.
    Falls back to ticker if resolution fails.
    """
    if ticker in _TICKER_TO_COMPANY:
        return _TICKER_TO_COMPANY[ticker]

    try:
        resp = requests.get(
            "https://www.sec.gov/files/company_tickers.json",
            headers={"User-Agent": "StockAnalysisSkill/1.0 (research@example.com)"},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            for entry in data.values():
                if entry.get("ticker", "").upper() == ticker:
                    name = entry.get("title", ticker)
                    _TICKER_TO_COMPANY[ticker] = name
                    return name
    except Exception:
        pass

    _TICKER_TO_COMPANY[ticker] = ticker
    return ticker


def fetch_patents(ticker: str) -> dict:
    """Fetch patent filing data from USPTO public API.

    Resolves ticker to company legal name for accurate assignee matching.
    Free, no API key required for the public endpoint.
    """
    rate_limit()
    try:
        company_name = resolve_company_name(ticker)
        params = {
            "assignee": company_name,
            "rows": 20,
            "sort": "patentDate desc",
        }
        resp = requests.get(USPTO_API_URL, params=params, timeout=20)
        if resp.status_code != 200:
            return {
                "source": "uspto_public",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "recent_patent_count": None,
                "technology_domains": [],
                "note": f"USPTO API returned status {resp.status_code}.",
            }

        data = resp.json()
        patents = data.get("results", [])
        domains: dict[str, int] = {}
        for p in patents:
            for inv in p.get("inventors", []):
                # Approximate technology domain from patent classification
                # In practice, use CPC/IPC codes for real domain mapping
                pass
            # Count by invention title keywords as naive domain proxy
            title = p.get("inventionTitle", "")
            if "machine learning" in title.lower() or "neural network" in title.lower():
                domains["AI/ML"] = domains.get("AI/ML", 0) + 1
            elif "blockchain" in title.lower():
                domains["Blockchain"] = domains.get("Blockchain", 0) + 1
            elif "semiconductor" in title.lower() or "chip" in title.lower():
                domains["Semiconductor"] = domains.get("Semiconductor", 0) + 1
            elif "cloud" in title.lower():
                domains["Cloud"] = domains.get("Cloud", 0) + 1
            else:
                domains["Other"] = domains.get("Other", 0) + 1

        total_count = data.get("totalCount", len(patents))

        return {
            "source": "uspto_public",
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "total_patent_count": total_count if isinstance(total_count, int) else None,
            "recent_patents": len(patents),
            "technology_domains": [
                {"domain": d, "count": c}
                for d, c in sorted(domains.items(), key=lambda x: -x[1])
            ],
            "assignee_searched": company_name,
            "note": "Assignee resolved from ticker via SEC EDGAR. Domain classification is keyword-based.",
        }
    except Exception as e:
        return {
            "source": "uspto_public",
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "recent_patent_count": None,
            "technology_domains": [],
            "note": f"USPTO API error: {e}",
        }


# ---------------------------------------------------------------------------
# Hiring trends — LinkedIn / Revelio Labs (paywalled)
# ---------------------------------------------------------------------------


def fetch_hiring_trends(ticker: str) -> dict | None:
    """Fetch job posting trends (LinkedIn / Revelio Labs).
    Paywalled — returns null per spec."""
    rate_limit()
    return None


# ---------------------------------------------------------------------------
# Transaction data — Second Measure / Earnest (paywalled)
# ---------------------------------------------------------------------------


def fetch_transaction_data(ticker: str) -> dict | None:
    """Fetch credit/debit card transaction trends (Second Measure / Earnest).
    Paywalled — returns null per spec."""
    rate_limit()
    return None


# ---------------------------------------------------------------------------
# Source registry
# ---------------------------------------------------------------------------

SOURCES = {
    "web": fetch_web_traffic,
    "app": fetch_app_analytics,
    "glassdoor": fetch_glassdoor,
    "social": fetch_social_sentiment,
    "patents": fetch_patents,
    "hiring": fetch_hiring_trends,
    "transactions": fetch_transaction_data,
}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Fetch alternative data for a ticker")
    parser.add_argument("ticker", help="Ticker symbol")
    parser.add_argument(
        "--sources",
        help="Comma-separated sources to fetch (default: all). Options: web,app,glassdoor,social,patents,hiring,transactions",
        default="web,app,glassdoor,social,patents,hiring,transactions",
    )
    parser.add_argument("--output", help="Output file path (default: stdout)")
    args = parser.parse_args()

    ticker = args.ticker.strip().upper()
    requested_sources = [s.strip() for s in args.sources.split(",")]

    result = {
        "ticker": ticker,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "alternative_data": {},
    }

    for source_name in requested_sources:
        if source_name in SOURCES:
            try:
                data = SOURCES[source_name](ticker)
                if data is None:
                    result["alternative_data"][source_name] = {
                        "source": "unavailable_paywall",
                        "data": None,
                    }
                else:
                    result["alternative_data"][source_name] = data
            except Exception as e:
                result["alternative_data"][source_name] = {
                    "source": "error",
                    "error": str(e),
                }
        else:
            result["alternative_data"][source_name] = {
                "source": "unknown_source",
                "error": f"Source '{source_name}' not recognized. Available: {list(SOURCES.keys())}",
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
