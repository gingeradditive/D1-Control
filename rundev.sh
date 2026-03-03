#!/bin/bash

echo "=== Avvio ambiente di sviluppo Dryer Controller ==="

# Install dependencies if needed
echo "Verifica dipendenze..."
if [ ! -d "frontend/node_modules" ]; then
    echo "Installazione dipendenze frontend..."
    cd frontend && npm install && cd ..
fi

# Install required Python packages if needed
for package in httpx uvicorn fastapi; do
    if ! python3 -c "import $package" 2>/dev/null; then
        echo "Installazione $package..."
        if command -v apt-get >/dev/null 2>&1; then
            case $package in
                httpx)
                    sudo apt-get install -y python3-httpx
                    ;;
                uvicorn)
                    sudo apt-get install -y python3-uvicorn || (python3 -m pip install uvicorn || pip3 install uvicorn || pip install uvicorn)
                    ;;
                fastapi)
                    sudo apt-get install -y python3-fastapi || (python3 -m pip install fastapi || pip3 install fastapi || pip install fastapi)
                    ;;
            esac
        elif command -v pip3 >/dev/null 2>&1; then
            pip3 install $package
        elif command -v pip >/dev/null 2>&1; then
            pip install $package
        elif python3 -m pip --version >/dev/null 2>&1; then
            python3 -m pip install $package
        else
            echo "ATTENZIONE: Impossibile installare $package. Il backend potrebbe non funzionare correttamente."
        fi
    fi
done

# Function to open new terminal window or run in background
open_new_terminal() {
    local command="$1"
    if command -v gnome-terminal >/dev/null 2>&1; then
        gnome-terminal -- bash -c "$command; exec bash" &
    elif command -v x-terminal-emulator >/dev/null 2>&1; then
        x-terminal-emulator -e bash -c "$command; exec bash" &
    elif command -v xterm >/dev/null 2>&1; then
        xterm -e bash -c "$command; exec bash" &
    else
        echo "Nessun terminale compatibile trovato. Esecuzione in background con nohup..."
        nohup bash -c "$command" > /dev/null 2>&1 &
        sleep 1  # Give the process time to start
    fi
}

# Avvia il backend in una nuova finestra
echo "Avvio backend..."
open_new_terminal "cd '$(pwd)' && python3 -m uvicorn backend.main:app --reload"

# Avvia il frontend React con Vite in una nuova finestra
echo "Avvio frontend React..."
open_new_terminal "cd '$(pwd)'/frontend && npm run dev"

echo "Avvio del reverse proxy"
open_new_terminal "cd '$(pwd)' && python3 -m uvicorn reverse_proxy:app --port 3000"

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