"""API FastAPI do Hermes RAG Engine.

Endpoints com validação, rate limiting, observabilidade e resiliência.
"""

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import uvicorn
import os
import sys
import time
import hashlib
import asyncio
import threading

# Adiciona a raiz do projeto ao path para importar de src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from src.services import HermesService
from src.config import RAGConfig
from src.utils.task_manager import TaskManager

# Módulos de robustez
from backend.schemas import (
    QueryRequest, ConfigUpdateRequest, DeleteDocumentRequest,
    validate_upload_files, sanitize_string, sanitize_filename,
    MAX_QUESTION_LENGTH, MAX_SUBJECT_LENGTH, MAX_FILES_PER_UPLOAD,
    ALLOWED_PROVIDERS,
)
from backend.observability import (
    setup_logging, RequestLoggingMiddleware, Metrics, check_health, timed
)

# --- Logging Estruturado ---
setup_logging(level=logging.INFO)
logger = logging.getLogger("hermes.api")

# --- App ---
app = FastAPI(title="Hermes RAG API", version="1.1.0")

# CORS (restritivo — apenas o frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware de observabilidade (request logging + correlation ID)
app.add_middleware(RequestLoggingMiddleware)

# --- Rate Limiting ---
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- State: Engine + Locks ---
_engine_lock = threading.Lock()
_upload_lock = asyncio.Lock()

# Cache de idempotência para uploads (hash → resultado)
_idempotency_cache: dict = {}  # {content_hash: {"task_id": ..., "timestamp": ...}}
_IDEMPOTENCY_TTL = 3600  # 1 hora

# Cache de queries (question_hash → response)
_query_cache: dict = {}
_QUERY_CACHE_TTL = 300  # 5 minutos

# Inicializa o serviço
try:
    config = RAGConfig()
    service = HermesService(config)
    logger.info("HermesService inicializado com sucesso")
except Exception as e:
    logger.error(f"Erro ao carregar configuração: {e}", exc_info=True)
    service = None


def _ensure_service():
    """Garante que o serviço está disponível, ou levanta HTTPException."""
    if not service:
        raise HTTPException(status_code=503, detail="Serviço não inicializado. Verifique as configurações.")


def _cleanup_cache(cache: dict, ttl: int):
    """Remove entradas expiradas de um cache."""
    now = time.time()
    expired = [k for k, v in cache.items() if now - v.get("_ts", 0) > ttl]
    for k in expired:
        del cache[k]


# ============================
# ENDPOINTS
# ============================

@app.get("/health")
def health_check():
    """Health check real: verifica ChromaDB, Engine e status geral."""
    return check_health(service)


@app.get("/metrics")
def get_metrics():
    """Retorna métricas de uso da API."""
    return Metrics.get_summary()


@app.get("/stats")
@limiter.limit("30/minute")
def get_stats(request: Request):
    _ensure_service()
    return service.get_database_stats()


