from src.core.database import db
from src.schemas.state import Explanation, AgentState
from datetime import datetime

async def saver_node(state: AgentState) -> AgentState:
    """解説をDBに保存するTool Node"""
    saved_count = 0
    for exp in state.get("explanations", []):
        await db.save_explanation(exp, state.get("date", datetime.now().strftime("%Y-%m-%d")))
        saved_count += 1
    
    print(f"Saver完了: {saved_count}件保存")
    
    return {"explanations": state.get("explanations", [])}  # 状態は維持