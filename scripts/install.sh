#!/bin/bash
set -e

export DEBIAN_FRONTEND=noninteractive

echo "=== 🛠️ INSTALLAZIONE SISTEMA KIOSK ==="

PROJECT_DIR=$(pwd)
USERNAME=$(whoami)

echo "📦 Aggiorno sistema e installo pacchetti base..."
sudo apt-get update -y
sudo apt-get upgrade -y
sudo apt-get install --no-install-recommends -y \
xserver-xorg \
x11-xserver-utils \
xinit \
openbox \
lightdm \
unclutter \
chromium-browser \
python3-venv \
python3-pip \
npm \
git \
curl

# Imposta LightDM per login automatico in grafica
echo "🖥️ Configuro LightDM per login automatico..."
LIGHTDM_CONF="/etc/lightdm/lightdm.conf"
sudo mkdir -p /etc/lightdm
sudo tee "$LIGHTDM_CONF" > /dev/null <<EOF
[Seat:*]
autologin-user=$USERNAME
autologin-user-timeout=0
user-session=openbox
EOF

echo "📦 Aggiorno Node..."
sudo apt-get remove -y nodejs || true
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

echo "🐍 Creo ambiente virtuale Python..."
python3 -m venv venv
source venv/bin/activate

echo "📦 Installo dipendenze Python da requirements.txt..."
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
echo "📦 Tentativo 1: installazione da piwheels + pypi"
if ! pip install -r requirements.txt --default-timeout=100; then
echo "⚠️ Ritento (2/3) usando solo PyPI..."
if ! pip install -r requirements.txt --index-url https://pypi.org/simple --default-timeout=100; then
echo "⚠️ Ritento (3/3) con DNS Google..."
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf > /dev/null || true
pip install -r requirements.txt --index-url https://pypi.org/simple --default-timeout=100
fi
fi
else
echo "⚠️ Nessun requirements.txt trovato, salto installazione pacchetti Python."
fi

echo "📦 Installo dipendenze npm per il frontend..."
if [ -d "$PROJECT_DIR/frontend" ]; then
cd "$PROJECT_DIR/frontend"
npm install --no-audit --no-fund
if npm run | grep -q "build"; then
npm run build
else
echo "⚠️ Nessuno script build trovato in package.json."
fi
cd "$PROJECT_DIR"
else
echo "⚠️ Cartella frontend non trovata, salto build."
fi

echo "📦 Installo globalmente il server statico serve..."
sudo npm install -g serve

echo "=== ⚙️ CONFIGURO SERVIZI SYSTEMD ==="

# Backend FastAPI service
sudo tee /etc/systemd/system/dryer-backend.service > /dev/null <<EOF
[Unit]
Description=Dryer Backend (FastAPI)
After=network.target

[Service]
User=$USERNAME
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Frontend serve service
sudo tee /etc/systemd/system/dryer-frontend.service > /dev/null <<EOF
[Unit]
Description=Dryer Frontend (React static build with serve)
After=network.target

[Service]
User=$USERNAME
WorkingDirectory=$PROJECT_DIR/frontend
ExecStart=/usr/bin/serve -s dist -l 3000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

echo "🔁 Abilito i servizi all'avvio..."
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable dryer-backend.service
sudo systemctl enable dryer-frontend.service

echo "📂 Creo cartella per i log dell'applicazione..."
mkdir -p "$PROJECT_DIR/logs"

echo "🛜 Aggiungo permessi per gestire le reti"
sudo usermod -aG netdev "$USERNAME"

POLKIT_FILE="/etc/polkit-1/localauthority/50-local.d/10-nmcli.pkla"
sudo tee "$POLKIT_FILE" > /dev/null <<EOF
[Allow NetworkManager all permissions for user]
Identity=unix-user:$USERNAME
Action=org.freedesktop.NetworkManager.*
ResultAny=yes
ResultInactive=yes
ResultActive=yes
EOF

echo "File $POLKIT_FILE creato con successo."

echo "🔌 Abilito interfacce hardware (SPI, I2C)"
sudo sed -i 's/^#dtparam=spi=on/dtparam=spi=on/' /boot/config.txt || true
grep -q '^dtparam=spi=on' /boot/config.txt || echo 'dtparam=spi=on' | sudo tee -a /boot/config.txt
sudo sed -i 's/^#dtparam=i2c_arm=on/dtparam=i2c_arm=on/' /boot/config.txt || true
grep -q '^dtparam=i2c_arm=on' /boot/config.txt || echo 'dtparam=i2c_arm=on' | sudo tee -a /boot/config.txt

echo "spi-dev" | sudo tee -a /etc/modules || true
echo "i2c-dev" | sudo tee -a /etc/modules || true

echo "🔧 Configuro permessi sudo per reboot senza password..."
REBOOT_PATH=$(which reboot)
SUDOERS_FILE="/etc/sudoers.d/reboot_without_password"
sudo tee "$SUDOERS_FILE" > /dev/null <<EOF
$USERNAME ALL=NOPASSWD: $REBOOT_PATH
EOF
sudo chmod 440 "$SUDOERS_FILE"

echo "🧩 Configuro autostart di Openbox (kiosk)..."
mkdir -p /home/$USERNAME/.config/openbox
cat > /home/$USERNAME/.config/openbox/autostart <<EOF
xset s off
xset -dpms
xset s noblank
unclutter -idle 0 &
chromium-browser --noerrdialogs --disable-infobars --kiosk http://localhost:3000/?kiosk=true &
EOF
chown -R $USERNAME:$USERNAME /home/$USERNAME/.config

echo "🔌 Installo e abilito pigpio daemon..."
sudo apt-get install -y pigpio
sudo systemctl enable pigpiod.service
sudo systemctl start pigpiod.service

echo "✅ Installazione completata — sistema kiosk pronto al riavvio!"