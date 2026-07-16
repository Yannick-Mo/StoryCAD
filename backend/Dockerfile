FROM python:3.11.11-slim AS base

WORKDIR /app

RUN addgroup --system --gid 1001 appuser && adduser --system --uid 1001 appuser

# Install runtime deps only
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY ./app ./app
COPY ./alembic ./alembic
COPY ./alembic.ini .

EXPOSE 8000

USER appuser

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port 8000 ${DEV_MODE:+--reload}"]
