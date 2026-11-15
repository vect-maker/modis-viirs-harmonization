FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /workspace/apps/worker

ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV UV_LINK_MODE=copy
ENV PATH="/opt/venv/bin:$PATH"

CMD ["sh", "-c", "uv sync --no-install-project && exec uv run --no-sync python main.py"]
