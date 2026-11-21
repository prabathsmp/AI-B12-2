#!/usr/bin/env bash
# Deploy SlotEase on an Ubuntu VPS that already runs nginx.
# Run from the project root (the folder with docker-compose.prod.yml):
#   bash deploy/deploy.sh <domain> [email-for-letsencrypt]
# The email is optional when certbot already has an account on this server.
# Example:
#   bash deploy/deploy.sh slotease.smpdigihub.online you@example.com
# Safe to re-run: it rebuilds containers and keeps the database volume.
set -euo pipefail

DOMAIN="${1:?Usage: bash deploy/deploy.sh <domain> <email>}"
EMAIL="${2:-}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

say() { printf '\n\033[1;35m==> %s\033[0m\n' "$*"; }
need_root() { [ "$(id -u)" -eq 0 ] || { echo "Run as root (or with sudo)."; exit 1; }; }
need_root

# ---------- 1. Docker ----------
say "Checking Docker"
if ! command -v docker >/dev/null 2>&1; then
  echo "Docker not found - installing from get.docker.com"
  curl -fsSL https://get.docker.com | sh
fi
docker compose version >/dev/null 2>&1 || { echo "docker compose plugin missing: apt-get install -y docker-compose-plugin"; exit 1; }
systemctl enable --now docker >/dev/null 2>&1 || true

# ---------- 2. .env ----------
set_kv() {  # set_kv KEY VALUE  (add or replace in .env)
  if grep -q "^$1=" .env; then sed -i "s|^$1=.*|$1=$2|" .env; else echo "$1=$2" >> .env; fi
}
if [ ! -f .env ]; then
  say "Creating .env with fresh random secrets"
  cp .env.example .env
  set_kv POSTGRES_PASSWORD "$(openssl rand -hex 24)"
  set_kv JWT_SECRET "$(openssl rand -hex 48)"
else
  say "Keeping existing .env (secrets unchanged)"
  if grep -qE '^(JWT_SECRET=change-me|POSTGRES_PASSWORD=change-me)' .env; then
    echo "ERROR: .env still has placeholder secrets. Edit them or delete .env and re-run."; exit 1
  fi
fi

PORT="$(grep -E '^FRONTEND_PORT=' .env | cut -d= -f2 || true)"
if [ -z "$PORT" ] || [ "$PORT" = "8080" ]; then PORT=8085; fi
# pick a free local port if the chosen one is taken by something else
while ss -ltn "( sport = :$PORT )" | grep -q LISTEN && ! docker ps --format '{{.Names}} {{.Ports}}' | grep -q "slotease-frontend.*:$PORT->"; do
  PORT=$((PORT + 1))
done
set_kv FRONTEND_PORT "$PORT"
set_kv PUBLIC_BASE_URL "https://$DOMAIN"
set_kv CORS_ORIGINS "https://$DOMAIN"
chmod 600 .env
echo "Frontend will listen on 127.0.0.1:$PORT"

# ---------- 3. Containers ----------
say "Building and starting containers (first build takes a few minutes)"
docker compose -f docker-compose.prod.yml up -d --build

say "Waiting for the app to become healthy"
for i in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:$PORT/api/health" >/dev/null 2>&1; then echo "App is up."; break; fi
  sleep 3
  [ "$i" -eq 60 ] && { echo "App did not become healthy. Check: docker compose -f docker-compose.prod.yml logs backend"; exit 1; }
done

# ---------- 4. nginx site ----------
say "Configuring nginx for $DOMAIN"
command -v nginx >/dev/null || apt-get install -y nginx
if [ -d /etc/nginx/sites-available ]; then
  SITE=/etc/nginx/sites-available/$DOMAIN
  LINK=/etc/nginx/sites-enabled/$DOMAIN
else
  SITE=/etc/nginx/conf.d/$DOMAIN.conf
  LINK=""
fi
if [ -f "$SITE" ] && grep -q "ssl_certificate" "$SITE"; then
  # already has HTTPS from a previous run: only update the upstream port
  sed -i -E "s|proxy_pass http://127.0.0.1:[0-9]+;|proxy_pass http://127.0.0.1:$PORT;|" "$SITE"
else
  sed -e "s|__DOMAIN__|$DOMAIN|g" -e "s|__PORT__|$PORT|g" deploy/nginx-site.conf.template > "$SITE"
fi
[ -n "$LINK" ] && ln -sf "$SITE" "$LINK"
nginx -t
systemctl reload nginx

# ---------- 5. Firewall ----------
if command -v ufw >/dev/null && ufw status | grep -q "Status: active"; then
  say "Opening HTTP/HTTPS in ufw"
  ufw allow 'Nginx Full' >/dev/null || { ufw allow 80/tcp; ufw allow 443/tcp; }
fi

# ---------- 6. HTTPS ----------
say "Getting a Let's Encrypt certificate"
if ! command -v certbot >/dev/null; then
  apt-get update -y && apt-get install -y certbot python3-certbot-nginx
fi
if [ -n "$EMAIL" ]; then
  certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "$EMAIL" --redirect --keep-until-expiring
elif ls /etc/letsencrypt/accounts/*/directory/* >/dev/null 2>&1; then
  certbot --nginx -d "$DOMAIN" --non-interactive --redirect --keep-until-expiring   # reuse existing account
else
  echo "No certbot account yet - re-run with an email: bash deploy/deploy.sh $DOMAIN you@example.com"; exit 1
fi

say "Checking https://$DOMAIN"
curl -fsS "https://$DOMAIN/api/health" && echo
echo
echo "Done. Open https://$DOMAIN  (demo booking page: https://$DOMAIN/glow-salon)"
echo "Logs:    docker compose -f docker-compose.prod.yml logs -f backend"
echo "Update:  git pull && bash deploy/deploy.sh $DOMAIN"
