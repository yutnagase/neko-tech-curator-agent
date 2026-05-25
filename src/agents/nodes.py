from langchain_core.messages import HumanMessage
from src.core.llm import get_llm
from src.utils.prompts import (
    DAILY_EXPLAINER_PROMPT, 
    REFLECTION_PROMPT, 
    REVISER_PROMPT,
    RECOMMENDER_PROMPT  
)
from src.schemas.state import AgentState, Explanation

import json

async def explainer_node(state: AgentState) -> AgentState:
    """解説生成ノード - Supervisorの指示を反映
    
    引数:
        state (AgentState) - ワークフローの現在の状態を表す辞書型のオブジェクト
    戻り値:
        dict - 生成された解説を含む辞書型のオブジェクト
    説明:
        解説生成ノード。与えられた技術ニュースのタイトルと要約を基に、初心者向けのわかりやすい解説を生成する。
        Supervisorからの特別指示がある場合は、それをプロンプトに追加して解説生成に反映させる。
        生成された解説は、AgentStateの"explanations"項目に追加される。

    """

    # Supervisorからの特別指示をプロンプトに追加
    instruction = state.get("supervisor_instruction", "")
    extra_instruction = f"\n\n【Supervisor特別指示】{instruction}" if instruction else ""
    
    # LLMの初期化（温度はやや高めに設定して多様な解説を促す）
    llm = get_llm(temperature=0.7)
    # 新しい解説を格納するリスト
    new_explanations = []
    
    # 取得したニュースごとに解説を生成
    for topic in state.get("raw_topics", []):
        prompt_text = DAILY_EXPLAINER_PROMPT.format(
            title=topic.title,
            summary=topic.summary or "詳細はリンクを参照してください。",
            url=topic.url
        ) + extra_instruction   # ← Supervisor指示を追加
        
        print(f"Explainerプロンプト:\n{prompt_text[:500]}...")  # プロンプトの一部をログに出力

        print(f"Explainer生成中... | トピック: {topic.title[:50]}...")  # 生成中のトピックをログに出力
        # LLMにプロンプトを投げて解説を生成
        response = await llm.ainvoke([HumanMessage(content=prompt_text)])
        
        # 生成された解説をリストに追加
        new_explanations.append(Explanation(
            topic=topic,
            content=response.content.strip()
        ))
    
    # 生成された解説の数とSupervisor指示の有無をログに出力
    print(f"Explainer完了: {len(new_explanations)}件生成 | Supervisor指示: {instruction[:50] if instruction else 'なし'}")

    # 生成された解説をAgentStateの"explanations"に追加して返す
    return {"explanations": new_explanations}


async def reflector_node(state: AgentState) -> AgentState:
    """自己批評ノード - Supervisorの指示を反映
    
    引数:
        state (AgentState) - ワークフローの現在の状態を表す辞型のオブジェクト
    戻り値:
        dict - 生成された自己批評を含む辞型のオブジェクト
    説明:
        自己批評ノード。生成された解説の品質を評価し、スコアや改善点を含む自己批評を生成する。
        Supervisorからの特別指示がある場合は、それをプロンプトに追加して自己批評生成に反映させる。
        生成された自己批評は、AgentStateの"critiques"項目に追加される。

    """

    # Supervisorからの特別指示をプロンプトに追加
    instruction = state.get("supervisor_instruction", "")
    extra_instruction = f"\n\n【Supervisor特別指示】{instruction}" if instruction else ""
    
    # LLMの初期化（温度は低めに設定して安定した評価を促す）
    llm = get_llm(temperature=0.0)
    # 生成された自己批評を格納するリスト
    critiques = []
    
    # 生成された解説ごとに自己批評を生成
    for exp in state.get("explanations", []):
        # 解説内容をプロンプトに入れて自己批評を生成
        prompt = REFLECTION_PROMPT.format(content=exp.content) + extra_instruction
        
        print(f"Reflectorプロンプト:\n{prompt[:500]}...")  # プロンプトの一部をログに出力
        print(f"Reflector生成中... | 解説: {exp.content[:50]}...")  # 生成中の解説をログに出力
        
        # LLMにプロンプトを投げて自己批評を生成
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        
        try:
            # LLMの応答をJSONとしてパースして自己批評を抽出
            critique = json.loads(response.content)
        except:
            critique = {
                "score": 3, 
                "strengths": "形式は守れている", 
                "weaknesses": "改善の余地あり", 
                "suggestion": "もう少しわかりやすい説明を入れてください。"
            }

        # 生成された自己批評をリストに追加
        critiques.append(critique)
    
    # 生成された自己批評の数とSupervisor指示の有無をログに出力
    print(f"Reflector完了: {len(critiques)}件評価 | Supervisor指示: {instruction[:50] if instruction else 'なし'}")

    # 生成された自己批評をAgentStateの"critiques"に追加して返す
    return {"critiques": critiques}


