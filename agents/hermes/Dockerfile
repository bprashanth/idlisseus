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

USER hermes
