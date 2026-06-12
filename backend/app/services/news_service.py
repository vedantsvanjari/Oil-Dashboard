import feedparser
from datetime import datetime, timezone
import time
import re
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Priority Topics for Relevance
PRIORITY_KEYWORDS = {
    "high": ["wti", "brent", "crude oil", "opec", "opec+", "supply disruption", "geopolitical risk", "us shale"],
    "medium": ["eia", "inventories", "refinery utilization", "refined products", "tanker markets", "demand forecast", "middle east"],
    "low": ["energy", "gasoline", "diesel", "rig count", "exports", "imports"]
}

# Lexicon for Oil Sentiment
BULLISH_TERMS = ["draw", "decline", "cut", "disruption", "tension", "tight", "surge", "spike", "record demand", "bullish", "jump", "rally", "escalate"]
BEARISH_TERMS = ["build", "increase", "glut", "surplus", "weak demand", "recession", "drop", "plunge", "bearish", "fall", "slide", "slowdown"]

def normalize_text(text: str) -> str:
    """Lowercase and remove non-alphanumeric characters for fuzzy matching."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', '', text)
    return " ".join(text.split())

def calculate_jaccard_similarity(s1: str, s2: str) -> float:
    set1 = set(s1.split())
    set2 = set(s2.split())
    if not set1 or not set2:
        return 0.0
    intersection = set1.intersection(set2)
    union = set1.union(set2)
    return len(intersection) / len(union)

def calculate_relevance(title: str, summary: str) -> int:
    score = 0
    t_lower = title.lower()
    s_lower = summary.lower()
    
    for term in PRIORITY_KEYWORDS["high"]:
        if term in t_lower: score += 10 * 2
        if term in s_lower: score += 10
        
    for term in PRIORITY_KEYWORDS["medium"]:
        if term in t_lower: score += 5 * 2
        if term in s_lower: score += 5
        
    for term in PRIORITY_KEYWORDS["low"]:
        if term in t_lower: score += 2 * 2
        if term in s_lower: score += 2
        
    return score

def analyze_sentiment(title: str, summary: str) -> Dict[str, Any]:
    text = (title + " " + summary).lower()
    bull_score = sum(1 for term in BULLISH_TERMS if term in text)
    bear_score = sum(1 for term in BEARISH_TERMS if term in text)
    
    total_signals = bull_score + bear_score
    if total_signals == 0:
        return {"sentiment": "Neutral", "confidence": 50}
        
    if bull_score > bear_score:
        sentiment = "Bullish"
        confidence = min(50 + (bull_score * 15), 98)
    elif bear_score > bull_score:
        sentiment = "Bearish"
        confidence = min(50 + (bear_score * 15), 98)
    else:
        sentiment = "Neutral"
        confidence = min(50 + (total_signals * 5), 85)
        
    return {"sentiment": sentiment, "confidence": int(confidence)}

class NewsService:
    def __init__(self):
        self.feeds = [
            {"url": "https://feeds.reuters.com/Reuters/worldNews", "source": "Reuters World News"},
            {"url": "https://feeds.reuters.com/reuters/businessNews", "source": "Reuters Business"},
            {"url": "https://www.eia.gov/rss/todayinenergy.xml", "source": "EIA News"},
            {"url": "https://oilprice.com/rss/main", "source": "OilPrice.com"},
            {"url": "https://www.cnbc.com/id/10000846/device/rss/rss.html", "source": "CNBC Energy"},
            {"url": "https://www.investing.com/rss/news_11.rss", "source": "Investing.com"},
            {"url": "https://www.rigzone.com/news/rss/rigzone_latest.aspx", "source": "Rigzone"},
            {"url": "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml", "source": "WSJ Business"}
        ]
        self.cached_articles = []
        self.last_fetch = 0
        self.aggregate_sentiment = {}

    def fetch_news(self) -> Dict[str, Any]:
        current_time = time.time()
        # Cache for 5 minutes
        if current_time - self.last_fetch < 300 and self.cached_articles:
            return {
                "articles": self.cached_articles,
                "sentiment_summary": self.aggregate_sentiment
            }

        raw_articles = []
        for feed_info in self.feeds:
            try:
                parsed = feedparser.parse(feed_info["url"])
                if not parsed.entries:
                    continue
                for entry in parsed.entries:
                    title = entry.get("title", "").strip()
                    if not title:
                        continue
                        
                    published_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
                    if published_parsed:
                        try:
                            published_at = datetime.fromtimestamp(time.mktime(published_parsed), tz=timezone.utc).isoformat()
                        except Exception:
                            published_at = datetime.now(timezone.utc).isoformat()
                    else:
                        published_at = datetime.now(timezone.utc).isoformat()
                        
                    summary = entry.get("summary", "")
                    if summary:
                        summary = re.sub(r'<[^>]+>', '', summary) # strip html
                        summary = summary[:500]
                        
                    raw_articles.append({
                        "title": title,
                        "source": feed_info["source"],
                        "published_at": published_at,
                        "url": entry.get("link", ""),
                        "summary": summary
                    })
            except Exception as e:
                logger.error(f"Error fetching feed {feed_info['url']}: {e}")

        # Processing Pipeline: Relevance -> Sort -> Deduplicate -> Sentiment
        
        # 1. Relevance
        for article in raw_articles:
            article["relevance_score"] = calculate_relevance(article["title"], article["summary"])
            
        # 2. Sort by Relevance (desc) and Recency (desc)
        raw_articles.sort(key=lambda x: (x["relevance_score"], x["published_at"]), reverse=True)
        
        # 3. Deduplication (Keep highest relevance)
        deduplicated = []
        seen_normalized_titles = []
        
        for article in raw_articles:
            if article["relevance_score"] == 0:
                continue # Filter out completely irrelevant news
                
            norm_title = normalize_text(article["title"])
            
            # Check Exact/Normalized match
            is_duplicate = False
            for seen_norm in seen_normalized_titles:
                if norm_title == seen_norm:
                    is_duplicate = True
                    break
                # Check Fuzzy match
                similarity = calculate_jaccard_similarity(norm_title, seen_norm)
                if similarity > 0.70:
                    is_duplicate = True
                    break
                    
            if not is_duplicate:
                deduplicated.append(article)
                seen_normalized_titles.append(norm_title)
                
            if len(deduplicated) >= 50:
                break
                
        # If we didn't hit 50, pad with general recent news
        if len(deduplicated) < 30:
            raw_articles.sort(key=lambda x: x["published_at"], reverse=True)
            for article in raw_articles:
                if article not in deduplicated:
                    norm_title = normalize_text(article["title"])
                    is_duplicate = False
                    for seen_norm in seen_normalized_titles:
                        if calculate_jaccard_similarity(norm_title, seen_norm) > 0.70:
                            is_duplicate = True
                            break
                    if not is_duplicate:
                        deduplicated.append(article)
                        seen_normalized_titles.append(norm_title)
                    if len(deduplicated) >= 40:
                        break

        # 4. Sentiment Assignment
        bullish_count = 0
        bearish_count = 0
        neutral_count = 0
        total_confidence = 0
        
        for article in deduplicated:
            sentiment_data = analyze_sentiment(article["title"], article["summary"])
            article["sentiment"] = sentiment_data["sentiment"]
            article["confidence"] = sentiment_data["confidence"]
            
            total_confidence += sentiment_data["confidence"]
            if sentiment_data["sentiment"] == "Bullish":
                bullish_count += 1
            elif sentiment_data["sentiment"] == "Bearish":
                bearish_count += 1
            else:
                neutral_count += 1
                
        # Aggregate Sentiment
        overall_sentiment = "Neutral"
        if bullish_count > bearish_count * 1.5:
            overall_sentiment = "Bullish"
        elif bearish_count > bullish_count * 1.5:
            overall_sentiment = "Bearish"
            
        avg_confidence = int(total_confidence / len(deduplicated)) if deduplicated else 50
            
        self.aggregate_sentiment = {
            "bullish": bullish_count,
            "bearish": bearish_count,
            "neutral": neutral_count,
            "market_sentiment": overall_sentiment,
            "confidence": avg_confidence
        }
        
        # Sort final output by recency
        deduplicated.sort(key=lambda x: x["published_at"], reverse=True)
        
        self.cached_articles = deduplicated
        self.last_fetch = current_time
        
        return {
            "articles": self.cached_articles,
            "sentiment_summary": self.aggregate_sentiment
        }

news_service = NewsService()
