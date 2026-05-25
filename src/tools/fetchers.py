import feedparser
import httpx
from typing import List
from src.schemas.state import TopicMetadata

async def fetch_hacker_news_top(limit: int = 10) -> List[TopicMetadata]:
    """Hacker Newsのトップストーリーを非同期で取得する関数
    
    引数:
        limit (int): 取得するトップストーリーの数（デフォルトは10）
    戻り値:
        List[TopicMetadata]: 取得したストーリーのリスト。各ストーリーはTopicMetadataオブジェクトとして表される。
    説明:
        Hacker NewsのAPIを使用して、最新のトップストーリーを非同期で取得する関数。
        取得したストーリーは、タイトル、要約（テキストの最初の300文字）、URL、ソース（Hacker News）、スコアを含むTopicMetadataオブジェクトのリストとして返される。
    
    """

    # Hacker NewsのAPIエンドポイントからデータを取得
    async with httpx.AsyncClient() as client:
        # APIからトップストーリーのIDを取得
        resp = await client.get("https://hacker-news.firebaseio.com/v0/topstories.json")
        # APIからのレスポンスをJSONとしてパースし、トップストーリーのIDをリストとして取得
        story_ids = resp.json()[:limit]
        
        # topicsを格納するリストを初期化
        topics = []

        # 各ストーリーIDに対して、ストーリーの詳細情報をAPIから取得し、TopicMetadataオブジェクトを作成してリストに追加
        for sid in story_ids:
            # APIからストーリーの詳細情報を取得
            item = await client.get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json")
            data = item.json()

            # データが存在し、URLがある場合にのみTopicMetadataオブジェクトを作成してリストに追加
            if data and data.get("url"):
                topics.append(TopicMetadata(
                    title=data.get("title", ""),
                    summary=data.get("text", "")[:300] or data.get("title", ""),
                    url=data.get("url", ""),
                    source="Hacker News",
                    score=data.get("score")
                ))
        return topics