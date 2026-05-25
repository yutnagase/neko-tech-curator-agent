import asyncio
from src.graph.workflow import build_graph
from datetime import datetime

async def main():
    # LangGraphのワークフローを構築
    graph = build_graph()
    
    # ワークフローの初期状態を定義
    initial_state = {
        # 実行日時の設定
        "date": datetime.now().strftime("%Y-%m-%d"),
        # 取得した技術ニュース
        "raw_topics": [],
        # 生成された解説、批評、提案を格納するためのリスト
        "explanations": [],
        # 自己批評
        "critiques": [],
        # 次回の改善提案
        "recommendations": []
    }
    
    print("=== 猫でもわかる技術解説エージェント - Daily Run ===")
    print("処理開始...\n")
    
    # ワークフローを非同期に実行
    result = await graph.ainvoke(initial_state)
    
    print(f"\n完了！ 生成・保存された解説数: {len(result.get('explanations', []))}")

if __name__ == "__main__":
    asyncio.run(main())