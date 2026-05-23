import asyncio
from src.graph.workflow import build_graph
from datetime import datetime

async def main():
    graph = build_graph()
    
    initial_state = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "raw_topics": [],
        "explanations": [],
        "critiques": [],
        "recommendations": []
    }
    
    print("=== 猫でもわかる技術解説エージェント - Daily Run ===")
    print("🚀 処理開始...\n")
    
    result = await graph.ainvoke(initial_state)
    
    print(f"\n✅ 完了！ 生成・保存された解説数: {len(result.get('explanations', []))}")

if __name__ == "__main__":
    asyncio.run(main())