#!/usr/bin/env bash
# install_playwright.sh
# Run once after pip install to download Chromium + its system deps.
# Safe to re-run — Playwright skips if already installed.

set -euo pipefail

echo "→ Installing Playwright browser binaries..."
python -m playwright install chromium

echo "→ Installing Chromium system dependencies..."
python -m playwright install-deps chromium

echo "✓ Playwright ready."
