import os
import sys
from pathlib import Path

# Adiciona o diretório atual ao path
sys.path.append(str(Path(__file__).parent))

from src.services import HermesService
from src.config import RAGConfig

def test_legal_queries():
    print("🧪 Testando Queries Jurídicas com Hermes...")
    config = RAGConfig()
    service = HermesService(config)
    
    queries = [
        "Qual o valor dos honorários mensais no contrato com a Global SA?",
        "Qual o número do processo do João da Silva e o que ele está pedindo?",
        "Como devo proceder para responder dúvidas básicas de clientes segundo o guia interno?"
    ]
    
    for q in queries:
        print(f"\n--- PERGUNTA: {q} ---")
        try:
            # Força inicialização do motor se necessário
            if not service.engine:
                service.initialize_engine()
            
            response = service.ask_question(q)
            print(f"RESPOSTA:\n{response}")
        except Exception as e:
            print(f"ERRO: {e}")

if __name__ == "__main__":
    test_legal_queries()
