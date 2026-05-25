from typing import TypedDict, Annotated, List
import operator
from pydantic import BaseModel

class TopicMetadata(BaseModel):
    title: str
    summary: str
    url: str
    source: str
    score: int | None = None

class Explanation(BaseModel):
    topic: TopicMetadata
    content: str
    cat_score: int = 0

class AgentState(TypedDict):
    """ワークフローの状態を表す型定義
    
    引数: 
        TypedDict - ワークフローの状態を表す辞書型の定義
    戻り値: 
        なし
    説明: 
        ワークフローの状態を表すための型定義。ワークフローの各ノードで必要な情報を保持するための項目を定義している。
        これにより、ワークフローの状態管理が容易になる

    """

    # ワークフローの状態を表す基本項目
    date: str   # ワークフローの実行日時
    raw_topics: Annotated[List[TopicMetadata], operator.add]    # 取得した技術ニュースのリスト
    explanations: Annotated[List[Explanation], operator.add]    # 生成された解説のリスト
    critiques: Annotated[List[dict], operator.add]  # 生成された自己批評のリスト（例: {"topic_title": str, "score": int, "comment": str}）  
    recommendations: List[Explanation]  # 次回の改善提案（解説形式で保存）
    
    # Supervisor強化用
    messages: Annotated[List[dict], operator.add]   # Supervisorとの対話履歴（例: {"role": "supervisor" or "agent", "content": str}）   
    revision_count: Annotated[int, operator.add] = 0    # 解説の修正回数
    supervisor_instruction: str = ""    # Supervisorからの最新の指示内容
    next: str = "explain"   # 次のノードを示す文字列（例: "explain", "reflect", "reviser", "saver"など）