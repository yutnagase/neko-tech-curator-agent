from langgraph.graph import StateGraph, START, END
from datetime import datetime
from src.schemas.state import AgentState
from src.agents.nodes import explainer_node, reflector_node, reviser_node, recommender_node
from src.agents.supervisor import supervisor_node
from src.tools.fetchers import fetch_hacker_news_top
from src.tools.storage import saver_node

async def fetch_node(state: AgentState):
    topics = await fetch_hacker_news_top(6)
    return {
        "raw_topics": topics,
        "date": datetime.now().strftime("%Y-%m-%d")
    }

def build_graph():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("fetch", fetch_node)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("explain", explainer_node)
    workflow.add_node("reflect", reflector_node)
    workflow.add_node("reviser", reviser_node)
    workflow.add_node("saver", saver_node)
    workflow.add_node("recommender", recommender_node)

    workflow.add_edge(START, "fetch")
    workflow.add_edge("fetch", "supervisor")

    # Supervisorによる動的ルーティング（これが核心）
    workflow.add_conditional_edges(
        "supervisor",
        lambda s: s.get("next", "explain"),
        {
            "research_more": "fetch",
            "explain": "explain",
            "reflect": "reflect",
            "revise": "reviser",
            "saver": "saver",
            "recommender": "recommender",
            "end": END,
        }
    )

    # 各ノード実行後は必ずSupervisorに戻す（中央集権化）
    workflow.add_edge("explain", "supervisor")
    workflow.add_edge("reflect", "supervisor")
    workflow.add_edge("reviser", "supervisor")
    
    workflow.add_edge("saver", "recommender")
    workflow.add_edge("recommender", END)

    return workflow.compile()