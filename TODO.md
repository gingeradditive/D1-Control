# TODO — Audit tecnico D1-Control

Audit del 2026-08-07 su `main` @ `312106f`, verificato contro la macchina di test
`192.168.1.114` (immagine `mainsailos`, aarch64, RPi 1.7 GB RAM).

Legenda priorità:

- 🔴 **Critico** — rischio sicurezza funzionale, danno hardware o perdita dati
- 🟠 **Bug** — comportamento sbagliato, non pericoloso
- 🟡 **Miglioria** — robustezza, manutenibilità, UX
- 🔵 **Ottimizzazione** — performance, usura SD, dimensione bundle, pulizia

---

## 🔵 Ottimizzazioni

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
