"""Módulo principal do motor RAG.

Este módulo implementa a classe RAGEngine que orquestra a indexação
de documentos e a geração de respostas usando LlamaIndex e Google Gemini.
"""

import time
import logging
from typing import Optional, List, Any, Dict, Union

from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log

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

from .config import RAGConfig

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
    
    def __init__(
        self, 
        config: RAGConfig, 
        api_key: Optional[str] = None
    ):
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
        
        # Configura o System Prompt especializado
        self._setup_system_prompt()
        
        # Configura o banco vetorial
        self._setup_vector_store()
        
        self.logger.info("RAGEngine inicializado com sucesso")

    def _setup_system_prompt(self):
        """Configura a personalidade e o formato de resposta do Hermes."""
        from llama_index.core import PromptTemplate
        
        system_prompt = (
            "Você é o Hermes, um assistente de IA especializado em análise de documentos e extração de conhecimento.\n"
            "Sua missão é fornecer respostas precisas, profissionais e extremamente bem estruturadas.\n\n"
            "DIRETRIZES DE FORMATAÇÃO:\n"
            "1. Use Markdown para estruturar TODAS as suas respostas.\n"
            "2. Utilize títulos (###) e subtítulos para organizar diferentes tópicos.\n"
            "3. Use listas com bullet points (-) para enumerar itens, habilidades ou características.\n"
            "4. Destaque termos técnicos, nomes de certificados, leis ou conceitos-chave em **negrito**.\n"
            "5. Se a resposta for longa, comece com um breve resumo e use seções claras.\n"
            "6. Mantenha um tom profissional, direto e analítico.\n"
            "7. Se a informação não estiver nos documentos, diga claramente que não encontrou, em vez de inventar.\n\n"
            "Sempre responda em Português do Brasil, a menos que solicitado o contrário."
        )
        
        # Define o prompt no Settings global para que todos os engines o utilizem
        Settings.system_prompt = system_prompt
        self.logger.info("System Prompt especializado configurado")
    
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
            # Tenta obter a resposta da IA (com retry para erros transitórios)
            response = self._llm_complete_with_retry(prompt)
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

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        before_sleep=before_sleep_log(logging.getLogger("hermes.retry"), logging.WARNING),
        reraise=True,
    )
    def _llm_complete_with_retry(self, prompt: str):
        """Chamada LLM com retry para erros transitórios."""
        try:
            return Settings.llm.complete(prompt)
        except Exception as e:
            error_str = str(e).lower()
            if any(kw in error_str for kw in ["rate limit", "429", "503", "timeout", "overloaded", "quota"]):
                self.logger.warning(f"Erro transitório LLM, retrying: {e}")
                raise ConnectionError(str(e)) from e
            raise
    
    def _setup_llm(self) -> None:
        """Configura o LLM com base no provedor escolhido."""
        try:
            provider = self.config.llm_provider.lower()
            
            # Detecta se é um modelo da Fireworks mesmo que o provedor esteja como 'openai'
            is_fireworks_model = "fireworks" in self.config.model_name.lower()
            
            if is_fireworks_model or "fireworks" in provider:
                from llama_index.llms.fireworks import Fireworks
                api_key = self.config.fireworks_api_key or self.api_key
                llm = Fireworks(
                    model=self.config.model_name,
                    api_key=api_key,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                )
            elif "openai" in provider:
                from llama_index.llms.openai import OpenAI
                api_key = self.config.openai_api_key or self.api_key
                llm = OpenAI(
                    model=self.config.model_name,
                    api_key=api_key,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    system_prompt=self.config.system_prompt,
                )
            elif "fireworks" in provider:
                from llama_index.llms.fireworks import Fireworks
                api_key = self.config.fireworks_api_key or self.api_key
                llm = Fireworks(
                    model=self.config.model_name,
                    api_key=api_key,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
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
            embedding_model_name = self.config.embedding_model
            
            # Se o modelo for da OpenAI ou o provedor for OpenAI (case-insensitive)
            if "text-embedding-" in embedding_model_name or self.config.llm_provider.lower() == "openai":
                from llama_index.embeddings.openai import OpenAIEmbedding
                
                # Usa a chave da OpenAI se disponível, senão tenta a chave geral
                api_key = self.config.openai_api_key or self.api_key
                
                self.logger.info(f"Configurando embeddings OpenAI: {embedding_model_name}")
                embed_model = OpenAIEmbedding(
                    model_name=embedding_model_name,
                    api_key=api_key,
                )
            else:
                from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
                self.logger.info(f"Configurando embeddings Google: {embedding_model_name}")
                embed_model = GoogleGenAIEmbedding(
                    model_name=embedding_model_name,
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
            
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=5),
        before_sleep=before_sleep_log(logging.getLogger("hermes.retry"), logging.WARNING),
        reraise=True,
    )
    def _setup_vector_store(self) -> None:
        """Configura a conexão com o banco de dados vetorial ChromaDB (com retry)."""
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
                    
                    from llama_index.core.postprocessor import LLMRerank
                    reranker = LLMRerank(top_n=5, llm=Settings.llm)
                    
                    self._query_engine = self.index.as_query_engine(
                        similarity_top_k=20,
                        response_mode="compact",
                        node_postprocessors=[reranker],
                        verbose=False,
                    )
                    self.logger.info(f"Índice carregado do banco de dados ({self.chroma_collection.count()} chunks)")
                else:
                    self.logger.info("Coleção vazia no banco de dados. Índice não carregado.")
            except Exception as inner_e:
                self.logger.warning(f"Não foi possível carregar o índice existente: {inner_e}")
                
            self.logger.info("Vector Store configurado")
        except Exception as e:
            self.logger.error(f"Erro ao configurar banco de dados: {e}")
            raise

    def _get_keyword_nodes(self, query: str, limit: int = 10) -> List[Any]:
        """Busca nós que contêm palavras-chave da query usando busca exata de texto.
        
        Isso ajuda a encontrar termos raros ou com grafia específica (ex: Ticuna)
        que a busca semântica por vetores pode ignorar.
        """
        import re
        # Extrai palavras com mais de 3 caracteres, ignorando termos comuns (PT e ES)
        words = re.findall(r'\w+', query.lower())
        stop_words = {
            'significa', 'quem', 'onde', 'como', 'quais', 'quando', 'sobre', 'texto', 'documento',
            'fala', 'quer', 'quiser', 'falar', 'dizer', 'você', 'pode', 'ajudar', 'qual', 'quais',
            'para', 'com', 'pelo', 'pela', 'está', 'este', 'esta', 'esse', 'essa', 'isso', 'aquilo',
            'como', 'pero', 'para', 'este', 'esta', 'esto', 'significa', 'dice', 'habla'
        }
        keywords = [w for w in words if len(w) > 3 and w not in stop_words]
        
        if not keywords:
            self.logger.info("Nenhuma palavra-chave relevante encontrada na query.")
            return []
            
        self.logger.info(f"Busca Híbrida - Palavras-chave extraídas: {keywords}")
        
        found_nodes = []
        seen_ids = set()
        
        try:
            for kw in keywords:
                # Busca no ChromaDB usando o operador $contains
                results = self.chroma_collection.get(
                    where_document={"$contains": kw},
                    limit=limit
                )
                
                if results and results['ids']:
                    for i, doc_id in enumerate(results['ids']):
                        if doc_id not in seen_ids:
                            from llama_index.core.schema import TextNode, NodeWithScore
                            node = TextNode(
                                text=results['documents'][i],
                                id_=doc_id,
                                metadata=results['metadatas'][i]
                            )
                            # Atribui um score alto para busca por palavra-chave
                            found_nodes.append(NodeWithScore(node=node, score=0.9))
                            seen_ids.add(doc_id)
            
            return found_nodes
        except Exception as e:
            self.logger.warning(f"Erro na busca por palavras-chave: {e}")
            return []
    
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
        
        # Sanitiza metadados para evitar erros no ChromaDB (converte listas em strings)
        for doc in documents:
            for key, value in doc.metadata.items():
                if isinstance(value, list):
                    doc.metadata[key] = ", ".join(map(str, value))
                elif not isinstance(value, (str, int, float, type(None))):
                    doc.metadata[key] = str(value)
        
        try:
            # LlamaIndex pode falhar se enviarmos muitos documentos de uma vez (Payload too large)
            # Vamos processar em batches menores para garantir estabilidade
            batch_size = 50
            total_docs = len(documents)
            
            for i in range(0, total_docs, batch_size):
                batch = documents[i : i + batch_size]
                self.logger.info(f"Processando batch {i//batch_size + 1} ({len(batch)} documentos)...")
                
                if self.index is not None:
                    # Se o índice já existe, inserimos os documentos um a um ou em batch
                    for doc in batch:
                        self.index.insert(doc)
                else:
                    # Se o índice não existe, criamos com o primeiro batch
                    self.index = VectorStoreIndex.from_documents(
                    batch,
                        storage_context=self.storage_context,
                        show_progress=show_progress,
                    )
            
            # Configura o Reranker (re-classificador) para maior precisão
            # Ele pega os top 20 resultados da busca vetorial e usa o LLM para escolher os 5 melhores
            from llama_index.core.postprocessor import LLMRerank
            reranker = LLMRerank(
                top_n=5, 
                llm=Settings.llm
            )
            
            # Atualiza o query engine com Reranking
            self._query_engine = self.index.as_query_engine(
                similarity_top_k=20,
                response_mode="compact",
                node_postprocessors=[reranker],
                verbose=False,
            )
            
            self.logger.info(f"Indexação concluída: {total_docs} documentos em {max(1, (total_docs + batch_size - 1) // batch_size)} batches")
            return self.index
            
        except Exception as e:
            self.logger.error(f"Erro na indexação: {e}")
            raise RuntimeError(f"Falha ao indexar documentos: {e}. Tente reduzir o número de arquivos ou use documentos menores.")
    
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
            return "Minha base de conhecimento está vazia no momento. Por favor, faça o upload de alguns documentos nas configurações para que eu possa ajudá-lo com informações específicas!"
        
        self.logger.info(f"Query: {question[:50]}...")
        
        try:
            # Prepara os filtros de metadados se um assunto foi especificado
            filters = None
            if subject_filter:
                filters = MetadataFilters(
                    filters=[ExactMatchFilter(key="subject", value=subject_filter)]
                )

            # --- BUSCA HÍBRIDA MANUAL ---
            # 1. Busca Semântica (Vetores)
            retriever = self.index.as_retriever(similarity_top_k=20, filters=filters)
            semantic_nodes = retriever.retrieve(question)
            self.logger.info(f"Busca semântica: {len(semantic_nodes)} nós encontrados")
            
            # 2. Busca por Palavras-Chave (Texto Exato)
            keyword_nodes = self._get_keyword_nodes(question)
            self.logger.info(f"Busca por palavras-chave: {len(keyword_nodes)} nós encontrados")
            
            # 3. Combinação e Reranking
            all_nodes = semantic_nodes + keyword_nodes
            
            if not all_nodes:
                self.logger.warning("Nenhum contexto encontrado para a pergunta.")
                return "Não encontrei informações específicas sobre isso nos documentos indexados. Tente reformular a pergunta ou verificar se o assunto correto está selecionado."

            from llama_index.core.postprocessor import LLMRerank
            reranker = LLMRerank(top_n=10, llm=Settings.llm)
            final_nodes = reranker.postprocess_nodes(all_nodes, query_str=question)
            self.logger.info(f"Após Reranking: {len(final_nodes)} nós selecionados")
            
            # 4. Geração de Resposta
            from llama_index.core.query_engine import RetrieverQueryEngine
            from llama_index.core.response_synthesizers import get_response_synthesizer
            from llama_index.core import PromptTemplate
            
            # Prompts customizados para forçar estrutura Markdown
            qa_prompt_str = (
                "Contexto:\n"
                "---------------------\n"
                "{context_str}\n"
                "---------------------\n"
                "Pergunta: {query_str}\n\n"
                "Responda à pergunta de forma profissional e extremamente bem estruturada usando Markdown.\n"
                "Use bullet points, negrito para termos chave e separe por tópicos se necessário.\n"
                "Se a informação não estiver no contexto, diga que não encontrou.\n"
                "Resposta:"
            )
            qa_prompt = PromptTemplate(qa_prompt_str)
            
            refine_prompt_str = (
                "A resposta original é: {existing_answer}\n"
                "Temos a oportunidade de refinar a resposta com mais contexto abaixo.\n"
                "---------------------\n"
                "{context_msg}\n"
                "---------------------\n"
                "Com base no novo contexto, refine a resposta original para ser ainda mais completa e bem estruturada.\n"
                "Mantenha a estrutura Markdown (bullet points, negrito, títulos).\n"
                "Se o novo contexto não ajudar, retorne a resposta original.\n"
                "Resposta Refinada:"
            )
            refine_prompt = PromptTemplate(refine_prompt_str)
            
            response_synthesizer = get_response_synthesizer(
                response_mode="compact",
                text_qa_template=qa_prompt,
                refine_template=refine_prompt
            )
            
            if use_chat_memory and self.chat_memory:
                # Usa chat engine com os nós híbridos
                chat_engine = self.index.as_chat_engine(
                    chat_mode=ChatMode.CONTEXT,
                    memory=self.chat_memory,
                    similarity_top_k=20,
                    filters=filters,
                    node_postprocessors=[reranker]
                )
                response = chat_engine.chat(question)
            else:
                # Para query normal, sintetizamos a resposta usando os nós finais selecionados
                response = response_synthesizer.synthesize(
                    query=question,
                    nodes=final_nodes
                )
            
            answer = str(response).strip()
            
            if not answer:
                self.logger.warning("LLM retornou resposta vazia.")
                return "O modelo não conseguiu gerar uma resposta com base no contexto encontrado. Tente perguntar de outra forma."

            self.logger.info(f"Resposta gerada ({len(answer)} caracteres): {answer[:100]}...")
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
            return "Minha base de conhecimento está vazia no momento. Por favor, faça o upload de alguns documentos nas configurações para que eu possa ajudá-lo com informações específicas!"
        
        if reset:
            self.clear_chat_memory()
        
        memory = self._init_chat_memory()
        
        # Prepara os filtros
        filters = None
        if subject_filter:
            filters = MetadataFilters(
                filters=[ExactMatchFilter(key="subject", value=subject_filter)]
            )
        
        from llama_index.core.postprocessor import LLMRerank
        reranker = LLMRerank(top_n=5, llm=Settings.llm)
        
        chat_engine = self.index.as_chat_engine(
            chat_mode=ChatMode.CONTEXT,
            memory=memory,
            similarity_top_k=20,
            filters=filters,
            node_postprocessors=[reranker]
        )
        
        response = chat_engine.chat(message)
        return str(response)
    
    def clear_index(self) -> None:
        """Limpa o índice de documentos e memória associada."""
        self.index = None
        self._query_engine = None
        self.clear_chat_memory()
        
        # Limpa do banco de dados (recria a coleção)
        try:
            # Se não tiver o cliente ainda, inicializa
            if not hasattr(self, 'chroma_client'):
                self.chroma_client = chromadb.HttpClient(
                    host=self.config.chroma_host, 
                    port=self.config.chroma_port
                )
            
            self.chroma_client.delete_collection("hermes_documents")
            self.chroma_collection = self.chroma_client.get_or_create_collection("hermes_documents")
            self.vector_store = ChromaVectorStore(chroma_collection=self.chroma_collection)
            self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
            self.logger.info("Banco de dados ChromaDB limpo com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao limpar ChromaDB: {e}")

    def delete_document(self, file_name: str) -> bool:
        """Deleta todos os chunks associados a um arquivo específico.
        
        Args:
            file_name: Nome do arquivo a ser deletado.
            
        Returns:
            bool: True se a deleção foi bem sucedida.
        """
        try:
            self.logger.info(f"Deletando documento: {file_name}")
            # Deleta da coleção do ChromaDB usando metadados
            self.chroma_collection.delete(
                where={"file_name": file_name}
            )
            
            # Recarrega o índice para refletir a mudança
            # (Em um sistema maior usaríamos index.delete_nodes, mas aqui recriar do banco é mais seguro)
            self.index = VectorStoreIndex.from_vector_store(
                self.vector_store, 
                storage_context=self.storage_context
            )
            self._query_engine = self.index.as_query_engine()
            
            return True
        except Exception as e:
            self.logger.error(f"Erro ao deletar documento {file_name}: {e}")
            return False
    
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
