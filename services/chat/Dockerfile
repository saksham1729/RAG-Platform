# ---- Build stage ----
# This image has gcc, headers, and pip's full toolchain — needed to compile
# any packages with C extensions. None of this ships to production.
FROM python:3.12-slim AS builder

WORKDIR /build

# Build tools only exist in this stage.
RUN apt-get update && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

# Create an isolated virtualenv so we can cleanly copy JUST the installed
# packages (not system Python, not build tools) into the runtime stage.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
# Layer caching: this only re-runs when requirements.txt changes, same
# principle as `go mod download` in the gateway's Dockerfile.
RUN pip install --no-cache-dir -r requirements.txt

# ---- Runtime stage ----
# Slim, not scratch: unlike Go's static binary, Python NEEDS an interpreter
# at runtime. "slim" gives us Python + minimal OS libs, with no compiler,
# no headers, no package manager cache — smallest image that can actually run.
FROM python:3.12-slim

# Run as a non-root user. If this container is ever compromised, the
# attacker doesn't get root inside it. This one line is a real production
# security practice, not just best-practice theater.
RUN useradd --create-home appuser
USER appuser
WORKDIR /app

# Copy ONLY the virtualenv built in the previous stage — no compiler,
# no build cache, no apt lists ever touch this final image.
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY --chown=appuser:appuser main.py .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
