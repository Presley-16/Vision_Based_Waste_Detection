#!/usr/bin/env bash
# One-time setup of PlanetWatch on a fresh Ubuntu 22.04/24.04 server.
#
#   sudo git clone https://github.com/Presley-16/Vision_Based_Waste_Detection.git /opt/planetwatch
#   sudo bash /opt/planetwatch/deploy/setup.sh <domain> <email>
#
# <domain> must already point at this server (e.g. planetwatch.southafricanorth.cloudapp.azure.com);
# <email> is where Let's Encrypt sends certificate expiry notices. Safe to re-run.
set -euo pipefail

DOMAIN="${1:?usage: setup.sh <domain> <email>}"
EMAIL="${2:?usage: setup.sh <domain> <email>}"
APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
[ "$APP_DIR" = /opt/planetwatch ] || { echo "Clone the repo to /opt/planetwatch first (see the top of this file)."; exit 1; }

echo "==> System packages"
apt-get update
apt-get install -y python3-venv python3-pip git nginx certbot python3-certbot-nginx libgl1 libglib2.0-0 sqlite3

# Swap so installing PyTorch and loading the model can't run the server out of memory.
if ! swapon --show | grep -q .; then
  echo "==> Adding 2 GB swap"
  fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
  grep -q /swapfile /etc/fstab || echo "/swapfile none swap sw 0 0" >> /etc/fstab
fi

echo "==> App user"
id planetwatch >/dev/null 2>&1 || useradd --system --create-home --home-dir /var/lib/planetwatch --shell /usr/sbin/nologin planetwatch

echo "==> Python environment (CPU-only PyTorch: the server has no GPU)"
[ -d "$APP_DIR/venv" ] || python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --upgrade pip
"$APP_DIR/venv/bin/pip" install torch torchvision --index-url https://download.pytorch.org/whl/cpu
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt" gunicorn

echo "==> Settings"
if [ ! -f "$APP_DIR/.env" ]; then
  MUNICIPAL_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(12))')"
  sed -e "s|__SECRET_KEY__|$(python3 -c 'import secrets; print(secrets.token_hex(32))')|" \
      -e "s|__DOMAIN__|$DOMAIN|" \
      -e "s|__MUNICIPAL_PASSWORD__|$MUNICIPAL_PASSWORD|" \
      "$APP_DIR/deploy/env.production.example" > "$APP_DIR/.env"
  echo "    Municipal dashboard: username admin, password $MUNICIPAL_PASSWORD  (write it down; it's also in $APP_DIR/.env)"
fi
mkdir -p "$APP_DIR/backend/instance" "$APP_DIR/backend/uploads" "$APP_DIR/model/weights" "$APP_DIR/mobile/dist"
chown -R planetwatch:planetwatch "$APP_DIR"
chmod 600 "$APP_DIR/.env"
git config --system --add safe.directory "$APP_DIR"

echo "==> Service"
cp "$APP_DIR/deploy/planetwatch.service" /etc/systemd/system/planetwatch.service
systemctl daemon-reload
systemctl enable planetwatch
systemctl restart planetwatch

echo "==> nginx + https"
sed "s|__DOMAIN__|$DOMAIN|" "$APP_DIR/deploy/nginx.conf" > /etc/nginx/sites-available/planetwatch
ln -sf /etc/nginx/sites-available/planetwatch /etc/nginx/sites-enabled/planetwatch
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx
certbot --nginx -d "$DOMAIN" -m "$EMAIL" --agree-tos --redirect --non-interactive

echo
echo "PlanetWatch is running at https://$DOMAIN"
[ -f "$APP_DIR/model/weights/best.pt" ] || echo "Next: upload the model weights to $APP_DIR/model/weights/best.pt (see deploy/README.md) — until then photos are refused with 'waste check unavailable'."
