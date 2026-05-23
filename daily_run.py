import asyncio
from src.graph.workflow import build_graph

async def main():
    graph = build_graph()
    
    initial_state = {
        "date": "2026-05-22",
        "raw_topics": [],
        "explanations": [],
        "critiques": [],
        "recommendations": []
    }
    
    print("=== 猫でもわかる技術解説エージェント - Daily Run ===")
    result = await graph.ainvoke(initial_state)
    
    print(f"\n✅ 生成された解説数: {len(result.get('explanations', []))}")
    for i, exp in enumerate(result.get('explanations', [])[:2], 1):
        print(f"\n--- 解説 {i} ---")
        print(exp.content[:400] + "..." if len(exp.content) > 400 else exp.content)

if __name__ == "__main__":
    asyncio.run(main())