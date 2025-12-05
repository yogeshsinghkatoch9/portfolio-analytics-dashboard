from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel
import yfinance as yf
import random

router = APIRouter()

class NewsItem(BaseModel):
    title: str
    publisher: str
    link: str
    publishDate: str
    thumbnail: Optional[str] = None
    relatedTickers: List[str] = []

class NewsResponse(BaseModel):
    news: List[NewsItem]

@router.get('/market/news', response_model=NewsResponse)
def get_market_news(tickers: Optional[str] = None):
    """
    Fetch news for specific tickers (comma separated) or general market news.
    """
    try:
        items = []
        
        if tickers:
            symbols = [t.strip().upper() for t in tickers.split(',') if t.strip()]
            
            # Limit to top 3 symbols to keep latency down
            for sym in symbols[:3]:
                try:
                    t = yf.Ticker(sym)
                    news = t.news
                    for n in news:
                        # Normalize structure
                        data = n.get('content', n) # Handle both nested and flat if any
                        
                        title = data.get('title')
                        if not title: continue
                        
                        # Extract Thumbnail
                        thumb = None
                        thumb_data = data.get('thumbnail')
                        if thumb_data and 'resolutions' in thumb_data:
                            ress = thumb_data['resolutions']
                            if ress:
                                thumb = ress[0]['url']
                                
                        # Extract Link
                        link_obj = data.get('clickThroughUrl') or data.get('canonicalUrl')
                        link = link_obj.get('url') if link_obj else data.get('link')
                        if not link: link = "#"

                        # Extract Publisher
                        pub_obj = data.get('provider')
                        publisher = pub_obj.get('displayName') if pub_obj else data.get('publisher', 'Unknown')
                        
                        items.append(NewsItem(
                            title=title,
                            publisher=publisher,
                            link=link,
                            publishDate=data.get('pubDate') or data.get('displayTime') or "",
                            thumbnail=thumb,
                            relatedTickers=data.get('relatedTickers', []) or []
                        ))
                except Exception as ex:
                    print(f"News error for {sym}: {ex}")
                    continue
            
        else:
            # General Market News via SPY
            t = yf.Ticker("SPY")
            news = t.news
            for n in news:
                data = n.get('content', n)
                
                title = data.get('title')
                if not title: continue
                
                thumb = None
                thumb_data = data.get('thumbnail')
                if thumb_data and 'resolutions' in thumb_data:
                    ress = thumb_data['resolutions']
                    if ress:
                        thumb = ress[0]['url']
                        
                link_obj = data.get('clickThroughUrl') or data.get('canonicalUrl')
                link = link_obj.get('url') if link_obj else data.get('link')
                if not link: link = "#"

                pub_obj = data.get('provider')
                publisher = pub_obj.get('displayName') if pub_obj else data.get('publisher', 'Unknown')
                
                items.append(NewsItem(
                    title=title,
                    publisher=publisher,
                    link=link,
                    publishDate=data.get('pubDate') or data.get('displayTime') or "",
                    thumbnail=thumb,
                    relatedTickers=data.get('relatedTickers', []) or []
                ))

        # Sort by date descending (simple string compare for ISO works approx)
        items.sort(key=lambda x: x.publishDate, reverse=True)
        return NewsResponse(news=items)
            
    except Exception as e:
        print(f"News fetch error: {e}")
        return NewsResponse(news=[])
