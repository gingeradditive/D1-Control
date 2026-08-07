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
