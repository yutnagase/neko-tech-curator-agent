from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from src.core.database import db
from src.graph.workflow import build_graph
from datetime import datetime
import re

# FastAPIアプリケーションの初期化
app = FastAPI(title="猫でもわかる技術解説エージェント")

# Jinja2テンプレート設定（シンプルに）
templates = Jinja2Templates(directory="src/api/templates")

def _format_content(content: str) -> str:
    """解説文を見やすく整形
    
    引数:
        content: str - 元の解説文
    戻り値:
        str - HTML形式で整形された解説文
    説明:
        解説文をHTML形式で整形するユーティリティ関数。
        - **太字** を <strong> に変換
        - 改行を <br> に変換（連続した改行は <p> に）
        - 見出し風の行を強調
    
    """

    # コンテンツが空の場合は空文字を返す
    if not content:
        return ""
    
    # **太字** を <strong> に変換
    content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
    
    # 改行を <br> に変換（連続した改行は <p> に）
    content = content.replace('\n\n', '</p><p>')
    content = content.replace('\n', '<br>')
    
    # 見出し風の行を強調
    content = re.sub(r'^(【.+?】)', r'<strong>\1</strong>', content, flags=re.MULTILINE)
    
    # 最後に全体を<p>で囲む（すでに<p>がある場合はそのまま）
    return f"<p>{content}</p>" if not content.startswith('<p>') else content


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """トップページ - 生成された解説の一覧表示
    
    引数:
        request: Request - FastAPIのリクエストオブジェクト
    戻り値:
        HTMLResponse - 生成された解説の一覧を表示するHTMLページ
    説明:
        トップページのエンドポイント。DBから最新の解説を取得し、Jinja2テンプレートを使用してHTMLページを生成して返す。
        解説の内容はHTML形式で整形され、見やすく表示される。エラーが発生した場合はエラーメッセージを表示する。
    
    """
    try:
        # DBから最新の解説を取得
        rows = list(db.sqlite_db["explanations"].rows_where(
            order_by="-created_at", 
            limit=15
        ))
        
        # 解説の内容をHTML形式で整形してリストに格納
        explanations = []
        for row in rows:
            exp_dict = dict(row)
            exp_dict["formatted_content"] = _format_content(exp_dict.get("content", ""))
            explanations.append(exp_dict)

        # Jinja2テンプレートを使用してHTMLページを生成して返す
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

    # エラーが発生した場合はエラーメッセージを表示
    except Exception as e:
        print(f"Error in index: {e}")
        return HTMLResponse(f"<h1>エラーが発生しました: {e}</h1>", status_code=500)

@app.post("/run_daily")
async def run_daily():
    """日次実行エンドポイント - ワークフローの実行と結果の返却
    
    引数: なし
    戻り値:
        dict - ワークフローの実行結果を含む辞書型のオブジェクト
    説明:
        日次実行のエンドポイント。LangGraphのワークフローを構築し、初期状態を定義して非同期に実行する。
        ワークフローの実行結果に基づいて、生成された解説の数や成功・失敗のステータスを含む辞書型のオブジェクトを返す。

    """

    try:
        # LangGraphのワークフローを構築して実行
        graph = build_graph()
        # ワークフローの初期状態を定義
        initial_state = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "raw_topics": [],
            "explanations": [],
            "critiques": [],
            "recommendations": []
        }
        # ワークフローを非同期に実行
        result = await graph.ainvoke(initial_state)
        
        # ワークフローの実行結果に基づいて、生成された解説の数や成功・失敗のステータスを含む辞書型のオブジェクトを返す
        return {
            "status": "success", 
            "count": len(result.get("explanations", [])),
            "message": f"{len(result.get('explanations', []))}件生成・保存しました！"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}