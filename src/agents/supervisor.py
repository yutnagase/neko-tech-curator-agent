from langchain_core.messages import HumanMessage
from src.core.llm import get_llm
from src.utils.prompts import SUPERVISOR_PROMPT
import json

async def supervisor_node(state):
    llm = get_llm(temperature=0.1)
    
    num_topics = len(state.get("raw_topics", []))
    num_explanations = len(state.get("explanations", []))
    num_critiques = len(state.get("critiques", []))
    revision_count = state.get("revision_count", 0)
    
    # より豊富なコンテキスト
    prompt = SUPERVISOR_PROMPT.format(
        date=state.get("date", "不明"),
        num_topics=num_topics,
        num_explanations=num_explanations,
        num_critiques=num_critiques,
        revision_count=revision_count,
        last_score=state["critiques"][-1].get("score", 0) if state.get("critiques") else 0
    )
    
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    
    try:
        decision = json.loads(response.content.strip())
        next_step = decision.get("next", "explain")
        reason = decision.get("reason", "")
        instruction = decision.get("instruction", "")
        tool_call = decision.get("tool_call", None)
    except Exception as e:
        print(f"Supervisor JSONエラー: {e}")
        next_step = "explain"
        reason = "パース失敗"
        instruction = ""
        tool_call = None

    # 強制ルール（安全策）
    if num_explanations == 0 and num_topics > 0:
        next_step = "explain"
        instruction = "新しいトピックについて分かりやすい解説を生成してください"
    elif num_explanations >= 6 and num_critiques == 0:
        next_step = "reflect"
        instruction = "生成された解説の品質を厳しく評価せよ。特に正確性を重視せよ。"
    elif revision_count >= 2:
        next_step = "saver"

    print(f"🤖 Supervisor決定 → {next_step} | 理由: {reason[:80]}... | "
          f"解説:{num_explanations} 評価:{num_critiques} 修正:{revision_count}")

    return {
        "messages": [{"role": "supervisor", "content": next_step, "reason": reason}],
        "next": next_step,
        "supervisor_instruction": instruction,
        "tool_calls": [{"tool": tool_call, "step": next_step}] if tool_call else []
    }