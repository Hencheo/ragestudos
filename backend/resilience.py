"""Módulo de resiliência do Hermes RAG Engine.

Fornece:
- Decorators de retry com backoff exponencial para chamadas externas
- Wrappers para operações ChromaDB com retry
- Circuit breaker simples para APIs externas
"""

import logging
import time
from typing import TypeVar, Callable
from functools import wraps

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log,
)

logger = logging.getLogger("hermes.resilience")

T = TypeVar("T")


# --- Exceções de Retry ---

class RetryableError(Exception):
    """Erro transitório que pode ser resolvido com retry."""
    pass


class NonRetryableError(Exception):
    """Erro permanente que não deve ser retried."""
    pass


# --- Retry Decorators ---

def retry_llm_call(func: Callable[..., T]) -> Callable[..., T]:
    """Retry para chamadas LLM (OpenAI, Gemini, Fireworks).
    
    3 tentativas com backoff exponencial: 1s, 2s, 4s.
    Retries em: ConnectionError, TimeoutError, exceções genéricas de API.
    """
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((
            ConnectionError,
            TimeoutError,
            OSError,
        )),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_str = str(e).lower()
            # Retry em erros transitórios conhecidos
            if any(kw in error_str for kw in [
                "rate limit", "429", "503", "502", "timeout",
                "connection", "temporarily", "overloaded", "quota"
            ]):
                logger.warning(f"Erro transitório na chamada LLM, tentando novamente: {e}")
                raise ConnectionError(str(e)) from e
            # Não retry em erros de autenticação, validação, etc.
            raise
    return wrapper


def retry_chroma_call(func: Callable[..., T]) -> Callable[..., T]:
    """Retry para operações ChromaDB.
    
    3 tentativas com backoff: 0.5s, 1s, 2s.
    """
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=5),
        retry=retry_if_exception_type((
            ConnectionError,
            TimeoutError,
            OSError,
            ConnectionRefusedError,
        )),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_str = str(e).lower()
            if any(kw in error_str for kw in [
                "connection", "refused", "timeout", "unavailable"
            ]):
                logger.warning(f"ChromaDB indisponível, tentando novamente: {e}")
                raise ConnectionError(str(e)) from e
            raise
    return wrapper


def retry_ocr_page(func: Callable[..., T]) -> Callable[..., T]:
    """Retry para processamento OCR de uma página individual.
    
    2 tentativas com wait fixo de 1s.
    """
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=3),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


# --- Circuit Breaker Simples ---

class CircuitBreaker:
    """Circuit breaker simples para proteger APIs externas.
    
    Após N falhas consecutivas, abre o circuito por T segundos,
    rejeitando chamadas imediatamente ao invés de sobrecarregar a API.
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0, name: str = "default"):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.name = name
        self._failures = 0
        self._last_failure_time = 0.0
        self._state = "closed"  # closed, open, half-open

    @property
    def state(self) -> str:
        if self._state == "open":
            elapsed = time.time() - self._last_failure_time
            if elapsed >= self.recovery_timeout:
                self._state = "half-open"
        return self._state

    def record_success(self):
        self._failures = 0
        self._state = "closed"

    def record_failure(self):
        self._failures += 1
        self._last_failure_time = time.time()
        if self._failures >= self.failure_threshold:
            self._state = "open"
            logger.error(
                f"Circuit breaker '{self.name}' ABERTO após {self._failures} falhas. "
                f"Recuperação em {self.recovery_timeout}s."
            )

    def can_execute(self) -> bool:
        state = self.state
        if state == "closed":
            return True
        if state == "half-open":
            return True  # Permite uma tentativa para testar
        return False

    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """Usa como decorator."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not self.can_execute():
                raise RetryableError(
                    f"Circuit breaker '{self.name}' aberto. "
                    f"Tente novamente em {self.recovery_timeout}s."
                )
            try:
                result = func(*args, **kwargs)
                self.record_success()
                return result
            except Exception as e:
                self.record_failure()
                raise
        return wrapper


# Instâncias globais dos circuit breakers
llm_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30, name="llm")
chroma_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=15, name="chromadb")
