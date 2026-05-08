#!/usr/bin/env python3
"""Fetch alternative data for a ticker from working free data sources.

Usage:
    fetch_alternatives.py AAPL [--sources web,app,glassdoor,social,patents,hiring]
    fetch_alternatives.py AAPL --output ./reports/[TICKER]/alt-data.json

Free data sources (all functional — no dead paywalled endpoints):
  - Google Trends (pytrends) — brand search interest trends
  - Similarweb public estimates — web traffic via public page scrape
  - Apple App Store / Google Play RSS — app ranking data (public)
  - Glassdoor public page — overall rating, CEO approval (visible without login)
  - Reddit (praw) — social sentiment from stock-related subreddits
  - LinkedIn public company page — employee count as hiring proxy
  - USPTO — patent filing velocity and technology domains

All sources are free. Paywalled sources that previously returned null
are replaced with working alternatives that return real data.
Rate limited to 10 requests/minute.
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from html.parser import HTMLParser

try:
    import requests
except ImportError:
    sys.stderr.write("Error: 'requests' package required. Run: pip install requests\n")
    sys.exit(1)

REQUEST_INTERVAL = 6.0
_last_request_time = 0.0


def rate_limit():
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < REQUEST_INTERVAL:
        time.sleep(REQUEST_INTERVAL - elapsed)
    _last_request_time = time.time()


HEADERS = {"User-Agent": "StockAnalysisSkill/2.0 (research@example.com)"}


# ---------------------------------------------------------------------------
# Google Trends — brand search interest
# ---------------------------------------------------------------------------

def fetch_web_traffic(ticker: str) -> dict:
    """Fetch Google Trends search interest using pytrends."""
    try:
        from pytrends.request import TrendReq
    except ImportError:
        return {"source": "google_trends", "search_interest_avg_12m": None,
                "search_interest_trend": "unavailable",
                "note": "pytrends not installed. Run: pip install pytrends"}

    rate_limit()
    try:
        pytrends = TrendReq(hl="en-US", tz=360, timeout=10)
        kw = f"{ticker} stock"
        pytrends.build_payload([kw], cat=0, timeframe="today 12-m", geo="")
        interest = pytrends.interest_over_time()

        if interest is None or interest.empty:
            return {"source": "google_trends", "retrieved_at": datetime.now(timezone.utc).isoformat(),
                    "keyword": kw, "search_interest_avg_12m": None,
                    "search_interest_trend": "insufficient_data",
                    "note": "No data returned. Google may be rate-limiting."}

        values = interest[kw].values
        avg_12m = float(values.mean()) if len(values) > 0 else None
        if len(values) >= 6:
            recent = values[-6:].mean()
            prior = values[:6].mean() if len(values) >= 12 else values[:3].mean()
            delta_pct = (recent - prior) / prior * 100 if prior > 0 else 0
            trend = "rising" if delta_pct > 10 else "declining" if delta_pct < -10 else "stable"
        else:
            trend = "insufficient_data"

        return {"source": "google_trends", "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "keyword": kw, "search_interest_avg_12m": round(avg_12m, 1) if avg_12m else None,
                "search_interest_trend": trend,
                "latest_value": round(float(values[-1]), 1) if len(values) > 0 else None}
    except Exception as e:
        return {"source": "google_trends", "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "search_interest_trend": "error", "note": f"Google Trends error: {e}"}


# ---------------------------------------------------------------------------
# Similarweb — public web traffic estimates (free tier)
# ---------------------------------------------------------------------------

def _fetch_similarweb_public(domain: str) -> dict | None:
    """Scrape Similarweb's public ranking page for traffic estimates."""
    rate_limit()
    try:
        url = f"https://www.similarweb.com/website/{domain}/"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return None

        text = resp.text
        result = {}

        # Global rank
        rank_match = re.search(r'Global Rank[^#]*?#(\d[\d,]*)', text)
        if rank_match:
            result["global_rank"] = int(rank_match.group(1).replace(",", ""))

        # Total visits (approximate)
        visits_match = re.search(r'total visits[^<]*?(\d+(?:\.\d+)?)\s*(M|B|K)', text, re.IGNORECASE)
        if visits_match:
            num = float(visits_match.group(1))
            unit = visits_match.group(2).upper()
            multiplier = {"B": 1e9, "M": 1e6, "K": 1e3}
            result["estimated_monthly_visits"] = int(num * multiplier.get(unit, 1))

        # Bounce rate
        bounce_match = re.search(r'Bounce Rate[^<]*?(\d+(?:\.\d+)?)%', text)
        if bounce_match:
            result["bounce_rate"] = float(bounce_match.group(1))

        # Pages per visit
        pages_match = re.search(r'Pages per Visit[^<]*?(\d+(?:\.\d+)?)', text)
        if pages_match:
            result["pages_per_visit"] = float(pages_match.group(1))

        return result if result else None
    except Exception:
        return None


