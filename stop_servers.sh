#!/bin/bash
echo "🛑 Parando servidores Hermes..."
fuser -k 8000/tcp 2>/dev/null
fuser -k 8001/tcp 2>/dev/null
echo "✅ Servidores parados."
