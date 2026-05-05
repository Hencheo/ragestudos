import logging
import tempfile
from pathlib import Path
from typing import List, Optional, Dict, Any
import chromadb

from .rag_engine import RAGEngine
from .document_loader import PDFDocumentLoader
from .config import RAGConfig

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

    def process_and_index_files(
        self, 
        files_data: List[Dict[str, Any]], 
        subject: str = "",
        task_id: Optional[str] = None,
        use_ocr: bool = True
    ) -> Dict[str, Any]:
        """Processa arquivos (bytes) e indexa no banco.
        
        Args:
            files_data: Lista de dicts com {'name': str, 'content': bytes}
            subject: Etiqueta de assunto opcional.
            task_id: ID da tarefa para rastrear progresso.
        """
        from .utils.task_manager import TaskManager
        
        if not self.engine:
            self.initialize_engine()
            
        all_docs = []
        total_files = len(files_data)
        
        for i, file_info in enumerate(files_data):
            if task_id and TaskManager.is_cancelled(task_id):
                logger.info(f"Tarefa {task_id} cancelada. Interrompendo processamento.")
                return {"success": False, "message": "Processamento cancelado pelo usuário."}

            suffix = Path(file_info['name']).suffix
            current_progress = int((i / total_files) * 100)
            
            if task_id:
                TaskManager.update_task(task_id, 
                    progress=current_progress, 
                    message=f"Processando arquivo {i+1} de {total_files}: {file_info['name']}",
                    processed_files=i
                )

            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(file_info['content'])
                tmp_path = tmp.name
            
            try:
                extra_meta = {"uploaded_filename": file_info['name']}
                if subject.strip():
                    extra_meta["subject"] = subject.strip()
                
                # Callback para progresso interno de cada arquivo
                def internal_callback(step_progress, step_msg):
                    if task_id:
                        if TaskManager.is_cancelled(task_id):
                            raise RuntimeError("CANCELLED_BY_USER")
                            
                        # O progresso interno (0-100) é mapeado para o slot do arquivo atual
                        file_slot_size = 100 / total_files
                        total_progress = int(current_progress + (step_progress * file_slot_size / 100))
                        TaskManager.update_task(task_id, progress=total_progress, message=step_msg)

                docs = self.loader.load_pdf(
                    tmp_path, 
                    extra_metadata=extra_meta, 
                    progress_callback=internal_callback,
                    use_ocr=use_ocr
                )
                
                # Extração Automática de Metadados via IA
                if docs and self.engine:
                    if task_id:
                        TaskManager.update_task(task_id, progress=85, message=f"Extraindo metadados inteligentes (IA) de {file_info['name']}...")
                    
                    # Usa o conteúdo do primeiro documento (página 1) para extrair metadados
                    ai_metadata = self.engine.extract_metadata_from_text(docs[0].text)
                    
                    # Aplica os metadados da IA em todos os chunks/páginas do arquivo
                    for doc in docs:
                        doc.metadata.update(ai_metadata)
                        
                    # Indexação imediata do arquivo processado (mais seguro e evita Payload too large)
                    if task_id:
                        TaskManager.update_task(task_id, progress=90, message=f"Indexando {file_info['name']} no banco vetorial...")
                    
                    self.engine.index_documents(docs)
                    all_docs.extend(docs)

            except RuntimeError as e:
                if str(e) == "CANCELLED_BY_USER":
                    logger.info(f"Processamento cancelado durante extração do arquivo {file_info['name']}")
                    return {"success": False, "message": "Processamento cancelado pelo usuário."}
                raise e
            finally:
                Path(tmp_path).unlink(missing_ok=True)
        
        if all_docs:
            if task_id:
                TaskManager.update_task(task_id, status="completed", progress=100, message="Processamento e indexação concluídos com sucesso!", processed_files=total_files)
            
            return {"success": True, "count": len(all_docs)}
        
        if task_id:
            TaskManager.update_task(task_id, status="failed", message="Nenhum documento extraído.")
            
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
        if not self.engine:
            self.initialize_engine()
            
        if self.engine:
            self.engine.clear_index()
            return {"success": True}
        return {"success": False, "message": "Motor não inicializado."}

    def delete_document(self, file_name: str) -> Dict[str, Any]:
        """Deleta um documento específico da base."""
        if not self.engine:
            self.initialize_engine()
            
        if self.engine:
            success = self.engine.delete_document(file_name)
            return {"success": success}
        return {"success": False, "message": "Motor não inicializado."}
