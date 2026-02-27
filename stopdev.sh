#!/bin/bash

echo "=== Arresto ambiente di sviluppo Dryer Controller ==="

# Trova e termina i processi uvicorn (backend e reverse proxy)
echo "Arresto backend e reverse proxy..."
pkill -f "uvicorn backend.main:app"
pkill -f "uvicorn reverse_proxy:app"

# Trova e termina i processi vite/npm (frontend)
echo "Arresto frontend..."
pkill -f "vite"
pkill -f "npm run dev"

# Attendi un momento per i processi
sleep 2

# Verifica se i processi sono stati terminati
echo ""
echo "=== VERIFICA PROCESSI ==="
if pgrep -f "uvicorn backend.main:app" > /dev/null; then
    echo "❌ Backend ancora in esecuzione"
else
    echo "✅ Backend arrestato"
fi

if pgrep -f "uvicorn reverse_proxy:app" > /dev/null; then
    echo "❌ Reverse proxy ancora in esecuzione"
else
    echo "✅ Reverse proxy arrestato"
fi

if pgrep -f "vite" > /dev/null; then
    echo "❌ Frontend ancora in esecuzione"
else
    echo "✅ Frontend arrestato"
fi

echo ""
echo "=== Arresto completato ==="
