#!/bin/bash
set -euo pipefail

# ─── Helpers ──────────────────────────────────────────────────────────────────

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log()  { echo -e "${GREEN}[✔]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[✘]${NC} $*" >&2; }
section() { echo -e "\n${BLUE}━━━ $* ━━━${NC}"; }

trap 'err "Errore alla linea $LINENO — installazione interrotta."; exit 1' ERR

# ─── Variabili ────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
USERNAME="pi"
VENV="$PROJECT_DIR/venv"
LOG_DIR="$PROJECT_DIR/logs"

# Compatibilità Bullseye (/boot/config.txt) e Bookworm (/boot/firmware/config.txt)
if [ -f /boot/firmware/config.txt ]; then
    BOOT_CONFIG=/boot/firmware/config.txt
else
    BOOT_CONFIG=/boot/config.txt
fi

export DEBIAN_FRONTEND=noninteractive

section "AVVIO INSTALLAZIONE SISTEMA KIOSK"
log "PROJECT_DIR: $PROJECT_DIR"
log "Boot config: $BOOT_CONFIG"

# ─── Utente ───────────────────────────────────────────────────────────────────

section "UTENTE"
if ! id "$USERNAME" &>/dev/null; then
    sudo useradd -m -s /bin/bash "$USERNAME"
    echo "$USERNAME:raspberry" | sudo chpasswd
    sudo usermod -aG sudo "$USERNAME"
    log "Utente '$USERNAME' creato"
else
    warn "Utente '$USERNAME' già esistente, aggiorno password"
    echo "$USERNAME:raspberry" | sudo chpasswd
fi

sudo groupadd -f autologin
sudo usermod -aG autologin "$USERNAME"

# ─── Swap (aumenta stabilità su RPi con poca RAM) ─────────────────────────────

section "SWAP"
SWAPFILE=/swapfile
if [ ! -f "$SWAPFILE" ]; then
    log "Creo swapfile da 1GB..."
    sudo fallocate -l 1G "$SWAPFILE"
    sudo chmod 600 "$SWAPFILE"
    sudo mkswap -f "$SWAPFILE"
    sudo swapon "$SWAPFILE"
    grep -q "$SWAPFILE" /etc/fstab || echo "$SWAPFILE none swap sw 0 0" | sudo tee -a /etc/fstab
    log "Swap da 1GB attivata"
else
    warn "Swapfile già presente, salto"
fi

# Riduci swappiness: il kernel evita di usare swap se possibile
sudo sysctl -q vm.swappiness=10
grep -q "vm.swappiness" /etc/sysctl.conf \
    && sudo sed -i 's/^vm.swappiness=.*/vm.swappiness=10/' /etc/sysctl.conf \
    || echo "vm.swappiness=10" | sudo tee -a /etc/sysctl.conf

# ─── Pacchetti di sistema ─────────────────────────────────────────────────────

section "PACCHETTI DI SISTEMA"
sudo apt-get update -y

log "Rimuovo versioni vecchie di Node..."
sudo apt-get remove --purge -y nodejs npm node-* handlebars \
    node-ansi-escapes node-argparse node-chokidar node-es-abstract \
    node-eslint-scope node-file-entry-cache node-flat-cache node-for-in \
    node-functional-red-black-tree node-is-extendable node-jest-worker \
    node-jsesc node-neo-async node-regenerate node-source-map-support \
    node-strip-json-comments node-to-regex-range node-unique-filename 2>/dev/null || true
sudo apt-get autoremove -y || true
sudo apt-get autoclean

log "Installo Node.js 20..."
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

log "Installo pacchetti kiosk..."
sudo apt-get install --no-install-recommends -y \
    xserver-xorg \
    x11-xserver-utils \
    xinit \
    openbox \
    lightdm \
    lightdm-gtk-greeter \
    unclutter \
    chromium-browser \
    python3-venv \
    python3-pip \
    git \
    curl \
    accountsservice \
    pigpio \
    nginx

# ─── LightDM — login automatico ───────────────────────────────────────────────

section "LIGHTDM AUTOLOGIN"
sudo mkdir -p /etc/lightdm/lightdm.conf.d

sudo tee /etc/lightdm/lightdm.conf > /dev/null <<EOF
[Seat:*]
autologin-user=$USERNAME
autologin-user-timeout=0
autologin-session=openbox
user-session=openbox
EOF

sudo tee /etc/lightdm/lightdm.conf.d/50-autologin.conf > /dev/null <<EOF
[Seat:*]
autologin-user=$USERNAME
autologin-user-timeout=0
autologin-session=openbox
user-session=openbox
EOF

# ─── Python venv ──────────────────────────────────────────────────────────────

section "PYTHON VENV"
cd "$PROJECT_DIR"
python3 -m venv "$VENV"
source "$VENV/bin/activate"

pip install --upgrade pip

