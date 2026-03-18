# Deployment Guide

Sentinel is deployed as a Docker Compose stack on a DigitalOcean droplet with Caddy as a reverse proxy handling automatic HTTPS via Let's Encrypt. This guide documents the exact steps used to deploy to sentineldemo.xyz.

---

## 1. Infrastructure

| Item | Detail |
|---|---|
| **Provider** | DigitalOcean |
| **Droplet** | Basic, 2GB RAM / 1 vCPU / 50GB SSD, Ubuntu 24.04 LTS, NYC3 region, Regular SSD (not Premium) |
| **Domain** | Purchased from Namecheap, DNS A records pointing `@` and `www` to the droplet IP |
| **HTTPS** | Caddy with automatic Let's Encrypt certificates |
| **Cost** | ~$12/month for the droplet + ~$1–15/year for domain |

---

## 2. Initial server setup

**Generate an SSH key locally (no passphrase):**

```bash
ssh-keygen -t ed25519 -C "sentinel-deploy" -f ~/.ssh/id_ed25519_sentinel -N ""
```

**If SSH key auth isn't working yet**, add the public key via the DigitalOcean browser console:

```bash
echo "YOUR_PUBLIC_KEY" >> ~/.ssh/authorized_keys
```

**SSH into the droplet:**

```bash
ssh -i ~/.ssh/id_ed25519_sentinel root@YOUR_DROPLET_IP
```

**Install Docker:**

```bash
curl -fsSL https://get.docker.com | sh
```

**Install Caddy:**

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install caddy
```

**Configure Caddy** (use the heredoc — no need for nano):

```bash
cat > /etc/caddy/Caddyfile << 'EOF'
sentineldemo.xyz, www.sentineldemo.xyz {
    reverse_proxy /api/* localhost:8000
    reverse_proxy /* localhost:3000
}
EOF

systemctl reload caddy
```

---

## 3. Application deployment

**Clone the repo:**

```bash
git clone https://github.com/OldEphraim/sentinel.git && cd sentinel
```

**Copy `.env` from your local machine** (run this locally, not on the droplet):

```bash
scp -i ~/.ssh/id_ed25519_sentinel .env root@YOUR_DROPLET_IP:~/sentinel/.env
```

Your `.env` must contain:
- `ANTHROPIC_API_KEY` — required even in mock mode
- `SECRET_KEY` — generate with `openssl rand -hex 32`
- `DEMO_KEY` — defaults to `SKYFI_DEMO` if omitted
- `SKYFI_API_KEY` — leave empty to use mock mode

**Start the stack:**

```bash
docker compose up --build -d
```

**Verify all services are running:**

```bash
docker compose ps          # all 5 services should show healthy/running
curl http://localhost:8000/health
```

---

## 4. Critical: NEXT_PUBLIC_API_URL

> **Warning:** `NEXT_PUBLIC_*` variables in Next.js are baked into the JavaScript bundle at **build time**, not injected at runtime. The `environment:` section in `docker-compose.yml` does **not** work for these variables — by the time Docker injects them, the Next.js build is already complete and the value is gone.

The correct approach is to pass the production URL as a Docker build `ARG` in `apps/web/Dockerfile`. This is already done in this repo:

```dockerfile
ARG NEXT_PUBLIC_API_URL=https://sentineldemo.xyz
```

The build arg is baked into the bundle during `docker compose up --build`. If you are deploying to a different domain, update this default value in `apps/web/Dockerfile` before building.

---

## 5. Updating the deployment

When code changes are pushed to GitHub:

```bash
ssh -i ~/.ssh/id_ed25519_sentinel root@YOUR_DROPLET_IP
cd ~/sentinel
git pull
docker compose down
docker builder prune -f
docker compose up --build -d
```

> **Note:** `docker builder prune -f` is required when changing `NEXT_PUBLIC_*` values or any frontend code. Without it, Docker's layer cache may serve a stale build and the domain change will not take effect.

---

## 6. DNS setup (Namecheap)

1. Go to namecheap.com → Account → Dashboard → Domain List → **Manage** → **Advanced DNS**
2. Delete any existing A records
3. Add A Record: Host `@`, Value: your droplet IP
4. Add A Record: Host `www`, Value: your droplet IP

DNS propagation takes 5–30 minutes. Test from your local machine:

```bash
dig sentineldemo.xyz +short
```

---

## 7. Monitoring and maintenance

```bash
# View all service logs (live)
docker compose logs -f

# View logs for a specific service
docker compose logs api -f

# Caddy logs (useful for SSL cert issues)
journalctl -u caddy -n 50

# Restart a single service without full rebuild
docker compose restart api

# Full restart without rebuild
docker compose down && docker compose up -d
```

**RabbitMQ management UI:** http://YOUR_DROPLET_IP:15672 (credentials: `guest` / `guest`)
Note: this is not proxied through Caddy — access it via the droplet IP directly, not the domain.

---

## 8. Destroying the deployment

```bash
# On the droplet:
docker compose down -v  # -v removes the postgres data volume

# Then in DigitalOcean dashboard: Droplets → your droplet → Destroy
```

> **Note:** Destroying the droplet stops all charges immediately. The domain continues to renew annually unless cancelled at Namecheap.
