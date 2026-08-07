#!/bin/bash

# Uscita immediata in caso di errore
set -e

echo "🔧 Spostamento nella cartella superiore..."
cd ..

echo "🛑 Arresto del servizio dryer-backend..."
sudo systemctl stop dryer-backend.service

echo "🐍 Attivazione ambiente virtuale..."
source venv/bin/activate

echo "🚀 Avvio del server FastAPI in modalità debug..."
# Come il servizio: solo loopback. Per esporlo temporaneamente in rete durante il
# debug: HOST=0.0.0.0 ./runbackend.sh
python -m uvicorn backend.main:app --host "${HOST:-127.0.0.1}" --port 8000