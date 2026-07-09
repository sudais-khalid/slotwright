# ---- Build stage ----
FROM python:3.12-slim AS build
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ---- Runtime stage ----
FROM python:3.12-slim AS runtime
WORKDIR /app
RUN useradd -m appuser
# packages were installed as root into /root/.local (unreadable by appuser) —
# copy them into appuser's own home so the non-root runtime user can execute them
COPY --from=build --chown=appuser:appuser /root/.local /home/appuser/.local
COPY --chown=appuser:appuser . .
ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1

RUN mkdir -p /app/data /app/models && chown -R appuser /app
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
