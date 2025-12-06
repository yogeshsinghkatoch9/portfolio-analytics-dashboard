"""
Market News API for VisionWealth
Fetches financial news for specific tickers or general market news
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from enum import Enum
import yfinance as yf
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


# Models

class NewsCategory(str, Enum):
    """News category types"""
    GENERAL = "general"
    EARNINGS = "earnings"
    DIVIDENDS = "dividends"
    ANALYST = "analyst"
    MARKET = "market"


class NewsItem(BaseModel):
    """Model for a single news item"""
    title: str
    publisher: str
    link: str
    publish_date: str
    thumbnail: Optional[str] = None
    related_tickers: List[str] = Field(default_factory=list)
    summary: Optional[str] = None
    category: Optional[str] = None


class NewsResponse(BaseModel):
    """Response model for news endpoint"""
    news: List[NewsItem]
    total_count: int
    tickers: List[str] = Field(default_factory=list)
    cached: bool = False
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class NewsStats(BaseModel):
    """Statistics about news coverage"""
    total_articles: int
    publishers: List[str]
    date_range: Dict[str, str]
    tickers_covered: List[str]


# Cache for news data (5 minute TTL)
news_cache: Dict[str, tuple[List[NewsItem], float]] = {}
CACHE_TTL = 300  # 5 minutes


@router.get('/market/news', response_model=NewsResponse, tags=["Market News"])
def get_market_news(
    tickers: Optional[str] = Query(None, description="Comma-separated ticker symbols", max_length=200),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of news items"),
    min_relevance: float = Query(0.0, ge=0.0, le=1.0, description="Minimum relevance score"),
    include_summary: bool = Query(False, description="Include article summaries")
):
    """
    Fetch financial news for specific tickers or general market news.
    
    **Examples**:
    - GET /market/news                          # General market news
    - GET /market/news?tickers=AAPL             # Apple news
    - GET /market/news?tickers=AAPL,GOOGL,MSFT  # Multiple tickers
    """
    start_time = time.time()
    
    try:
        ticker_list = []
        if tickers:
            ticker_list = [t.strip().upper() for t in tickers.split(',') if t.strip()][:10]
            
            if not ticker_list:
                raise HTTPException(status_code=400, detail="No valid tickers provided")
        
        logger.info(f"Fetching news for tickers: {ticker_list if ticker_list else 'general market'}")
        
        # Check cache
        cache_key = f"{','.join(sorted(ticker_list)) if ticker_list else 'general'}:{limit}"
        cached_result = _get_from_cache(cache_key)
        
        if cached_result:
            logger.info(f"Returning cached news for {cache_key}")
            return NewsResponse(
                news=cached_result[:limit],
                total_count=len(cached_result),
                tickers=ticker_list,
                cached=True,
                timestamp=datetime.utcnow()
            )
        
        # Fetch fresh news
        news_items = []
        
        if ticker_list:
            news_items = _fetch_ticker_news(ticker_list, include_summary)
        else:
            news_items = _fetch_general_news(include_summary)
        
        # Filter by relevance
        if min_relevance > 0:
            news_items = [item for item in news_items if _calculate_relevance(item) >= min_relevance]
        
        # Sort by date
        news_items = _sort_news_by_date(news_items)
        
        # Store in cache
        _store_in_cache(cache_key, news_items)
        
        # Apply limit
        limited_news = news_items[:limit]
        
        elapsed_time = time.time() - start_time
        logger.info(f"Fetched {len(limited_news)} news items in {elapsed_time:.2f}s")
        
        return NewsResponse(
            news=limited_news,
            total_count=len(news_items),
            tickers=ticker_list,
            cached=False,
            timestamp=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching news: {e}", exc_info=True)
        return NewsResponse(
            news=[],
            total_count=0,
            tickers=ticker_list if ticker_list else [],
            cached=False,
            timestamp=datetime.utcnow()
        )


@router.get('/market/news/stats', response_model=NewsStats, tags=["Market News"])
def get_news_stats(tickers: Optional[str] = Query(None, description="Comma-separated ticker symbols")):
    """Get statistics about news coverage for specified tickers"""
    try:
        ticker_list = []
        if tickers:
            ticker_list = [t.strip().upper() for t in tickers.split(',') if t.strip()][:10]
        
        # Fetch news
        if ticker_list:
            news_items = _fetch_ticker_news(ticker_list, False)
        else:
            news_items = _fetch_general_news(False)
        
        # Calculate stats
        publishers = list(set(item.publisher for item in news_items))
        
        dates = [item.publish_date for item in news_items if item.publish_date]
        dates.sort()
        
        date_range = {
            "earliest": dates[0] if dates else "",
            "latest": dates[-1] if dates else ""
        }
        
        all_tickers = set()
        for item in news_items:
            all_tickers.update(item.related_tickers)
        
        return NewsStats(
            total_articles=len(news_items),
            publishers=publishers,
            date_range=date_range,
            tickers_covered=sorted(list(all_tickers))
        )
        
    except Exception as e:
        logger.error(f"Error getting news stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error calculating news statistics")


@router.delete('/market/news/cache', tags=["Market News"])
def clear_news_cache():
    """Clear the news cache"""
    global news_cache
    count = len(news_cache)
    news_cache.clear()
    logger.info(f"Cleared {count} items from news cache")
    
    return {
        "success": True,
        "items_cleared": count,
        "message": f"Cache cleared successfully ({count} items)"
    }


# Helper Functions

def _fetch_ticker_news(tickers: List[str], include_summary: bool = False) -> List[NewsItem]:
    """Fetch news for specific tickers"""
    all_items = []
    seen_titles = set()
    
    for symbol in tickers:
        try:
            logger.info(f"Fetching news for {symbol}")
            ticker = yf.Ticker(symbol)
            news = ticker.news
            
            if not news:
                logger.warning(f"No news found for {symbol}")
                continue
            
            for article in news:
                try:
                    item = _parse_news_article(article, include_summary)
                    
                    if not item or item.title in seen_titles:
                        continue
                    
                    seen_titles.add(item.title)
                    all_items.append(item)
                    
                except Exception as e:
                    logger.warning(f"Error parsing article for {symbol}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error fetching news for {symbol}: {e}")
            continue
    
    return all_items


def _fetch_general_news(include_summary: bool = False) -> List[NewsItem]:
    """Fetch general market news via SPY"""
    try:
        logger.info("Fetching general market news")
        ticker = yf.Ticker("SPY")
        news = ticker.news
        
        items = []
        seen_titles = set()
        
        for article in news:
            try:
                item = _parse_news_article(article, include_summary)
                
                if not item or item.title in seen_titles:
                    continue
                
                seen_titles.add(item.title)
                items.append(item)
                
            except Exception as e:
                logger.warning(f"Error parsing general news article: {e}")
                continue
        
        return items
        
    except Exception as e:
        logger.error(f"Error fetching general news: {e}")
        return []


def _parse_news_article(article: Dict[str, Any], include_summary: bool = False) -> Optional[NewsItem]:
    """Parse a news article from yfinance format"""
    try:
        data = article.get('content', article)
        
        title = data.get('title')
        if not title:
            return None
        
        # Extract thumbnail
        thumbnail = None
        thumb_data = data.get('thumbnail')
        if thumb_data and isinstance(thumb_data, dict):
            resolutions = thumb_data.get('resolutions', [])
            if resolutions and isinstance(resolutions, list):
                thumbnail = resolutions[-1].get('url')
        
        # Extract link
        link = None
        click_through = data.get('clickThroughUrl')
        canonical = data.get('canonicalUrl')
        
        if click_through:
            link = click_through.get('url') if isinstance(click_through, dict) else click_through
        elif canonical:
            link = canonical.get('url') if isinstance(canonical, dict) else canonical
        else:
            link = data.get('link', '#')
        
        # Extract publisher
        publisher = "Unknown"
        provider = data.get('provider')
        if provider:
            publisher = provider.get('displayName') if isinstance(provider, dict) else provider
        elif data.get('publisher'):
            publisher = data.get('publisher')
        
        # Extract publish date
        publish_date = data.get('providerPublishTime') or data.get('pubDate') or data.get('displayTime') or ""
        
        if isinstance(publish_date, (int, float)):
            publish_date = datetime.fromtimestamp(publish_date).isoformat()
        
        # Extract related tickers
        related_tickers = data.get('relatedTickers', []) or []
        if not isinstance(related_tickers, list):
            related_tickers = []
        
        # Extract summary
        summary = None
        if include_summary:
            summary = data.get('summary') or data.get('description')
        
        # Determine category
        category = _determine_category(title, summary or "")
        
        return NewsItem(
            title=title,
            publisher=publisher,
            link=link,
            publish_date=publish_date,
            thumbnail=thumbnail,
            related_tickers=related_tickers,
            summary=summary,
            category=category
        )
        
    except Exception as e:
        logger.warning(f"Error parsing news article: {e}")
        return None


def _determine_category(title: str, summary: str) -> Optional[str]:
    """Determine news category based on content"""
    content = (title + " " + summary).lower()
    
    if any(word in content for word in ['earnings', 'quarterly', 'revenue', 'profit']):
        return NewsCategory.EARNINGS.value
    elif any(word in content for word in ['dividend', 'payout', 'yield']):
        return NewsCategory.DIVIDENDS.value
    elif any(word in content for word in ['analyst', 'rating', 'upgrade', 'downgrade', 'price target']):
        return NewsCategory.ANALYST.value
    elif any(word in content for word in ['market', 'index', 'dow', 's&p', 'nasdaq']):
        return NewsCategory.MARKET.value
    else:
        return NewsCategory.GENERAL.value


def _calculate_relevance(item: NewsItem) -> float:
    """Calculate relevance score for a news item"""
    score = 0.5
    
    if item.thumbnail:
        score += 0.2
    
    if item.related_tickers:
        score += 0.2
    
    if item.summary:
        score += 0.1
    
    try:
        if item.publish_date:
            pub_date = datetime.fromisoformat(item.publish_date.replace('Z', '+00:00'))
            age_hours = (datetime.utcnow() - pub_date.replace(tzinfo=None)).total_seconds() / 3600
            if age_hours < 24:
                score += 0.1
    except:
        pass
    
    return min(score, 1.0)


def _sort_news_by_date(items: List[NewsItem]) -> List[NewsItem]:
    """Sort news items by publication date (newest first)"""
    def get_sort_key(item: NewsItem):
        try:
            if not item.publish_date:
                return datetime.min
            
            date_str = item.publish_date
            
            if isinstance(date_str, (int, float)) or date_str.isdigit():
                return datetime.fromtimestamp(float(date_str))
            
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            
        except Exception as e:
            logger.warning(f"Error parsing date '{item.publish_date}': {e}")
            return datetime.min
    
    try:
        return sorted(items, key=get_sort_key, reverse=True)
    except Exception as e:
        logger.warning(f"Error sorting news: {e}")
        return items


def _get_from_cache(key: str) -> Optional[List[NewsItem]]:
    """Get news from cache if not expired"""
    if key in news_cache:
        items, timestamp = news_cache[key]
        if time.time() - timestamp < CACHE_TTL:
            return items
        else:
            del news_cache[key]
    return None


def _store_in_cache(key: str, items: List[NewsItem]):
    """Store news in cache with timestamp"""
    news_cache[key] = (items, time.time())
    
    # Clean up old cache entries (keep last 100)
    if len(news_cache) > 100:
        sorted_keys = sorted(news_cache.keys(), key=lambda k: news_cache[k][1])
        for old_key in sorted_keys[:-100]:
            del news_cache[old_key]
