# 日次バッチ処理の流れ

1. 起動（daily_run.py）
2. 新着トピック取得
3. Supervisorがワークフローを制御
4. 各トピックに対して Explain → Reflect → (Reviser) → Save
5. 完了

**実行時間目安**: 10〜30トピックで5〜15分程度（モデル・PCスペックによる）