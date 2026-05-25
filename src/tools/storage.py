from src.core.database import db
from src.schemas.state import Explanation, AgentState
from datetime import datetime

async def saver_node(state: AgentState) -> AgentState:
    """解説をDBに保存するTool Node"""
    saved_count = 0
    for exp in state.get("explanations", []):
        print(f"Saving解説: {exp.topic[:30]}... | 日付: {state.get('date', '不明')}")
        print(f"解説内容: {exp.content[:100]}...")  # 解説内容の一部をログに出力
        await db.save_explanation(exp, state.get("date", datetime.now().strftime("%Y-%m-%d")))
        saved_count += 1
    
    print(f"Saver完了: {saved_count}件保存")
    
    return {"explanations": state.get("explanations", [])}  # 状態は維持