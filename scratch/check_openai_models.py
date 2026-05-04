import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("❌ Erro: OPENAI_API_KEY não encontrada no .env")
    exit(1)

client = OpenAI(api_key=api_key)

try:
    print(f"--- Testando Chave: {api_key[:8]}...{api_key[-4:]} ---")
    models = client.models.list()
    model_ids = [m.id for m in models.data]
    
    target = "text-embedding-3-large"
    if target in model_ids:
        print(f"✅ SUCESSO: O modelo '{target}' ESTÁ disponível para esta chave!")
    else:
        print(f"❌ ERRO: O modelo '{target}' NÃO foi encontrado na lista de modelos desta chave.")
        print("\nModelos de embedding disponíveis:")
        for m_id in sorted(model_ids):
            if "embed" in m_id:
                print(f"  - {m_id}")

except Exception as e:
    print(f"💥 Erro ao conectar com a OpenAI: {e}")
