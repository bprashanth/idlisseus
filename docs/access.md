# Team Access — Idlisseus on idli.cc

## How users reach the system

```
Browser (anywhere, no VPN, no install)
  → https://chat.idli.cc  (HTTPS, TLS by Cloudflare)
    → Cloudflare Access  (email one-time-code gate)
      → Cloudflare Tunnel / cloudflared (running on Spark, QUIC protocol)
        → localhost:7000  (Idlisseus / Odysseus container)
          → 172.17.0.1:8001  (Qwen3-Next-80B FP8, vLLM)
```

The Spark never exposes a port to the internet. Cloudflare Tunnel makes
the outbound connection; all inbound traffic goes through Cloudflare's edge.

## Inviting a team member

**Step 1 — Add them to Cloudflare Access** (you do this, takes 30 seconds):
1. Go to [dash.cloudflare.com](https://dash.cloudflare.com) → **Zero Trust** → **Access** → **Applications**
2. Click the **idlisseus** application → **Edit** → **Policies**
3. Add a rule: **Emails** → enter their email address → Save

**Step 2 — Send them this message:**
> You've been invited to Idlisseus, our team AI assistant.
> Open https://chat.idli.cc in your browser.
> Enter your email when prompted — you'll receive a one-time code.
> After that you'll reach the Idlisseus login screen — click "Sign Up" to create your account.

That's it. No VPN, no software to install, no password to set in advance.

## Two-layer auth

Users go through two login steps:

| Layer | Who runs it | What it does |
|-------|------------|--------------|
| Cloudflare Access | Cloudflare (your dashboard) | Network gate — only approved emails can reach the site at all |
| Idlisseus login | Odysseus app | App session — per-user chat history, settings, memories |

The Cloudflare layer is the security boundary. The Idlisseus login is for per-user
state (different chat histories, different settings per person).

## Infrastructure on the Spark

| Component | How it runs | Config |
|-----------|------------|--------|
| `cloudflared` | systemd service (`cloudflared.service`), starts at boot | `/etc/systemd/system/cloudflared.service` |
| Idlisseus UI | Docker Compose (`chatbots/odysseus/docker-compose.yml`), port 7000 | `chatbots/odysseus/.env` |
| Qwen3-Next-80B | Docker container `qwen80b-vllm`, port 8001 | `deploy/qwen80b/run.sh` (or `docker start qwen80b-vllm`) |

## Starting / stopping

```bash
# Start everything (normal boot — cloudflared starts automatically)
docker start qwen80b-vllm                                          # 80B model (~9 min cold load)
cd chatbots/odysseus && docker compose up -d                       # UI

# Stop everything
cd chatbots/odysseus && docker compose down
docker stop qwen80b-vllm

# Restart just the UI (after config change)
cd chatbots/odysseus && docker compose build odysseus && docker compose up -d --force-recreate odysseus

# Check tunnel status
sudo systemctl status cloudflared
```

## Changing CORS / allowed origins

If you add another public URL for the UI, add it to `ALLOWED_ORIGINS` in `chatbots/odysseus/.env`:

```
ALLOWED_ORIGINS=http://localhost,http://127.0.0.1,https://chat.idli.cc
```

Then rebuild and recreate the container:
```bash
cd chatbots/odysseus && docker compose build odysseus && docker compose up -d --force-recreate odysseus
```

## Security notes

- The Spark's vLLM port (8001) is bound to `172.17.0.1` (Docker bridge only) — not reachable from the internet
- `SECURE_COOKIES=true` — session cookies require HTTPS
- Do not add real passwords or API keys to `.env` and commit it
- If a team member leaves: remove their email from the Cloudflare Access policy (they're locked out immediately, no token to revoke)
