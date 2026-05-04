#!/bin/bash

# Cores para o log
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Iniciando Ecossistema Hermes...${NC}"

# 1. Ativando VENV
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo -e "${GREEN}✅ Virtual Env Ativada.${NC}"
else
    echo "❌ Erro: .venv não encontrada!"
    exit 1
fi

# 2. Limpando portas (caso tenham ficado presas)
echo -e "${BLUE}🧹 Limpando portas 8000 e 8001...${NC}"
fuser -k 8000/tcp 2>/dev/null
fuser -k 8001/tcp 2>/dev/null

# 3. Iniciando ChromaDB (Porta 8001)
echo -e "${BLUE}📦 Iniciando ChromaDB na porta 8001...${NC}"
uv run chroma run --path ./db --host 0.0.0.0 --port 8001 > chroma.log 2>&1 &
CHROMA_PID=$!

# 4. Aguardando o ChromaDB subir
sleep 3

# 5. Iniciando Backend API (Porta 8000)
echo -e "${BLUE}🧠 Iniciando API FastAPI na porta 8000...${NC}"
export CHROMA_PORT=8001 # Garante que a API saiba onde o Chroma está
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload > api.log 2>&1 &
API_PID=$!

echo -e "${GREEN}✨ Tudo pronto!${NC}"
echo -e "---------------------------------------"
echo -e "ChromaDB rodando em: http://localhost:8001 (PID: $CHROMA_PID)"
echo -e "API Backend rodando em: http://localhost:8000 (PID: $API_PID)"
echo -e "---------------------------------------"
echo -e "Logs salvos em: chroma.log e api.log"
echo -e "Para parar tudo, use: ./stop_servers.sh"