if [ -f requirements.txt ]; then
    log "Installazione dipendenze Python (tentativo 1/3)..."
    if ! pip install -r requirements.txt --default-timeout=120; then
        warn "Ritento (2/3) con PyPI diretto..."
        if ! pip install -r requirements.txt --index-url https://pypi.org/simple --default-timeout=120; then
            warn "Ritento (3/3) con DNS Google..."
            echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf > /dev/null || true
            pip install -r requirements.txt --index-url https://pypi.org/simple --default-timeout=120
        fi
    fi
else
    warn "Nessun requirements.txt trovato"
fi

deactivate

# ─── Frontend build ───────────────────────────────────────────────────────────

section "FRONTEND BUILD"
if [ -d "$PROJECT_DIR/frontend" ]; then
    cd "$PROJECT_DIR/frontend"
    npm install --no-audit --no-fund
    npm run build
    cd "$PROJECT_DIR"
    log "Frontend buildato"
else
    warn "Cartella frontend non trovata"
fi

log "Installo server statico serve..."
sudo npm install -g serve
SERVE_PATH=$(which serve)
log "serve: $SERVE_PATH"

# ─── Cartella log ─────────────────────────────────────────────────────────────

section "LOG"
mkdir -p "$LOG_DIR"
chown "$USERNAME:$USERNAME" "$LOG_DIR" 2>/dev/null || true

# ─── Journald — limite dimensione log su SD card ──────────────────────────────

sudo mkdir -p /etc/systemd/journald.conf.d
sudo tee /etc/systemd/journald.conf.d/size-limit.conf > /dev/null <<EOF
[Journal]
SystemMaxUse=100M
SystemKeepFree=200M
MaxRetentionSec=7day
EOF
sudo systemctl restart systemd-journald || true

# ─── Servizi systemd ──────────────────────────────────────────────────────────

section "SERVIZI SYSTEMD"

# Backend FastAPI
sudo tee /etc/systemd/system/dryer-backend.service > /dev/null <<EOF
[Unit]
Description=Dryer Backend (FastAPI)
Documentation=https://github.com/gingeradditive/D1-Control
After=network.target pigpiod.service
Wants=pigpiod.service

[Service]
User=$USERNAME
WorkingDirectory=$PROJECT_DIR
Environment=PYTHONUNBUFFERED=1
ExecStart=$VENV/bin/python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --log-level warning
ExecStop=/bin/kill -SIGTERM \$MAINPID

# Riavvio automatico: solo su crash, non su stop intenzionale
Restart=on-failure
RestartSec=5
StartLimitIntervalSec=120
StartLimitBurst=5

# Shutdown pulito
TimeoutStartSec=60
TimeoutStopSec=15
KillSignal=SIGTERM
KillMode=mixed

# Log su journald (niente file su SD per evitare usura)
StandardOutput=journal
StandardError=journal
SyslogIdentifier=dryer-backend

# Limiti risorse per RPi
LimitNOFILE=65536
MemoryMax=400M
MemorySwapMax=100M
Nice=0

# Hardening minimale
NoNewPrivileges=yes
PrivateTmp=yes

[Install]
WantedBy=multi-user.target
EOF

# Frontend serve (file statici React)
sudo tee /etc/systemd/system/dryer-frontend.service > /dev/null <<EOF
[Unit]
Description=Dryer Frontend (React static build)
Documentation=https://github.com/gingeradditive/D1-Control
After=network.target

[Service]
User=$USERNAME
WorkingDirectory=$PROJECT_DIR/frontend
ExecStart=$SERVE_PATH -s dist -l 3000 --no-clipboard
ExecStop=/bin/kill -SIGTERM \$MAINPID

# Riavvio automatico: solo su crash
Restart=on-failure
RestartSec=5
StartLimitIntervalSec=120
StartLimitBurst=5

# Shutdown pulito
TimeoutStartSec=30
TimeoutStopSec=10
KillSignal=SIGTERM
KillMode=mixed

# Log su journald
StandardOutput=journal
StandardError=journal
SyslogIdentifier=dryer-frontend

# Limiti risorse per RPi
LimitNOFILE=4096
MemoryMax=100M
MemorySwapMax=50M
Nice=5

# Hardening minimale
NoNewPrivileges=yes
PrivateTmp=yes

[Install]
WantedBy=multi-user.target
EOF

log "Ricarico systemd e abilito servizi..."
sudo systemctl daemon-reload
sudo systemctl enable dryer-backend.service
sudo systemctl enable dryer-frontend.service

# ─── pigpiod ──────────────────────────────────────────────────────────────────

section "PIGPIOD"
sudo systemctl enable pigpiod.service
sudo systemctl start pigpiod.service

# ─── Permessi rete (NetworkManager / polkit) ──────────────────────────────────

section "PERMESSI RETE"
sudo usermod -aG netdev "$USERNAME"

sudo tee /etc/polkit-1/localauthority/50-local.d/10-nmcli.pkla > /dev/null <<EOF
[Allow NetworkManager all permissions for user]
Identity=unix-user:$USERNAME
Action=org.freedesktop.NetworkManager.*
ResultAny=yes
ResultInactive=yes
ResultActive=yes
EOF

# ─── Hardware: SPI e I2C ──────────────────────────────────────────────────────

