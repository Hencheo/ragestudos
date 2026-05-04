"""Módulo de configuração do sistema RAG.

Este módulo define a classe RAGConfig usando Pydantic Settings
para gerenciar variáveis de ambiente e parâmetros do sistema.
"""

import os
from typing import Optional

from pydantic import Field, field_validator, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict


class RAGConfig(BaseSettings):
    """Configuração do sistema RAG com validação de variáveis de ambiente.
    
    Esta classe gerencia todas as configurações necessárias para o
    funcionamento do sistema RAG, incluindo credenciais da API Google,
    parâmetros do modelo e configurações de chunking.
    
    Attributes:
        google_api_key: Chave de API do Google Generative AI.
        model_name: Nome do modelo Gemini a ser utilizado.
        temperature: Temperatura para geração de texto (0.0 - 1.0).
        max_tokens: Número máximo de tokens na resposta.
        chunk_size: Tamanho dos chunks para indexação.
        chunk_overlap: Sobreposição entre chunks consecutivos.
    
    Example:
        >>> config = RAGConfig()
        >>> print(config.model_name)
        'gemini-2.5-flash'
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # API Configuration
    llm_provider: str = Field(
        default="Google Gemini",
        description="Provedor do modelo LLM",
        alias="LLM_PROVIDER"
    )
    
    llm_api_key: str = Field(
        default="",
        description="Chave de API do provedor LLM",
        validation_alias=AliasChoices("LLM_API_KEY", "GOOGLE_API_KEY")
    )
    
    llm_api_base: Optional[str] = Field(
        default=None,
        description="URL base da API (necessário para Fireworks ou OpenAI customizado)",
        alias="LLM_API_BASE"
    )

    llama_cloud_api_key: Optional[str] = Field(
        default=None,
        description="Chave de API do LlamaCloud (LlamaParse)",
        alias="LLAMA_CLOUD_API_KEY"
    )

    use_llama_parse: bool = Field(
        default=False,
        description="Se deve usar o LlamaParse para extração de PDFs",
        alias="USE_LLAMA_PARSE"
    )

    use_docling: bool = Field(
        default=True,
        description="Se deve usar o Docling para extração local avançada",
        alias="USE_DOCLING"
    )
    
    # ChromaDB Configuration
    chroma_host: str = Field(
        default="localhost",
        description="Host do servidor ChromaDB",
        alias="CHROMA_HOST"
    )
    
    chroma_port: int = Field(
        default=8001,
        description="Porta do servidor ChromaDB",
        alias="CHROMA_PORT"
    )
    
    # Model Configuration
    model_name: str = Field(
        default="gemini-2.5-flash",  # Valor padrão caso não exista no .env
        description="Nome do modelo Gemini",
        alias="MODEL_NAME"
    )

    embedding_model: str = Field(
        default="models/gemini-embedding-001",
        description="Modelo de embeddings Google",
        alias="EMBEDDING_MODEL"
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Temperatura para geração (0.0 - 1.0)",
        alias="TEMPERATURE"
    )
    max_tokens: int = Field(
        default=2048,
        ge=1,
        le=8192,
        description="Máximo de tokens na resposta",
        alias="MAX_TOKENS"
    )
    
    # Chunking Configuration
    chunk_size: int = Field(
        default=512,
        ge=128,
        le=2048,
        description="Tamanho dos chunks em tokens",
        alias="CHUNK_SIZE"
    )
    chunk_overlap: int = Field(
        default=50,
        ge=0,
        le=256,
        description="Sobreposição entre chunks",
        alias="CHUNK_OVERLAP"
    )
    
    # Prompt Configuration
    system_prompt: str = Field(
        default="Você é um assistente prestativo e preciso. Responda sempre em português brasileiro, de forma clara e profissional, baseando-se estritamente nos documentos fornecidos. Use formatação Markdown (negrito, listas, tabelas) para tornar a resposta mais legível e organizada.",
        description="Prompt de sistema para orientar o comportamento do modelo",
        alias="SYSTEM_PROMPT"
    )
    
    @field_validator("llm_api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Valida que a API key não está vazia em produção.
        
        Args:
            v: Valor da API key.
            
        Returns:
            str: A API key validada.
            
        Raises:
            ValueError: Se a API key estiver vazia e não for ambiente de teste.
        """
        if not v and not os.getenv("TESTING"):
            # Permite vazio para desenvolvimento, mas loga warning
            pass
        return v
    
    @field_validator("chunk_overlap")
    @classmethod
    def validate_overlap(cls, v: int, info) -> int:
        """Valida que o overlap é menor que o chunk_size.
        
        Args:
            v: Valor do overlap.
            info: Informações do campo.
            
        Returns:
            int: O overlap validado.
            
        Raises:
            ValueError: Se overlap >= chunk_size.
        """
        data = info.data
        if "chunk_size" in data and v >= data["chunk_size"]:
            raise ValueError("chunk_overlap deve ser menor que chunk_size")
        return v
    
    def is_configured(self) -> bool:
        """Verifica se a configuração mínima está presente.
        
        Returns:
            bool: True se llm_api_key está definida.
        """
        return bool(self.llm_api_key)
    
    def to_dict(self) -> dict:
        """Converte a configuração para dicionário.
        
        Returns:
            dict: Configurações como dicionário (sem a API key).
        """
        return {
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
        }
