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
    date: str
    raw_topics: Annotated[List[TopicMetadata], operator.add]
    explanations: Annotated[List[Explanation], operator.add]
    critiques: Annotated[List[dict], operator.add]
    recommendations: List[Explanation]
    
    # Supervisor強化用
    messages: Annotated[List[dict], operator.add]
    revision_count: Annotated[int, operator.add] = 0
    supervisor_instruction: str = ""
    next: str = "explain"
    # 新規追加：ツール呼び出し履歴
    tool_calls: Annotated[List[dict], operator.add] = []