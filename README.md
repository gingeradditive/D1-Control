# GingerDryer

GingerDryer è un progetto per la gestione di asciugatrici intelligenti basato su un backend Python, un frontend React e servizi di sistema per l'esecuzione su dispositivi embedded come Raspberry Pi.

## Panoramica

Il progetto fornisce:
- un backend FastAPI per controllare lo stato dell'asciugatrice, la rete, le configurazioni, gli aggiornamenti e le preset.
- un frontend React con Vite per la UI touchscreen / browser.
- uno script di sviluppo per avviare backend, frontend e reverse proxy in locale.
- uno script di installazione per configurare un sistema kiosk con servizi systemd e Nginx.

## Architettura del repository

```
├── backend/                # API Python, controller, stato condiviso
│   ├── api/                # router FastAPI
│   │   └── routes/         # endpoint REST
│   ├── core/               # stato globale e loop di background
│   ├── dryer/              # controller dryer e componenti hardware
│   ├── network/            # controller rete e scanner Wi-Fi
│   ├── update/             # aggiornamenti software e git
│   └── config_control.py   # gestione configurazioni
│
├── frontend/               # App React + Vite
│   ├── public/
│   ├── src/                # componenti UI e client API
│   └── package.json
│
├── scripts/                # script di installazione, esecuzione e restart
│   ├── install.sh
│   ├── restart_dryer_services.sh
│   └── runbackend.sh
│
├── rundev.sh               # avvia ambiente di sviluppo con backend/frontend/proxy
├── stopdev.sh              # arresta i processi di sviluppo
├── reverse_proxy.py        # proxy dev per routing delle richieste API
├── requirements.txt        # dipendenze Python
└── README.md
```

## Componenti principali

### Backend
- `backend/main.py`: entrypoint FastAPI e avvio del loop di background.
- `backend/api/routes/`: endpoint REST per dryer, network, update, config, stats, presets.
- `backend/core/background.py`: ciclo di aggiornamento periodico del dryer e dei sensori.
- `backend/core/state.py`: oggetto `controllers` condiviso tra router e loop.
- `backend/dryer/controller.py`: logica di controllo temperatura, ventola, valvola, purge e ciclo.
- `backend/network/`: gestione connessione Wi-Fi con NetworkManager.
- `backend/update/`: controllo aggiornamenti git, installazione dipendenze, build frontend e reboot.

### Frontend
- `frontend/src/api.jsx`: client Axios per tutte le API del backend.
- `frontend/src/App.jsx`: applicazione React principale.
- `frontend/src/components/`: dialog, monitoraggio stato, impostazioni, grafici, tastiera virtuale.
- `frontend/package.json`: dipendenze React, MUI, Recharts, Vite.

### Dev & Proxy
- `rundev.sh`: apre un backend uvicorn con reload, un frontend Vite e un reverse proxy.
- `reverse_proxy.py`: inoltra `/api/*` al backend e tutte le altre richieste al frontend.
- `stopdev.sh`: arresta i processi di sviluppo `uvicorn`, `vite` e proxy.

## Dipendenze

### Python
Il backend usa le dipendenze definite in `requirements.txt`, tra cui:
- `fastapi`, `uvicorn`, `httpx`
- `RPi.GPIO`, `pigpio`, `spidev`
- `adafruit-circuitpython-*`

### Frontend
Il frontend React usa:
- `react`, `react-dom`, `@mui/material`, `@mui/icons-material`
- `axios`, `recharts`, `chart.js`
- `vite`, `eslint`, `tailwindcss`

## Installazione e avvio

### Ambiente di sviluppo

1. Installa dipendenze frontend:
   ```bash
   cd frontend
   npm install
   ```
2. Installa dipendenze Python:
   ```bash
   python3 -m pip install -r requirements.txt
   ```
3. Avvia il backend in sviluppo:
   ```bash
   python3 -m uvicorn backend.main:app --reload
   ```
4. Avvia il frontend:
   ```bash
   cd frontend
   npm run dev
   ```
5. Avvia il proxy di sviluppo:
   ```bash
   python3 -m uvicorn reverse_proxy:app --port 3000
   ```

### Avvio rapido in locale

Esegui:
```bash
bash rundev.sh
```

### Interruzione ambiente sviluppo

Esegui:
```bash
bash stopdev.sh
```

### Installazione su dispositivo embedded

Lo script `scripts/install.sh` configura un sistema kiosk completo con:
- utente `pi` e login automatico
- installazione di Node.js, Python, X11, Openbox, LightDM, Chromium
- venv Python e installazione di `requirements.txt`
- build del frontend e servizio `serve`
- servizi systemd: `dryer-backend.service`, `dryer-frontend.service`
- nginx reverse proxy per frontend e API
- abilitazione `pigpiod` e interfacce hardware SPI/I2C
- permessi di rete tramite PolicyKit

Per eseguire l'installazione:
```bash
bash scripts/install.sh
```

## Servizi e porte
- Backend FastAPI: `http://localhost:8000`
- Frontend React dev: `http://localhost:5173`
- Reverse proxy dev: `http://localhost:3000`
- Nginx kiosk (post-install): `http://localhost`

## API principali

### Dryer
- `GET /api/dryer/status`
- `POST /api/dryer/status/{status}`
- `GET /api/dryer/history`
- `POST /api/dryer/setpoint/{value}`
- `POST /api/dryer/filter/reset`
- `POST /api/dryer/filter/set/{hours}`
- `GET /api/dryer/purge-time`
- `POST /api/dryer/purge-time/{seconds}`
- `GET /api/dryer/cycle-time`
- `POST /api/dryer/cycle-time/{seconds}`

### Network
- `GET /api/network/`
- `POST /api/network/connect`
- `GET /api/network/status`
- `GET /api/network/g1os`
- `POST /api/network/forget`

### Config
- `GET /api/config/`
- `POST /api/config/set`
- `GET /api/config/reload`
- `GET /api/config/{key}`
- `POST /api/config/timezone`
- `GET /api/config/timezone`
- `POST /api/config/reset`

### Update
- `GET /api/update/version`
- `GET /api/update/check`
- `POST /api/update/apply`

### Presets
- `GET /api/presets/`
- `GET /api/presets/pinned`
- `PUT /api/presets/pinned`
- `POST /api/presets/`
- `PUT /api/presets/{preset_id}`
- `DELETE /api/presets/{preset_id}`

### Stats
- `GET /api/stats`

## Note hardware

La parte hardware del backend usa driver e librerie per Raspberry Pi, SPI e sensori:
- `backend/dryer/components/sensors.py`
- `backend/dryer/components/fan.py`
- `backend/dryer/components/heater.py`
- `backend/dryer/components/valve.py`

## Contribuire

1. Crea una branch feature.
2. Modifica il codice o la documentazione.
3. Apri una pull request con una breve descrizione delle modifiche.

---

Questa documentazione descrive la struttura e l'uso del progetto GingerDryer. Per dettagli specifici sul funzionamento interno dei controller e dei router, esplora le directory `backend/` e `frontend/src/`.

