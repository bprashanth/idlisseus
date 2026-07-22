# Odysseus (chat UI)

Day-to-day operation of the Odysseus instance. For starting/stopping the container stack, see
`setup.md`. For which model it's currently pointed at, see `models.md`.

For the provider-neutral Codex ecology bridge, live skill activity, Why/audit panel and explicit
T4GC model-request flow, see `idli-insight.md`.

## Login

- **URL:** `http://localhost:7000` (or via the SSH tunnel described in `setup.md`).
- **Admin username:** `admin`.
- **Admin password:** auto-generated on first boot, printed once to
  `docker compose logs odysseus`. Current known value is in `odysseus/.env`'s
  `ODYSSEUS_ADMIN_PASSWORD` if it was ever pre-seeded there — if not, you must recover it from
  the original `docker compose logs odysseus` output or reset it directly in the database.
- **To change it:** log in, Settings -> change password. Or pre-seed a new one via
  `ODYSSEUS_ADMIN_PASSWORD` in `odysseus/.env` before a future container rebuild.

## Adding a user

```bash
curl -s -b <admin_session_cookie> -X POST http://127.0.0.1:7000/api/auth/users \
  -H 'Content-Type: application/json' \
  -d '{"username":"user11","password":"<choose-a-password>","is_admin":false}'
```

Or Settings -> Users in the UI. New accounts get isolated chat history automatically — no new
container or volume needed (this is the whole reason the original 10-container + login-router
design from `PLAN.md` was dropped in favor of Odysseus's native multi-user accounts).

## Registering / changing a model endpoint

Model endpoints live in Odysseus's own database, not a config file. Either:

- **UI:** Settings -> Models -> add/edit endpoint.
- **API** (what was used to set this up originally):
  ```bash
  curl -s -b <admin_session_cookie> -X POST http://127.0.0.1:7000/api/model-endpoints \
    -F "name=ds4" \
    -F "base_url=http://host.docker.internal:8000/v1" \
    -F "api_key=local-dummy-key" \
    -F "model_type=llm" \
    -F "shared=true"
  ```
  Note: from *inside* the Odysseus container, the model server is reached via
  `host.docker.internal` (Docker's hostname for the host machine), not `172.17.0.1` directly —
  Docker resolves that to the host gateway, which happens to be the same `172.17.0.1` address
  the model servers bind to.
- Check current registrations: `curl -s -b <cookie> http://127.0.0.1:7000/api/model-endpoints`.

**Only `ds4` is registered right now.** Nemotron-3 and Seed-OSS were tested directly via API/
Hermes and never wired into Odysseus — if you want either available in the Odysseus UI, register
it the same way, pointed at whichever model is actually running (see `models.md` — remember only
one can be up at a time).

## The Pro/Flash alias gotcha

Odysseus's model picker shows both `deepseek-v4-flash` and `deepseek-v4-pro` as selectable
models once `ds4` is registered. **These are not two different models** — see `models.md` for
the full explanation. Don't read "both options work" as evidence that DeepSeek V4 Pro is
actually running; it isn't, ds4 only ever has the one Flash GGUF loaded.

## No automatic model routing

Checked directly in Odysseus's source: model selection is **per-session and manual** (you pick
a model-endpoint when creating a chat). There is a "Compare" feature for running the same prompt
against multiple registered models side-by-side, but nothing that inspects a query and
auto-routes it to a model by task type. If you want "long task -> model A, quick query -> model
B," that's a manual choice per chat today, not something Odysseus does for you.

## Viewing logs

```bash
cd odysseus
docker compose logs -f odysseus     # the app itself
docker compose logs -f              # everything (chromadb, searxng, ntfy too)
```

## Known issue: build memory spike

Building/rebuilding the Odysseus Docker image while a model is loaded is risky on this
unified-memory box — `apt-get` inside the Dockerfile has been observed growing to ~123GB of
anonymous memory and getting OOM-killed (see `setup.md`). Stop whatever model is running first.
