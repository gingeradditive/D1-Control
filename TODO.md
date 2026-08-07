# TODO — Audit tecnico D1-Control

Audit del 2026-08-07 su `main` @ `312106f`, verificato contro la macchina di test
`192.168.1.114` (immagine `mainsailos`, aarch64, RPi 1.7 GB RAM).

Legenda priorità:

- 🔴 **Critico** — rischio sicurezza funzionale, danno hardware o perdita dati
- 🟠 **Bug** — comportamento sbagliato, non pericoloso
- 🟡 **Miglioria** — robustezza, manutenibilità, UX
- 🔵 **Ottimizzazione** — performance, usura SD, dimensione bundle, pulizia

---

## 🟠 Bug

### Installazione / sistema

- [ ] **`reverse_proxy.py` importa `httpx`, assente da `requirements.txt`.**
- [ ] **`import board` in [scanner.py](backend/network/scanner.py)**: import inutilizzato di
      Adafruit Blinka, **non dichiarato in `requirements.txt`**. Oggi funziona solo perché il
      pacchetto è presente nell'immagine `mainsailos` di base (verificato: lo scan restituisce
      reti reali). Se sparisse, `IS_RASPBERRY` diventerebbe `False` e lo scan Wi-Fi
      restituirebbe in silenzio **le tre reti finte di simulazione** in produzione. Rimuovere
      l'import.

---

## 🟡 Migliorie

- [ ] **Isteresi troppo stretta.** `tolerance = setpoint * 1%`
      ([controller.py:37](backend/dryer/controller.py#L37)): a 50 °C sono 0.5 °C, cioè due LSB
      del MAX6675 (risoluzione 0.25 °C). Il riscaldatore ciclerà sul rumore. Usare
      un'isteresi assoluta configurabile (es. 1.5 °C).
- [ ] **Nessun rilevamento "riscalda ma non sale".** Se la termocoppia si sfila dal blocco, se
      l'SSR si guasta aperto o se la resistenza si brucia, il sistema resta acceso all'infinito
      senza accorgersene. Aggiungere un check sulla derivata: riscaldatore ON per N minuti con
      ΔT < soglia → errore.
- [ ] **Nessun limite di sicurezza assoluto** indipendente dal setpoint: `SENSOR_TEMP_MAX` è a
      300 °C, cioè una soglia di guasto sensore, non un limite di processo. Aggiungere un
      cutoff duro (es. 90 °C) che spegne comunque.
- [ ] **Media/filtro sulle letture.** Il MAX6675 converte in ~220 ms e viene letto a 1 Hz senza
      filtro: la temperatura mostrata è un singolo campione rumoroso. Media mobile su 3-5
      letture.
- [ ] **Il MAX6675 non logga mai il raw in caso di anomalia**
      ([sensors.py:38-43](backend/dryer/components/sensors.py#L38-L43)). Con i due byte grezzi
      a disposizione questo bug si sarebbe diagnosticato in un minuto.
- [ ] **La `history` vive solo in RAM** (43200 punti,
      [controller.py:48](backend/dryer/controller.py#L48)) e si perde ad ogni riavvio, benché il
      CSV giornaliero esista già su disco e non venga mai riletto.
- [ ] **Nessun endpoint `/api/health`.** Un endpoint che riporti l'età dell'ultima lettura
      sensore, lo stato del thread di background e l'uptime avrebbe reso il bug di oggi
      evidente in cinque secondi. È la singola aggiunta con il miglior rapporto
      valore/sforzo di questa lista.
- [ ] **Nessun accesso ai log dalla UI**: per capire cosa è successo serve `journalctl`, cioè
      SSH, che è chiuso.
- [ ] **Nessun test automatico.** Il bug di oggi sarebbe stato preso da un singolo test che fa
      girare `background_loop` per 11 secondi e verifica che la history cresca. Partire da lì:
      `read_sensor` (validi/non validi/fault), `update_heater` (isteresi, valvola aperta),
      `_accumulate_session_hours`, `FileConfig` concorrente.
- [ ] **Nessuna CI** che almeno importi il backend e builda il frontend su PR.
- [ ] **Stato "acceso" non persistente**: dopo un riavvio imprevisto il dryer resta spento senza
      alcuna segnalazione all'operatore che il ciclo è stato interrotto.
- [ ] **Messaggi misti italiano/inglese** in log e UI (`"Setpoint aggiornato a"` accanto a
      `"Heater ON"`). Scegliere una lingua per i log e una per la UI (UTILIZZARE INGLESE)
- [ ] **`screensaver_delay` è una chiave di config morta**: il codice usa
      `inactivity_timeout`. Rimuoverla dai default.
- [ ] **Versione = hash di commit** ([SettingsDialog.jsx:325](frontend/src/components/SettingsDialog.jsx#L325)):
      per il supporto sul campo serve un tag semver leggibile.

---

## 🔵 Ottimizzazioni

- [ ] **Usura della SD.** `FileConfig` rilegge e riscrive l'intero JSON con `fsync` ad **ogni**
      `get()` e `set()` ([file_config.py](backend/core/config/file_config.py)). Tenere lo stato
      in memoria e scrivere in write-behind solo su modifica reale.
- [ ] **`periodic_save_hours` fa due `set()`**
      ([controller.py:262-269](backend/dryer/controller.py#L262-L269)) = due cicli
      read+write+fsync ogni 5 minuti dove ne basta uno.
- [ ] **`get_history_data` è O(n × finestre).** Scansiona tutti i 43200 punti una volta per
      ciascuna delle 60 finestre ([controller.py:309-334](backend/dryer/controller.py#L309-L334)).
      In modalità `1m` il ChartDialog la chiama **ogni secondo**. La deque è ordinata: usare
      `bisect` per tagliare l'intervallo, o un singolo passaggio con bucket.
- [ ] **`_cpu_usage()` fa `time.sleep(0.1)` dentro una route sincrona**
      ([stats.py:22-35](backend/api/routes/stats.py#L22-L35)), bloccando un worker del
      threadpool ad ogni richiesta di statistiche.
- [ ] **Re-render dell'intero albero a 1 Hz**: `setStatus(res.data)` sostituisce sempre
      l'oggetto, anche quando nulla è cambiato. Su un Pi conta. Confrontare e aggiornare solo
      sui campi realmente variati.
- [ ] **86400 richieste HTTP/giorno solo per lo status.** Il proxy nginx ha già la `location
      /ws/` configurata ma non esiste alcun WebSocket lato backend: sostituire il polling con
      un push.
- [ ] **Dipendenze morte da rimuovere** (tempo di `npm install` e build sul Pi):
      `chart.js`, `react-chartjs-2`, `react-simple-keyboard`, `simple-keyboard-layouts` in
      [frontend/package.json](frontend/package.json) — l'unico grafico usa `recharts` e la
      tastiera è stata riscritta in `c8c6268`. Anche il
      [package.json](package.json) di root esiste solo per una dipendenza `notistack` inutile.
- [ ] **Nessun code splitting**: tutti i dialog (Settings, Stats, Presets, Chart, Wifi) sono nel
      bundle iniziale. `React.lazy` su ciascuno.
- [ ] **Chromium avviato con `--disable-gpu`** ([install.sh:389](scripts/install.sh#L389)):
      se è un workaround per un bug specifico va documentato, altrimenti costa fluidità alle
      animazioni del display.