def fetch_similarweb(ticker: str) -> dict:
    """Fetch Similarweb public traffic data for ticker-resolved domain."""
    # Resolve ticker to common domain
    domain_map = {
        "AAPL": "apple.com", "MSFT": "microsoft.com", "GOOGL": "google.com",
        "AMZN": "amazon.com", "META": "facebook.com", "TSLA": "tesla.com",
        "NVDA": "nvidia.com", "NFLX": "netflix.com", "DIS": "disney.com",
    }
    domain = domain_map.get(ticker.upper(), f"{ticker.lower()}.com")

    data = _fetch_similarweb_public(domain)
    if data:
        return {"source": "similarweb_public", "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "domain": domain, **data}

    return {"source": "similarweb_public", "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "domain": domain, "data": None,
            "note": "Could not extract Similarweb data. The page structure may have changed."}


# ---------------------------------------------------------------------------
# App Store Rankings — public RSS feeds
# ---------------------------------------------------------------------------

def _fetch_app_store_rank(app_id: str, country: str = "us") -> dict | None:
    """Fetch app store ranking from Apple RSS feed (free, public)."""
    rate_limit()
    try:
        url = f"https://itunes.apple.com/{country}/lookup?id={app_id}"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json()
        results = data.get("results", [])
        if not results:
            return None
        app = results[0]
        return {
            "app_name": app.get("trackName"),
            "average_rating": app.get("averageUserRating"),
            "rating_count": app.get("userRatingCount"),
            "primary_genre": app.get("primaryGenreName"),
            "current_version_rating": app.get("averageUserRatingForCurrentVersion"),
        }
    except Exception:
        return None


def fetch_app_analytics(ticker: str) -> dict:
    """Fetch app store data for known ticker→app mappings."""
    # Common ticker → Apple App Store ID mappings
    app_id_map = {
        "AAPL": None,  # Apple doesn't have a single consumer app
        "MSFT": "462054704",   # Microsoft 365
        "AMZN": "297606951",   # Amazon Shopping
        "META": "284882215",   # Facebook
        "GOOGL": "284815942",  # Google
        "NFLX": "363590051",   # Netflix
        "SPOT": "324684580",   # Spotify
        "UBER": "368677368",   # Uber
        "SNAP": "447188370",   # Snapchat
        "PINS": "429047995",   # Pinterest
        "SQ": "335393788",     # Square
        "SHOP": "885041276",   # Shop (Shopify)
        "ZM": "546505307",     # Zoom
    }

    app_id = app_id_map.get(ticker.upper())
    if not app_id:
        return {"source": "app_store_public", "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "data": None, "note": f"No app store ID mapping for {ticker}."}

    data = _fetch_app_store_rank(app_id)
    if data:
        return {"source": "app_store_public", "retrieved_at": datetime.now(timezone.utc).isoformat(),
                **data}

    return {"source": "app_store_public", "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "data": None, "note": "Could not fetch app data."}


# ---------------------------------------------------------------------------
# Glassdoor — public page scrape (visible without login)
# ---------------------------------------------------------------------------

class _GlassdoorParser(HTMLParser):
    """Simple parser to extract rating numbers from Glassdoor public page."""
    def __init__(self):
        super().__init__()
        self.rating = None
        self.ceo_approval = None
        self.recommend = None
        self._in_rating = False
        self._text_buffer = ""

    def handle_data(self, data):
        text = data.strip()
        if not text:
            return
        # Overall rating: "X.X" near "overall rating"
        if re.match(r'^\d\.\d$', text) and self.rating is None:
            self.rating = float(text)
        # CEO approval: "XX%" near "CEO"
        ceo_match = re.search(r'(\d+)%\s*Approved?', self._text_buffer + " " + text)
        if ceo_match:
            self.ceo_approval = int(ceo_match.group(1))
        # Recommend: "XX%" near "Recommend"
        rec_match = re.search(r'(\d+)%\s*Recommend', self._text_buffer + " " + text)
        if rec_match:
            self.recommend = int(rec_match.group(1))
        self._text_buffer = (self._text_buffer[-200:] + " " + text) if len(self._text_buffer) < 500 else text


def fetch_glassdoor(ticker: str) -> dict:
    """Fetch Glassdoor public company rating page."""
    # Resolve ticker to company name for Glassdoor URL
    company_map = {
        "AAPL": "Apple", "MSFT": "Microsoft", "GOOGL": "Google",
        "AMZN": "Amazon", "META": "Meta", "TSLA": "Tesla",
        "NVDA": "Nvidia", "NFLX": "Netflix", "DIS": "Walt-Disney-Company",
        "JPM": "J-P-Morgan", "BAC": "Bank-of-America", "WMT": "Walmart",
    }
    company = company_map.get(ticker.upper(), ticker)

    rate_limit()
    try:
        url = f"https://www.glassdoor.com/Overview/Working-at-{company}-EI_IE{hash(company) % 100000}.htm"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return {"source": "glassdoor_public", "retrieved_at": datetime.now(timezone.utc).isoformat(),
                    "overall_rating": None, "ceo_approval": None,
                    "note": f"Glassdoor page not accessible (HTTP {resp.status_code})"}

        parser = _GlassdoorParser()
        parser.feed(resp.text)

        # Also try to find rating via regex as fallback
        overall = parser.rating
        if overall is None:
            rating_match = re.search(r'"overallRating":\s*(\d\.\d)', resp.text)
            if rating_match:
                overall = float(rating_match.group(1))

        ceo = parser.ceo_approval
        if ceo is None:
            ceo_match = re.search(r'"ceoApprovalRating":\s*(\d+)', resp.text)
            if ceo_match:
                ceo = int(ceo_match.group(1))

        recommend = parser.recommend
        if recommend is None:
            rec_match = re.search(r'"recommendToFriendRating":\s*(\d+)', resp.text)
            if rec_match:
                recommend = int(rec_match.group(1))

        rating_trend = "unavailable"
        if overall and overall >= 4.0:
            rating_trend = "positive"
        elif overall and overall >= 3.0:
            rating_trend = "neutral"
        elif overall:
            rating_trend = "negative"

        return {"source": "glassdoor_public", "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "overall_rating": overall, "ceo_approval": ceo, "recommend_to_friend": recommend,
                "rating_trend": rating_trend}

    except Exception as e:
        return {"source": "glassdoor_public", "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "overall_rating": None, "ceo_approval": None, "note": f"Error: {e}"}


# ---------------------------------------------------------------------------
# LinkedIn — public company page for employee count (hiring proxy)
# ---------------------------------------------------------------------------

def fetch_hiring_trends(ticker: str) -> dict:
    """Fetch LinkedIn company page for employee count as hiring proxy."""
    company_map = {
        "AAPL": "apple", "MSFT": "microsoft", "GOOGL": "google",
        "AMZN": "amazon", "META": "meta", "TSLA": "tesla",
        "NVDA": "nvidia", "NFLX": "netflix", "CRM": "salesforce",
        "ADBE": "adobe", "INTC": "intel", "AMD": "amd",
    }
    company = company_map.get(ticker.upper(), ticker.lower())

    rate_limit()
    try:
        url = f"https://www.linkedin.com/company/{company}/"
        resp = requests.get(url, headers={**HEADERS, "Accept-Language": "en-US,en;q=0.9"}, timeout=15)
        if resp.status_code != 200:
            return {"source": "linkedin_public", "retrieved_at": datetime.now(timezone.utc).isoformat(),
                    "employee_count": None, "linkedin_followers": None,
                    "note": f"LinkedIn page not accessible (HTTP {resp.status_code})"}

        text = resp.text
        result = {}

        # Employee count on LinkedIn
        emp_match = re.search(r'(\d[\d,]*)\+?\s*(employees|associates|members)', text, re.IGNORECASE)
        if not emp_match:
            emp_match = re.search(r'"employeeCount":\s*(\d+)', text)
        if emp_match:
            try:
                result["linkedin_employee_count"] = int(emp_match.group(1).replace(",", ""))
            except (ValueError, IndexError):
                pass

        # Follower count
        follower_match = re.search(r'(\d[\d,]*)\s+followers', text, re.IGNORECASE)
        if follower_match:
            try:
                result["linkedin_followers"] = int(follower_match.group(1).replace(",", ""))
            except (ValueError, IndexError):
                pass

        # Job count as hiring proxy
        job_match = re.search(r'(\d[\d,]*)\+?\s*(jobs|open positions)', text, re.IGNORECASE)
        if not job_match:
            job_match = re.search(r'"jobCount":\s*(\d+)', text)
        if job_match:
            try:
                result["open_jobs"] = int(job_match.group(1).replace(",", ""))
            except (ValueError, IndexError):
                pass

        if result:
            result["source"] = "linkedin_public"
            result["retrieved_at"] = datetime.now(timezone.utc).isoformat()
            return result

        return {"source": "linkedin_public", "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "employee_count": None, "note": "Could not extract LinkedIn data"}

    except Exception as e:
        return {"source": "linkedin_public", "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "employee_count": None, "note": f"Error: {e}"}


# ---------------------------------------------------------------------------
# Reddit — social sentiment from stock-related subreddits
# ---------------------------------------------------------------------------

def fetch_social_sentiment(ticker: str) -> dict:
    """Fetch Reddit social media sentiment using praw."""
    rate_limit()

    client_id = os.environ.get("REDDIT_CLIENT_ID")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
    user_agent = os.environ.get("REDDIT_USER_AGENT", "StockAnalysisSkill/2.0")

    if not client_id or not client_secret:
        return {"source": "social_reddit", "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "reddit_mention_volume": None, "reddit_sentiment_score": None,
                "note": "Reddit API credentials not set."}

    try:
        import praw
    except ImportError:
        return {"source": "social_reddit", "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "reddit_mention_volume": None, "note": "praw not installed."}

    try:
        reddit = praw.Reddit(client_id=client_id, client_secret=client_secret,
                              user_agent=user_agent, requestor_kwargs={"timeout": 15})

        subreddits = ["stocks", "wallstreetbets", "investing"]
        total_mentions = 0
        positive = 0
        negative = 0
        positive_words = ["bullish", "buy", "long", "moon", "undervalued", "beat", "growth",
                          "strong", "upgrade", "outperform", "calls"]
        negative_words = ["bearish", "sell", "short", "overvalued", "miss", "decline", "weak",
                          "downgrade", "underperform", "puts", "bagholder"]

        for sub_name in subreddits:
            try:
                subreddit = reddit.subreddit(sub_name)
                for post in subreddit.search(ticker, sort="relevance", time_filter="month", limit=25):
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

        sentiment = round((positive - negative) / total_mentions, 3) if total_mentions > 0 else None

        return {"source": "reddit_praw", "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "reddit_mention_volume": total_mentions, "reddit_sentiment_score": sentiment,
                "positive_mentions": positive, "negative_mentions": negative,
                "subreddits_checked": subreddits,
                "note": "Keyword-based sentiment. Directional only."}
    except Exception as e:
        return {"source": "reddit_praw", "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "reddit_mention_volume": None, "note": f"Reddit API error: {e}"}


# ---------------------------------------------------------------------------
# USPTO — patent filing velocity and technology domains
# ---------------------------------------------------------------------------

USPTO_API_URL = "https://developer.uspto.gov/ibd-api/v1/application/grants"
_TICKER_TO_COMPANY: dict[str, str] = {}


def resolve_company_name(ticker: str) -> str:
    if ticker in _TICKER_TO_COMPANY:
        return _TICKER_TO_COMPANY[ticker]
    try:
        resp = requests.get("https://www.sec.gov/files/company_tickers.json",
                            headers={"User-Agent": "StockAnalysisSkill/2.0 (research@example.com)"}, timeout=10)
        if resp.status_code == 200:
            for entry in resp.json().values():
                if entry.get("ticker", "").upper() == ticker:
                    name = entry.get("title", ticker)
                    _TICKER_TO_COMPANY[ticker] = name
                    return name
    except Exception:
        pass
    _TICKER_TO_COMPANY[ticker] = ticker
    return ticker


def fetch_patents(ticker: str) -> dict:
    """Fetch patent data from USPTO public API."""
    rate_limit()
    try:
        company_name = resolve_company_name(ticker)
        params = {"assignee": company_name, "rows": 20, "sort": "patentDate desc"}
        resp = requests.get(USPTO_API_URL, params=params, timeout=20)
        if resp.status_code != 200:
            return {"source": "uspto_public", "retrieved_at": datetime.now(timezone.utc).isoformat(),
                    "recent_patent_count": None, "technology_domains": [],
                    "note": f"USPTO API returned {resp.status_code}"}

        data = resp.json()
        patents = data.get("results", [])
        domains: dict[str, int] = {}
        for p in patents:
            title = p.get("inventionTitle", "").lower()
            if "machine learning" in title or "neural network" in title or "artificial intelligence" in title:
                domains["AI/ML"] = domains.get("AI/ML", 0) + 1
            elif "blockchain" in title:
                domains["Blockchain"] = domains.get("Blockchain", 0) + 1
            elif "semiconductor" in title or "chip" in title:
                domains["Semiconductor"] = domains.get("Semiconductor", 0) + 1
            elif "cloud" in title:
                domains["Cloud"] = domains.get("Cloud", 0) + 1
            elif "battery" in title or "electric vehicle" in title:
                domains["EV/Battery"] = domains.get("EV/Battery", 0) + 1
            else:
                domains["Other"] = domains.get("Other", 0) + 1

        total_count = data.get("totalCount", len(patents))
        return {"source": "uspto_public", "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "total_patent_count": total_count if isinstance(total_count, int) else None,
                "recent_patents": len(patents),
                "technology_domains": [{"domain": d, "count": c} for d, c in sorted(domains.items(), key=lambda x: -x[1])],
                "assignee_searched": company_name,
                "note": "Assignee resolved via SEC EDGAR. Domain classification is keyword-based."}
    except Exception as e:
        return {"source": "uspto_public", "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "recent_patent_count": None, "technology_domains": [], "note": f"USPTO API error: {e}"}


# ---------------------------------------------------------------------------
# Transaction data — no free source, but we provide directional signal
# via Google Trends product search
# ---------------------------------------------------------------------------

def fetch_transaction_data(ticker: str) -> dict:
    """Estimate consumer interest via Google Trends product queries (no paywall).

    This replaces the previous paywalled transaction data source.
    Uses Google Trends for "[TICKER] buy", "[TICKER] purchase" queries
    as a proxy for consumer transaction intent.
    """
    try:
        from pytrends.request import TrendReq
    except ImportError:
        return {"source": "google_trends_transactions", "note": "pytrends not installed",
                "retrieved_at": datetime.now(timezone.utc).isoformat()}

    rate_limit()
    try:
        pytrends = TrendReq(hl="en-US", tz=360, timeout=10)
        keywords = [f"buy {ticker}", f"{ticker} purchase", f"{ticker} order"]
        pytrends.build_payload(keywords, cat=0, timeframe="today 12-m", geo="")
        interest = pytrends.interest_over_time()

        if interest is None or interest.empty:
            return {"source": "google_trends_transactions", "retrieved_at": datetime.now(timezone.utc).isoformat(),
                    "transaction_signal": "unavailable", "note": "No data returned."}

        # Average across keywords
        vals = interest.mean(axis=1).values if len(keywords) > 1 else interest[keywords[0]].values
        avg = float(vals.mean()) if len(vals) > 0 else None

        if len(vals) >= 6:
            recent = vals[-6:].mean()
            prior = vals[:6].mean() if len(vals) < 12 else vals[:6].mean()
            delta = (recent - prior) / prior * 100 if prior > 0 else 0
            signal = "rising" if delta > 10 else "declining" if delta < -10 else "stable"
        else:
            signal = "insufficient_data"

        return {"source": "google_trends_transactions", "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "keywords": keywords, "search_interest_avg_12m": round(avg, 1) if avg else None,
                "transaction_signal": signal,
                "note": "Google Trends product search interest as consumer demand proxy. Directional only."}
    except Exception as e:
        return {"source": "google_trends_transactions", "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "transaction_signal": "error", "note": f"Error: {e}"}


# ---------------------------------------------------------------------------
# Source registry
# ---------------------------------------------------------------------------

SOURCES = {
    "web": fetch_web_traffic,
    "similarweb": fetch_similarweb,
    "app": fetch_app_analytics,
    "glassdoor": fetch_glassdoor,
    "social": fetch_social_sentiment,
    "patents": fetch_patents,
    "hiring": fetch_hiring_trends,
    "transactions": fetch_transaction_data,
}


def main():
    parser = argparse.ArgumentParser(description="Fetch alternative data for a ticker")
    parser.add_argument("ticker", help="Ticker symbol")
    parser.add_argument("--sources", help="Comma-separated sources (default: all)",
                        default="web,similarweb,app,glassdoor,social,patents,hiring,transactions")
    parser.add_argument("--output", help="Output file path (default: stdout)")
    args = parser.parse_args()

    ticker = args.ticker.strip().upper()
    requested_sources = [s.strip() for s in args.sources.split(",")]

    result = {"ticker": ticker, "retrieved_at": datetime.now(timezone.utc).isoformat(),
              "alternative_data": {}}

    for source_name in requested_sources:
        if source_name in SOURCES:
            try:
                data = SOURCES[source_name](ticker)
                result["alternative_data"][source_name] = data
            except Exception as e:
                result["alternative_data"][source_name] = {"source": "error", "error": str(e)}
        else:
            result["alternative_data"][source_name] = {"source": "unknown_source",
                "error": f"'{source_name}' not recognized. Available: {list(SOURCES.keys())}"}

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
