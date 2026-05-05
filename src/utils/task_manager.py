import uuid
from typing import Dict, Any, Optional
from datetime import datetime
import threading

class TaskManager:
    """Gerenciador de tarefas assíncronas para o Hermes.
    
    Permite rastrear o progresso de operações pesadas como OCR e indexação.
    """
    _tasks: Dict[str, Dict[str, Any]] = {}
    _lock = threading.Lock()

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
