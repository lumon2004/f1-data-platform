# Ambiente dei test di accettazione: Python 3.12 + Chromium per Playwright.
FROM mcr.microsoft.com/playwright/python:v1.48.0-noble
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --break-system-packages -r /tmp/requirements.txt
WORKDIR /repo
