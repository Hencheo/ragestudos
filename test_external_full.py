import asyncio
import sys
import os
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.append(str(Path(__file__).parent))

from src.services import HermesService
from src.config import RAGConfig

async def test_full_external_flow():
    print("🧪 Testando Fluxo Completo: API Externa -> RAG Engine...")
    
    config = RAGConfig()
    service = HermesService(config)
    service.initialize_engine()
    
    process_number = "0009876-54.2024.8.26.0100"
    
    print(f"\n1. Sincronizando processo {process_number}...")
    result = await service.fetch_and_index_external_process(process_number)
    
    if result["success"]:
        print(f"✅ Sucesso: {result['message']}")
        
        print("\n2. Testando consulta sobre o processo sincronizado...")
        question = "Quem são as partes no processo 0009876-54.2024.8.26.0100 e qual o assunto?"
        response = service.ask_question(question)
        
        print("\nRESPOSTA DO HERMES:")
        print("-" * 50)
        print(response)
        print("-" * 50)
    else:
        print(f"❌ Falha: {result['message']}")

if __name__ == "__main__":
    asyncio.run(test_full_external_flow())
