FROM python:3.12-slim

# ── System deps for Playwright's Chromium ─────────────────────
# (playwright install-deps chromium handles the full list,
#  but we pre-install common ones for layer caching)
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Chromium shared libraries
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 libgbm1 \
    libpango-1.0-0 libcairo2 libasound2 libxshmfence1 \
    # Font rendering
    fonts-liberation fonts-noto-color-emoji \
    # Process management
    dumb-init \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Python deps ────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Playwright browser ─────────────────────────────────────────
RUN python -m playwright install chromium \
 && python -m playwright install-deps chromium

# ── App code ───────────────────────────────────────────────────
COPY . .

RUN mkdir -p /tmp/reports

EXPOSE 8000

ENTRYPOINT ["dumb-init", "--"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
