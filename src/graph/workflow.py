from langgraph.graph import StateGraph, START, END
from datetime import datetime
from typing import Literal

from src.schemas.state import AgentState
from src.agents.nodes import explainer_node, reflector_node, reviser_node, recommender_node
from src.agents.supervisor import supervisor_node
from src.tools.fetchers import fetch_hacker_news_top
from src.tools.storage import saver_node


async def fetch_node(state: AgentState):
    """Hacker Newsからトピックを取得"""
    topics = await fetch_hacker_news_top(6)  # 必要に応じて数を調整
    return {
        "raw_topics": topics,
        "date": datetime.now().strftime("%Y-%m-%d")
    }


def should_revise(state: AgentState) -> Literal["reviser", "saver"]:
    """Reflect後の分岐判定（シンプル版）"""
    critiques = state.get("critiques", [])
    if not critiques:
        return "saver"
    
    latest_score = critiques[-1].get("score", 0) if isinstance(critiques[-1], dict) else 0
    
    # 猫スコアが低い場合は修正
    if latest_score < 70:   # 閾値は調整可能
        return "reviser"
    else:
        return "saver"


def build_graph():
    workflow = StateGraph(AgentState)
    
    # ノード登録
    workflow.add_node("fetch", fetch_node)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("explain", explainer_node)
    workflow.add_node("reflect", reflector_node)
    workflow.add_node("reviser", reviser_node)
    workflow.add_node("saver", saver_node)
    workflow.add_node("recommender", recommender_node)

    # 開始フロー
    workflow.add_edge(START, "fetch")
    workflow.add_edge("fetch", "supervisor")

    # ==================== Supervisor中心の動的ルーティング ====================
    workflow.add_conditional_edges(
        "supervisor",
        lambda state: state.get("next", "explain"),   # supervisor_nodeが返す "next" を使用
        {
            "research_more": "fetch",
            "explain": "explain",
            "reflect": "reflect",
            "revise": "reviser",      # "revise" と "reviser" の対応
            "saver": "saver",
            "recommender": "recommender",
            "end": END,
        }
    )

    # 各ノード実行後は基本的にSupervisorへ戻す
    workflow.add_edge("explain", "supervisor")
    workflow.add_edge("reviser", "supervisor")

    # reflectだけは品質判定をして分岐（should_revise使用）
    workflow.add_conditional_edges(
        "reflect",
        should_revise,
        {
            "reviser": "reviser",
            "saver": "saver"
        }
    )

    # 保存後はおすすめ生成へ
    workflow.add_edge("saver", "recommender")
    workflow.add_edge("recommender", END)

    return workflow.compile()