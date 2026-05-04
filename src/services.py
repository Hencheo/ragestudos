import logging
import tempfile
from pathlib import Path
from typing import List, Optional, Dict, Any
import chromadb

from src.rag_engine import RAGEngine
from src.document_loader import PDFDocumentLoader
from src.config import RAGConfig

logger = logging.getLogger(__name__)

class HermesService:
    """Camada de serviço pura para gerenciar a lógica do Hermes RAG.
    
    Esta classe é independente de interface (Streamlit, FastAPI, etc).
    """
    
    def __init__(self, config: RAGConfig):
        self.config = config
        self.engine: Optional[RAGEngine] = None
        self.loader = PDFDocumentLoader(config=config)
        
    def initialize_engine(self) -> bool:
        """Inicializa o motor RAG se houver uma API Key válida."""
        if not self.config.llm_api_key:
            return False
            
        try:
            self.engine = RAGEngine(
                api_key=self.config.llm_api_key, 
                config=self.config
            )
            return True
        except Exception as e:
            logger.error(f"Falha ao inicializar motor: {e}")
            raise e

    def process_and_index_files(self, files_data: List[Dict[str, Any]], subject: str = "") -> Dict[str, Any]:
        """Processa arquivos (bytes) e indexa no banco.
        
        Args:
            files_data: Lista de dicts com {'name': str, 'content': bytes}
            subject: Etiqueta de assunto opcional.
        """
        if not self.engine:
            self.initialize_engine()
            
        all_docs = []
        for file_info in files_data:
            suffix = Path(file_info['name']).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(file_info['content'])
                tmp_path = tmp.name
            
            try:
                extra_meta = {"uploaded_filename": file_info['name']}
                if subject.strip():
                    extra_meta["subject"] = subject.strip()
                
                docs = self.loader.load_pdf(tmp_path, extra_metadata=extra_meta)
                all_docs.extend(docs)
            finally:
                Path(tmp_path).unlink(missing_ok=True)
        
        if all_docs:
            self.engine.index_documents(all_docs)
            return {"success": True, "count": len(all_docs)}
        
        return {"success": False, "message": "Nenhum documento extraído."}

    def ask_question(self, question: str, subject_filter: Optional[str] = None) -> str:
        """Executa uma query no motor RAG."""
        if not self.engine:
            raise RuntimeError("Motor RAG não inicializado.")
            
        return self.engine.query(
            question, 
            use_chat_memory=False, 
            subject_filter=subject_filter
        )

    def get_database_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas da base de conhecimento atual."""
        try:
            client = chromadb.HttpClient(
                host=self.config.chroma_host, 
                port=self.config.chroma_port
            )
            collection = client.get_collection(name="hermes_documents")
            results = collection.get()
            
            files_info = {}
            for meta in results['metadatas']:
                fname = meta.get('file_name', 'Desconhecido')
                subj = meta.get('subject', 'Sem Assunto')
                if fname not in files_info:
                    files_info[fname] = {"subject": subj, "chunks": 0}
                files_info[fname]["chunks"] += 1
                
            return {
                "total_files": len(files_info),
                "files": files_info
            }
        except Exception:
            return {"total_files": 0, "files": {}}

    def clear_database(self):
        """Limpa toda a base de conhecimento."""
        if self.engine:
            self.engine.clear_index()
        else:
            # Fallback se o motor não estiver ativo mas o banco estiver rodando
            client = chromadb.HttpClient(
                host=self.config.chroma_host, 
                port=self.config.chroma_port
            )
            try:
                client.delete_collection("hermes_documents")
            except Exception:
                pass
