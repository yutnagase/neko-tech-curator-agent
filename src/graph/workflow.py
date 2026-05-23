from langgraph.graph import StateGraph, START, END
from langgraph.graph import add_conditional_edges
from src.schemas.state import AgentState
from src.agents.nodes import (
    explainer_node, 
    reflector_node, 
    reviser_node
)
from src.tools.fetchers import fetch_hacker_news_top

async def fetch_node(state: AgentState):
    # 3Bモデルなので負荷を抑える
    topics = await fetch_hacker_news_top(6)
    return {"raw_topics": topics}

def build_graph():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("fetch", fetch_node)
    workflow.add_node("explain", explainer_node)
    workflow.add_node("reflect", reflector_node)
    workflow.add_node("reviser", reviser_node)
    # saverは次Phaseで追加

    workflow.add_edge(START, "fetch")
    workflow.add_edge("fetch", "explain")
    workflow.add_edge("explain", "reflect")
    
    # 条件分岐：低評価ならreviserへ、高評価ならsaverへ
    workflow.add_conditional_edges(
        "reflect",
        should_revise,
        {
            "reviser": "reviser",
            "saver": END   # 現在はsaver未実装なので一旦END
        }
    )
    
    # Reviser → Reflectへ戻す（ループ）
    workflow.add_edge("reviser", "reflect")

    return workflow.compile()