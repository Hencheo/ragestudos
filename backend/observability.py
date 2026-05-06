"""Módulo de observabilidade do Hermes RAG Engine.

Fornece:
- Logging estruturado em JSON
- Middleware de request logging com correlation ID
- Métricas in-memory para monitoramento
- Health check real (ChromaDB + Engine)
- Timer decorator para medir duração de operações
"""

import time
import uuid
import logging
import functools
from typing import Optional, Dict, Any
from datetime import datetime
from contextvars import ContextVar
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# --- Context Variables ---
request_id_var: ContextVar[str] = ContextVar("request_id", default="no-request")


# --- Structured Logger Setup ---

class StructuredFormatter(logging.Formatter):
    """Formatter que adiciona request_id e timestamps ISO em cada log."""

    def format(self, record: logging.LogRecord) -> str:
        record.request_id = request_id_var.get("no-request")
        record.timestamp = datetime.utcnow().isoformat() + "Z"

        # Formato estruturado legível
        level = record.levelname
        msg = record.getMessage()
        module = record.module
        req_id = record.request_id[:8]

        base = f"[{record.timestamp}] [{level}] [{req_id}] {module}: {msg}"

        if record.exc_info and record.exc_info[0]:
            base += "\n" + self.formatException(record.exc_info)

        return base


def setup_logging(level: int = logging.INFO) -> None:
    """Configura logging estruturado para toda a aplicação."""
    root = logging.getLogger()

    # Remove handlers existentes para evitar duplicação
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter())
    root.addHandler(handler)
    root.setLevel(level)

    # Silencia loggers excessivamente verbosos
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


# --- Request Logging Middleware ---

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware que loga cada request com método, path, status e duração."""

    async def dispatch(self, request: Request, call_next) -> Response:
        req_id = str(uuid.uuid4())
        request_id_var.set(req_id)

        start_time = time.perf_counter()
        method = request.method
        path = request.url.path

        logger = logging.getLogger("hermes.http")

        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000
            status = response.status_code

            log_msg = f"{method} {path} → {status} ({duration_ms:.0f}ms)"

            if status >= 500:
                logger.error(log_msg)
            elif status >= 400:
                logger.warning(log_msg)
            else:
                logger.info(log_msg)

            # Registra métrica
            Metrics.record_request(method, path, status, duration_ms)

            # Adiciona headers de rastreabilidade
            response.headers["X-Request-ID"] = req_id
            return response

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"{method} {path} → EXCEPTION ({duration_ms:.0f}ms): {e}")
            Metrics.record_request(method, path, 500, duration_ms)
            raise


# --- In-Memory Metrics ---

class Metrics:
    """Métricas in-memory simples para monitoramento."""

    _data: Dict[str, Any] = {
        "requests_total": 0,
        "requests_by_status": defaultdict(int),
        "requests_by_path": defaultdict(int),
        "errors_total": 0,
        "queries_total": 0,
        "query_duration_ms_sum": 0.0,
        "uploads_total": 0,
        "indexing_duration_ms_sum": 0.0,
        "started_at": datetime.utcnow().isoformat() + "Z",
    }

    @classmethod
    def record_request(cls, method: str, path: str, status: int, duration_ms: float):
        cls._data["requests_total"] += 1
        cls._data["requests_by_status"][str(status)] += 1
        cls._data["requests_by_path"][f"{method} {path}"] += 1
        if status >= 500:
            cls._data["errors_total"] += 1

    @classmethod
    def record_query(cls, duration_ms: float):
        cls._data["queries_total"] += 1
        cls._data["query_duration_ms_sum"] += duration_ms

    @classmethod
    def record_upload(cls, duration_ms: float):
        cls._data["uploads_total"] += 1
        cls._data["indexing_duration_ms_sum"] += duration_ms

    @classmethod
    def get_summary(cls) -> Dict[str, Any]:
        data = cls._data.copy()
        data["requests_by_status"] = dict(data["requests_by_status"])
        data["requests_by_path"] = dict(data["requests_by_path"])

        # Médias
        if data["queries_total"] > 0:
            data["query_avg_ms"] = round(data["query_duration_ms_sum"] / data["queries_total"], 1)
        else:
            data["query_avg_ms"] = 0

        return data

    @classmethod
    def reset(cls):
        cls._data["requests_total"] = 0
        cls._data["requests_by_status"] = defaultdict(int)
        cls._data["requests_by_path"] = defaultdict(int)
        cls._data["errors_total"] = 0
        cls._data["queries_total"] = 0
        cls._data["query_duration_ms_sum"] = 0.0
        cls._data["uploads_total"] = 0
        cls._data["indexing_duration_ms_sum"] = 0.0


# --- Timer Decorator ---

def timed(operation_name: str):
    """Decorator que mede e loga a duração de uma operação."""
    def decorator(func):
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = logging.getLogger("hermes.timing")
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                elapsed = (time.perf_counter() - start) * 1000
                logger.info(f"⏱ {operation_name}: {elapsed:.0f}ms")
                return result
            except Exception as e:
                elapsed = (time.perf_counter() - start) * 1000
                logger.error(f"⏱ {operation_name}: FAILED after {elapsed:.0f}ms — {e}")
                raise

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = logging.getLogger("hermes.timing")
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                elapsed = (time.perf_counter() - start) * 1000
                logger.info(f"⏱ {operation_name}: {elapsed:.0f}ms")
                return result
            except Exception as e:
                elapsed = (time.perf_counter() - start) * 1000
                logger.error(f"⏱ {operation_name}: FAILED after {elapsed:.0f}ms — {e}")
                raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator


# --- Health Check Utility ---

def check_health(service) -> Dict[str, Any]:
    """Verifica saúde real do sistema: engine + ChromaDB."""
    result = {
        "status": "ok",
        "engine_ready": False,
        "chroma_connected": False,
        "chroma_doc_count": 0,
        "uptime_since": Metrics._data.get("started_at"),
    }

    # Verifica engine
    if service and service.engine:
        result["engine_ready"] = service.engine.is_ready()

    # Verifica ChromaDB
    try:
        import chromadb
        from src.config import RAGConfig
        config = RAGConfig()
        client = chromadb.HttpClient(host=config.chroma_host, port=config.chroma_port)
        client.heartbeat()
        result["chroma_connected"] = True

        try:
            col = client.get_collection("hermes_documents")
            result["chroma_doc_count"] = col.count()
        except Exception:
            pass
    except Exception:
        result["status"] = "degraded"

    if not result["engine_ready"] and not result["chroma_connected"]:
        result["status"] = "unhealthy"

    return result
