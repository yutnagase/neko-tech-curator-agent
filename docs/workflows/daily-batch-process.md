# 日次バッチ処理の流れ（LangGraph ワークフロー）

本ドキュメントは、`daily_run.py` と `src/graph/workflow.py` で実装されたLangGraphベースの日次バッチ処理パイプラインの詳細を記載しています。

---

## 📋 目次

1. [アーキテクチャ概要](#アーキテクチャ概要)
2. [ファイル構成](#ファイル構成)
3. [LangGraphとは](#langgraphとは)
4. [ワークフロー全体フロー](#ワークフロー全体フロー)
5. [ノード（Node）詳細](#ノード詳細)
6. [状態管理（AgentState）](#状態管理agenstate)
7. [Supervisor Agent](#supervisor-agent)
8. [条件付き分岐（Conditional Edges）](#条件付き分岐conditional-edges)
9. [実行フロー例](#実行フロー例)
10. [実装詳細](#実装詳細)
11. [実行時間と性能](#実行時間と性能)
12. [トラブルシューティング](#トラブルシューティング)

---

## アーキテクチャ概要

このプロジェクトは **LangGraph** を活用した **Supervisor Agent パターン** を採用しています。

### 主な特徴

| 特徴 | 説明 |
|------|------|
| **フレームワーク** | LangGraph（LangChainエコシステム） |
| **パターン** | Supervisor Agent + Reflection Loop |
| **実行方式** | 非同期処理（async/await） |
| **状態管理** | TypedDict + Annotated型による統一状態オブジェクト |
| **LLM** | ローカルLLM（Llama-3.2-3B, Qwen2.5など、GGUF形式） |
| **特色** | 品質自動判定 + 低品質時の自動修正 |

---

## ファイル構成

### 関連するPythonファイル

```
neko-tech-curator-agent/
├── daily_run.py                          # 【入口】日次実行スクリプト
├── src/
│   ├── graph/
│   │   └── workflow.py                   # 【コア】LangGraphワークフロー定義
│   ├── schemas/
│   │   └── state.py                      # 【状態】AgentState定義
│   ├── agents/
│   │   ├── supervisor.py                 # Supervisor Agentの実装
│   │   └── nodes.py                      # 各ノード実装（explain, reflect等）
│   ├── tools/
│   │   ├── fetchers.py                   # ニュース取得ツール
│   │   └── storage.py                    # 保存処理（saver_node）
│   ├── core/
│   │   ├── llm.py                        # LLM初期化・実行
│   │   └── database.py                   # DB操作
│   └── config/
│       └── settings.py                   # 設定ファイル
```

### ファイル別役割

| ファイル | 役割 |
|---------|------|
| `daily_run.py` | 日次バッチの起動点。初期状態を準備し、ワークフローを `ainvoke()` で実行 |
| `workflow.py` | LangGraphの `StateGraph` を使ってワークフロー全体を定義。ノード、エッジ、条件分岐を制御 |
| `state.py` | 全ノード間で共有される `AgentState` TypedDictを定義 |
| `supervisor.py` | Supervisor Agentの実装。次に実行するノードを判定 |
| `nodes.py` | 各処理ノード（explain, reflect, reviser, recommender）の実装 |
| `fetchers.py` | Hacker News APIからニュースを非同期取得 |
| `storage.py` | 生成された解説をDB/ベクトルDBに保存 |

---

## LangGraphとは

### LangGraphの役割

LangGraphは LangChain の拡張ライブラリで、**複雑なマルチエージェント・ワークフロー** を **グラフ構造** として定義・実行できます。

```python
# LangGraphの基本構造
from langgraph.graph import StateGraph, START, END

workflow = StateGraph(StateType)

# 1. ノード追加
workflow.add_node("node_name", node_function)

# 2. エッジ（接続）追加
workflow.add_edge(START, "node_name")
workflow.add_edge("node_name", "next_node")

# 3. 条件付き分岐
workflow.add_conditional_edges("node_name", routing_function, {
    "path1": "node_a",
    "path2": "node_b"
})

# 4. コンパイルして実行
graph = workflow.compile()
result = graph.invoke(initial_state)
```

### LangGraph vs 従来の実装

| 項目 | 従来の実装 | LangGraph |
|------|----------|-----------|
| **フロー制御** | if/else の入れ子 | グラフとして視覚化可能 |
| **状態管理** | グローバル変数 | 統一的な StateDict |
| **エラーハンドリング** | try/catch | ノード単位で独立 |
| **デバッグ** | ログ追跡 | グラフ構造で可視化 |
| **スケーラビリティ** | 複雑度が増す | ノード追加で拡張可能 |
| **非同期対応** | 手作業 | 標準サポート |

---

## ワークフロー全体フロー

### グラフ構造図

```
┌─────────────────────────────────────────────────────────────┐
│                        START                                │
└────────────────────────┬────────────────────────────────────┘
                         ↓
        ┌────────────────────────────┐
        │   【1】 fetch_node         │
        │ Hacker Newsから最新ニュース6件 │
        │ 取得（非同期）              │
        └──────────┬─────────────────┘
                   ↓
        ┌────────────────────────────┐
        │   【2】 supervisor_node    │
        │ 次のアクション判定          │
        │ ("next" = アクション名)     │
        └──────────┬─────────────────┘
                   ↓
      ┌────────────────────────────────┐
      │  どのアクション？               │
      └────────────────────────────────┘
        │             │              │              │
        ↓             ↓              ↓              ↓
    "explain"    "reflect"    "revise"         "end"
        │             │              │              │
        ↓             ↓              ↓              ↓
   【explain】   【reflect】    【reviser】      【END】
   解説生成      批評・採点      修正生成
        │             │              │
        └─→ sup ←─────┼─→ sup ←─────┘
            erv         erv
            isor        isor
                        │
              ┌─────────┴──────────┐
              ↓                    ↓
          猫スコア≥70          猫スコア<70
              ↓                    ↓
         【saver】            【reviser】
         DB保存                修正実行
              ↓                    ↓
         【recommender】    → supervisor へ
         推奨生成
              ↓
            【END】
```

### 主要フロー（正常系）

```
1. START
   ↓
2. fetch_node（非同期）
   └→ raw_topics[] に Hacker News トップ6 を格納
   ↓
3. supervisor_node
   └→ 利用可能なトピックを確認
   ↓
4. explainer_node（各トピック処理）
   ├→ トピックをプロンプトに組み込み
   ├→ LLMで「猫でもわかる解説」を生成
   └→ explanations[] に追加
   ↓
5. reflector_node
   ├→ 生成された解説を読む
   ├→ LLMで「猫視点の批評」を実施
   ├→ 品質スコア（0〜100）を計算
   └→ critiques[] に追加
   ↓
6. should_revise() で分岐判定
   │
   ├─ スコア < 70（低品質）
   │  ↓
   │  reviser_node
   │  ├→ 批評内容を反映して修正
   │  ├→ 改めてLLMで解説生成
   │  └→ explanations[] を更新
   │  ↓
   │  supervisor へ戻す（再度処理）
   │
   └─ スコア ≥ 70（合格）
      ↓
      saver_node
      ├→ SQLite に説明を保存
      ├→ LanceDB にベクトル化して保存
      └→ ファイルシステムに JSON 出力
      ↓
      recommender_node
      ├→ 保存済み説明からおすすめを生成
      └→ recommendations[] に追加
      ↓
7. END
```

---

## ノード詳細

### 【1】 fetch_node（ニュース取得ノード）

**役割**: Hacker NewsのAPIから最新技術ニュースを非同期で取得

**実装**（[workflow.py](workflow.py) より）

```python
async def fetch_node(state: AgentState):
    """Hacker Newsからトピックを取得"""
    topics = await fetch_hacker_news_top(6)  # 最大6件
    return {
        "raw_topics": topics,
        "date": datetime.now().strftime("%Y-%m-%d")
    }
```

**入力**: 初期状態
**出力**:
- `raw_topics`: List[TopicMetadata] - 取得したニュース
- `date`: str - 実行日

**TopicMetadata スキーマ**

```python
class TopicMetadata(BaseModel):
    title: str              # ニュースタイトル
    summary: str            # 要約
    url: str                # 元記事URL
    source: str             # ソース（Hacker News等）
    score: int | None = None  # ニューススコア
```

---

### 【2】 supervisor_node（監督エージェント）

**役割**: LLMが次に実行すべきアクションを判定し、全体フローを制御

**実装**（[agents/supervisor.py](agents/supervisor.py) より、概念図）

```python
def supervisor_node(state: AgentState):
    """
    Supervisor Agent: 次のアクションを判定
    
    選択肢:
    - "explain": トピック説明を生成
    - "reflect": 生成済み説明を批評
    - "revise": 低品質説明を修正
    - "research_more": さらに詳しく調査
    - "end": 処理終了
    """
    # LLMが現在の状態を見て判定
    messages = build_supervisor_messages(state)
    response = llm.invoke(messages)
    
    next_action = parse_action(response)  # "explain", "reflect" など
    
    return {
        "next": next_action,
        "messages": [{"role": "assistant", "content": response}]
    }
```

**判定ロジック**

```
IF 未処理トピックがある
    → next = "explain"  # 解説を生成
ELSE IF 解説済みだが未批評
    → next = "reflect"  # 品質を批評
ELSE IF 批評済みだが品質が低い
    → next = "revise"   # 修正
ELSE IF すべてのトピック処理済み
    → next = "end"      # 終了
```

---

### 【3】 explainer_node（解説生成ノード）

**役割**: 技術ニュースを「猫でもわかる解説」に変換

**実装概念**

```python
async def explainer_node(state: AgentState):
    """
    トピックを「猫でもわかる技術解説」に変換
    - 難しい技術用語を平易に
    - 具体例を添える
    - 実生活への影響を説明
    """
    for topic in state.get("raw_topics", []):
        if topic not in processed_topics:
            prompt = f"""
以下の技術ニュースを「猫でもわかる解説」に変換してください。

タイトル: {topic.title}
内容: {topic.summary}

要件:
- 難しい技術用語は初心者向けに説明する
- 5〜7行の簡潔な説明
- 実生活への影響を含める
"""
            response = await llm.agenerate([prompt])
            
            explanations.append(Explanation(
                topic=topic,
                content=response.text,
                cat_score=0
            ))
    
    return {"explanations": explanations}
```

**入力**: `raw_topics[]`
**出力**: 
- `explanations[]`: List[Explanation] - 生成済み解説

**Explanation スキーマ**

```python
class Explanation(BaseModel):
    topic: TopicMetadata    # 元のトピック
    content: str            # 生成された解説文
    cat_score: int = 0      # 猫スコア（0〜100）
```

---

### 【4】 reflector_node（批評・採点ノード）

**役割**: 生成された解説を猫視点で批評し、品質スコアを計算

**実装概念**

```python
async def reflector_node(state: AgentState):
    """
    「猫視点」で解説を評価：
    - わかりやすさ: 0〜30点
    - 実用性: 0〜30点
    - 正確性: 0〜25点
    - 面白さ: 0〜15点
    → 合計 0〜100点
    """
    for explanation in state.get("explanations", []):
        if not explanation.critiqued:
            prompt = f"""
以下の技術解説を「猫の学習効果」の観点から採点してください。

解説: {explanation.content}

採点基準:
- わかりやすさ（0〜30）: 初心者理解度
- 実用性（0〜30）: 実生活への応用可能性
- 正確性（0〜25）: 技術的な誤りの有無
- 面白さ（0〜15）: 猫の興味を引く度

最後に:
SCORE: [合計点数]
FEEDBACK: [改善点]
"""
            response = await llm.agenerate([prompt])
            score = extract_score(response.text)  # プロンプトから数字抽出
            
            critiques.append({
                "explanation_id": explanation.id,
                "score": score,
                "feedback": response.text,
                "timestamp": datetime.now().isoformat()
            })
    
    return {"critiques": critiques}
```

**入力**: `explanations[]`
**出力**: 
- `critiques[]`: List[dict] - 批評スコア情報

---

### 【5】 reviser_node（修正ノード）

**役割**: スコア < 70 の低品質解説を修正

**実装概念**

```python
async def reviser_node(state: AgentState):
    """
    品質が低い解説を改善
    """
    for i, critique in enumerate(state.get("critiques", [])):
        if critique.get("score", 0) < 70:
            original = state["explanations"][i]
            feedback = critique.get("feedback", "")
            
            prompt = f"""
以下の解説を改善してください。

現在の解説:
{original.content}

批評:
{feedback}

改善版（より詳しく、わかりやすく）:
"""
            revised_content = await llm.agenerate([prompt])
            
            # explanations を更新
            state["explanations"][i].content = revised_content.text
            state["revision_count"] += 1
    
    return {
        "explanations": state["explanations"],
        "revision_count": state["revision_count"]
    }
```

**入力**: `explanations[]`, `critiques[]`
**出力**: 修正済み `explanations[]`

---

### 【6】 saver_node（保存ノード）

**役割**: 高品質（スコア ≥ 70）の解説をDB/ベクトルDBに永続化

**保存先**:
- **SQLite**: メタデータ、スコア、タイムスタンプ
- **LanceDB**: テキストのベクトル表現（ベクトル検索用）
- **JSON ファイル**: 人間が読める形式でローカル保存

**実装概念**

```python
async def saver_node(state: AgentState):
    """
    高品質解説を複数の保存先に保存
    """
    saved_ids = []
    
    for explanation in state.get("explanations", []):
        # ベクトル化
        embedding = embed(explanation.content)
        
        # LanceDB に保存
        lance_db.add({
            "id": uuid4(),
            "content": explanation.content,
            "embedding": embedding,
            "topic": explanation.topic.title,
            "date": state["date"]
        })
        
        # SQLite に保存
        db.insert_explanation({
            "topic_title": explanation.topic.title,
            "url": explanation.topic.url,
            "content": explanation.content,
            "cat_score": explanation.cat_score,
            "saved_date": datetime.now()
        })
        
        saved_ids.append(explanation.id)
    
    return {"saved_explanation_ids": saved_ids}
```

---

### 【7】 recommender_node（推奨生成ノード）

**役割**: 保存済み解説から、ユーザーへの「おすすめ」を生成

**実装概念**

```python
async def recommender_node(state: AgentState):
    """
    保存済み解説の中から「おすすめベスト3」を選定
    - ユーザーの過去の「いいね」を参考（将来機能）
    - トレンドスコア
    - 多様性
    """
    saved = state.get("explanations", [])
    
    prompt = f"""
以下の解説の中から、最も「猫にとって学習価値の高い」
ベスト3を選んでください。

解説リスト:
{json.dumps([e.dict() for e in saved], ensure_ascii=False, indent=2)}

選定理由も記載してください。
"""
    response = await llm.agenerate([prompt])
    recommendations = parse_recommendations(response.text)
    
    return {"recommendations": recommendations}
```

---

## 状態管理（AgentState）

### AgentState の構造

すべてのノード間で共有される状態オブジェクト（[state.py](state.py) より）

```python
class AgentState(TypedDict):
    # 基本情報
    date: str                                   # 実行日 YYYY-MM-DD
    
    # 処理結果データ
    raw_topics: Annotated[List[TopicMetadata], operator.add]
    explanations: Annotated[List[Explanation], operator.add]
    critiques: Annotated[List[dict], operator.add]
    recommendations: List[Explanation]
    
    # ワークフロー制御用
    messages: Annotated[List[dict], operator.add]
    revision_count: Annotated[int, operator.add] = 0
    supervisor_instruction: str = ""
    next: str = "explain"  # Supervisorが指定する次アクション
```

### `Annotated[..., operator.add]` の意味

```python
Annotated[List[TopicMetadata], operator.add]
```

LangGraphで **複数ノードからの出力をマージ** するため：

```python
# ノード1が返す
{"raw_topics": [topic_a, topic_b]}

# ノード2が返す
{"raw_topics": [topic_c, topic_d]}

# 結果：自動的に連結される
state["raw_topics"] = [topic_a, topic_b, topic_c, topic_d]
```

---

## Supervisor Agent

### 役割

複数のエージェント（explain, reflect, reviser等）の **実行順序と条件** を動的に決定する「監督者」

### 判定ロジック

```
状態を確認
    ↓
【判定1】未処理トピックがあるか？
    YES → "explain" へ
    NO  → 【判定2】へ
        
【判定2】説明済みだが未批評のものがあるか？
    YES → "reflect" へ
    NO  → 【判定3】へ
        
【判定3】スコア < 70の説明があるか？
    YES → "revise" へ
    NO  → 【判定4】へ
        
【判定4】すべてが完了したか？
    YES → "end"
    NO  → 【判定1】へ（ループ）
```

### 実装（概念図）

```python
def supervisor_node(state: AgentState) -> dict:
    """次のアクションを判定する監督エージェント"""
    
    # 現在の状態から判定用情報を抽出
    unprocessed_topics = [t for t in state["raw_topics"] 
                          if t not in processed]
    unexplained = [e for e in state["explanations"] 
                   if not e.explained]
    low_score_explanations = [c for c in state["critiques"] 
                              if c.get("score", 0) < 70]
    
    # LLMプロンプト組立
    system_message = """
あなたは技術解説エージェントの監督者です。
次に実行すべきアクションを選択してください。
"""
    
    user_message = f"""
現在の状態:
- 未処理トピック数: {len(unprocessed_topics)}
- 説明済み数: {len(state['explanations'])}
- 低品質説明数: {len(low_score_explanations)}

次のアクションを以下から選択:
1. "explain" - トピック説明を生成
2. "reflect" - 説明を批評
3. "revise" - 低品質説明を修正
4. "end" - 処理終了

選択: """
    
    response = llm.invoke([system_message, user_message])
    next_action = extract_action(response)  # "explain" 等を抽出
    
    return {
        "next": next_action,
        "messages": [...],
        "supervisor_instruction": f"次は {next_action} を実行"
    }
```

---

## 条件付き分岐（Conditional Edges）

### 概要

LangGraphの **条件付きエッジ** により、ノードの出力に基づいて異なる次のノードへ分岐します。

### 実装例（[workflow.py](workflow.py) より）

```python
# 【1】 Supervisor の出力に基づいて分岐
workflow.add_conditional_edges(
    "supervisor",
    lambda state: state.get("next", "explain"),  # supervisor_node が返す "next" を参照
    {
        "research_more": "fetch",      # さらに調査が必要 → fetch ノード
        "explain": "explain",          # 説明生成 → explainer
        "reflect": "reflect",          # 批評実施 → reflector
        "revise": "reviser",           # 修正 → reviser
        "saver": "saver",              # 保存 → saver
        "recommender": "recommender",  # 推奨生成 → recommender
        "end": END,                    # 処理終了
    }
)

# 【2】 Reflect ノード後の品質判定分岐
workflow.add_conditional_edges(
    "reflect",
    should_revise,  # 品質判定関数
    {
        "reviser": "reviser",  # 低品質 → 修正
        "saver": "saver"       # 高品質 → 保存
    }
)
```

### 分岐判定関数

```python
def should_revise(state: AgentState) -> Literal["reviser", "saver"]:
    """Reflect後の分岐判定"""
    critiques = state.get("critiques", [])
    
    if not critiques:
        return "saver"  # 批評なし → 保存
    
    # 最新の批評スコアを取得
    latest_score = critiques[-1].get("score", 0) \
        if isinstance(critiques[-1], dict) else 0
    
    # 猫スコアが低い場合は修正
    if latest_score < 70:   # 閾値: 70点
        return "reviser"    # 再修正ノードへ
    else:
        return "saver"      # 保存ノードへ
```

---

## 実行フロー例

### シナリオ

最新ニュース6件を処理し、すべてを解説→批評→保存する例

### ステップバイステップ

```
【ステップ1】 START
├─ 初期状態作成
│  raw_topics: []
│  explanations: []
│  critiques: []
│  recommendations: []
└─ 状態完成

【ステップ2】 fetch_node 実行
├─ Hacker News API 呼び出し（非同期）
├─ 取得: [トピックA, トピックB, トピックC, トピックD, トピックE, トピックF]
└─ raw_topics に追加

【ステップ3】 supervisor_node 実行
├─ 判定: "未処理トピック6件あり → explain すべき"
└─ next = "explain"

【ステップ4】 explainer_node 実行（トピックA処理）
├─ LLM: "Pythonの新しい非同期ライブラリについて..."
├─ 生成: "猫でもわかる解説"
└─ explanations に追加

【ステップ5】 supervisor_node 実行（再度）
├─ 判定: "未処理トピック5件まだある → explain"
└─ next = "explain"

... (トピックB〜F も同様に explain)

【ステップN】 supervisor_node 実行（ステップ14後）
├─ 判定: "説明済み6件だが未批評 → reflect"
└─ next = "reflect"

【ステップN+1】 reflector_node 実行
├─ LLM: 「この解説はわかりやすい。スコア: 82点」
├─ critiques に追加: {score: 82, feedback: "..."}
└─ explain → supervisor へ戻す

【ステップN+2】 should_revise() 実行
├─ スコア 82 >= 70? YES
└─ 分岐: "saver" へ

【ステップN+3】 saver_node 実行
├─ SQLite に保存
├─ LanceDB にベクトル化して保存
└─ ローカルファイルに JSON 出力

【ステップN+4】 recommender_node 実行
├─ LLM: "ベスト3解説を選定"
└─ recommendations に追加

【ステップN+5】 END
└─ ワークフロー完了
```

### 実行時の状態遷移

| ステップ | ノード | 入力状態 | 出力状態 |
|---------|--------|---------|---------|
| 1 | fetch | raw_topics: [] | raw_topics: [A,B,C,D,E,F] |
| 2-7 | explain | raw_topics: [...] | explanations: [A,B,C,D,E,F] |
| 8-13 | reflect | explanations: [...] | critiques: [...] |
| 14 | saver | critiques: [...] | saved_ids: [...] |
| 15 | recommender | explanations: [...] | recommendations: [...] |
| 16 | END | - | 完了 |

---

## 実装詳細

### 非同期処理（async/await）

すべての LLM 呼び出しと API 呼び出しは非同期で実行：

```python
# daily_run.py
async def main():
    graph = build_graph()
    initial_state = { ... }
    
    # ainvoke() で非同期実行
    result = await graph.ainvoke(initial_state)
    print(f"完了！解説数: {len(result['explanations'])}")

# 実行
if __name__ == "__main__":
    asyncio.run(main())
```

### ノード登録とエッジ定義

```python
# workflow.py
workflow = StateGraph(AgentState)

# ノード登録
workflow.add_node("fetch", fetch_node)
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("explain", explainer_node)
workflow.add_node("reflect", reflector_node)
workflow.add_node("reviser", reviser_node)
workflow.add_node("saver", saver_node)
workflow.add_node("recommender", recommender_node)

# エッジ定義
workflow.add_edge(START, "fetch")
workflow.add_edge("fetch", "supervisor")
workflow.add_conditional_edges("supervisor", lambda s: s.get("next", "explain"), {...})
...

# コンパイル
return workflow.compile()
```

### LLM 呼び出しパターン

```python
# core/llm.py での実装例
async def generate_explanation(topic: TopicMetadata) -> str:
    """トピックから解説を生成"""
    
    prompt = f"""
以下の技術ニュースを「猫でもわかる」ように解説してください：

タイトル: {topic.title}
内容: {topic.summary}

要件:
- 難しい用語は初心者向けに説明
- 5-7行の簡潔さ
- 実生活への影響を明記
"""
    
    # 非同期 LLM 呼び出し
    response = await llm.agenerate([prompt])
    return response.text

# ノード内での使用
async def explainer_node(state: AgentState):
    for topic in state["raw_topics"]:
        content = await generate_explanation(topic)
        explanations.append(Explanation(topic=topic, content=content))
    return {"explanations": explanations}
```

### エラーハンドリング

```python
async def safe_node_execution(node_func, state: AgentState):
    """ノード実行時のエラーハンドリング"""
    try:
        result = await node_func(state)
        return result
    except TimeoutError:
        logger.error("LLM タイムアウト")
        return {"error": "timeout", "state": state}
    except ValueError as e:
        logger.error(f"値のエラー: {e}")
        return {"error": "value_error", "state": state}
    except Exception as e:
        logger.error(f"予期しないエラー: {e}")
        return {"error": "unknown", "state": state}
```

---

## 実行時間と性能

### 時間目安

| トピック数 | PC スペック | 推定時間 |
|-----------|-----------|---------|
| 6件 | メモリ 16GB | 5～10分 |
| 6件 | メモリ 32GB | 3～7分 |
| 12件 | メモリ 16GB | 15～25分 |
| 12件 | メモリ 32GB | 8～15分 |

**変動要因**:
- LLMモデルのサイズ（3B vs 7B）
- GPU/CPU 性能
- ローカルネットワーク速度（Hacker News API 呼び出し）
- システム負荷

### パフォーマンス最適化

```python
# 1. 並列処理の活用（複数トピックの同時処理）
async def explainer_node(state: AgentState):
    tasks = [
        generate_explanation(topic) 
        for topic in state["raw_topics"]
    ]
    results = await asyncio.gather(*tasks)  # 並列実行
    return {"explanations": results}

# 2. バッチ処理
batch_size = 3
for i in range(0, len(topics), batch_size):
    batch = topics[i:i+batch_size]
    # バッチ処理

# 3. キャッシング
from functools import lru_cache

@lru_cache(maxsize=100)
def get_cached_embedding(text: str):
    return embed(text)
```

---

## トラブルシューティング

### 【問題1】 処理が遅い / タイムアウト

**原因と対策**:

| 症状 | 原因 | 対策 |
|------|------|------|
| LLM 呼び出し遅延 | モデルサイズ大きい | 3B モデルに変更 |
| メモリ不足 | 複数トピック同時処理 | バッチサイズ削減 |
| ネットワーク遅延 | Hacker News API 遅い | リトライ機構追加 |

```python
# リトライ機構
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def fetch_hacker_news_top(n: int):
    return await fetch_with_timeout(n, timeout=30)
```

### 【問題2】 解説品質が低い

**原因と対策**:

```python
# プロンプトテンプレートの改善
improved_prompt = """
以下の技術ニュースについて、「5歳の子猫にも理解できるレベル」で
説明してください（使用禁止: 専門用語、複雑な数式）：

{topic}

出力形式:
1行目: 簡潔な要約
2-4行目: 具体例を交えた説明
最後: 「だから何がすごいのか」を明記
"""
```

### 【問題3】 データベースエラー

**原因と対策**:

```python
# SQLite ロック問題
import sqlite3
from contextlib import contextmanager

@contextmanager
def get_db_connection():
    conn = sqlite3.connect('data/curator.db', timeout=30.0)
    try:
        yield conn
    finally:
        conn.close()

# LanceDB 接続失敗
try:
    db = lancedb.connect("data/vector_db")
except Exception as e:
    logger.error(f"LanceDB 接続失敗: {e}")
    # フォールバック処理
```

### 【問題4】 状態オブジェクトが正しく渡されない

**原因と対策**:

```python
# 正しい: 辞書形式で return
def my_node(state: AgentState) -> dict:
    return {
        "explanations": [...]  # 必ず AgentState の定義済みキー
    }

# 誤り: 直接 AgentState を return しない
def bad_node(state: AgentState) -> AgentState:  # ❌
    state["explanations"] = [...]
    return state

# 誤り: 定義されていないキーを追加
def bad_node2(state: AgentState) -> dict:
    return {
        "undefined_key": "value"  # ❌ AgentState に存在しない
    }
```

### 【問題5】 Supervisor が無限ループする

**原因**: `next` キーが常に同じアクションを返す

**対策**:

```python
def supervisor_node(state: AgentState) -> dict:
    # 状態を確認して異なる next を返す
    if no_more_topics(state):
        next_action = "end"
    elif has_unexplained(state):
        next_action = "explain"
    elif has_uncritiqued(state):
        next_action = "reflect"
    else:
        next_action = "end"
    
    return {"next": next_action}

# ❌ 常に同じ値を返している
def bad_supervisor(state: AgentState) -> dict:
    return {"next": "explain"}  # 常に "explain"
```

---

## 今後の拡張予定

- [ ] **ユーザーフィードバック統合**: いいね・評価に基づく学習
- [ ] **キャッシング機構**: 同じニュースの重複処理を削減
- [ ] **複数ソース対応**: Hacker News + Reddit + Product Hunt
- [ ] **定期実行**: APScheduler による自動スケジューリング
- [ ] **Web UI の充実**: リアルタイム処理表示、評価機能
- [ ] **マルチLLM対応**: 複数モデルの自動選択
- [ ] **エラーログ可視化**: 処理失敗の詳細ダッシュボード

---

## 参考リソース

- [LangGraph 公式ドキュメント](https://langchain-ai.github.io/langgraph/)
- [LangChain 日本語ドキュメント](https://python.langchain.com/docs/get_started/introduction)
- [Pydantic TypedDict](https://docs.pydantic.dev/)
- [Python asyncio](https://docs.python.org/3/library/asyncio.html)

---

## 更新履歴

| 日付 | 更新内容 |
|------|---------|
| 2026-05-25 | 初版作成：LangGraph ワークフロー詳細ドキュメント |