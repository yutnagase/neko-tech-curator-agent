# Agent / LangGraph 詳細設計

## LangGraphとは？

LangGraphは、**状態（State）を持つ有向グラフ**としてAIワークフローを定義できるライブラリです。
従来のLangChain Chainとは異なり、**条件分岐・ループ・複数エージェント協調**を自然に表現できます。

### 本プロジェクトでのState定義（src/schemas/state.py）

```python
class AgentState(TypedDict):
    raw_topics: list          # Hacker Newsから取得した生トピック
    explanations: list        # 生成済み解説
    critiques: list           # 自己批評結果
    next: str                 # Supervisorが次に指示するノード名
    date: str
    # ... その他
```

## 主要ノード解説

| ノード名       | 役割                                   | 使用LLM温度 | 特徴 |
|----------------|----------------------------------------|-------------|------|
| `fetch`        | Hacker Newsトップストーリー取得       | -           | メタデータのみ |
| `supervisor`   | 次にどのノードを実行するか決定         | 0.3（低め） | 動的ルーティングの要 |
| `explain`      | 「猫でもわかる」解説を生成             | 0.7         | 親しみやすい口調を徹底 |
| `reflect`      | 生成した解説を猫目線で批評             | 0.5         | スコアリング実施 |
| `reviser`      | 批評に基づいて解説を修正               | 0.6         | Reflection Loop |
| `saver`        | 最終結果をDBに保存                     | -           | SQLite + LanceDB |

### Reflection Loopの仕組み（超重要）

1. Explainerが解説を作成
2. Reflectorが「猫でもわかる度」を1-100でスコアリング
3. 70点未満 → Reviserが修正 → 再度Reflect
4. 70点以上 or 最大修正回数到達 → Saverへ

これにより、**単発生成より大幅に品質が安定**します。

**Supervisorの実装ポイント**:
最近 `create_react_agent` + ToolNodeを使った本格的なSupervisorにリファクタ中です。これにより、柔軟な動的ルーティングが可能になっています。