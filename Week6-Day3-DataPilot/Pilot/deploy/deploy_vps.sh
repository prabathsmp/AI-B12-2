#!/usr/bin/env bash
# DataPilot - one-shot HTTPS deployment on an Ubuntu/Debian VPS (Docker + Nginx + Let's Encrypt).
#
# Usage (run ON the VPS, from the Pilot folder):
#   sudo bash deploy/deploy_vps.sh
#
# Optional env vars:
#   DOMAIN=datapilot.smpdigihub.online   public hostname (DNS A record must point at this VPS)
#   APP_PORT=8503                        local port the container listens on (127.0.0.1 only)
#   LE_EMAIL=you@example.com             Let's Encrypt email (only needed if certbot was never registered)
#   BASIC_AUTH_USER=admin                if set, protects the site with a username/password prompt
#   BASIC_AUTH_PASS=...                  (prompted for if BASIC_AUTH_USER is set and this is empty)
set -euo pipefail

DOMAIN="${DOMAIN:-datapilot.smpdigihub.online}"
APP_PORT="${APP_PORT:-8503}"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SITE="/etc/nginx/sites-available/datapilot"

log() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
die() { printf '\n\033[1;31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || die "Run as root (sudo)."
cd "$APP_DIR"
[[ -f docker-compose.yml ]] || die "docker-compose.yml not found in $APP_DIR"

# ---------------------------------------------------------------- 1. prerequisites
log "Checking prerequisites"
command -v docker >/dev/null || { log "Installing Docker"; curl -fsSL https://get.docker.com | sh; }
docker compose version >/dev/null 2>&1 || die "Docker Compose v2 plugin missing (apt install docker-compose-plugin)."

if ! command -v nginx >/dev/null; then
  # Another proxy already owns 80/443? Then don't install nginx on top of it.
  if ss -ltnp 2>/dev/null | grep -qE ':(80|443)\s'; then
    ss -ltnp | grep -E ':(80|443)\s' || true
    die "Ports 80/443 are used by something other than nginx (Caddy/Traefik/another container?). Configure that proxy to forward $DOMAIN -> 127.0.0.1:$APP_PORT instead (see deploy/README-deploy.md)."
  fi
  log "Installing nginx"
  apt-get update -y && apt-get install -y nginx
fi
command -v certbot >/dev/null || { log "Installing certbot"; apt-get update -y && apt-get install -y certbot python3-certbot-nginx; }

# ---------------------------------------------------------------- 2. port check
if ss -ltn | grep -qE "[:.]${APP_PORT}\s" && ! docker ps --format '{{.Names}}' | grep -qx datapilot; then
  die "Port $APP_PORT is already in use on this VPS. Re-run with APP_PORT=<free port>, e.g. APP_PORT=8513."
fi

# ---------------------------------------------------------------- 3. app container (localhost only)
log "Building and starting DataPilot container on 127.0.0.1:$APP_PORT"
cat > .env <<EOF
DATAPILOT_BIND=127.0.0.1
DATAPILOT_PORT=$APP_PORT
EOF
docker compose up -d --build
for i in $(seq 1 30); do
  curl -fs "http://127.0.0.1:$APP_PORT/_stcore/health" >/dev/null && break
  sleep 2
  [[ $i -eq 30 ]] && { docker compose logs --tail 40; die "Container did not become healthy."; }
done
log "Container healthy"

# ---------------------------------------------------------------- 4. optional basic auth
AUTH_BLOCK=""
if [[ -n "${BASIC_AUTH_USER:-}" ]]; then
  command -v htpasswd >/dev/null || apt-get install -y apache2-utils
  if [[ -z "${BASIC_AUTH_PASS:-}" ]]; then read -rsp "Password for $BASIC_AUTH_USER: " BASIC_AUTH_PASS; echo; fi
  htpasswd -bc /etc/nginx/.datapilot_htpasswd "$BASIC_AUTH_USER" "$BASIC_AUTH_PASS" >/dev/null
  AUTH_BLOCK='auth_basic "DataPilot"; auth_basic_user_file /etc/nginx/.datapilot_htpasswd;'
  log "Basic auth enabled for user $BASIC_AUTH_USER"
fi

# ---------------------------------------------------------------- 5. nginx site (HTTP first; certbot adds HTTPS)
log "Writing nginx site for $DOMAIN"
cat > "$SITE" <<EOF
map \$http_upgrade \$datapilot_conn { default upgrade; '' close; }

server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;

    client_max_body_size 50M;           # dataset uploads

    location / {
        $AUTH_BLOCK
        proxy_pass http://127.0.0.1:$APP_PORT;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;       # Streamlit uses WebSockets
        proxy_set_header Connection \$datapilot_conn;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 86400;                       # long agent runs
        proxy_send_timeout 86400;
        proxy_buffering off;
    }
}
EOF
ln -sf "$SITE" /etc/nginx/sites-enabled/datapilot
nginx -t
systemctl reload nginx

# ---------------------------------------------------------------- 6. TLS certificate
log "Requesting Let's Encrypt certificate for $DOMAIN"
if [[ -n "${LE_EMAIL:-}" ]]; then EMAIL_ARGS=(--email "$LE_EMAIL"); else EMAIL_ARGS=(--register-unsafely-without-email); fi
certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --redirect "${EMAIL_ARGS[@]}"
nginx -t && systemctl reload nginx

# ---------------------------------------------------------------- 7. firewall (only if ufw is active)
if command -v ufw >/dev/null && ufw status | grep -q "Status: active"; then
  ufw allow 'Nginx Full' >/dev/null || true
fi

# ---------------------------------------------------------------- 8. verify
log "Verifying https://$DOMAIN"
code=$(curl -s -o /dev/null -w '%{http_code}' "https://$DOMAIN/_stcore/health" || true)
echo "HTTPS health check: HTTP $code (200 = OK, 401 = OK with basic auth)"
echo
echo "DataPilot is live at:  https://$DOMAIN"
echo "Update later with:     cd $APP_DIR && git pull && docker compose up -d --build"
