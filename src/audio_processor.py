import whisper
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class AudioProcessor:
    """Processador de áudio usando OpenAI Whisper para transcrição.
    
    Esta classe permite converter arquivos de áudio em texto, permitindo
    que o sistema RAG processe comandos de voz.
    """
    
    def __init__(self, model_name: str = "base"):
        """Inicializa o modelo Whisper.
        
        Args:
            model_name: Nome do modelo (tiny, base, small, medium, large).
                        O 'base' é um bom equilíbrio entre velocidade e precisão.
        """
        self.model_name = model_name
        self._model = None
        self.logger = logging.getLogger(self.__class__.__name__)

    @property
    def model(self):
        """Carregamento lazy do modelo para economizar memória na inicialização."""
        if self._model is None:
            self.logger.info(f"Carregando modelo Whisper: {self.model_name}")
            self._model = whisper.load_model(self.model_name)
        return self._model

    def transcribe(self, audio_content: bytes, suffix: str = ".wav") -> Optional[str]:
        """Transcreve o conteúdo binário de um áudio para texto.
        
        Args:
            audio_content: Bytes do arquivo de áudio.
            suffix: Extensão do arquivo (ex: .wav, .mp3, .m4a).
            
        Returns:
            Texto transcrito ou None se falhar.
        """
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(audio_content)
            tmp_path = tmp.name
            
        try:
            self.logger.info(f"Iniciando transcrição de áudio ({len(audio_content)} bytes)")
            result = self.model.transcribe(tmp_path, fp16=False) # fp16=False evita avisos em CPUs sem GPU
            text = result.get("text", "").strip()
            return text
        except Exception as e:
            self.logger.error(f"Erro na transcrição de áudio: {e}")
            return None
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def transcribe_file(self, file_path: str) -> Optional[str]:
        """Transcreve um arquivo de áudio existente no disco."""
        try:
            result = self.model.transcribe(file_path, fp16=False)
            return result.get("text", "").strip()
        except Exception as e:
            self.logger.error(f"Erro ao transcrever arquivo {file_path}: {e}")
            return None
