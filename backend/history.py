import sqlite3
import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger("hermes.history")

class HistoryManager:
    """Gerenciador de histórico de chat usando SQLite.
    
    Responsável por persistir sessões e mensagens de forma isolada
    da lógica principal do RAG.
    """
    
    def __init__(self, db_path: str = "db/history.db"):
        # Garante que o diretório db existe
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Inicializa as tabelas do banco de dados."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Tabela de Sessões
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS sessions (
                        id TEXT PRIMARY KEY,
                        title TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                # Tabela de Mensagens
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT,
                        role TEXT,
                        content TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
                    )
                ''')
                conn.commit()
                logger.info(f"Banco de dados de histórico inicializado em {self.db_path}")
        except Exception as e:
            logger.error(f"Erro ao inicializar banco de histórico: {e}")

    def save_message(self, session_id: str, role: str, content: str):
        """Salva uma mensagem no histórico."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Garante que a sessão existe (INSERT OR IGNORE)
                # O título inicial é "Nova Conversa", será atualizado depois via IA
                cursor.execute(
                    "INSERT OR IGNORE INTO sessions (id, title) VALUES (?, ?)", 
                    (session_id, "Nova Conversa")
                )
                # Salva a mensagem
                cursor.execute(
                    "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
                    (session_id, role, content)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Erro ao salvar mensagem: {e}")

    def get_messages(self, session_id: str) -> List[Dict[str, str]]:
        """Recupera todas as mensagens de uma sessão."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT role, content FROM messages WHERE session_id = ? ORDER BY timestamp ASC", 
                    (session_id,)
                )
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Erro ao recuperar mensagens: {e}")
            return []

    def list_sessions(self) -> List[Dict[str, Any]]:
        """Lista todas as sessões salvas."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT id, title, created_at FROM sessions ORDER BY created_at DESC")
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Erro ao listar sessões: {e}")
            return []

    def update_session_title(self, session_id: str, title: str):
        """Atualiza o título de uma sessão."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE sessions SET title = ? WHERE id = ?", (title, session_id))
                conn.commit()
                logger.info(f"Título da sessão {session_id} atualizado para: {title}")
        except Exception as e:
            logger.error(f"Erro ao atualizar título: {e}")

    def delete_session(self, session_id: str):
        """Remove uma sessão e todas as suas mensagens."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # O ON DELETE CASCADE cuidará das mensagens se o SQLite estiver configurado corretamente
                # Mas vamos garantir deletando manualmente também por segurança
                cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
                cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
                conn.commit()
        except Exception as e:
            logger.error(f"Erro ao deletar sessão: {e}")

    def is_new_session(self, session_id: str) -> bool:
        """Verifica se a sessão é nova (tem apenas 1 ou 2 mensagens)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM messages WHERE session_id = ?", (session_id,))
                count = cursor.fetchone()[0]
                # Se tem 2 mensagens (pergunta + resposta), é o momento ideal para gerar título
                return count <= 2
        except Exception:
            return False
