
import os
from src.config import RAGConfig

# Simula o que o FastAPI faz
config = RAGConfig()
print(f"LLM_PROVIDER: {config.llm_provider}")
print(f"LLM_API_KEY: {'[SET]' if config.llm_api_key else '[EMPTY]'}")
print(f"GOOGLE_API_KEY env: {'[SET]' if os.getenv('GOOGLE_API_KEY') else '[EMPTY]'}")
print(f"MODEL_NAME: {config.model_name}")
print(f"CHROMA_PORT: {config.chroma_port}")
