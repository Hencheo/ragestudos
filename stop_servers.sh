#!/bin/bash

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🛑 Parando Ecossistema Hermes...${NC}"

# Tenta matar os processos pelas portas
echo -e "Encerrando processos na porta 8000 (API)..."
fuser -k 8000/tcp 2>/dev/null

echo -e "Encerrando processos na porta 8001 (ChromaDB)..."
fuser -k 8001/tcp 2>/dev/null

# Limpeza adicional para processos uvicorn ou chroma que possam ter ficado órfãos
echo -e "Limpando processos residuais..."
pkill -f "uvicorn backend.main:app" 2>/dev/null
pkill -f "chromadb.cli.cli run" 2>/dev/null

echo -e "${GREEN}✅ Todos os servidores Hermes foram parados.${NC}"
