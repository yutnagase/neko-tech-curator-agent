import feedparser
import httpx
from typing import List
from src.schemas.state import TopicMetadata

async def fetch_hacker_news_top(limit: int = 10) -> List[TopicMetadata]:
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://hacker-news.firebaseio.com/v0/topstories.json")
        story_ids = resp.json()[:limit]
        
        topics = []
        for sid in story_ids:
            item = await client.get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json")
            data = item.json()
            if data and data.get("url"):
                topics.append(TopicMetadata(
                    title=data.get("title", ""),
                    summary=data.get("text", "")[:300] or data.get("title", ""),
                    url=data.get("url", ""),
                    source="Hacker News",
                    score=data.get("score")
                ))
        return topics