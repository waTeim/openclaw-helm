# ---- OpenClaw Gateway + Playwright (full) addon image ----
ARG BASE_IMAGE=ghcr.io/openclaw/openclaw:latest
FROM ${BASE_IMAGE}

# The upstream image switches to USER node at the end.
# We need root to install OS deps and browser binaries cleanly.
USER root

# Where Playwright browser binaries will live (your preference)
ENV PLAYWRIGHT_BROWSERS_PATH=/usr/local/share/playwright

# Install Debian packages commonly required for Playwright browsers (Bookworm)
# Keep this list fairly complete to avoid runtime surprises.
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      ca-certificates curl \
      libnss3 libnspr4 \
      libatk1.0-0 libatk-bridge2.0-0 libatspi2.0-0 \
      libx11-6 libxcomposite1 libxdamage1 libxrandr2 libxfixes3 libxext6 libxi6 libxtst6 \
      libdrm2 libgbm1 libxshmfence1 \
      libasound2 \
      libpangocairo-1.0-0 libpango-1.0-0 libcairo2 \
      libcups2 \
      libglib2.0-0 libdbus-1-3 \
      libgtk-3-0 \
      fonts-liberation fonts-noto-color-emoji \
      xdg-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

# Install Playwright and download browser binaries.
WORKDIR /app
RUN npm install -g playwright && \
    mkdir -p /usr/local/share/playwright && \
    playwright install chromium firefox webkit && \
    chown -R node:node /usr/local/share/playwright

# Return to hardened runtime user
USER node

# Inherit the upstream CMD/ENTRYPOINT (gateway)
