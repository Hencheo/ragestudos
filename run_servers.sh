#!/bin/bash

# Cores para o log
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Iniciando Ecossistema Hermes...${NC}"

# 1. Verificando VENV
if [ ! -d ".venv" ]; then
    echo -e "${RED}❌ Erro: .venv não encontrada! Rode 'uv sync' primeiro.${NC}"
    exit 1
fi

PYTHON_VENV=".venv/bin/python"
CHROMA_EXEC=".venv/bin/chroma"

# 2. Limpando processos antigos (Portas 8000 e 8001)
echo -e "${BLUE}🧹 Limpando portas 8000 e 8001...${NC}"
fuser -k 8000/tcp 2>/dev/null
fuser -k 8001/tcp 2>/dev/null
sleep 1

# 3. Iniciando ChromaDB (Porta 8001)
echo -e "${BLUE}📦 Iniciando ChromaDB na porta 8001...${NC}"
$CHROMA_EXEC run --path ./db --host 0.0.0.0 --port 8001 > chroma.log 2>&1 &
CHROMA_PID=$!

# 4. Aguardando o ChromaDB subir
echo -e "${YELLOW}⏳ Aguardando ChromaDB (5s)...${NC}"
sleep 5

# 5. Iniciando Backend API (Porta 8000)
echo -e "${BLUE}🧠 Iniciando API FastAPI na porta 8000...${NC}"
export CHROMA_PORT=8001
export PYTHONPATH=$PYTHONPATH:$(pwd)

$PYTHON_VENV -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload > api.log 2>&1 &
API_PID=$!

# 6. Verificação final
sleep 2
if ps -p $API_PID > /dev/null; then
    echo -e "${GREEN}✨ Tudo pronto!${NC}"
    echo -e "---------------------------------------"
    echo -e "ChromaDB rodando em: http://localhost:8001 (PID: $CHROMA_PID)"
    echo -e "API Backend rodando em: http://localhost:8000 (PID: $API_PID)"
    echo -e "---------------------------------------"
    echo -e "Logs salvos em: chroma.log e api.log"
    echo -e "Para parar tudo, use: ./stop_servers.sh"
else
    echo -e "${RED}❌ Falha ao iniciar o servidor de API. Verifique 'api.log'.${NC}"
fi
