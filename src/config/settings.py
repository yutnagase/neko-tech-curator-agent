from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    LLM_MODEL_PATH: str = "models/llama3.2-3b-q4_k_m.gguf"
    LLM_N_CTX: int = 8192
    LLM_N_GPU_LAYERS: int = 0          # WSLでCUDA有効なら8〜12くらい
    LLM_N_THREADS: int = 4

    DB_PATH: str = "data/explanations.db"
    VECTOR_DB_PATH: str = "data/vector_db"

settings = Settings()
