#!/bin/bash
set -e

echo "=== 🔄 AGGIORNAMENTO MANUALE DOPO GIT PULL ==="

PROJECT_DIR=$(pwd)
USERNAME="pi"

echo "📥 Aggiornamento Backend (Python)..."
if [ -d "$PROJECT_DIR/venv" ]; then
    echo "✅ Ambiente virtuale trovato, attivo..."
    source "$PROJECT_DIR/venv/bin/activate"
    
    if [ -f "requirements.txt" ]; then
        echo "📦 Aggiorno dipendenze Python..."
        pip install --upgrade pip
        if ! pip install -r requirements.txt --default-timeout=100; then
            echo "⚠️ Ritento usando solo PyPI..."
            pip install -r requirements.txt --index-url https://pypi.org/simple --default-timeout=100
        fi
    else
        echo "⚠️ Nessun requirements.txt trovato."
    fi
else
    echo "❌ Ambiente virtuale non trovato in $PROJECT_DIR/venv"
    echo "💡 Esegui prima: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
fi

echo "📦 Aggiornamento Frontend (React)..."
if [ -d "$PROJECT_DIR/frontend" ]; then
    cd "$PROJECT_DIR/frontend"
    
    if [ -f "package.json" ]; then
        echo "📦 Aggiorno dipendenze npm..."
        npm install --no-audit --no-fund
        
        if npm run | grep -q "build"; then
            echo "🔨 Build frontend..."
            npm run build
        else
            echo "⚠️ Nessuno script build trovato in package.json."
        fi
    else
        echo "⚠️ Nessun package.json trovato in frontend/"
    fi
    
    cd "$PROJECT_DIR"
else
    echo "❌ Cartella frontend non trovata."
fi

echo "🔁 Riavvio servizi..."
if systemctl is-active --quiet dryer-backend.service; then
    echo "🔄 Riavvio backend..."
    sudo systemctl restart dryer-backend.service
else
    echo "ℹ️ Servizio backend non attivo, lo avvio..."
    sudo systemctl start dryer-backend.service
fi

if systemctl is-active --quiet dryer-frontend.service; then
    echo "🔄 Riavvio frontend..."
    sudo systemctl restart dryer-frontend.service
else
    echo "ℹ️ Servizio frontend non attivo, lo avvio..."
    sudo systemctl start dryer-frontend.service
fi

echo "📊 Stato servizi:"
echo "Backend: $(systemctl is-active dryer-backend.service)"
echo "Frontend: $(systemctl is-active dryer-frontend.service)"

echo "✅ Aggiornamento completato!"
