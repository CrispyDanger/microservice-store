FROM python:3.14-slim
COPY --from=ghcr.io/astral-sh/uv:0.9.10 /uv /bin/uv

ARG SERVICE
# DEV=true also installs the dev dependency group (pytest, httpx...) for local development
ARG DEV=false
RUN test -n "$SERVICE" || (echo "Pass --build-arg SERVICE=<name>" && exit 1)

ENV SERVICE=${SERVICE} \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    if [ "$DEV" = "true" ]; then \
        uv sync --frozen --package ${SERVICE}; \
    else \
        uv sync --frozen --no-dev --package ${SERVICE}; \
    fi

ENV PATH="/app/.venv/bin:$PATH"
CMD ["sh", "-c", "exec \"$SERVICE\""]
