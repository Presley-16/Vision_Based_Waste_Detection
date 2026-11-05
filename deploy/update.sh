#!/usr/bin/env bash
# Pull the latest code from GitHub and restart:  sudo bash /opt/planetwatch/deploy/update.sh
# The database, uploaded photos, weights and .env are not in git, so they're kept.
set -euo pipefail
APP_DIR=/opt/planetwatch

sudo -u planetwatch git -C "$APP_DIR" pull --ff-only
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt" gunicorn
chown -R planetwatch:planetwatch "$APP_DIR"
systemctl restart planetwatch
systemctl --no-pager --lines=5 status planetwatch
