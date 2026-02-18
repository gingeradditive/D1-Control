#!/bin/bash

echo "=== Avvio ambiente di sviluppo Dryer Controller ==="

# Install dependencies if needed
echo "Verifica dipendenze..."
if [ ! -d "frontend/node_modules" ]; then
    echo "Installazione dipendenze frontend..."
    cd frontend && npm install && cd ..
fi

# Install httpx if needed
python3 -c "import httpx" 2>/dev/null || pip3 install httpx

# Avvia il backend in una nuova finestra
echo "Avvio backend..."
osascript -e "tell application \"Terminal\" to do script \"cd '$(pwd)' && python3 -m uvicorn backend.main:app --reload\""

# Avvia il frontend React con Vite in una nuova finestra
echo "Avvio frontend React..."
osascript -e "tell application \"Terminal\" to do script \"cd '$(pwd)'/frontend && npm run dev\""

echo "Avvio del reverse proxy"
osascript -e "tell application \"Terminal\" to do script \"cd '$(pwd)' && python3 -m uvicorn reverse_proxy:app --port 3000\""

echo ""
echo "=== SERVIZI AVVIATI ==="
echo "🔧 Backend API:     http://localhost:8000"
echo "🌐 Frontend React:  http://localhost:5173"
echo "🔄 Reverse Proxy:   http://localhost:3000"
echo ""
echo "📝 Note:"
echo "   - Il reverse proxy instrada le richieste API al backend (porta 8000)"
echo "   - Il frontend React serve su porta 5173 (Vite dev server)"
echo "   - Accedi all'applicazione completa tramite http://localhost:3000"
echo "   - Per usare la porta 80, esegui: sudo python3 -m uvicorn reverse_proxy:app --port 80"
echo "=== ====================== ==="
