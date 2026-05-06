"""Gerenciador de tarefas assíncronas para o Hermes.

Permite rastrear o progresso de operações pesadas como OCR e indexação.
Inclui limpeza automática de tasks antigas para evitar memory leak.
"""

import uuid
from typing import Dict, Any, Optional
from datetime import datetime
import threading
import time
import logging

logger = logging.getLogger("hermes.tasks")

# Tempo máximo que uma task fica na memória (1 hora)
TASK_TTL_SECONDS = 3600
# Intervalo de limpeza (a cada 100 operações)
CLEANUP_INTERVAL = 100


class TaskManager:
    """Gerenciador de tarefas assíncronas para o Hermes.
    
    Permite rastrear o progresso de operações pesadas como OCR e indexação.
    Tasks são automaticamente limpas após 1 hora para evitar memory leak.
    """
    _tasks: Dict[str, Dict[str, Any]] = {}
    _lock = threading.Lock()
    _op_counter = 0

    @classmethod
    def _maybe_cleanup(cls):
        """Remove tasks expiradas a cada N operações (chamado dentro do lock)."""
        cls._op_counter += 1
        if cls._op_counter % CLEANUP_INTERVAL != 0:
            return

        now = time.time()
        expired = []
        for task_id, task in cls._tasks.items():
            created_str = task.get("created_at", "")
            try:
                created_dt = datetime.fromisoformat(created_str)
                age = now - created_dt.timestamp()
                if age > TASK_TTL_SECONDS and task.get("status") in ("completed", "failed", "cancelled"):
                    expired.append(task_id)
            except (ValueError, TypeError):
                continue

        for task_id in expired:
            del cls._tasks[task_id]

        if expired:
            logger.info(f"TaskManager: limpou {len(expired)} tasks expiradas. {len(cls._tasks)} restantes.")

    @classmethod
    def create_task(cls, total_files: int, subject: str = "") -> str:
        task_id = str(uuid.uuid4())
        with cls._lock:
            cls._tasks[task_id] = {
                "id": task_id,
                "status": "processing",
                "progress": 0,
                "message": "Iniciando processamento...",
                "total_files": total_files,
                "processed_files": 0,
                "subject": subject,
                "created_at": datetime.now().isoformat(),
                "result": None,
                "error": None
            }
            cls._maybe_cleanup()
        logger.info(f"Task criada: {task_id} ({total_files} arquivos)")
        return task_id

    @classmethod
    def update_task(cls, task_id: str, **kwargs):
        with cls._lock:
            if task_id in cls._tasks:
                cls._tasks[task_id].update(kwargs)

    @classmethod
    def cancel_task(cls, task_id: str):
        with cls._lock:
            if task_id in cls._tasks:
                cls._tasks[task_id]["status"] = "cancelled"
                cls._tasks[task_id]["message"] = "Processamento interrompido pelo usuário."
        logger.info(f"Task cancelada: {task_id}")

    @classmethod
    def is_cancelled(cls, task_id: str) -> bool:
        with cls._lock:
            task = cls._tasks.get(task_id)
            return task is not None and task.get("status") == "cancelled"

    @classmethod
    def get_task(cls, task_id: str) -> Optional[Dict[str, Any]]:
        with cls._lock:
            return cls._tasks.get(task_id)

    @classmethod
    def list_tasks(cls) -> Dict[str, Dict[str, Any]]:
        with cls._lock:
            return cls._tasks.copy()

    @classmethod
    def active_count(cls) -> int:
        """Retorna o número de tasks em processamento ativo."""
        with cls._lock:
            return sum(1 for t in cls._tasks.values() if t.get("status") == "processing")
