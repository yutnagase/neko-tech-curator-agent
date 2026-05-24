# LLM 実行環境

## 使用ライブラリ
- `llama.cpp` + `langchain_community.llms.ChatLlamaCpp`

## 推奨モデル
- `Llama-3.2-3B-Instruct` (Q5_K_M 程度)

## 設定ポイント
- **温度 (Temperature)**: 解説生成時は0.7（創造性）、批評時は0.5（客観性）
- **コンテキスト長**: 4096〜8192トークン
- **GPU対応**: llama.cppのCUDA/Metal対応で高速化可能

**Tips**: メモリが厳しい場合は3Bモデル、余裕があれば8B〜13Bモデルへスケールアップ可能。
