from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from src.core.database import db
from src.graph.workflow import build_graph
from datetime import datetime
import re

app = FastAPI(title="猫でもわかる技術解説エージェント")

# Jinja2テンプレート設定（シンプルに）
templates = Jinja2Templates(directory="src/api/templates")

def format_content(content: str) -> str:
    """解説文を見やすく整形"""
    if not content:
        return ""
    
    # **太字** を <strong> に変換
    content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
    
    # 改行を <br> に変換（連続した改行は <p> に）
    content = content.replace('\n\n', '</p><p>')
    content = content.replace('\n', '<br>')
    
    # 見出し風の行を強調
    content = re.sub(r'^(【.+?】)', r'<strong>\1</strong>', content, flags=re.MULTILINE)
    
    return f"<p>{content}</p>" if not content.startswith('<p>') else content

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    try:
        # DBから最新の解説を取得
        rows = list(db.sqlite_db["explanations"].rows_where(
            order_by="-created_at", 
            limit=15
        ))
        
        # 確実にPythonのdictに変換
        explanations = []
        for row in rows:
            exp_dict = dict(row)
            exp_dict["formatted_content"] = format_content(exp_dict.get("content", ""))
            explanations.append(exp_dict)


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