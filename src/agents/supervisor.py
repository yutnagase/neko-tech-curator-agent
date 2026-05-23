from langchain_core.messages import HumanMessage
from src.core.llm import get_llm
from src.utils.prompts import SUPERVISOR_PROMPT
import json

async def supervisor_node(state):
    llm = get_llm(temperature=0.3)
    
    last_score = state["critiques"][-1].get("score", 0) if state.get("critiques") else 0
    
    prompt = SUPERVISOR_PROMPT.format(
        date=state.get("date"),
        num_topics=len(state.get("raw_topics", [])),
        num_explanations=len(state.get("explanations", [])),
        last_score=last_score
    )
    
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    
    try:
        decision = json.loads(response.content)
        next_step = decision.get("next", "saver")
    except:
        next_step = "saver"
    
    print(f"🤖 Supervisor判断: {next_step}")
    return {"messages": [{"role": "supervisor", "content": next_step}]}
