from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import uvicorn
import os
import sys

# Adiciona a raiz do projeto ao path para importar de src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from src.services import HermesService
from src.config import RAGConfig
from src.utils.task_manager import TaskManager

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Hermes RAG API")

# ... (CORS configuration remains the same)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializa o serviço
try:
    config = RAGConfig()
    service = HermesService(config)
except Exception as e:
    print(f"Erro ao carregar configuração: {e}")
    service = None

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/stats")
def get_stats():
    if not service:
        raise HTTPException(status_code=500, detail="Serviço não inicializado")
    return service.get_database_stats()

@app.post("/upload")
async def upload_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...), 
    subject: str = Form(""),
    use_ocr: bool = Form(True)
):
    if not service:
        raise HTTPException(status_code=500, detail="Serviço não inicializado")
    
    files_data = []
    print(f"📥 Recebendo {len(files)} arquivos para indexação (Assunto: {subject}, OCR: {use_ocr})...")
    for file in files:
        content = await file.read()
        files_data.append({"name": file.filename, "content": content})
    
    # Cria uma tarefa no TaskManager
    task_id = TaskManager.create_task(total_files=len(files), subject=subject)
    
    # Agenda o processamento em background
    background_tasks.add_task(run_upload_task, task_id, files_data, subject, use_ocr)
    
    return {"success": True, "task_id": task_id, "message": "Upload recebido. Processamento iniciado em segundo plano."}

def run_upload_task(task_id: str, files_data: list, subject: str, use_ocr: bool):
    """Função que roda em background para processar os arquivos."""
    try:
        service.process_and_index_files(files_data, subject, task_id=task_id, use_ocr=use_ocr)
    except Exception as e:
        import traceback
        traceback.print_exc()
        TaskManager.update_task(task_id, status="failed", message=f"Erro fatal: {str(e)}")

@app.get("/upload/status/{task_id}")
def get_upload_status(task_id: str):
    task = TaskManager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    return task
    
@app.post("/upload/cancel/{task_id}")
def cancel_upload(task_id: str):
    TaskManager.cancel_task(task_id)
    return {"success": True, "message": "Solicitação de cancelamento enviada."}


@app.post("/query")
def query_rag(
    question: str = Form(...), 
    subject: Optional[str] = Form(None)
):
    if not service:
        raise HTTPException(status_code=500, detail="Serviço não inicializado")
    
    if not service.engine:
        service.initialize_engine()
        
    try:
        response = service.ask_question(question, subject_filter=subject)
        logger.info(f"Resposta gerada para '{question[:30]}...': {len(response)} caracteres")
        return {"response": response}
    except Exception as e:
        logger.error(f"Erro na query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/clear")
def clear_db():
    if not service:
        raise HTTPException(status_code=500, detail="Serviço não inicializado")
    return service.clear_database()

@app.delete("/documents/{file_name}")
def delete_document(file_name: str):
    if not service:
        raise HTTPException(status_code=500, detail="Serviço não inicializado")
    result = service.delete_document(file_name)
    if not result["success"]:
        raise HTTPException(status_code=500, detail="Falha ao deletar documento")
    return result

@app.get("/config")
def get_config():
    if not service:
        raise HTTPException(status_code=500, detail="Serviço não inicializado")
    return {
        "llm_provider": service.config.llm_provider,
        "model_name": service.config.model_name
    }

@app.post("/config")
def update_config(
    llm_provider: str = Form(...),
    model_name: str = Form(...)
):
    if not service:
        raise HTTPException(status_code=500, detail="Serviço não inicializado")
    
    service.config.llm_provider = llm_provider
    service.config.model_name = model_name
    # Re-inicializa o motor para aplicar as mudanças de modelo/provedor
    service.initialize_engine()
    return {"status": "success", "provider": llm_provider, "model": model_name}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
