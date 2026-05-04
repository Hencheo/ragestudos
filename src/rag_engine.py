"""Módulo principal do motor RAG.

Este módulo implementa a classe RAGEngine que orquestra a indexação
de documentos e a geração de respostas usando LlamaIndex e Google Gemini.
"""

import logging
from typing import List, Optional

import chromadb
from llama_index.core import Document, Settings, VectorStoreIndex, StorageContext
from llama_index.core.chat_engine.types import ChatMode
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.vector_stores import MetadataFilters, ExactMatchFilter
from llama_index.core.postprocessor import LLMRerank

from src.config import RAGConfig

# Configuração de logging
logger = logging.getLogger(__name__)


class RAGEngine:
    """Motor principal de Retrieval-Augmented Generation.
    
    Esta classe gerencia todo o fluxo RAG: configuração de LLM e embeddings,
    indexação de documentos, e execução de queries com contexto recuperado.
    
    Attributes:
        api_key: Chave de API do Google.
        config: Configuração do sistema RAG.
        index: Índice vetorial dos documentos (None se não indexado).
        chat_memory: Buffer de memória para conversas.
    
    Example:
        >>> config = RAGConfig(google_api_key="...")
        >>> engine = RAGEngine(api_key="...", config=config)
        >>> engine.index_documents(docs)
        >>> response = engine.query("O que é RAG?")
    """
    
    def __init__(self, api_key: str, config: RAGConfig):
        """Inicializa o motor RAG com configurações e credenciais.
        
        Args:
            api_key: Chave de API do Google Generative AI.
            config: Instância de RAGConfig com parâmetros.
            
        Raises:
            ValueError: Se a API key for vazia ou inválida.
        """
        if not api_key:
            raise ValueError("API key é obrigatória")
        
        self.api_key = api_key
        self.config = config
        self.index: Optional[VectorStoreIndex] = None
        self.chat_memory: Optional[ChatMemoryBuffer] = None
        self._query_engine: Optional[RetrieverQueryEngine] = None
        
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info(f"Inicializando RAGEngine com modelo: {config.model_name}")
        
        # Configura o LLM e embeddings globalmente
        self._setup_llm()
        self._setup_embeddings()
        self._setup_chunking()
        
        # Configura o banco vetorial
        self._setup_vector_store()
        
        self.logger.info("RAGEngine inicializado com sucesso")
    
    def extract_metadata_from_text(self, text: str) -> dict:
        """Usa a IA para extrair metadados inteligentes de um texto.
        
        Args:
            text: O texto extraído do documento (ou amostra dele).
            
        Returns:
            dict: Dicionário com document_type, main_subject, keywords e summary.
        """
        # Pega apenas o início do texto para economizar tokens e tempo
        sample_text = text[:3000]
        
        prompt = f"""
        Analise o texto abaixo e extraia informações organizadas para indexação em um sistema RAG.
        Responda APENAS em formato JSON válido, sem explicações adicionais.
        
        Texto:
        ---
        {sample_text}
        ---
        
        JSON esperado:
        {{
            "document_type": "Ex: Tutorial, Prova, Documentação, Currículo, Livro, Artigo",
            "main_subject": "O tópico central do arquivo em poucas palavras",
            "keywords": ["tag1", "tag2", "tag3"],
            "summary": "Um resumo de uma frase sobre o conteúdo"
        }}
        """
        
        try:
            # Tenta obter a resposta da IA
            response = Settings.llm.complete(prompt)
            import json
            import re
            
            # Limpa a resposta para garantir que seja um JSON válido (remove markdown se houver)
            content = str(response).strip()
            if "```json" in content:
                content = re.search(r"```json\s+(.*?)\s+```", content, re.DOTALL).group(1)
            elif "```" in content:
                content = re.search(r"```\s+(.*?)\s+```", content, re.DOTALL).group(1)
                
            return json.loads(content)
        except Exception as e:
            self.logger.warning(f"Falha na extração automática de metadados: {e}")
            return {
                "document_type": "Desconhecido",
                "main_subject": "Indeterminado",
                "keywords": [],
                "summary": "Não foi possível gerar resumo."
            }
    
    def _setup_llm(self) -> None:
        """Configura o LLM com base no provedor escolhido."""
        try:
            if self.config.llm_provider == "OpenAI":
                from llama_index.llms.openai import OpenAI
                llm = OpenAI(
                    model=self.config.model_name,
                    api_key=self.api_key,
                    api_base=self.config.llm_api_base,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    system_prompt=self.config.system_prompt,
                )
            elif self.config.llm_provider == "Fireworks AI":
                from llama_index.llms.openai import OpenAI
                # Fireworks usa a interface da OpenAI
                api_base = self.config.llm_api_base or "https://api.fireworks.ai/inference/v1"
                llm = OpenAI(
                    model=self.config.model_name,
                    api_key=self.api_key,
                    api_base=api_base,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    system_prompt=self.config.system_prompt,
                )
            else: # Padrão para Google Gemini
                from llama_index.llms.google_genai import GoogleGenAI
                llm = GoogleGenAI(
                    model=self.config.model_name,
                    api_key=self.api_key,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    system_prompt=self.config.system_prompt,
                )
                
            Settings.llm = llm
            self.logger.info(f"LLM configurado: {self.config.model_name} via {self.config.llm_provider}")
        except Exception as e:
            self.logger.error(f"Erro ao configurar LLM: {e}")
            raise
    
    def _setup_embeddings(self) -> None:
        """Configura o modelo de embeddings com base no provedor."""
        try:
            if self.config.llm_provider in ["OpenAI", "Fireworks AI"]:
                from llama_index.embeddings.openai import OpenAIEmbedding
                # O Fireworks suporta modelos de embeddings na mesma API
                api_base = self.config.llm_api_base if self.config.llm_provider == "OpenAI" else "https://api.fireworks.ai/inference/v1"
                embed_model = OpenAIEmbedding(
                    model_name=self.config.embedding_model,
                    api_key=self.api_key,
                    api_base=api_base,
                )
            else:
                from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
                embed_model = GoogleGenAIEmbedding(
                    model_name=self.config.embedding_model,
                    api_key=self.api_key,
                )
            Settings.embed_model = embed_model
            self.logger.info("Modelo de embeddings configurado")
        except Exception as e:
            self.logger.error(f"Erro ao configurar embeddings: {e}")
            raise
    
    def _setup_chunking(self) -> None:
        """Configura o parser de chunks para indexação."""
        try:
            node_parser = SentenceSplitter(
                chunk_size=self.config.chunk_size,
                chunk_overlap=self.config.chunk_overlap,
                paragraph_separator="\n\n",
                secondary_chunking_regex="[^,.;。]+[,.;。]?",
            )
            Settings.node_parser = node_parser
            self.logger.info(
                f"Chunking configurado: size={self.config.chunk_size}, "
                f"overlap={self.config.chunk_overlap}"
            )
        except Exception as e:
            self.logger.error(f"Erro ao configurar chunking: {e}")
            raise
            
    def _setup_vector_store(self) -> None:
        """Configura a conexão com o banco de dados vetorial ChromaDB."""
        try:
            # Conecta ao ChromaDB rodando como servidor
            self.chroma_client = chromadb.HttpClient(
                host=self.config.chroma_host, 
                port=self.config.chroma_port
            )
            
            # Obtém ou cria a coleção
            self.chroma_collection = self.chroma_client.get_or_create_collection(
                name="hermes_documents"
            )
            
            # Configura o VectorStore do LlamaIndex
            self.vector_store = ChromaVectorStore(chroma_collection=self.chroma_collection)
            self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
            
            # Tenta carregar o índice existente, se houver documentos na coleção
            try:
                if self.chroma_collection.count() > 0:
                    self.index = VectorStoreIndex.from_vector_store(
                        self.vector_store,
                    )
                    self._query_engine = self.index.as_query_engine(
                        similarity_top_k=10, # Traz mais candidatos para o Rerank
                        node_postprocessors=[
                            LLMRerank(choice_batch_size=5, top_n=3)
                        ],
                        response_mode="compact",
                        verbose=False,
                    )
                    self.logger.info(f"Índice carregado do banco de dados ({self.chroma_collection.count()} chunks) com Reranking ativo")
                else:
                    self.logger.info("Coleção vazia no banco de dados. Índice não carregado.")
            except Exception as inner_e:
                self.logger.warning(f"Não foi possível carregar o índice existente: {inner_e}")
                
            self.logger.info("Vector Store configurado")
        except Exception as e:
            self.logger.error(f"Erro ao configurar banco de dados: {e}")
            raise
    
    def _init_chat_memory(self) -> ChatMemoryBuffer:
        """Inicializa o buffer de memória de chat.
        
        Returns:
            ChatMemoryBuffer: Buffer de memória configurado.
        """
        if self.chat_memory is None:
            self.chat_memory = ChatMemoryBuffer.from_defaults(
                token_limit=3000,
            )
        return self.chat_memory
    
    def index_documents(
        self, 
        documents: List[Document],
        show_progress: bool = True
    ) -> VectorStoreIndex:
        """Indexa uma lista de documentos para recuperação.
        
        Processa os documentos, divide em chunks e cria um índice
        vetorial para busca semântica.
        
        Args:
            documents: Lista de Documentos LlamaIndex.
            show_progress: Se True, mostra barra de progresso.
            
        Returns:
            VectorStoreIndex: Índice vetorial criado.
            
        Raises:
            ValueError: Se a lista de documentos estiver vazia.
            RuntimeError: Se houver erro na indexação.
            
        Example:
            >>> docs = [Document(text="Conteúdo...")]
            >>> index = engine.index_documents(docs)
        """
        if not documents:
            raise ValueError("Lista de documentos não pode estar vazia")
        
        self.logger.info(f"Indexando {len(documents)} documentos...")
        
        try:
            if self.index is not None:
                self.logger.info("Adicionando novos documentos ao índice existente...")
                for doc in documents:
                    self.index.insert(doc)
            else:
                self.logger.info("Criando novo índice vetorial...")
                self.index = VectorStoreIndex.from_documents(
                    documents,
                    storage_context=self.storage_context,
                    show_progress=show_progress,
                )
            
            # Atualiza o query engine com Reranking
            self._query_engine = self.index.as_query_engine(
                similarity_top_k=10, # Aumentado para dar mais opções ao Reranker
                node_postprocessors=[
                    LLMRerank(choice_batch_size=5, top_n=3)
                ],
                response_mode="compact",
                verbose=False,
            )
            
            self.logger.info(f"Indexação concluída: {len(documents)} documentos")
            return self.index
            
        except Exception as e:
            self.logger.error(f"Erro na indexação: {e}")
            raise RuntimeError(f"Falha ao indexar documentos: {e}")
    
    def query(
        self, 
        question: str,
        use_chat_memory: bool = False,
        subject_filter: Optional[str] = None
    ) -> str:
        """Executa uma query no sistema RAG.
        
        Recupera contexto relevante dos documentos indexados e
        gera uma resposta usando o LLM configurado.
        
        Args:
            question: Pergunta do usuário.
            use_chat_memory: Se True, mantém contexto de conversa.
            
        Returns:
            str: Resposta gerada pelo modelo.
            
        Raises:
            RuntimeError: Se não houver documentos indexados.
            ValueError: Se a pergunta estiver vazia.
            
        Example:
            >>> response = engine.query("O que é machine learning?")
            >>> print(response)
        """
        if not question or not question.strip():
            raise ValueError("Pergunta não pode estar vazia")
        
        if self.index is None or self._query_engine is None:
            raise RuntimeError(
                "Nenhum documento indexado. "
                "Chame index_documents() primeiro."
            )
        
        self.logger.info(f"Query: {question[:50]}...")
        
        try:
            # Prepara os filtros de metadados se um assunto foi especificado
            filters = None
            if subject_filter:
                filters = MetadataFilters(
                    filters=[ExactMatchFilter(key="subject", value=subject_filter)]
                )

            if use_chat_memory and self.chat_memory:
                # Usa chat engine com memória
                chat_engine = self.index.as_chat_engine(
                    chat_mode=ChatMode.CONTEXT,
                    memory=self.chat_memory,
                    similarity_top_k=5,
                    filters=filters,
                )
                response = chat_engine.chat(question)
            else:
                # Query simples (com ou sem filtro)
                if filters:
                    temp_query_engine = self.index.as_query_engine(
                        similarity_top_k=10,
                        node_postprocessors=[
                            LLMRerank(choice_batch_size=5, top_n=3)
                        ],
                        response_mode="compact",
                        filters=filters,
                    )
                    response = temp_query_engine.query(question)
                else:
                    response = self._query_engine.query(question)
            
            answer = str(response)
            self.logger.info(f"Resposta gerada: {len(answer)} caracteres")
            return answer
            
        except Exception as e:
            self.logger.error(f"Erro na query: {e}")
            raise RuntimeError(f"Falha ao executar query: {e}")
    
    def chat(
        self, 
        message: str,
        reset: bool = False,
        subject_filter: Optional[str] = None
    ) -> str:
        """Executa uma mensagem em modo chat com memória.
        
        Mantém o histórico de conversa para contexto contínuo.
        
        Args:
            message: Mensagem do usuário.
            reset: Se True, limpa o histórico antes.
            
        Returns:
            str: Resposta do assistente.
            
        Raises:
            RuntimeError: Se não houver documentos indexados.
        """
        if self.index is None:
            raise RuntimeError("Nenhum documento indexado")
        
        if reset:
            self.clear_chat_memory()
        
        memory = self._init_chat_memory()
        
        # Prepara os filtros
        filters = None
        if subject_filter:
            filters = MetadataFilters(
                filters=[ExactMatchFilter(key="subject", value=subject_filter)]
            )
        
        chat_engine = self.index.as_chat_engine(
            chat_mode=ChatMode.CONTEXT,
            memory=memory,
            similarity_top_k=5,
            filters=filters,
        )
        
        response = chat_engine.chat(message)
        return str(response)
    
    def clear_index(self) -> None:
        """Limpa o índice de documentos e memória associada.
        
        Remove todos os documentos indexados e reseta o estado
        do motor para permitir nova indexação.
        
        Example:
            >>> engine.clear_index()
            >>> print(engine.index)  # None
        """
        self.index = None
        self._query_engine = None
        self.clear_chat_memory()
        
        # Limpa também do banco de dados (recria a coleção)
        if hasattr(self, 'chroma_client'):
            try:
                self.chroma_client.delete_collection("hermes_documents")
                self.chroma_collection = self.chroma_client.get_or_create_collection("hermes_documents")
                self.vector_store = ChromaVectorStore(chroma_collection=self.chroma_collection)
                self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
            except Exception as e:
                self.logger.error(f"Erro ao limpar banco de dados: {e}")
                
        self.logger.info("Índice limpo")
    
    def clear_chat_memory(self) -> None:
        """Limpa a memória de conversa.
        
        Remove todo o histórico de mensagens do chat.
        """
        if self.chat_memory:
            self.chat_memory.reset()
            self.logger.info("Memória de chat limpa")
    
    def is_ready(self) -> bool:
        """Verifica se o motor está pronto para queries.
        
        Returns:
            bool: True se há documentos indexados.
        """
        return self.index is not None and self._query_engine is not None
    
    def get_stats(self) -> dict:
        """Retorna estatísticas do motor.
        
        Returns:
            dict: Estatísticas incluindo estado do índice e configurações.
        """
        return {
            "is_ready": self.is_ready(),
            "has_index": self.index is not None,
            "has_chat_memory": self.chat_memory is not None,
            "model_name": self.config.model_name,
            "temperature": self.config.temperature,
            "chunk_size": self.config.chunk_size,
            "chunk_overlap": self.config.chunk_overlap,
        }
