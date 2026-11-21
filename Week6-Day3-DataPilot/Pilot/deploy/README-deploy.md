# Deploying DataPilot on a VPS with HTTPS

Target: `https://datapilot.smpdigihub.online` → Nginx (TLS by Let's Encrypt) → `127.0.0.1:8503` → DataPilot container.

## Prerequisites
- DNS `A` record `datapilot.smpdigihub.online` → VPS IP (already set).
- Ports 80 and 443 open in the Hostinger firewall.

## Deploy (on the VPS)
```bash
cd /root/AI-B12-2/Week6-Day3-DataPilot/Pilot
git pull
sudo bash deploy/deploy_vps.sh
```
Recommended, since the app has no login of its own:
```bash
BASIC_AUTH_USER=admin sudo -E bash deploy/deploy_vps.sh     # prompts for a password
```
Other options: `APP_PORT=8513` if 8503 is taken · `LE_EMAIL=you@example.com` for expiry notices.

The script:
1. installs Docker / nginx / certbot if missing,
2. starts the container bound to **127.0.0.1 only** (not reachable from the internet directly),
3. writes an nginx site with WebSocket support (Streamlit needs it), 50 MB uploads and long timeouts,
4. obtains the certificate and adds the HTTP→HTTPS redirect (auto-renewed by certbot's timer),
5. checks `https://datapilot.smpdigihub.online/_stcore/health`.

It only adds its own nginx site (`/etc/nginx/sites-available/datapilot`); existing sites such as the main
domain are untouched. If ports 80/443 belong to another proxy (Caddy, Traefik, an nginx container), the script
stops and you point that proxy at `127.0.0.1:8503` instead.

## Update / operate
```bash
git pull && docker compose up -d --build     # update
docker compose logs -f                       # logs
docker compose restart                       # restart
```
