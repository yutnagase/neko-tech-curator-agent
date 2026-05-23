import lancedb
import sqlite_utils
from datetime import datetime
from src.config.settings import settings
from src.schemas.state import Explanation

class Database:
    def __init__(self):
        self.sqlite_db = sqlite_utils.Database(settings.DB_PATH)
        self.vector_db = lancedb.connect(settings.VECTOR_DB_PATH)
        
        # SQLiteテーブル作成
        self.sqlite_db["explanations"].create({
            "id": str,
            "date": str,
            "title": str,
            "content": str,
            "url": str,
            "source": str,
            "created_at": str,
        }, if_not_exists=True)
        
        # LanceDBテーブル（ベクトル検索用）
        if "explanations" not in self.vector_db.table_names():
            self.vector_db.create_table("explanations", data=[{
                "id": "init",
                "title": "",
                "content": "",
                "embedding": [0.0] * 384  # 簡易embedding次元
            }])

    async def save_explanation(self, explanation: Explanation, date: str):
        exp_id = f"{date}_{hash(explanation.topic.title)}"
        
        # SQLiteに保存
        self.sqlite_db["explanations"].insert({
            "id": exp_id,
            "date": date,
            "title": explanation.topic.title,
            "content": explanation.content,
            "url": explanation.topic.url,
            "source": explanation.topic.source,
            "created_at": datetime.now().isoformat()
        })
        
        print(f"💾 保存完了: {explanation.topic.title[:60]}...")
        return exp_id

db = Database()