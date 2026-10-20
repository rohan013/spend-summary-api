FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-cache
ENV PATH="/app/.venv/bin:$PATH"

COPY app.py budget.py plaid_client.py token_store.py models.py ./

ENV PORT=8000
EXPOSE 8000

CMD gunicorn -w 2 -b 0.0.0.0:${PORT} app:app
