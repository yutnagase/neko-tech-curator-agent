from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from src.core.database import db
from src.graph.workflow import build_graph
from datetime import datetime

app = FastAPI(title="猫でもわかる技術解説エージェント")

# Jinja2テンプレート設定（シンプルに）
templates = Jinja2Templates(directory="src/api/templates")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    try:
        # DBから最新の解説を取得
        rows = list(db.sqlite_db["explanations"].rows_where(
            order_by="-created_at", 
            limit=15
        ))
        
        # 確実にPythonのdictに変換
        explanations = [dict(row) for row in rows]


        return templates.TemplateResponse(
            request=request,                    # requestをキーワード引数で渡す
            name="index.html",                  # テンプレート名を明示
            context={                           # 渡したいデータを辞書でまとめる
                "explanations": explanations,
                "title": "猫でもわかる技術解説エージェント",
                "current_date": datetime.now().strftime("%Y年%m月%d日"),
                "count": len(explanations)
            }
        )



    except Exception as e:
        print(f"Error in index: {e}")
        return HTMLResponse(f"<h1>エラーが発生しました: {e}</h1>", status_code=500)

@app.post("/run_daily")
async def run_daily():
    try:
        graph = build_graph()
        initial_state = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "raw_topics": [],
            "explanations": [],
            "critiques": [],
            "recommendations": []
        }
        result = await graph.ainvoke(initial_state)
        
        return {
            "status": "success", 
            "count": len(result.get("explanations", [])),
            "message": f"✅ {len(result.get('explanations', []))}件生成・保存しました！"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}