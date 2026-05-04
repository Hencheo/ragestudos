import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

try:
    print(f"--- Tentando criar embedding com: {api_key[:8]}... ---")
    response = client.embeddings.create(
        input="Teste de sanidade do Hermes",
        model="text-embedding-3-large"
    )
    print("✅ SUCESSO TOTAL! Consegui criar o embedding via API direta.")
    print(f"Dimensões do vetor: {len(response.data[0].embedding)}")
except Exception as e:
    print(f"❌ FALHA NA CRIAÇÃO: {e}")
