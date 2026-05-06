import logging
import asyncio
from typing import Optional
from src.models.legal_process import LegalProcess, LegalMovement

logger = logging.getLogger(__name__)

class ExternalApiService:
    """Serviço para integração com APIs Jurídicas Externas (CNJ, DataJud, etc)."""

    def __init__(self):
        self.mock_mode = True # Começamos em modo Mock para segurança

    async def fetch_process_data(self, process_number: str) -> Optional[LegalProcess]:
        """
        Busca dados de um processo pelo número.
        Por enquanto, opera em modo Sandbox/Mock.
        """
        logger.info(f"Iniciando busca externa para o processo: {process_number}")
        
        if self.mock_mode:
            return await self._get_mock_data(process_number)
        
        # TODO: Implementar integração real com DataJud aqui
        return None

    async def _get_mock_data(self, process_number: str) -> LegalProcess:
        """Simula uma resposta da API do CNJ para fins de demonstração e teste."""
        await asyncio.sleep(1.5) # Simula latência de rede
        
        return LegalProcess(
            numero=process_number,
            classe="Procedimento Comum Cível",
            tribunal="Tribunal de Justiça do Estado de São Paulo",
            data_ajuizamento="15/01/2024",
            assunto="Indenização por Dano Moral",
            partes=[
                {"nome": "João da Silva", "tipo": "REQUERENTE"},
                {"nome": "Banco Digital S.A.", "tipo": "REQUERIDO"}
            ],
            movimentacoes=[
                LegalMovement(data="05/05/2024", descricao="Certidão de Publicação Expedida", complemento="Relação: 0123/2024"),
                LegalMovement(data="02/05/2024", descricao="Conclusos para Decisão", complemento="Despacho Próximo"),
                LegalMovement(data="20/04/2024", descricao="Petição de Manifestação Juntada", complemento="Réplica do Autor"),
                LegalMovement(data="10/04/2024", descricao="Contestação Juntada", complemento="Defesa do Banco"),
                LegalMovement(data="15/01/2024", descricao="Distribuição Sorteio", complemento="Distribuidor Cível")
            ],
            metadados_extra={"origem": "MOCK_DATAJUD_API"}
        )
