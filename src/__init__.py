"""RAG Engine - Sistema de Retrieval-Augmented Generation.

Este pacote fornece componentes para criar um sistema RAG completo
usando LlamaIndex e Google Gemini.

Exports:
    RAGConfig: Configuração do sistema RAG com Pydantic Settings.
    RAGEngine: Motor principal de indexação e query.
    PDFDocumentLoader: Carregador de documentos PDF.

Version:
    1.0.0
"""

from .config import RAGConfig
from .rag_engine import RAGEngine
from .document_loader import PDFDocumentLoader

__version__ = "1.0.0"
__all__ = ["RAGConfig", "RAGEngine", "PDFDocumentLoader"]
