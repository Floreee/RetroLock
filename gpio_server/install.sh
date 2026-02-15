#!/bin/bash

set -e

DOMAIN="domain.net"
EMAIL="mail@gmail.com"  # <- Ersetze mit deiner echten Adresse!
APP_DIR="/home/pi/retrolock"
VENV_DIR="$APP_DIR/venv"
LOG_FILE="/var/log/retrolock.log"
TOKEN_DIR="/etc/retrolock"
TOKEN_FILE="$TOKEN_DIR/token"
SERVICE_FILE="/etc/systemd/system/retrolock.service"
CERT_DIR="/etc/letsencrypt/live/$DOMAIN"
SCRIPT_FILE="$APP_DIR/retrolock.py"
HOOK_PATH="/etc/letsencrypt/renewal-hooks/post/restart-retrolock.sh"

echo "📦 Installiere System-Abhängigkeiten..."
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv nginx certbot python3-certbot-nginx openssl

echo "📁 Erstelle Anwendungsverzeichnisse..."
mkdir -p "$APP_DIR"
sudo mkdir -p "$TOKEN_DIR"
sudo touch "$LOG_FILE"
sudo chown pi:pi "$LOG_FILE"

echo "🐍 Erstelle Python venv in $VENV_DIR..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

echo "📦 Installiere Python-Abhängigkeiten im venv..."
pip install --upgrade pip
pip install flask RPi.GPIO

echo "🔐 Token-Datei prüfen/erzeugen..."
if [ ! -f "$TOKEN_FILE" ]; then
    GENERATED_TOKEN=$(openssl rand -hex 32)
    echo "$GENERATED_TOKEN" | sudo tee "$TOKEN_FILE" > /dev/null
    sudo chown pi:pi "$TOKEN_FILE"
    sudo chmod 600 "$TOKEN_FILE"
    echo "✅ Neuer Token wurde generiert."
else
    GENERATED_TOKEN=$(sudo cat "$TOKEN_FILE")
    echo "ℹ️  Existierender Token gefunden."
fi

echo "🚚 Stelle sicher, dass das Python-Skript vorhanden ist..."
if [ ! -f "$SCRIPT_FILE" ]; then
    echo "❌ Datei $SCRIPT_FILE fehlt. Bitte zuerst dort ablegen."
    exit 1
fi
sudo chown pi:pi "$SCRIPT_FILE"

echo "🌐 Erzeuge SSL-Zertifikat mit Let's Encrypt..."
sudo systemctl enable nginx
sudo systemctl start nginx

sudo certbot --nginx --non-interactive --agree-tos -m "$EMAIL" -d "$DOMAIN"

if ! sudo test -f "$CERT_DIR/fullchain.pem" || ! sudo test -f "$CERT_DIR/privkey.pem"; then
    echo "❌ SSL-Zertifikate konnten nicht erstellt werden. Abbruch."
    exit 1
fi

echo "🔁 Installiere Certbot-Hook zum automatischen Neustart nach Erneuerung..."

sudo mkdir -p "$(dirname "$HOOK_PATH")"

sudo bash -c "cat > $HOOK_PATH" <<EOF
#!/bin/bash
# Certbot-Hook: Wird nach erfolgreicher Zertifikat-Erneuerung ausgeführt

echo "[INFO] SSL-Zertifikat wurde erneuert. Starte retrolock neu..."
systemctl restart retrolock.service
EOF

sudo chmod +x "$HOOK_PATH"
echo "✅ Certbot-Hook installiert: $HOOK_PATH"


sudo systemctl stop nginx
sudo systemctl disable nginx

echo "🛠️ Erstelle systemd-Service-Datei..."
sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=RetroLock GPIO Flask Server
After=network.target

[Service]
User=pi
WorkingDirectory=$APP_DIR
ExecStart=$VENV_DIR/bin/python $SCRIPT_FILE
Restart=always

[Install]
WantedBy=multi-user.target
EOF

echo "🔄 Lade systemd und starte Dienst..."
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable retrolock.service
sudo systemctl restart retrolock.service

echo ""
echo "✅ Installation abgeschlossen!"
echo "🌐 Service läuft unter: https://$DOMAIN:5000"
echo "🔑 Dein Zugriffstoken lautet:"
echo ""
echo "$GENERATED_TOKEN"
echo ""

