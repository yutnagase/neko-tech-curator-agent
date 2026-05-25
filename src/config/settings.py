from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
import sys

class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore",
        # .envが存在しない場合はエラーを出す
        env_file_required=True
    )

    # LLM設定
    LLM_MODEL_PATH: str
    LLM_N_CTX: int = 8192
    LLM_N_GPU_LAYERS: int = 0
    LLM_N_THREADS: int = 8

    # データベース
    DB_PATH: str = "data/explanations.db"
    VECTOR_DB_PATH: str = "data/vector_db"

    # 開発設定
    DEBUG: bool = True

    def model_post_init(self, __context):
        """起動時にバリデーション"""
        model_path = Path(self.LLM_MODEL_PATH)
        if not model_path.exists():
            print(f"❌ エラー: 指定されたモデルファイルが見つかりません")
            print(f"   パス: {model_path}")
            print("   .envファイルで正しいLLM_MODEL_PATHを設定してください。")
            sys.exit(1)

        print(f"モデルロード準備完了: {model_path.name}")


# グローバルインスタンス
settings = Settings()