section "HARDWARE SPI/I2C"
for PARAM in "dtparam=spi=on" "dtparam=i2c_arm=on"; do
    KEY="${PARAM%%=*}=${PARAM##*=on}"   # dtparam=spi / dtparam=i2c_arm
    sudo sed -i "s/^#${PARAM}/${PARAM}/" "$BOOT_CONFIG" || true
    grep -q "^${PARAM}" "$BOOT_CONFIG" || echo "$PARAM" | sudo tee -a "$BOOT_CONFIG"
done

for MOD in spi-dev i2c-dev; do
    grep -q "^$MOD" /etc/modules || echo "$MOD" | sudo tee -a /etc/modules
done

# ─── Sudo reboot senza password ───────────────────────────────────────────────

section "SUDO REBOOT"
REBOOT_PATH=$(which reboot)
SUDOERS_FILE=/etc/sudoers.d/dryer-reboot
sudo tee "$SUDOERS_FILE" > /dev/null <<EOF
$USERNAME ALL=NOPASSWD: $REBOOT_PATH
EOF
sudo chmod 440 "$SUDOERS_FILE"
sudo visudo -c -f "$SUDOERS_FILE" || { err "sudoers non valido, rimuovo"; sudo rm "$SUDOERS_FILE"; exit 1; }

# ─── Openbox — kiosk Chromium ─────────────────────────────────────────────────

section "KIOSK OPENBOX"
mkdir -p /home/$USERNAME/.config/openbox
tee /home/$USERNAME/.config/openbox/autostart > /dev/null <<EOF
# Disabilita screensaver e risparmio energetico display
xset s off
xset -dpms
xset s noblank
unclutter -idle 0 &

# Avvia Chromium in modalità kiosk
chromium-browser \\
  --noerrdialogs \\
  --disable-infobars \\
  --kiosk \\
  --disable-gpu \\
  --disable-software-rasterizer \\
  --disable-dev-shm-usage \\
  --no-sandbox \\
  --process-per-site \\
  --disk-cache-size=1 \\
  --media-cache-size=1 \\
  http://localhost/?kiosk=true &
EOF
chmod +x /home/$USERNAME/.config/openbox/autostart
chown -R $USERNAME:$USERNAME /home/$USERNAME/.config

# ─── Nginx reverse proxy ──────────────────────────────────────────────────────

section "NGINX"
NGINX_CONF=/etc/nginx/sites-available/dryer

sudo tee "$NGINX_CONF" > /dev/null <<EOF
server {
    listen 80 default_server;
    server_name _;

    # Frontend React (file statici)
    location / {
        proxy_pass         http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header   Host \$host;
        proxy_set_header   X-Real-IP \$remote_addr;
        proxy_read_timeout 30;
    }

    # API Backend
    location /api/ {
        proxy_pass            http://localhost:8000/api/;
        proxy_http_version    1.1;
        proxy_set_header      Host \$host;
        proxy_set_header      X-Real-IP \$remote_addr;
        proxy_read_timeout    300;
        proxy_connect_timeout 10;
        proxy_send_timeout    300;
        proxy_buffering       off;
    }

    # WebSocket
    location /ws/ {
        proxy_pass          http://localhost:8000/ws/;
        proxy_http_version  1.1;
        proxy_set_header    Upgrade \$http_upgrade;
        proxy_set_header    Connection "upgrade";
        proxy_set_header    Host \$host;
        proxy_read_timeout  3600;
    }

    gzip on;
    gzip_types text/plain text/css application/json application/javascript application/xml;
    gzip_min_length 256;
}
EOF

sudo ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/dryer
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl enable nginx
sudo systemctl restart nginx

# ─── LightDM & grafica ────────────────────────────────────────────────────────

section "LIGHTDM"
sudo systemctl enable lightdm
sudo systemctl set-default graphical.target

# ─── Avvio servizi ────────────────────────────────────────────────────────────

section "AVVIO SERVIZI"
log "Avvio dryer-backend..."
sudo systemctl restart dryer-backend.service
log "Avvio dryer-frontend..."
sudo systemctl restart dryer-frontend.service

sleep 3
log "Stato servizi:"
sudo systemctl is-active dryer-backend.service  && log "  dryer-backend:  ATTIVO" || warn "  dryer-backend:  non attivo"
sudo systemctl is-active dryer-frontend.service && log "  dryer-frontend: ATTIVO" || warn "  dryer-frontend: non attivo"
sudo systemctl is-active pigpiod.service        && log "  pigpiod:        ATTIVO" || warn "  pigpiod:        non attivo"
sudo systemctl is-active nginx.service          && log "  nginx:          ATTIVO" || warn "  nginx:          non attivo"

# ─── Fine ─────────────────────────────────────────────────────────────────────

section "INSTALLAZIONE COMPLETATA"
log "Sistema kiosk pronto."
log "Per i log: journalctl -u dryer-backend -f  |  journalctl -u dryer-frontend -f"
warn "Riavvio consigliato per applicare le modifiche al boot config: sudo reboot"