async def reviser_node(state: AgentState) -> AgentState:
    """解説修正ノード - Supervisorの指示を反映
    
    引数:
        state (AgentState) - ワークフローの現在の状態を表す辞型のオブジェクト
    戻り値:
        dict - 生成された修正済み解説を含む辞型のオブジェクト
    説明:
        解説修正ノード。自己批評の内容に基づいて、解説の修正を行う。
        Supervisorからの特別指示がある場合は、それをプロンプトに追加して修正生成に反映させる。
        生成された修正済み解説は、AgentStateの"explanations"項目に上書きされる。  

    
    """

    # Supervisorからの特別指示をプロンプトに追加
    instruction = state.get("supervisor_instruction", "")
    extra_instruction = f"\n\n【Supervisor特別指示】{instruction}" if instruction else ""
    
    # LLMの初期化（温度はやや高めに設定して多様な修正を促す）
    llm = get_llm(temperature=0.65)
    # 修正された解説を格納するリスト
    revised_explanations = []
    
    # 生成された解説ごとに対応する自己批評を参照しながら修正を生成
    explanations = state.get("explanations", [])
    # 対応する自己批評を取得（ない場合は空の辞書を使用）
    critiques = state.get("critiques", [])
    
    # 解説と対応する自己批評を基に修正を生成
    for i, exp in enumerate(explanations):
        critique = critiques[i] if i < len(critiques) else {}
        suggestion = critique.get("suggestion", "より分かりやすく、猫らしい表現としてください。")
        
        # 解説内容と自己批評の改善指示をプロンプトに入れて修正を生成
        prompt = REVISER_PROMPT.format(
            content=exp.content,
            suggestion=suggestion
        ) + extra_instruction
        
        print(f"Reviserプロンプト:\n{prompt[:500]}...")  # プロンプトの一部をログに出力
        print(f"Reviser生成中... | 解説: {exp.content[:50]}...")  # 生成中の解説をログに出力

        # LLMにプロンプトを投げて修正された解説を生成
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        
        # 生成された修正済み解説をリストに追加
        revised_explanations.append(Explanation(
            topic=exp.topic,
            content=response.content.strip()
        ))
    
    # 生成された修正済み解説の数とSupervisor指示の有無をログに出力
    print(f"Reviser完了: {len(revised_explanations)}件修正")

    # 生成された修正済み解説をAgentStateの"explanations"に上書きして返す
    return {"explanations": revised_explanations}


def should_revise(state: AgentState) -> str:
    """Reflection後の条件分岐
    
    引数:
        state (AgentState) - ワークフローの現在の状態を表す辞型のオブジェクト
    戻り値:
        str - 次のノードを示す文字列（例: "reviser", "saver"）
    説明:
        Reflectionノードで生成された自己批評の内容に基づいて、解説の品質が十分でないと判断された場合は"reviser"を返し、
        品質が良好と判断された場合は"saver"を返す関数。
        Supervisorノードの判断ロジックで使用される。ワークフロー内で品質管理と柔軟な分岐を実現するための重要な関数。

    
    """
    if not state.get("critiques"):
        return "saver"
    
    # 最後のcritiqueをチェック
    last_critique = state["critiques"][-1]
    score = last_critique.get("score", 0) if isinstance(last_critique, dict) else 0
    
    # スコアが低い場合は修正（閾値は調整可能）
    if score <= 3:
        return "reviser"
    return "saver"


async def recommender_node(state: AgentState) -> AgentState:
    """おすすめ生成ノード
    
    引数:
        state (AgentState) - ワークフローの現在の状態を表す辞型のオブジェクト
    戻り値:
        dict - 生成されたおすすめ解説を含む辞型のオブジェクト
    説明:
        おすすめ生成ノード。ユーザーの興味に合った技術トピックをおすすめするためのノード。過去のユーザーの好み（いいねした分野）を考慮して、おすすめ解説を提案する。
        Supervisorからの特別指示がある場合は、それをプロンプトに追加しておすすめ生成に反映させる。
        生成されたおすすめ解説は、AgentStateの"recommendations"項目に追加される。
    
    """

    # Supervisorからの特別指示をプロンプトに追加
    instruction = state.get("supervisor_instruction", "")
    # おすすめ生成のプロンプトにSupervisorの指示を追加（ある場合のみ）
    extra_instruction = f"\n\n【Supervisor特別指示】{instruction}" if instruction else ""
    
    # LLMの初期化（温度はやや高めに設定して多様なおすすめを促す）
    llm = get_llm(temperature=0.7)
    # 生成されたおすすめを格納するリスト
    recommendations = []
    
    # プロンプトを構築してLLMに投げる
    prompt = RECOMMENDER_PROMPT + extra_instruction
    
    # LLMにプロンプトを投げておすすめを生成
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    
    # 生成されたおすすめをリストに追加
    recommendations.append({
        "title": "今日のおすすめネタ",
        "content": response.content.strip()
    })
    
    # 生成されたおすすめの内容とSupervisor指示の有無をログに出力
    print(f"Recommender完了: {len(recommendations)}件")

    # 生成されたおすすめをAgentStateの"recommendations"に追加して返す
    return {"recommendations": recommendations}