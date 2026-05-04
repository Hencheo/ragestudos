"""Módulo de carregamento de documentos PDF.

Este módulo fornece a classe PDFDocumentLoader para extrair
conteúdo de arquivos PDF e convertê-los em documentos LlamaIndex.
"""

import logging
from pathlib import Path
from typing import List, Optional, Union

from llama_index.core import Document
import fitz  # PyMuPDF
from llama_parse import LlamaParse

from .config import RAGConfig

# Configuração de logging
logger = logging.getLogger(__name__)


class PDFDocumentLoader:
    """Carregador de documentos PDF para o sistema RAG.
    
    Esta classe extrai texto de arquivos PDF mantendo a estrutura
    de páginas e metadados, convertendo-os em objetos Document
    compatíveis com LlamaIndex.
    
    Attributes:
        supported_extensions: Lista de extensões suportadas.
    
    Example:
        >>> loader = PDFDocumentLoader()
        >>> docs = loader.load_pdf("documento.pdf")
        >>> print(f"Carregadas {len(docs)} páginas")
    """
    
    SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx", ".html", ".png", ".jpg", ".jpeg"}
    
    def __init__(self, config: Optional[RAGConfig] = None):
        """Inicializa o carregador de documentos.
        
        Args:
            config: Configuração opcional com parâmetros de extração.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = config
        self._llama_parser = None
        self._docling_reader = None
        
        if config:
            # 1. Tenta inicializar LlamaParse (Nuvem)
            if config.use_llama_parse and config.llama_cloud_api_key:
                try:
                    from llama_parse import LlamaParse
                    self.logger.info("Inicializando LlamaParse")
                    self._llama_parser = LlamaParse(
                        api_key=config.llama_cloud_api_key,
                        result_type="markdown",
                        verbose=True,
                        language="pt"
                    )
                except ImportError:
                    self.logger.warning("llama-parse não instalado")

            # 2. Tenta inicializar Docling (Local Avançado)
            if config.use_docling:
                try:
                    from llama_index.readers.docling import DoclingReader
                    self.logger.info("Inicializando DoclingReader (Local Premium)")
                    self._docling_reader = DoclingReader()
                except (ImportError, Exception) as e:
                    self.logger.warning(f"Erro ao carregar DoclingReader: {e}. Fallback para PyMuPDF.")
    
    def load_pdf(
        self, 
        file_path: Union[str, Path],
        extra_metadata: Optional[dict] = None
    ) -> List[Document]:
        """Carrega um arquivo e retorna lista de Documentos.
        
        Tenta usar LlamaParse (se ativo), depois Docling (se ativo),
        e por fim PyMuPDF (apenas para PDFs) como fallback.
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
        
        suffix = file_path.suffix.lower()
        if suffix not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Extensão {suffix} não suportada. Use: {self.SUPPORTED_EXTENSIONS}")
        
        self.logger.info(f"Processando arquivo: {file_path}")
        
        # --- OPÇÃO 1: LlamaParse (Nuvem) ---
        if self._llama_parser:
            try:
                self.logger.info(f"Usando LlamaParse para: {file_path.name}")
                documents = self._llama_parser.load_data(str(file_path))
                return self._post_process_docs(documents, file_path, "llama_parse", extra_metadata)
            except Exception as e:
                self.logger.error(f"Erro no LlamaParse: {e}")

        # --- OPÇÃO 2: Docling (Local Premium) ---
        if self._docling_reader:
            try:
                self.logger.info(f"Usando Docling para: {file_path.name}")
                documents = self._docling_reader.load_data(str(file_path))
                return self._post_process_docs(documents, file_path, "docling", extra_metadata)
            except Exception as e:
                self.logger.error(f"Erro no Docling: {e}")

        # --- OPÇÃO 3: PyMuPDF (Fallback apenas para PDF) ---
        if suffix == ".pdf":
            try:
                self.logger.info(f"Usando PyMuPDF fallback para: {file_path.name}")
                import fitz
                doc = fitz.open(str(file_path))
                documents = []
                for page_num, page in enumerate(doc, start=1):
                    text = page.get_text()
                    if text.strip():
                        documents.append(Document(
                            text=text,
                            metadata={"page_number": page_num}
                        ))
                doc.close()
                return self._post_process_docs(documents, file_path, "pymupdf", extra_metadata)
            except Exception as e:
                self.logger.error(f"Erro no PyMuPDF: {e}")

        return []

    def _post_process_docs(
        self, 
        documents: List[Document], 
        file_path: Path, 
        source: str,
        extra_metadata: Optional[dict]
    ) -> List[Document]:
        """Padroniza metadados após o carregamento."""
        base_metadata = {
            "file_name": file_path.name,
            "file_path": str(file_path.absolute()),
            "total_pages": len(documents),
            "source_type": source,
        }
        if extra_metadata:
            base_metadata.update(extra_metadata)
            
        for i, doc in enumerate(documents):
            # Preserva metadados que o parser já possa ter colocado (ex: page_number)
            current_meta = doc.metadata.copy()
            doc.metadata.update(base_metadata)
            doc.metadata.update(current_meta) 
            
            if "page_number" not in doc.metadata:
                doc.metadata["page_number"] = i + 1
            
            doc.id_ = f"{file_path.stem}_{source}_page_{doc.metadata['page_number']}"
            
        return documents
    
    def load_pdfs(
        self, 
        file_paths: List[Union[str, Path]],
        extra_metadata: Optional[dict] = None
    ) -> List[Document]:
        """Carrega múltiplos arquivos PDF.
        
        Args:
            file_paths: Lista de caminhos para arquivos PDF.
            extra_metadata: Metadados adicionais.
            
        Returns:
            List[Document]: Lista combinada de todos os documentos.
            
        Example:
            >>> loader = PDFDocumentLoader()
            >>> pdfs = ["doc1.pdf", "doc2.pdf"]
            >>> all_docs = loader.load_pdfs(pdfs)
        """
        all_documents = []
        
        for file_path in file_paths:
            try:
                docs = self.load_pdf(file_path, extra_metadata)
                all_documents.extend(docs)
            except Exception as e:
                self.logger.error(f"Erro ao carregar {file_path}: {e}")
                continue
        
        self.logger.info(f"Total de documentos carregados: {len(all_documents)}")
        return all_documents
    
    def load_from_directory(
        self, 
        directory: Union[str, Path],
        recursive: bool = False
    ) -> List[Document]:
        """Carrega todos os PDFs de um diretório.
        
        Args:
            directory: Caminho do diretório.
            recursive: Se True, busca em subdiretórios.
            
        Returns:
            List[Document]: Lista de todos os documentos encontrados.
            
        Raises:
            NotADirectoryError: Se o caminho não for um diretório.
        """
        directory = Path(directory)
        
        if not directory.is_dir():
            raise NotADirectoryError(f"Não é um diretório: {directory}")
        
        pattern = "**/*.pdf" if recursive else "*.pdf"
        pdf_files = list(directory.glob(pattern))
        
        self.logger.info(f"Encontrados {len(pdf_files)} PDFs em {directory}")
        
        return self.load_pdfs(pdf_files)
