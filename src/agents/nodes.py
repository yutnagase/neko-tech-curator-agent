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
    llm = get_llm(temperature=0.7)
    new_explanations = []
    
    for topic in state.get("raw_topics", []):
        prompt_text = DAILY_EXPLAINER_PROMPT.format(
            title=topic.title,
            summary=topic.summary or "詳細はリンクを参照してください。",
            url=topic.url
        )
        response = await llm.ainvoke([HumanMessage(content=prompt_text)])
        
        new_explanations.append(Explanation(
            topic=topic,
            content=response.content.strip()
        ))
    
    return {"explanations": new_explanations}


async def reflector_node(state: AgentState) -> AgentState:
    llm = get_llm(temperature=0.0)
    critiques = []
    
    for exp in state.get("explanations", []):
        prompt = REFLECTION_PROMPT.format(content=exp.content)
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
    
    return {"critiques": critiques}


async def reviser_node(state: AgentState) -> AgentState:
    llm = get_llm(temperature=0.65)
    revised_explanations = []
    
    # 最後の解説と最後のcritiqueを対応させる（簡易版）
    explanations = state.get("explanations", [])
    critiques = state.get("critiques", [])
    
    for i, exp in enumerate(explanations):
        critique = critiques[i] if i < len(critiques) else {}
        suggestion = critique.get("suggestion", "よりわかりやすくしてください。")
        
        prompt = REVISER_PROMPT.format(
            content=exp.content,
            suggestion=suggestion
        )
        
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        
        revised_explanations.append(Explanation(
            topic=exp.topic,
            content=response.content.strip()
        ))
    
    # 修正版で上書き
    return {"explanations": revised_explanations}


def should_revise(state: AgentState) -> str:
    """Reflection後の条件分岐"""
    if not state.get("critiques"):
        return "saver"
    
    # 最後のcritiqueをチェック
    last_critique = state["critiques"][-1]
    score = last_critique.get("score", 0)
    
    # 3点以下なら修正ループへ（最大2回程度にしたい場合は後で制限追加）
    if score <= 3:
        return "reviser"
    return "saver"

async def recommender_node(state: AgentState) -> AgentState:
    llm = get_llm(temperature=0.7)
    recommendations = []
    
    # 簡易版（将来的にユーザー履歴を反映）
    prompt = RECOMMENDER_PROMPT
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    
    recommendations.append({
        "title": "今日のおすすめネタ",
        "content": response.content.strip()
    })
    
    print("📌 Recommender完了")
    return {"recommendations": recommendations}