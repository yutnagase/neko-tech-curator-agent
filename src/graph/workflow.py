from langgraph.graph import StateGraph, START, END
from datetime import datetime
from typing import Literal

from src.schemas.state import AgentState
from src.agents.nodes import explainer_node, reflector_node, reviser_node, recommender_node
from src.agents.supervisor import supervisor_node
from src.tools.fetchers import fetch_hacker_news_top
from src.tools.storage import saver_node


async def _fetch_node(state: AgentState):
    """ニュース取得ノード（プライベート関数）

    引数:
        state: AgentState - ワークフローの状態を表すオブジェクト
    戻り値: 
        dict - 取得したニュースと実行日時を含む辞書
    説明:
        Hacker NewsのAPIから最新技術ニュースを非同期で取得するノード。
        このモジュール内でのみ使用されるプライベート関数。
    """
    topics = await fetch_hacker_news_top(6)  # 必要に応じて数を調整

    print(f"Fetch完了: {len(topics)}件のニュースを取得 | 日付: {datetime.now().strftime('%Y-%m-%d')}")
    
    # 取得したニュースと実行日時を返す
    return {
        "raw_topics": topics,
        "date": datetime.now().strftime("%Y-%m-%d")
    }


def _should_revise(state: AgentState) -> Literal["reviser", "saver"]:
    """品質判定ノード - Reflect後の分岐判定（プライベート関数）

    引数:
        state: AgentState - ワークフローの状態を表すオブジェクト
    戻り値:
        Literal["reviser", "saver"] - 次のノードを示す文字列
    説明:
        Reflectノードで生成された自己批評の内容に基づいて、解説の品質が十分でないと判断された場合は"reviser"を返し、
        品質が良好と判断された場合は"saver"を返すシンプルな品質判定ノード。
        このモジュール内でのみ使用されるプライベート関数。
    
    """

    # 異常系の防御
    # ワークフローのstate(状態)から自己批評のリスト(critiques)を確認し、存在しない場合はsaver(保存)とする
    critiques = state.get("critiques", [])
    if not critiques:
        return "saver"
    
    # 最新の自己批評のスコアを取得（スコアがない場合は0とみなす）
    latest_score = critiques[-1].get("score", 0) if isinstance(critiques[-1], dict) else 0
    
    print(f"品質判定: 最新の自己批評スコア = {latest_score} | 判定結果 = {'reviser' if latest_score <= 70 else 'saver'}")  # スコアと判定結果をログに出力

    # スコアが低い場合は修正
    if latest_score < 3:   # scoreは1-5の範囲、閾値は調整可能
        return "reviser"
    else:
        return "saver"


def build_graph():
    """LangGraphのワークフロー構築

    引数: なし
    戻り値:
        StateGraph - 構築されたワークフローの状態グラフオブジェクト
    説明:
        LangGraphのStateGraphを使用して、猫でもわかる技術解説エージェントのワークフローを構築する関数
        
    """

    # 状態グラフの初期化
    workflow = StateGraph(AgentState)
    
    # ノード登録（7つのエージェント/処理）
    workflow.add_node("fetch", _fetch_node)  # ニュース取得ノード
    workflow.add_node("supervisor", supervisor_node)    # Supervisorノード
    workflow.add_node("explain", explainer_node)    # 解説生成ノード
    workflow.add_node("reflect", reflector_node)    # 自己批評ノード
    workflow.add_node("reviser", reviser_node)  # 解説修正ノード
    workflow.add_node("saver", saver_node)  # 解説保存ノード
    workflow.add_node("recommender", recommender_node)  # おすすめ生成ノード

    # エッジ（接続）の定義
    workflow.add_edge(START, "fetch")   # ワークフロー開始はニュース取得から
    workflow.add_edge("fetch", "supervisor")    # ニュース取得後はSupervisorへ

    # 条件付き分岐（動的ルーティング）
    # Supervisorノードの出力に基づいて、次のノードを動的に選択する
    # state から "next" キーの値を取得し、存在しない場合は "explain" をデフォルトとする
    # "next" の値に応じて、対応するノードへルーティングする
    workflow.add_conditional_edges(
        "supervisor",   # supervisorを条件分岐の起点とする
        lambda state: state.get("next", "explain"),   # 分岐判定関数()
        {
            "research_more": "fetch",      # "research_more(追加調査必要時)" → fetch(ニュース取得) ノードへ
            "explain": "explain",          # "explain(新しい解説生成)" → explain(解説生成) ノードへ
            "reflect": "reflect",          # "reflect(自己批評)" → reflect(自己批評) ノードへ
            "revise": "reviser",           # "revise(解説修正)" → reviser(解説修正) ノードへ
            "saver": "saver",              # "saver(保存)" → saver(保存) ノードへ
            "recommender": "recommender",  # "recommender(おすすめ生成)" → recommender(おすすめ生成) ノードへ
            "end": END,                    # "end(終了)" → ワークフロー終了
        }
    )

    # explain(解説生成) 、reviser(解説修正) ノード実行後は修正ループの可能性が有るので、Supervisorへ戻しておく
    workflow.add_edge("explain", "supervisor")
    workflow.add_edge("reviser", "supervisor")

    # reflectだけは品質判定をして分岐（_should_revise使用）
    workflow.add_conditional_edges(
        "reflect",
        _should_revise,
        {
            "reviser": "reviser",
            "saver": "saver"
        }
    )

    # 保存後はおすすめ生成へ
    workflow.add_edge("saver", "recommender")
    workflow.add_edge("recommender", END)

    return workflow.compile()