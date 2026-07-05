# Dryad — the authenticated ("login") connector

Dryad has a rich pool of Western-Ghats / India ecology datasets, but unlike Zenodo its
file **downloads require an OAuth bearer token** (search + metadata are open — that's why
the crawl can *list* Dryad datasets but got `401` on the bytes). This is our first
connector that needs a login, and the pattern generalises to any authenticated source.

## Get credentials (one-time, ~5 min)

1. Go to **https://datadryad.org** → **Login** (top-right). Auth is via **ORCID** — sign
   in with your ORCID iD, or make one at https://orcid.org first.
2. **Log in at least once** so Dryad creates your user record.
3. Go to **https://datadryad.org/account** → generate **API credentials**. You get an
   **application/client id** and a **client secret**.

Any free account can mint a *download* token — Dryad "membership" is only needed to
*submit* data, which we don't do.

## Install the creds (never committed — lives outside the repo)

```bash
cp ~/.config/idlisseus/dryad.json.example ~/.config/idlisseus/dryad.json
# edit it, paste your client_id + client_secret
chmod 600 ~/.config/idlisseus/dryad.json
```

Read order (first hit wins): `DRYAD_CLIENT_ID`/`DRYAD_CLIENT_SECRET` env →
`~/.hermes/secrets/dryad.json` (uid-10000, for the Hermes sandbox) →
`~/.config/idlisseus/dryad.json` (host, for the crawl). The 10-hour bearer token is
exchanged via `client_credentials` and cached best-effort.

## Validate

```bash
python3 research/dryad_check.py
```

Expected: `✓ creds found` → `✓ got bearer token` → `✓ downloaded N bytes WITH token`.

## Fold Dryad into the corpus

Once validated, the crawl auto-enables its **hop 3 (Dryad)** — otherwise it prints
`hop 3: Dryad SKIPPED (no creds)`:

```bash
python3 research/paper_crawl.py --max-datasets 250 --theme-per-query 15
```

Then rebuild cards + re-run the retrieval benchmark on the widened corpus:

```bash
python3 ../discovery/build_cards.py
python3 ../discovery/retrieval_bench.py
```

## Runtime use by Hermes

`paper_data.dryad_find(query)` and the auth layer are in the connector itself, so Hermes
can search Dryad **at runtime** with a fair query (mirrors what a plain cursor CLI could
*not* do without the token). To enable that path, place the same creds at
`~/.hermes/secrets/dryad.json` owned by uid 10000 (same as the EE creds) so the sandbox
can read them.
