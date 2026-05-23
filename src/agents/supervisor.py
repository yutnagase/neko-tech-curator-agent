from langchain_core.messages import HumanMessage
from src.core.llm import get_llm
from src.utils.prompts import SUPERVISOR_PROMPT
import json

async def supervisor_node(state):
    llm = get_llm(temperature=0.1)  # 判断は低温度
    
    num_topics = len(state.get("raw_topics", []))
    num_explanations = len(state.get("explanations", []))
    num_critiques = len(state.get("critiques", []))
    
    prompt = SUPERVISOR_PROMPT.format(
        date=state.get("date"),
        num_topics=num_topics,
        num_explanations=num_explanations,
        last_score=state["critiques"][-1].get("score", 0) if state.get("critiques") else 0
    )
    
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    
    try:
        decision = json.loads(response.content.strip())
        next_step = decision.get("next", "reflect")
        reason = decision.get("reason", "")
    except Exception as e:
        print(f"Supervisor JSONエラー: {e}")
        next_step = "reflect" if num_explanations > 0 else "explain"
        reason = "パース失敗"

    # 強制ルール（無限ループ防止）
    if num_explanations == 0 and num_topics > 0:
        next_step = "explain"
    elif num_explanations > 0 and num_critiques == 0:
        next_step = "reflect"
    elif num_explanations >= 6:
        next_step = "saver"

    print(f"🤖 Supervisor決定 → {next_step} | 理由: {reason[:70]}... | "
          f"解説数: {num_explanations}, 評価数: {num_critiques}")

    return {
        "messages": [{"role": "supervisor", "content": next_step, "reason": reason}],
        "next": next_step   # ← これを追加
    }