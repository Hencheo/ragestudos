from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import uvicorn
import os
import sys

# Adiciona a raiz do projeto ao path para importar de src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services import HermesService
from src.config import RAGConfig

app = FastAPI(title="Hermes RAG API")

# Configuração de CORS para permitir que o Next.js acesse a API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Em produção, especifique a URL do frontend
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
    files: List[UploadFile] = File(...), 
    subject: str = Form("")
):
    if not service:
        raise HTTPException(status_code=500, detail="Serviço não inicializado")
    
    files_data = []
    for file in files:
        content = await file.read()
        files_data.append({"name": file.filename, "content": content})
    
    result = service.process_and_index_files(files_data, subject)
    return result

@app.post("/query")
async def query_rag(
    question: str = Form(...), 
    subject: Optional[str] = Form(None)
):
    if not service:
        raise HTTPException(status_code=500, detail="Serviço não inicializado")
    
    if not service.engine:
        service.initialize_engine()
        
    try:
        response = service.ask_question(question, subject_filter=subject)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/clear")
def clear_db():
    if not service:
        raise HTTPException(status_code=500, detail="Serviço não inicializado")
    service.clear_database()
    return {"success": True}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
