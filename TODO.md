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

- [ ] **Nessun code splitting**: tutti i dialog (Settings, Stats, Presets, Chart, Wifi) sono nel
      bundle iniziale. `React.lazy` su ciascuno.
- [ ] **Chromium avviato con `--disable-gpu`** ([install.sh:389](scripts/install.sh#L389)):
      se è un workaround per un bug specifico va documentato, altrimenti costa fluidità alle
      animazioni del display.
