from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class LegalMovement(BaseModel):
    data: str
    descricao: str
    complemento: Optional[str] = None

class LegalProcess(BaseModel):
    numero: str
    classe: str
    tribunal: str
    data_ajuizamento: str
    partes: List[Dict[str, str]]
    movimentacoes: List[LegalMovement]
    assunto: Optional[str] = None
    metadados_extra: Dict[str, Any] = Field(default_factory=dict)

    def to_rag_text(self) -> str:
        """Converte os dados do processo em um texto estruturado para o RAG."""
        text = f"PROCESSO NÚMERO: {self.numero}\n"
        text += f"Tribunal: {self.tribunal} | Classe: {self.classe}\n"
        text += f"Data de Ajuizamento: {self.data_ajuizamento}\n"
        text += f"Assunto: {self.assunto or 'Não informado'}\n\n"
        
        text += "PARTES ENVOLVIDAS:\n"
        for parte in self.partes:
            text += f"- {parte.get('nome')} ({parte.get('tipo', 'Parte')})\n"
        
        text += "\nÚLTIMAS MOVIMENTAÇÕES:\n"
        for mov in self.movimentacoes[:5]: # Pegamos as 5 mais recentes
            text += f"- {mov.data}: {mov.descricao} {f'({mov.complemento})' if mov.complemento else ''}\n"
            
        return text
