import asyncio
import sys
import os
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.append(str(Path(__file__).parent))

from src.services_ext.external_api import ExternalApiService

async def test_external_fetch():
    print("🧪 Testando ExternalApiService (Modo Mock)...")
    service = ExternalApiService()
    
    process_number = "0001234-56.2024.8.26.0000"
    process = await service.fetch_process_data(process_number)
    
    if process:
        print("\n✅ Processo recuperado com sucesso!")
        print(f"Tribunal: {process.tribunal}")
        print("-" * 30)
        print("CONTEÚDO PARA O RAG:")
        print(process.to_rag_text())
        print("-" * 30)
    else:
        print("\n❌ Falha ao recuperar processo.")

if __name__ == "__main__":
    asyncio.run(test_external_fetch())
