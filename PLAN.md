# LocalAI DGX Spark POC Implementation Plan

## Goal

Set up a clean DGX Spark as a local multi-user chatbot platform.

The POC has four phases:

1. Install and test `ds4` running DeepSeek V4 Flash through API.
2. Install and test Odysseus or chosen chat frontend independently.
3. Connect Odysseus to the shared `ds4` OpenAI-compatible endpoint.
4. Add a simple local login router that maps 10 predefined users to 10 separate frontend containers.

## Target Architecture

```text
User browser
  ↓
Login router / reverse proxy
  ↓
User-specific Odysseus container
  ↓
Shared ds4 OpenAI-compatible API
  ↓
DeepSeek V4 Flash on DGX Spark
```

Each user gets their own frontend container and local data volume.

All users share one `ds4` inference backend.

Everything should run on just this one machine and tested via localhost. 

Odysseus referes to: https://github.com/pewdiepie-archdaemon/odysseus
DS4 refers to: https://github.com/antirez/ds4

## Assumptions

* Fresh DGX Spark machine.
* Ubuntu or NVIDIA DGX OS.
* Admin/sudo access available.
* Tailscale or LAN access available.
* No production-grade auth needed yet.
* User list can be stored in local JSON.
* 10 initial users only.
* No MCP/data retrieval yet.
* No file upload isolation beyond per-container frontend volumes unless frontend supports it.

---

# Phase 0: Base System Setup

## Install required packages

```bash
sudo apt update
sudo apt install -y \
  git curl wget build-essential cmake pkg-config \
  python3 python3-venv python3-pip \
  nodejs npm \
  nginx \
  jq htop nvtop unzip
```

## Install Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

Log out and back in, then verify:

```bash
docker --version
docker compose version
```
Don't use root more than you need to. 


## Install NVIDIA container runtime

Follow NVIDIA Container Toolkit install instructions for the installed OS.

Then verify:

```bash
nvidia-smi
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

Success condition:

```text
Docker can access the GPU.
```

---

# Phase 1: Setup and Test ds4

## Clone ds4

```bash
mkdir -p /home/beeps/src/github.com/bprashanth/idlisseus
cd /home/beeps/src/github.com/bprashanth/idlisseus
git clone https://github.com/antirez/ds4.git
cd ds4
```

## Build ds4

Follow the repository README exactly.

Expected target binaries may include:

```text
ds4
ds4-server
```

## Download model weights

Download the `q2-imatrix` quant (~81GB on disk) via `./download_model.sh q2-imatrix`. This is the
quant ds4's own docs recommend for 96-128GB unified-memory machines, which matches this DGX Spark's
~121GiB available RAM.

Create:

```bash
mkdir -p /home/beeps/src/github.com/bprashanth/idlisseus/models/deepseek-v4-flash
mkdir -p /home/beeps/src/github.com/bprashanth/idlisseus/ds4-kv
```

Store model files under:

```text
/home/beeps/src/github.com/bprashanth/idlisseus/models/deepseek-v4-flash
```

## Start ds4 server

Start with conservative context first.

```bash
cd /home/beeps/src/github.com/bprashanth/idlisseus/ds4

./ds4-server \
  --ctx 100000 \
  --kv-disk-dir /home/beeps/src/github.com/bprashanth/idlisseus/ds4-kv \
  --kv-disk-space-mb 8192
```

Confirm which port it binds to. Default appears to commonly be:

```text
127.0.0.1:8000
```

## API test

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "deepseek-v4-flash",
    "messages": [
      {"role": "user", "content": "Say hello and explain what model you are."}
    ],
    "stream": false
  }'
```

Success condition:

```text
Valid JSON response from ds4.
```

## Streaming test

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "deepseek-v4-flash",
    "messages": [
      {"role": "user", "content": "Write a short explanation of ecological restoration."}
    ],
    "stream": true
  }'
```

Success condition:

```text
Streaming tokens are returned.
```

## Create systemd service for ds4

Create:

```bash
sudo nano /etc/systemd/system/ds4.service
```

Example:

```ini
[Unit]
Description=ds4 DeepSeek V4 Flash Server
After=network.target

[Service]
Type=simple
User=prashanth
WorkingDirectory=/home/prashanth/localai/ds4
ExecStart=/home/prashanth/localai/ds4/ds4-server --ctx 100000 --kv-disk-dir /home/prashanth/localai/ds4-kv --kv-disk-space-mb 8192
Restart=always
RestartSec=5
Environment=HOME=/home/prashanth

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable ds4
sudo systemctl start ds4
sudo systemctl status ds4
```

---

# Phase 2: Setup Odysseus / Chat Frontend

## Requirement

The frontend must support:

```text
OpenAI-compatible base URL
custom model name
local user data persistence
containerized deployment
```

Use Odysseus if it supports this cleanly.

If Odysseus cannot easily point to a custom OpenAI-compatible endpoint, fallback options are:

```text
Open WebUI
LibreChat
custom minimal Next.js chat UI
```

## Test one frontend container first

Create directory:

```bash
mkdir -p /home/beeps/src/github.com/bprashanth/idlisseus/frontends/user01
```

Run one frontend instance mapped to a test port, for example:

```text
user01 frontend → host port 3101
```

Configure it with:

```text
OPENAI_API_BASE=http://host.docker.internal:8000/v1
OPENAI_API_KEY=local-dummy-key
MODEL=deepseek-v4-flash
```

On Linux, Docker may need:

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

Success condition:

```text
Frontend loads in browser.
Frontend can send a prompt.
Response comes from ds4.
```

---

# Phase 3: Connect Odysseus to ds4

## Direct connection test

From inside the frontend container:

```bash
curl http://host.docker.internal:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "deepseek-v4-flash",
    "messages": [{"role": "user", "content": "Ping"}],
    "stream": false
  }'
