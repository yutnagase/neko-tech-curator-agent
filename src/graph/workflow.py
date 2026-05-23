from langgraph.graph import StateGraph, START, END
from datetime import datetime
from src.schemas.state import AgentState
from src.agents.nodes import explainer_node, reflector_node, reviser_node
from src.tools.fetchers import fetch_hacker_news_top
from src.tools.storage import saver_node

async def fetch_node(state: AgentState):
    topics = await fetch_hacker_news_top(6)
    return {
        "raw_topics": topics, 
        "date": datetime.now().strftime("%Y-%m-%d")
    }

def should_revise(state: AgentState) -> str:
    """Reflection後の条件分岐"""
    if not state.get("critiques"):
        return "saver"
    
    last_critique = state["critiques"][-1]
    score = last_critique.get("score", 0)
    
    if score <= 3:
        return "reviser"
    return "saver"

def build_graph():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("fetch", fetch_node)
    workflow.add_node("explain", explainer_node)
    workflow.add_node("reflect", reflector_node)
    workflow.add_node("reviser", reviser_node)
    workflow.add_node("saver", saver_node)

    workflow.add_edge(START, "fetch")
    workflow.add_edge("fetch", "explain")
    workflow.add_edge("explain", "reflect")
    
    # 条件分岐（正しい書き方）
    workflow.add_conditional_edges(
        "reflect",
        should_revise,
        {
            "reviser": "reviser",
            "saver": "saver"
        }
    )
    
    workflow.add_edge("reviser", "reflect")
    workflow.add_edge("saver", END)

    return workflow.compile()