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

### Backend

- [ ] **Limiti di temperatura incoerenti su tre livelli**: backend setpoint `0–90`
      ([dryer.py:58](backend/api/routes/dryer.py#L58)), preset `0–70`
      ([presets.py](backend/api/routes/presets.py)), UI clamp `0–70`
      ([StatusManager.jsx:227](frontend/src/components/StatusManager.jsx#L227)).
      Serve una costante unica.
- [ ] **`purge_time` / `cycle_time`: unità ambigue.** Il controller li tratta come **minuti**
      (`* 60`, [controller.py:373](backend/dryer/controller.py#L373)), la UI li etichetta
      "(min)", ma le route li chiamano `seconds`
      ([dryer.py:89](backend/api/routes/dryer.py#L89),
      [dryer.py:101](backend/api/routes/dryer.py#L101)). Il `config.json` versionato nel repo
      ha `purge_time: 60, cycle_time: 3600`, cioè valori scritti pensando ai secondi: chi lo
      usasse otterrebbe uno spurgo da **60 minuti**.
- [ ] **Preset creato con `pinned: true` non viene mai pinnato.**
      `create_preset` ([presets.py](backend/api/routes/presets.py)) salva il campo nel file
      ma non aggiorna `pinned_preset_ids` in config, che è la vera fonte di verità
      (`GET /presets/` sovrascrive `p["pinned"]` da lì). Doppia fonte di verità da eliminare.
- [ ] **Read-modify-write senza lock** su `config.json` e `presets.json`, da thread di
      background e worker FastAPI concorrenti. `os.replace` rende atomica la sostituzione del
      file, non la sequenza leggi→modifica→scrivi: due `set()` simultanei perdono un
      aggiornamento. Serve un `threading.Lock` in `FileConfig`.
- [ ] **`valve` non verifica che pigpiod risponda.** [valve.py:26](backend/dryer/components/valve.py#L26)
      fa `pigpio.pi()` e non controlla `.connected`: se il demone non è attivo ogni
      `set_servo_pulsewidth` solleva un'eccezione — ora silenziata dal `try/except` che ho
      aggiunto al loop, quindi la valvola fallirebbe **in silenzio**.
- [ ] **`Fan.on()` non fa il setup difensivo** che fa `Heater.on()`
      ([fan.py:19](backend/dryer/components/fan.py#L19) vs
      [heater.py:19-30](backend/dryer/components/heater.py#L19-L30)). Se la ventola merita
      meno protezione del riscaldatore va detto in un commento, altrimenti va allineata.
- [ ] **`Valve._set_angle` lascia un `threading.Timer` per ogni movimento** e non lo traccia:
      a `shutdown()` può ancora scattare su un `pi` già chiuso.
- [ ] **`forget()` spezza male l'output nmcli**: `conn.split(":", 1)`
      ([connection.py](backend/network/connection.py)) assume che il *nome* non contenga `:`.
      Va usato `rsplit(":", 1)`.
- [ ] **`subprocess.run` senza `timeout`** in `connect()` e `forget()`
      ([connection.py](backend/network/connection.py)): un nmcli bloccato occupa per sempre
      un worker del threadpool.
- [ ] **`except:` nudo** in [status.py](backend/network/status.py) — cattura anche
      `KeyboardInterrupt`/`SystemExit`.
- [ ] **`is_update_available()` fa `git fetch` sincrono**
      ([git_manager.py](backend/update/git_manager.py)): senza rete solleva → 500 all'apertura
      della UI. Va gestito come "non determinabile", non come errore.
- [ ] **`git clean -fd`** ([git_manager.py](backend/update/git_manager.py)) cancella qualsiasi
      file non tracciato e non ignorato presente sul dispositivo. `config.json`, `presets.json`
      e `logs/` sono in `.gitignore` quindi sopravvivono, ma il margine è sottile: aggiungere
      `-e` espliciti o rimuovere il `clean`.
- [ ] **`install_backend_dependencies` non quota il path**:
      `f"{venv_pip} install -r requirements.txt"` con `shell=True`
      ([dependencies.py](backend/update/dependencies.py)) si rompe se il progetto sta in una
      directory con spazi.

### Frontend

- [ ] **Race su +/- setpoint.**
      [StatusManager.jsx:226-242](frontend/src/components/StatusManager.jsx#L226-L242):
      `api.setPoint(newSet)` non è atteso e subito dopo parte `api.getStatus()` → può leggere
      il valore vecchio e far "rimbalzare" indietro la UI.
- [ ] **Mostra `0°` invece di `--` all'avvio.** `get_status_data()` ritorna `0.0` se la
      history è vuota ([controller.py:350-352](backend/dryer/controller.py#L350-L352)) e
      `currentTemp !== null` è vero per `0`
      ([TemperatureDisplay.jsx:107](frontend/src/components/TemperatureDisplay.jsx#L107)).
- [ ] **`round(temp)` in `/status`** ([dryer.py:17](backend/api/routes/dryer.py#L17)) butta
      via la risoluzione del sensore (0.25 °C) prima ancora che la UI decida come formattarla.
- [ ] **Closure stale sullo screensaver.** `resetTimer`
      ([StatusManager.jsx:200-224](frontend/src/components/StatusManager.jsx#L200-L224)) è
      catturato dall'effect con deps `[inactivityTimeout, isKiosk]` e vede sempre
      `isScreensaverActive === false`: gli eventi globali non lo chiudono, funziona solo il
      tap sull'overlay.
- [ ] **Il check aggiornamenti gira solo al mount**
      ([StatusManager.jsx:125-156](frontend/src/components/StatusManager.jsx#L125-L156)). In
      kiosk la pagina non si ricarica mai → un aggiornamento pubblicato dopo il boot non viene
      mai segnalato.
- [ ] **`checkG1OS` senza `catch`** ([App.jsx:40-45](frontend/src/App.jsx#L40-L45)) → unhandled
      rejection se il backend non risponde.
- [ ] **`Grid item xs={4}`** ([SettingsDialog.jsx:249](frontend/src/components/SettingsDialog.jsx#L249)):
      la prop `item` è stata rimossa nel Grid di MUI v7.
- [ ] **Nessun `timeout` sul client axios** ([api.jsx](frontend/src/api.jsx)): una richiesta
      appesa resta appesa, e il polling a 1 Hz continua ad accodarne altre.
- [ ] **Polling `/status` senza guardia sull'in-flight**
      ([StatusManager.jsx:104-122](frontend/src/components/StatusManager.jsx#L104-L122)): se il
      backend rallenta, le richieste si accumulano.
- [ ] **`timerSet={false} // TODO`** in [Footer.jsx](frontend/src/components/Footer.jsx) — spia
      sempre spenta.

### Installazione / sistema

- [ ] **`chromium-browser` non esiste su Bookworm** (il pacchetto è `chromium`):
      [install.sh:139](scripts/install.sh#L139) e
      [install.sh:385](scripts/install.sh#L385). Lo script dichiara compatibilità
      Bullseye/Bookworm ma il kiosk non partirebbe su Bookworm.
- [ ] **SSH non raggiungibile sull'immagine** (porta 22 rifiuta la connessione sulla macchina
      di test). Diagnosticare da remoto è impossibile: oggi ho potuto lavorare solo perché la
      8000 è esposta. Decidere consapevolmente se abilitarlo o fornire un canale diagnostico
      alternativo.
- [ ] **Credenziali di default hardcoded**: utente `pi` con password `raspberry` e sudo pieno
      ([install.sh:69](scripts/install.sh#L69),
      [install.sh:74](scripts/install.sh#L74)).
- [ ] **Variabile morta** `KEY` in [install.sh:353](scripts/install.sh#L353), calcolata e mai
      usata.
- [ ] **`sudo sysctl` e `sudo swapon` non sono sotto la guardia `IS_BUILD`**
      ([install.sh:107](scripts/install.sh#L107)) — in chroot possono fallire.
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
      `"Heater ON"`). Scegliere una lingua per i log e una per la UI.
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
