FROM python:3.11-slim

WORKDIR /app

# Install docker CLI (static binary) + curl for healthcheck
# Debian's docker.io is not reliable on trixie; fetch static docker binary instead
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
  && rm -rf /var/lib/apt/lists/* \
  && curl -fsSL https://download.docker.com/linux/static/stable/x86_64/docker-24.0.7.tgz | tar -xz -C /tmp \
  && mv /tmp/docker/docker /usr/local/bin/docker \
  && chmod +x /usr/local/bin/docker \
  && docker --version

# Pre-pull sandbox image so first request is fast (best-effort, not fatal if offline at build)
# (done at runtime via the host's docker, not at build time, so skip here)

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# Run as root inside the runner for docker.sock access.
# The *spawned* sandbox containers are still non-root (--user 65534) — this is the security boundary.
# If we ever need non-root runner, add: groupadd -g 969 docker && usermod -aG docker runner
USER root
RUN useradd -m -u 1000 runner 2>/dev/null || true && chown -R runner:runner /app
# Keep running as root so docker sock (root:969) is accessible; spawned containers remain non-root

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --retries=5 CMD curl -sf http://localhost:8000/health || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
