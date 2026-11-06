# Daleel: one container with the API, the pipeline worker and the web app.
# Built for free hosting (Hugging Face Spaces, Docker SDK, port 7860), and runs anywhere Docker runs.

# ---- 1. Build the web app
FROM node:22-slim AS web
WORKDIR /web
RUN corepack enable
COPY web/package.json web/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY web/ ./
RUN pnpm build

# ---- 2. Python runtime
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /usr/local/bin/uv
# Run as a non root user (Hugging Face Spaces requires uid 1000).
RUN useradd -m -u 1000 daleel
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock backend/
RUN cd backend && uv sync --frozen --no-dev --no-install-project
COPY backend/ backend/
RUN cd backend && uv sync --frozen --no-dev
COPY rulebook/ rulebook/
COPY mappings/ mappings/
COPY docs/sources/ docs/sources/
COPY --from=web /web/dist web/dist
RUN mkdir -p backend/var && chown -R daleel:daleel /app
USER daleel
ENV PATH="/app/backend/.venv/bin:$PATH" ENVIRONMENT=production PORT=7860
EXPOSE 7860
CMD ["daleel", "serve"]
