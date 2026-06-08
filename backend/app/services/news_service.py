import feedparser
from datetime import datetime, timezone
import time
from typing import List, Dict, Any

def fetch_latest_news() -> List[Dict[str, Any]]:
    feeds = [
        {"url": "https://feeds.reuters.com/Reuters/worldNews", "source": "Reuters World News"},
        {"url": "https://feeds.reuters.com/reuters/businessNews", "source": "Reuters Business"},
        {"url": "https://www.eia.gov/rss/todayinenergy.xml", "source": "EIA News"},
        {"url": "https://oilprice.com/rss/main", "source": "OilPrice.com"}
    ]
    
    articles = []
    seen_titles = set()
    
    for feed_info in feeds:
        try:
            parsed = feedparser.parse(feed_info["url"])
            if not parsed.entries:
                continue
                
            for entry in parsed.entries:
                title = entry.get("title", "").strip()
                if not title or title in seen_titles:
                    continue
                    
                seen_titles.add(title)
                
                # Parse published date
                published_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
                if published_parsed:
                    try:
                        dt = datetime.fromtimestamp(time.mktime(published_parsed), tz=timezone.utc)
                        published_at = dt.isoformat()
                    except Exception:
                        published_at = datetime.now(timezone.utc).isoformat()
                else:
                    published_at = datetime.now(timezone.utc).isoformat()
                
                # Clean up summary
                summary = entry.get("summary", "")
                if summary:
                    # Strip basic html tags if needed, or just truncate
                    summary = summary[:500]
                
                articles.append({
                    "title": title,
                    "source": feed_info["source"],
                    "published_at": published_at,
                    "url": entry.get("link", ""),
                    "summary": summary
                })
        except Exception as e:
            print(f"Error fetching feed {feed_info['url']}: {e}")
            
    # Sort by published_at descending
    articles.sort(key=lambda x: x["published_at"], reverse=True)
    
    return articles[:20]
