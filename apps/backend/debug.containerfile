FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV UV_LINK_MODE=copy
ENV PATH="/opt/venv/bin:$PATH"

EXPOSE 8080

CMD ["sh", "-c", "uv sync --no-install-project && exec uv run --no-sync fastapi dev main.py --host 0.0.0.0 --port 8080"]
