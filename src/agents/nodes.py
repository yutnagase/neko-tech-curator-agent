from langchain_core.messages import HumanMessage
from src.core.llm import get_llm
from src.utils.prompts import DAILY_EXPLAINER_PROMPT, REFLECTION_PROMPT
from src.schemas.state import AgentState, Explanation
import json

async def explainer_node(state: AgentState) -> AgentState:
    llm = get_llm(temperature=0.7)
    new_explanations = []
    
    for topic in state["raw_topics"]:
        prompt_text = DAILY_EXPLAINER_PROMPT.format(
            title=topic.title,
            summary=topic.summary or "",
            url=topic.url
        )
        response = await llm.ainvoke([HumanMessage(content=prompt_text)])
        
        new_explanations.append(Explanation(
            topic=topic,
            content=response.content.strip()
        ))
    
    return {"explanations": new_explanations}


async def reflector_node(state: AgentState) -> AgentState:
    llm = get_llm(temperature=0.0)   # 評価は正確に
    critiques = []
    
    for exp in state["explanations"]:
        prompt = REFLECTION_PROMPT.format(content=exp.content)
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        
        try:
            critique = json.loads(response.content)
        except:
            critique = {"score": 3, "strengths": "", "weaknesses": "JSONパース失敗", "suggestion": ""}
        
        critiques.append(critique)
    
    return {"critiques": critiques}


def should_revise(state: AgentState) -> str:
    """Reflection後の条件分岐"""
    if not state.get("critiques"):
        return "saver"
    
    last_critique = state["critiques"][-1]
    if last_critique.get("score", 0) <= 3:
        return "reviser"
    return "saver"