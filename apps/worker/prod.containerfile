FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

WORKDIR /workspace/apps/worker

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

COPY shared /workspace/shared
COPY apps/worker/pyproject.toml apps/worker/uv.lock ./
RUN uv sync --no-install-project

COPY apps/worker .

FROM docker.io/library/python:3.13-slim-bookworm AS runtime

WORKDIR /workspace/apps/worker

COPY --from=builder /workspace/shared /workspace/shared
COPY --from=builder /workspace/apps/worker/.venv /workspace/apps/worker/.venv
COPY --from=builder /workspace/apps/worker /workspace/apps/worker

ENV PATH="/workspace/apps/worker/.venv/bin:$PATH"

CMD ["python", "main.py"]
