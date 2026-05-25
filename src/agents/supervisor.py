from langchain_core.messages import HumanMessage
from src.core.llm import get_llm
from src.utils.prompts import SUPERVISOR_PROMPT
import json

async def supervisor_node(state):
    """Supervisorノード - ワークフロー全体の「監督者エージェント」 

    引数:
        state (AgentState) - ワークフローの現在の状態を表す辞書型のオブジェクト
    戻り値:
        dict - 次のノードへの指示や追加情報を含む辞書型のオブジェクト
    説明:
        ワークフロー全体の「監督者エージェント」として機能するノード。
        現在の状態を分析し、次のノードへの最適なアクションを決定する。
        LLMを使用して、状態に基づいた判断を行い、次のノードへの指示や理由を生成する。
        ワークフローの品質管理と柔軟な分岐を実現するための重要なノード    
    
    """

    # LLMの初期化（温度は低めに設定して安定した出力を促す）
    llm = get_llm(temperature=0.1)
    
    num_topics = len(state.get("raw_topics", []))   # 取得したニュース数
    num_explanations = len(state.get("explanations", []))   # 生成済み解説数
    num_critiques = len(state.get("critiques", []))  # 生成済み自己批評数
    revision_count = state.get("revision_count", 0) # 解説の修正回数
    
    # プロンプト構築 - 現在の状況を分析し、最適な次のアクションと具体的な指示を決めるためのプロンプト
    prompt = SUPERVISOR_PROMPT.format(
        date=state.get("date", "不明"),
        num_topics=num_topics,
        num_explanations=num_explanations,
        num_critiques=num_critiques,
        revision_count=revision_count,
        last_score=state["critiques"][-1].get("score", 0) if state.get("critiques") else 0
    )
    
    print(f"Supervisor: 状況分析 → トピック数: {num_topics}, 解説数: {num_explanations}, 評価数: {num_critiques}, 修正回数: {revision_count}, 最新スコア: {state['critiques'][-1].get('score', 0) if state.get('critiques') else 0} ")  # 状況をログに出力
      
    print(f"Supervisorプロンプト:\n{prompt[:500]}...")  # プロンプトの一部をログに出力

    print(f"Supervisor判断中... | 状況: トピック{num_topics} 解説{num_explanations} 評価{num_critiques} 修正{revision_count}")
    # LLMにプロンプトを投げて次のアクションを決定
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    
    # LLMの応答を解析して次のノードへの指示を抽出
    try:
        decision = json.loads(response.content.strip())
        next_step = decision.get("next", "explain") # 次のアクション: デフォルトは"explain"（新しい解説生成）
        reason = decision.get("reason", "") # 判断理由
        instruction = decision.get("instruction", "")   # 次のノードへの具体的な指示
    except Exception as e:
        print(f"Supervisor JSONエラー: {e}")
        next_step = "explain"
        reason = "パース失敗"
        instruction = ""

    # 強制ルール（安全策）
    if num_explanations == 0 and num_topics > 0:
        # トピックがあるのに解説が1つもない場合は、優先的に解説生成を指示
        next_step = "explain"
        instruction = "新しいトピックについて分かりやすい解説を生成してください"
    elif num_explanations >= 6 and num_critiques == 0:
        # 解説が6件以上完了したのに自己批評が1件もない場合は、品質評価を指示
        next_step = "reflect"
        instruction = "生成された解説の品質を厳しく評価せよ。特に正確性を重視せよ。"
    elif revision_count >= 2:
        # 修正回数が2回以上の場合は、保存へ進むよう指示（無限ループ防止）
        next_step = "saver"

    # ロギング - Supervisorの判断と理由をログに出力
    print(f"Supervisor決定 → {next_step} | 理由: {reason[:80]}... | "
          f"解説:{num_explanations} 評価:{num_critiques} 修正:{revision_count}"
          f" | 指示: {instruction[:80]}...")

    # 次のノードへの指示を返す
    return {
        "messages": [{"role": "supervisor", "content": next_step, "reason": reason}],
        "next": next_step,
        "supervisor_instruction": instruction
    }