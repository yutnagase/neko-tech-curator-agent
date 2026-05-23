from langgraph.graph import StateGraph, START, END
from src.schemas.state import AgentState
from src.agents.nodes import explainer_node
from src.tools.fetchers import fetch_hacker_news_top

async def fetch_node(state: AgentState):
    topics = await fetch_hacker_news_top(10)
    return {"raw_topics": topics}

def build_graph():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("fetch", fetch_node)
    workflow.add_node("explain", explainer_node)
    
    workflow.add_edge(START, "fetch")
    workflow.add_edge("fetch", "explain")
    workflow.add_edge("explain", END)
    
    return workflow.compile()