```

If this fails, fix Docker networking before touching frontend config.

## Optional compatibility proxy

If Odysseus expects slightly different OpenAI behavior, insert LiteLLM:

```text
Odysseus → LiteLLM → ds4
```

Run LiteLLM only if needed.

Success condition:

```text
Odysseus can chat with DeepSeek V4 Flash through ds4.
```

---

# Phase 4-6: Multi-user via Odysseus's built-in accounts (revised)

Odysseus already ships multi-user auth: an admin account created on first boot, open/closed
signup, per-user accounts, and per-user privilege gating (non-admin users don't get
shell/file/MCP-management access by default). Running 10 separate containers plus a
hand-rolled login router and Nginx reverse proxy in front of them would duplicate this for no
benefit, and would mean 10x the idle resource footprint for one shared backend. Revised plan:

* Run **one** Odysseus container/instance, pointed at the shared ds4 endpoint.
* Create 10 named non-admin user accounts inside Odysseus (one per real user) using its
  normal signup/admin-invite flow.
* Each account gets isolated chat history/data natively via Odysseus's own per-user storage —
  no separate container or volume needed per user.
* Bind Odysseus to `127.0.0.1` (Docker Compose default) and rely on Tailscale for access,
  per Odysseus's own security notes. No custom login router or Nginx needed for the POC.

## Create docker-compose override

```bash
cd /home/beeps/src/github.com/bprashanth/idlisseus/odysseus
cp .env.example .env
```

Set in `.env` (exact var names per `docs/setup.md` — confirm against that file):

```text
OPENAI_API_BASE=http://host.docker.internal:8000/v1
OPENAI_API_KEY=local-dummy-key
MODEL=deepseek-v4-flash
```

On Linux, Docker may need:

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

Start:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu-nvidia.yml up -d --build
docker compose logs odysseus   # grab the generated admin password
```

Success condition:

```text
Odysseus loads in browser at http://localhost:7000.
Admin can log in, configure the ds4 endpoint in Settings, and chat.
```

## Add the 10 users

* Log in as admin.
* Create 10 non-admin accounts (e.g. user01..user10) via Settings → Users, or enable signup
  temporarily and have each person register, then disable signup again.
* Confirm each account is non-admin (per Odysseus's own security guidance).

Success condition:

```text
user01 logs in and sees only user01's chat history.
user02 logs in and sees only user02's chat history.
```

---

# Phase 7: Smoke Tests

Run these tests:

## ds4 health

```bash
curl http://127.0.0.1:8000/v1/chat/completions ...
```

## frontend health

```bash
curl http://127.0.0.1:7000
```

## user isolation

* Log into user01.
* Send chat.
* Log into user02.
* Confirm user02 cannot see user01 chat history.

## concurrency

Open 3–5 users and send simultaneous prompts.

Record:

```text
time to first token
tokens/sec
errors
GPU/memory usage
ds4 logs
container logs
```

## boot-persistence check (no actual reboot)

A live reboot is disruptive to an in-progress unattended run, so verify boot persistence
without rebooting:

```bash
systemctl is-enabled ds4
docker inspect -f '{{.HostConfig.RestartPolicy.Name}}' odysseus   # expect "unless-stopped" or "always"
```

If both report enabled/always-restart, the stack will come back after a reboot. An actual
`sudo reboot` test is left for the user to run by hand when convenient.

---

# Phase 8: Deliverables

The coding agent should leave behind:

```text
/home/beeps/src/github.com/bprashanth/idlisseus/README.md
/home/beeps/src/github.com/bprashanth/idlisseus/ds4/ (build + setup notes)
/home/beeps/src/github.com/bprashanth/idlisseus/odysseus/.env (gitignored, not committed)
systemd service for ds4
docker-compose-based restart policy for Odysseus
smoke-test script
```

## README must include

* How to start/stop ds4.
* How to start/stop the Odysseus container.
* How to add a new user (via Odysseus admin Settings).
* How to change the ds4 endpoint.
* How to view logs.
* Known issues.
* Benchmark results.

---

# Hard Stop Criteria

Stop and report if:

1. ds4 cannot run on the DGX Spark.
2. ds4 API does not expose OpenAI-compatible chat completions.
3. Odysseus cannot use a custom OpenAI-compatible endpoint.
4. Odysseus's built-in accounts cannot isolate chat history per user.
5. Concurrent use makes ds4 unusably slow.

If Odysseus fails, switch to Open WebUI or LibreChat rather than spending too much time debugging Odysseus internals.

---

# Preferred Final State

```text
One DGX Spark
One ds4 DeepSeek V4 Flash backend
One Odysseus instance with ten isolated user accounts
Tailscale-only access
No public internet exposure
```