@app.post("/upload")
@limiter.limit("10/minute")
async def upload_files(
    request: Request,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    subject: str = Form(""),
    use_ocr: bool = Form(True),
):
    _ensure_service()

    # Validação de quantidade
    if len(files) > MAX_FILES_PER_UPLOAD:
        raise HTTPException(status_code=400, detail=f"Máximo de {MAX_FILES_PER_UPLOAD} arquivos por upload")

    # Sanitiza subject
    subject = sanitize_string(subject, MAX_SUBJECT_LENGTH)

    # Lê e valida arquivos
    files_data = []
    content_parts = []
    for file in files:
        content = await file.read()
        name = sanitize_filename(file.filename or "unknown.pdf")
        files_data.append({"name": name, "content": content})
        content_parts.append(content)

    # Valida extensões, tamanhos, etc.
    try:
        files_data = validate_upload_files(files_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # --- IDEMPOTÊNCIA: hash do conteúdo ---
    content_hash = hashlib.sha256(b"".join(content_parts)).hexdigest()
    _cleanup_cache(_idempotency_cache, _IDEMPOTENCY_TTL)

    if content_hash in _idempotency_cache:
        cached = _idempotency_cache[content_hash]
        logger.info(f"Upload duplicado detectado (hash: {content_hash[:12]}...), retornando resultado anterior")
        return {
            "success": True,
            "task_id": cached.get("task_id"),
            "message": "Upload já processado anteriormente. Retornando resultado existente.",
            "deduplicated": True,
        }

    # --- DEDUPLICAÇÃO: verifica se arquivos já existem no ChromaDB ---
    try:
        if service.engine and hasattr(service.engine, 'chroma_collection'):
            for f in files_data:
                existing = service.engine.chroma_collection.get(
                    where={"file_name": f["name"]},
                    limit=1
                )
                if existing and existing.get("ids"):
                    logger.warning(f"Arquivo '{f['name']}' já indexado ({len(existing['ids'])} chunks). Será reindexado.")
    except Exception as e:
        logger.warning(f"Erro ao verificar duplicação: {e}")

    logger.info(f"📥 Recebendo {len(files_data)} arquivos para indexação (Assunto: {subject}, OCR: {use_ocr})")

    # Cria tarefa no TaskManager
    task_id = TaskManager.create_task(total_files=len(files_data), subject=subject)

    # Registra no cache de idempotência
    _idempotency_cache[content_hash] = {"task_id": task_id, "_ts": time.time()}

    # Agenda o processamento em background
    background_tasks.add_task(run_upload_task, task_id, files_data, subject, use_ocr)

    return {"success": True, "task_id": task_id, "message": "Upload recebido. Processamento iniciado em segundo plano."}


def run_upload_task(task_id: str, files_data: list, subject: str, use_ocr: bool):
    """Função que roda em background para processar os arquivos."""
    start = time.perf_counter()
    try:
        service.process_and_index_files(files_data, subject, task_id=task_id, use_ocr=use_ocr)
        duration_ms = (time.perf_counter() - start) * 1000
        Metrics.record_upload(duration_ms)
        logger.info(f"Upload task {task_id} concluída em {duration_ms:.0f}ms")
    except Exception as e:
        import traceback
        logger.error(f"Upload task {task_id} falhou: {e}", exc_info=True)
        TaskManager.update_task(task_id, status="failed", message=f"Erro fatal: {str(e)}")


@app.get("/upload/status/{task_id}")
def get_upload_status(task_id: str):
    task = TaskManager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    return task


@app.post("/upload/cancel/{task_id}")
def cancel_upload(task_id: str):
    task = TaskManager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    TaskManager.cancel_task(task_id)
    return {"success": True, "message": "Solicitação de cancelamento enviada."}


@app.post("/query")
@limiter.limit("20/minute")
def query_rag(
    request: Request,
    question: str = Form(...),
    subject: Optional[str] = Form(None),
):
    _ensure_service()

    # Validação
    question = sanitize_string(question, MAX_QUESTION_LENGTH)
    if not question.strip():
        raise HTTPException(status_code=400, detail="Pergunta não pode estar vazia")

    if subject:
        subject = sanitize_string(subject, MAX_SUBJECT_LENGTH)

    # Inicializa engine se necessário (thread-safe)
    if not service.engine:
        with _engine_lock:
            if not service.engine:
                service.initialize_engine()

    # --- CACHE de queries ---
    cache_key = hashlib.md5(f"{question}:{subject or ''}".encode()).hexdigest()
    _cleanup_cache(_query_cache, _QUERY_CACHE_TTL)

    if cache_key in _query_cache:
        logger.info(f"Cache hit para query '{question[:30]}...'")
        return {"response": _query_cache[cache_key]["response"], "cached": True}

    try:
        start = time.perf_counter()
        response = service.ask_question(question, subject_filter=subject)
        duration_ms = (time.perf_counter() - start) * 1000

        Metrics.record_query(duration_ms)
        logger.info(f"Query respondida em {duration_ms:.0f}ms: '{question[:30]}...' → {len(response)} chars")

        # Armazena no cache
        _query_cache[cache_key] = {"response": response, "_ts": time.time()}

        return {"response": response}
    except Exception as e:
        logger.error(f"Erro na query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/clear")
@limiter.limit("5/minute")
def clear_db(request: Request):
    _ensure_service()

    # Limpa caches
    _query_cache.clear()
    _idempotency_cache.clear()

    return service.clear_database()


@app.delete("/documents/{file_name}")
@limiter.limit("10/minute")
def delete_document(request: Request, file_name: str):
    _ensure_service()

    # Sanitiza o nome do arquivo
    file_name = sanitize_filename(file_name)
    if not file_name:
        raise HTTPException(status_code=400, detail="Nome de arquivo inválido")

    result = service.delete_document(file_name)

    # Invalida cache de queries (documento removido pode afetar respostas)
    _query_cache.clear()

    if not result["success"]:
        raise HTTPException(status_code=500, detail="Falha ao deletar documento")
    return result


@app.get("/config")
def get_config():
    _ensure_service()
    return {
        "llm_provider": service.config.llm_provider,
        "model_name": service.config.model_name,
    }


@app.post("/config")
@limiter.limit("5/minute")
def update_config(
    request: Request,
    llm_provider: str = Form(...),
    model_name: str = Form(...),
):
    _ensure_service()

    # Validação
    llm_provider = sanitize_string(llm_provider, 50)
    model_name = sanitize_string(model_name, 200)

    # Salva config anterior para rollback
    prev_provider = service.config.llm_provider
    prev_model = service.config.model_name

    try:
        with _engine_lock:
            service.config.llm_provider = llm_provider
            service.config.model_name = model_name
            service.initialize_engine()

        # Limpa cache de queries (modelo mudou)
        _query_cache.clear()

        logger.info(f"Config atualizada: {llm_provider}/{model_name}")
        return {"status": "success", "provider": llm_provider, "model": model_name}

    except Exception as e:
        # Rollback
        logger.error(f"Falha ao atualizar config, fazendo rollback: {e}")
        service.config.llm_provider = prev_provider
        service.config.model_name = prev_model
        raise HTTPException(
            status_code=500,
            detail=f"Falha ao aplicar configuração. Restaurado para {prev_provider}/{prev_model}. Erro: {str(e)}"
        )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
