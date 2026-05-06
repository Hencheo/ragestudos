"""Schemas de validação para todos os endpoints da API Hermes.

Define modelos Pydantic para request/response com validação rigorosa
de tamanhos, tipos e sanitização de strings.
"""

import re
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


# --- Constantes de Validação ---
MAX_QUESTION_LENGTH = 5000
MAX_SUBJECT_LENGTH = 100
MAX_FILENAME_LENGTH = 255
MAX_FILES_PER_UPLOAD = 10
MAX_FILE_SIZE_MB = 100
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx", ".pptx", ".xlsx", ".html", ".png", ".jpg", ".jpeg"}
ALLOWED_PROVIDERS = {"google gemini", "openai", "fireworks ai", "fireworks"}
ALLOWED_MIME_PREFIXES = {
    "application/pdf", "text/plain", "text/html",
    "image/png", "image/jpeg",
    "application/vnd.openxmlformats-officedocument",
}


def sanitize_string(value: str, max_length: int = 500) -> str:
    """Remove caracteres perigosos e limita tamanho."""
    # Remove null bytes e caracteres de controle
    value = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', value)
    # Remove path traversal
    value = value.replace('../', '').replace('..\\', '')
    return value[:max_length].strip()


def sanitize_filename(name: str) -> str:
    """Sanitiza nome de arquivo removendo path traversal e caracteres perigosos."""
    # Remove diretórios (mantém apenas o basename)
    name = name.replace('\\', '/').split('/')[-1]
    # Remove caracteres perigosos
    name = re.sub(r'[<>:"|?*\x00-\x1f]', '_', name)
    # Remove path traversal
    name = name.replace('..', '_')
    return name[:MAX_FILENAME_LENGTH].strip()


# --- Request Schemas ---

class QueryRequest(BaseModel):
    """Schema para o endpoint /query."""
    question: str = Field(..., min_length=1, max_length=MAX_QUESTION_LENGTH)
    subject: Optional[str] = Field(None, max_length=MAX_SUBJECT_LENGTH)

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        v = sanitize_string(v, MAX_QUESTION_LENGTH)
        if not v.strip():
            raise ValueError("Pergunta não pode estar vazia")
        return v

    @field_validator("subject")
    @classmethod
    def validate_subject(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = sanitize_string(v, MAX_SUBJECT_LENGTH)
            if not v.strip():
                return None
        return v


class ConfigUpdateRequest(BaseModel):
    """Schema para o endpoint POST /config."""
    llm_provider: str = Field(..., min_length=1, max_length=50)
    model_name: str = Field(..., min_length=1, max_length=200)

    @field_validator("llm_provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        v = sanitize_string(v, 50)
        if v.lower() not in ALLOWED_PROVIDERS:
            raise ValueError(f"Provedor inválido. Permitidos: {ALLOWED_PROVIDERS}")
        return v

    @field_validator("model_name")
    @classmethod
    def validate_model(cls, v: str) -> str:
        v = sanitize_string(v, 200)
        # Apenas alfanuméricos, hifens, barras e pontos
        if not re.match(r'^[a-zA-Z0-9/_\-.:]+$', v):
            raise ValueError("Nome do modelo contém caracteres inválidos")
        return v


class DeleteDocumentRequest(BaseModel):
    """Schema para validar nome do documento a deletar."""
    file_name: str = Field(..., min_length=1, max_length=MAX_FILENAME_LENGTH)

    @field_validator("file_name")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        return sanitize_filename(v)


# --- Response Schemas ---

class HealthResponse(BaseModel):
    """Response do health check."""
    status: str
    engine_ready: bool
    chroma_connected: bool

class UploadResponse(BaseModel):
    """Response do upload."""
    success: bool
    task_id: Optional[str] = None
    message: str

class QueryResponse(BaseModel):
    """Response da query."""
    response: str

class ErrorResponse(BaseModel):
    """Response de erro padronizado."""
    detail: str
    error_code: Optional[str] = None


def validate_upload_files(files_data: list) -> list:
    """Valida arquivos de upload: extensão, tamanho, quantidade.
    
    Args:
        files_data: Lista de dicts com 'name' e 'content'.
        
    Returns:
        Lista validada e sanitizada.
        
    Raises:
        ValueError: Se alguma validação falhar.
    """
    if len(files_data) > MAX_FILES_PER_UPLOAD:
        raise ValueError(f"Máximo de {MAX_FILES_PER_UPLOAD} arquivos por upload")

    if not files_data:
        raise ValueError("Nenhum arquivo enviado")

    validated = []
    for f in files_data:
        name = sanitize_filename(f["name"])
        content = f["content"]

        # Validar extensão
        ext = '.' + name.rsplit('.', 1)[-1].lower() if '.' in name else ''
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Extensão '{ext}' não permitida em '{name}'. Permitidas: {ALLOWED_EXTENSIONS}")

        # Validar tamanho
        size = len(content)
        if size > MAX_FILE_SIZE_BYTES:
            raise ValueError(f"Arquivo '{name}' excede o limite de {MAX_FILE_SIZE_MB}MB ({size / 1024 / 1024:.1f}MB)")

        if size == 0:
            raise ValueError(f"Arquivo '{name}' está vazio")

        validated.append({"name": name, "content": content})

    return validated
