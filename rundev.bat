@echo off
echo === Avvio ambiente di sviluppo Dryer Controller ===

REM Avvia il backend in una nuova finestra
echo Avvio backend...
start cmd /k "python3 -m uvicorn backend.main:app --reload"

REM Avvia il frontend React con Vite in una nuova finestra
echo Avvio frontend React...
start cmd /k "cd frontend && npm run dev"

echo Avvio del reverse proxy
start cmd /k "python3 -m uvicorn reverse_proxy:app --port 80"

echo === ====================== ===