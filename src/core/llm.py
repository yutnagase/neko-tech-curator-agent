from langchain_community.chat_models import ChatLlamaCpp
from src.config.settings import settings

def get_llm(temperature: float = 0.7):
    return ChatLlamaCpp(
        model_path=settings.LLM_MODEL_PATH,
        n_ctx=settings.LLM_N_CTX,
        n_gpu_layers=settings.LLM_N_GPU_LAYERS,
        n_threads=settings.LLM_N_THREADS,
        temperature=temperature,
        verbose=False,
    )