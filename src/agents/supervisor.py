from langchain_core.messages import HumanMessage
from src.core.llm import get_llm
from src.utils.prompts import SUPERVISOR_SYSTEM_PROMPT
import json
from typing import Literal

SupervisorDecision = Literal["research_more", "explain", "reflect", "revise", "saver", "recommender", "end"]

async def supervisor_node(state):
    llm = get_llm(temperature=0.1)  # 判断は低温度で安定させる
    
    context = {
        "date": state.get("date", "不明"),
        "raw_topics_count": len(state.get("raw_topics", [])),
        "explanations_count": len(state.get("explanations", [])),
        "revision_count": state.get("revision_count", 0),
        "max_revision": 2,
        "last_critiques": state.get("critiques", [])[-2:] if state.get("critiques") else [],
    }
    
    prompt = SUPERVISOR_SYSTEM_PROMPT.format(**context)
    
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    
    try:
        decision = json.loads(response.content.strip())
        next_step = decision.get("next", "saver")
        reason = decision.get("reason", "判断できませんでした")
        instruction = decision.get("instruction", "")
    except Exception as e:
        print(f"Supervisor JSONパース失敗: {e}")
        next_step = "saver"
        reason = "JSONパースエラー"
        instruction = ""
    
    print(f"🤖 Supervisor決定 → {next_step} | 理由: {reason[:60]}...")
    
    return {
        "messages": [{"role": "supervisor", "content": next_step, "reason": reason}],
        "next": next_step,
        "supervisor_instruction": instruction,
        "revision_count": 1 if next_step == "revise" else 0   # 修正時はカウントアップ
    }