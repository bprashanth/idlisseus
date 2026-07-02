FROM nousresearch/hermes-agent:latest

# Install as root, then restore the hermes user (uid 10000) so the s6-overlay
# init chain continues to work correctly.  Do NOT override ENTRYPOINT — Hermes
# depends on /init for process supervision.
USER root

# CLI tools the model commonly reaches for that aren't in the base image.
# Python packages belong in execute_code (uv auto-installs on first import),
# not here — keep this list to system-level tools only.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       jq \
       wget \
       sudo \
    && rm -rf /var/lib/apt/lists/*

# Allow the hermes user to run sudo without a password.
# This lets the model apt-get install additional system tools at runtime if it
# discovers it needs them.  The container is already an isolation boundary;
# see docs/agents.md for the security posture around when to run this image.
RUN echo 'hermes ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/hermes \
    && chmod 0440 /etc/sudoers.d/hermes

# Connector packages whose import name != pip name, so the agent's execute_code
# `import ee` (earthengine-api) and `import fitz` (pymupdf) work without a runtime
# install. The base image's auto-install-on-import can't map ee->earthengine-api
# or fitz->pymupdf, which is why runtime `import ee` fails. Installed into the
# agent's venv (first on PATH).
RUN uv pip install --python /opt/hermes/.venv/bin/python earthengine-api pymupdf

# The base image defaults HOME=/root, but the agent runs as uid 10000 whose home
# is the /opt/data mount. execute_code sandboxes inherit HOME, so with HOME=/root
# `ee.Initialize()` looks for creds at /root/.config/earthengine (unreadable by
# uid 10000) and fails auth. Pin HOME to /opt/data so ~/.config/earthengine
# resolves to the mounted, staged credentials.
ENV HOME=/opt/data

USER hermes
