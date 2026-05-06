"""Módulo de carregamento de documentos PDF.

Este módulo fornece a classe PDFDocumentLoader para extrair
conteúdo de arquivos PDF e convertê-los em documentos LlamaIndex.
"""

import logging
import tempfile
from pathlib import Path
from typing import List, Optional, Union

from llama_index.core import Document
import fitz  # PyMuPDF
from llama_parse import LlamaParse

from .config import RAGConfig
from PIL import Image, ImageOps, ImageEnhance
import io

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
    
    SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx", ".html", ".png", ".jpg", ".jpeg", ".txt"}
    
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
                    from docling.datamodel.base_models import InputFormat
                    from docling.document_converter import DocumentConverter, PdfFormatOption
                    from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions
                    
                    self.logger.info("Inicializando DoclingReader (Local Premium)")
                    
                    # Configuração para evitar deadlocks em ambientes multi-processo
                    import os
                    os.environ["OMP_NUM_THREADS"] = "1"
                    os.environ["MKL_NUM_THREADS"] = "1"
                    
                    # Configuração avançada do Docling para melhorar OCR

                    pipeline_options = PdfPipelineOptions()
                    pipeline_options.do_ocr = True
                    pipeline_options.images_scale = 1.5  # Escala equilibrada para performance e precisão
                    
                    # Foco em Espanhol e Inglês para o dicionário Ticuna
                    pipeline_options.ocr_options = RapidOcrOptions(lang=["es", "en"])
                    pipeline_options.ocr_options.force_full_page_ocr = False
                    pipeline_options.ocr_options.text_score = 0.4
                    
                    # Cria o conversor com opções customizadas
                    converter = DocumentConverter(
                        format_options={
                            InputFormat.PDF: PdfFormatOption(
                                pipeline_options=pipeline_options
                            )
                        }
                    )
                    
                    self._docling_reader = DoclingReader(doc_converter=converter)

                    # Cria um conversor secundário sem OCR para máxima velocidade
                    pipeline_options_no_ocr = PdfPipelineOptions()
                    pipeline_options_no_ocr.do_ocr = False
                    converter_no_ocr = DocumentConverter(
                        format_options={
                            InputFormat.PDF: PdfFormatOption(
                                pipeline_options=pipeline_options_no_ocr
                            )
                        }
                    )
                    self._docling_reader_no_ocr = DoclingReader(doc_converter=converter_no_ocr)
                    
                except (ImportError, Exception) as e:
                    self.logger.warning(f"Erro ao carregar DoclingReader: {e}. Fallback para PyMuPDF.")
    
    def load_pdf(
        self, 
        file_path: Union[str, Path],
        extra_metadata: Optional[dict] = None,
        progress_callback: Optional[callable] = None,
        use_ocr: bool = True
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
        
        if progress_callback:
            progress_callback(5, f"Iniciando extração de {file_path.name}...")

        # --- TRATAMENTO PRÉ-DOCLING (Para Imagens) ---
        if self.config and self.config.use_image_treatment and suffix in {".png", ".jpg", ".jpeg"}:
            try:
                self.logger.info(f"Aplicando tratamento de imagem em: {file_path.name}")
                if progress_callback:
                    progress_callback(15, "Tratando imagem para melhorar OCR...")
                with open(file_path, "rb") as f:
                    content = f.read()
                treated_content = self._preprocess_image_data(content)
                with open(file_path, "wb") as f:
                    f.write(treated_content)
            except Exception as e:
                self.logger.warning(f"Erro ao tratar imagem {file_path.name}: {e}")

        # --- OPÇÃO 1: LlamaParse (Nuvem) ---
        if self._llama_parser:
            try:
                self.logger.info(f"Usando LlamaParse para: {file_path.name}")
                if progress_callback:
                    progress_callback(10, "Enviando para LlamaParse (Cloud)...")
                documents = self._llama_parser.load_data(str(file_path))
                if progress_callback:
                    progress_callback(90, "Extração LlamaParse concluída.")
                return self._post_process_docs(documents, file_path, "llama_parse", extra_metadata)
            except Exception as e:
                self.logger.error(f"Erro no LlamaParse: {e}")

        # --- OPÇÃO 2: Docling (Local Premium) ---
        if self._docling_reader:
            try:
                import fitz
                from docling.datamodel.base_models import InputFormat
                from llama_index.readers.docling import DoclingReader
                
                # Seleciona o leitor (com ou sem OCR)
                reader = self._docling_reader if use_ocr else self._docling_reader_no_ocr
                
                self.logger.info(f"Usando Docling (OCR: {use_ocr}) para: {file_path.name}")
                
                # Abre o PDF para contar páginas e processar individualmente
                doc_pdf = fitz.open(str(file_path))
                total_pages = len(doc_pdf)
                self.logger.info(f"Documento tem {total_pages} páginas.")
                
                all_documents = []
                
                for i in range(total_pages):
                    page_num = i + 1
                    # Calcula progresso relativo (entre 15% e 80%)
                    rel_progress = 15 + int((i / total_pages) * 65)
                    
                    if progress_callback:
                        progress_callback(rel_progress, f"Analisando página {page_num} de {total_pages}...")
                    
                    # Extrai apenas uma página para um PDF temporário
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_page:
                        single_page_doc = fitz.open()
                        single_page_doc.insert_pdf(doc_pdf, from_page=i, to_page=i)
                        single_page_doc.save(tmp_page.name)
                        single_page_doc.close()
                        tmp_page_path = tmp_page.name
                    
                    try:
                        # Processa apenas esta página com Docling
                        page_docs = reader.load_data(tmp_page_path)
                        
                        # Ajusta o número da página nos metadados
                        for d in page_docs:
                            d.metadata["page_number"] = page_num
                        
                        all_documents.extend(page_docs)
                    finally:
                        Path(tmp_page_path).unlink(missing_ok=True)

                doc_pdf.close()
                
                if progress_callback:
                    progress_callback(80, "Processamento de todas as páginas concluído.")
                
                return self._post_process_docs(all_documents, file_path, "docling", extra_metadata)
                
            except Exception as e:
                self.logger.error(f"Erro no Docling Cirúrgico: {e}")
                # Fallback para o modo padrão se o modo cirúrgico falhar
                try:
                    self.logger.info("Tentando modo Docling padrão como fallback...")
                    documents = reader.load_data(str(file_path))
                    return self._post_process_docs(documents, file_path, "docling", extra_metadata)
                except Exception as inner_e:
                    self.logger.error(f"Erro no Docling Fallback: {inner_e}")



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
        
        # --- OPÇÃO 4: Leitor de Texto Puro (.txt) ---
        if suffix == ".txt":
            try:
                self.logger.info(f"Usando leitor de texto puro para: {file_path.name}")
                # Tenta ler com UTF-8, cai para latin-1 se falhar
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        text = f.read()
                except UnicodeDecodeError:
                    with open(file_path, "r", encoding="latin-1") as f:
                        text = f.read()
                        
                documents = [Document(text=text)]
                return self._post_process_docs(documents, file_path, "txt_reader", extra_metadata)
            except Exception as e:
                self.logger.error(f"Erro ao ler arquivo TXT: {e}")

        return []

    def _preprocess_image_data(self, image_bytes: bytes) -> bytes:
        """Aplica 'tratamento' na imagem para melhorar o OCR.
        
        Converte para tons de cinza, aumenta contraste e nitidez.
        """
        try:
            img = Image.open(io.BytesIO(image_bytes))
            
            # 1. Converter para escala de cinza
            img = ImageOps.grayscale(img)
            
            # 2. Aumentar contraste
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(2.0)
            
            # 3. Aumentar nitidez
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1.5)
            
            # Salva de volta para bytes
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            return img_byte_arr.getvalue()
        except Exception as e:
            self.logger.warning(f"Falha no pré-processamento da imagem: {e}")
            return image_bytes

    def _post_process_docs(
        self, 
        documents: List[Document], 
        file_path: Path, 
        source: str,
        extra_metadata: Optional[dict]
    ) -> List[Document]:
        """Padroniza metadados após o carregamento."""
        base_metadata = {
            "file_name": (extra_metadata or {}).get("uploaded_filename", file_path.name),
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
