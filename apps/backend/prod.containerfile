FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

WORKDIR /workspace/apps/backend

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

COPY shared /workspace/shared
COPY apps/backend/pyproject.toml apps/backend/uv.lock ./
RUN uv sync --no-install-project

COPY apps/backend .

FROM docker.io/library/python:3.13-slim-bookworm AS runtime

WORKDIR /workspace/apps/backend

COPY --from=builder /workspace/shared /workspace/shared
COPY --from=builder /workspace/apps/backend/.venv /workspace/apps/backend/.venv
COPY --from=builder /workspace/apps/backend /workspace/apps/backend

ENV PATH="/workspace/apps/backend/.venv/bin:$PATH"

EXPOSE 8080

CMD ["fastapi", "run", "main.py", "--host", "0.0.0.0", "--port", "8080"]
