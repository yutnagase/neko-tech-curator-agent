from langchain_core.messages import SystemMessage, HumanMessage
from src.core.llm import get_llm
from src.utils.prompts import DAILY_EXPLAINER_PROMPT
from src.schemas.state import AgentState, Explanation

async def explainer_node(state: AgentState) -> AgentState:
    llm = get_llm(temperature=0.65)   # 少し創造性を残しつつ
    new_explanations = []
    
    for topic in state["raw_topics"]:
        # プロンプトにurlも渡す
        prompt_text = DAILY_EXPLAINER_PROMPT.format(
            title=topic.title,
            summary=topic.summary or "詳細はリンク先を参照",
            url=topic.url
        )
        
        response = await llm.ainvoke([HumanMessage(content=prompt_text)])
        
        new_explanations.append(Explanation(
            topic=topic,
            content=response.content.strip()
        ))
    
    return {"explanations": new_explanations}