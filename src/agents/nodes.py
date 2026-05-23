from langchain_core.messages import HumanMessage
from src.core.llm import get_llm
from src.utils.prompts import (
    DAILY_EXPLAINER_PROMPT, 
    REFLECTION_PROMPT, 
    REVISER_PROMPT,
    RECOMMENDER_PROMPT  
)
from src.schemas.state import AgentState, Explanation

import json

async def explainer_node(state: AgentState) -> AgentState:
    """解説生成ノード - Supervisorの指示を反映"""
    instruction = state.get("supervisor_instruction", "")
    extra_instruction = f"\n\n【Supervisor特別指示】{instruction}" if instruction else ""
    
    llm = get_llm(temperature=0.7)
    new_explanations = []
    
    for topic in state.get("raw_topics", []):
        prompt_text = DAILY_EXPLAINER_PROMPT.format(
            title=topic.title,
            summary=topic.summary or "詳細はリンクを参照してください。",
            url=topic.url
        ) + extra_instruction   # ← Supervisor指示を追加
        
        response = await llm.ainvoke([HumanMessage(content=prompt_text)])
        
        new_explanations.append(Explanation(
            topic=topic,
            content=response.content.strip()
        ))
    
    print(f"✅ Explainer完了: {len(new_explanations)}件生成 | Supervisor指示: {instruction[:50] if instruction else 'なし'}")
    return {"explanations": new_explanations}


async def reflector_node(state: AgentState) -> AgentState:
    """品質評価ノード - Supervisorの指示を反映"""
    instruction = state.get("supervisor_instruction", "")
    extra_instruction = f"\n\n【Supervisor特別指示】{instruction}" if instruction else ""
    
    llm = get_llm(temperature=0.0)
    critiques = []
    
    for exp in state.get("explanations", []):
        prompt = REFLECTION_PROMPT.format(content=exp.content) + extra_instruction
        
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        
        try:
            critique = json.loads(response.content)
        except:
            critique = {
                "score": 3, 
                "strengths": "形式は守れている", 
                "weaknesses": "改善の余地あり", 
                "suggestion": "もう少し猫らしい例えを入れてください。"
            }
        critiques.append(critique)
    
    print(f"✅ Reflector完了: {len(critiques)}件評価 | Supervisor指示: {instruction[:50] if instruction else 'なし'}")
    return {"critiques": critiques}


async def reviser_node(state: AgentState) -> AgentState:
    """修正ノード - Supervisorの指示を反映"""
    instruction = state.get("supervisor_instruction", "")
    extra_instruction = f"\n\n【Supervisor特別指示】{instruction}" if instruction else ""
    
    llm = get_llm(temperature=0.65)
    revised_explanations = []
    
    explanations = state.get("explanations", [])
    critiques = state.get("critiques", [])
    
    for i, exp in enumerate(explanations):
        critique = critiques[i] if i < len(critiques) else {}
        suggestion = critique.get("suggestion", "よりわかりやすく、猫らしくしてください。")
        
        prompt = REVISER_PROMPT.format(
            content=exp.content,
            suggestion=suggestion
        ) + extra_instruction
        
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        
        revised_explanations.append(Explanation(
            topic=exp.topic,
            content=response.content.strip()
        ))
    
    print(f"✅ Reviser完了: {len(revised_explanations)}件修正")
    return {"explanations": revised_explanations}


def should_revise(state: AgentState) -> str:
    """Reflection後の条件分岐"""
    if not state.get("critiques"):
        return "saver"
    
    # 最後のcritiqueをチェック
    last_critique = state["critiques"][-1]
    score = last_critique.get("score", 0) if isinstance(last_critique, dict) else 0
    
    # スコアが低い場合は修正（閾値は調整可能）
    if score <= 3:
        return "reviser"
    return "saver"


async def recommender_node(state: AgentState) -> AgentState:
    """おすすめ生成ノード"""
    instruction = state.get("supervisor_instruction", "")
    extra_instruction = f"\n\n【Supervisor特別指示】{instruction}" if instruction else ""
    
    llm = get_llm(temperature=0.7)
    recommendations = []
    
    prompt = RECOMMENDER_PROMPT + extra_instruction
    
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    
    recommendations.append({
        "title": "今日のおすすめネタ",
        "content": response.content.strip()
    })
    
    print("📌 Recommender完了")
    return {"recommendations": recommendations}