from langgraph.graph import StateGraph, START, END
from src.schemas.state import AgentState
from src.agents.nodes import explainer_node, reflector_node
from src.tools.fetchers import fetch_hacker_news_top

async def fetch_node(state: AgentState):
    topics = await fetch_hacker_news_top(8)   # 3Bモデルなので少し減らす
    return {"raw_topics": topics}

def build_graph():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("fetch", fetch_node)
    workflow.add_node("explain", explainer_node)
    workflow.add_node("reflect", reflector_node)
    # 将来: reviser, saver ノードも追加予定

    workflow.add_edge(START, "fetch")
    workflow.add_edge("fetch", "explain")
    workflow.add_edge("explain", "reflect")
    workflow.add_edge("reflect", END)   # ひとまずここで終了

    return workflow.compile()