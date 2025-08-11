FROM python:3.11-slim

# Variables d'environnement
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:1

# Installation des dépendances système pour Playwright + VNC
RUN apt-get update && apt-get install -y \
    # Dépendances Playwright existantes
    wget \
    gnupg \
    libnss3 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libxss1 \
    libasound2 \
    # Dépendances VNC et X11
    xvfb \
    x11vnc \
    fluxbox \
    supervisor \
    curl \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Création de l'utilisateur non-root
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Répertoire de travail
WORKDIR /app

# Copie et installation des dépendances Python
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Installation des navigateurs Playwright (en tant que root pour accès système)
RUN playwright install chromium \
    && playwright install-deps chromium

# Configurer les variables d'environnement Playwright pour utiliser les navigateurs système
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Configuration Supervisor pour gérer VNC et l'application
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Copie du code source
COPY ai_interface_actions/ ./ai_interface_actions/
COPY .env.example .env

# Script de démarrage
COPY start-railway.sh /app/start-railway.sh
RUN chmod +x /app/start-railway.sh

# Création des répertoires et permissions
RUN mkdir -p /app/logs /tmp/.X11-unix /home/appuser/.vnc \
    && chown -R appuser:appuser /app /home/appuser \
    && chmod 1777 /tmp/.X11-unix \
    && chmod -R 755 /ms-playwright 2>/dev/null || true

# Exposition des ports (API + VNC)
EXPOSE 8000 5900

# Variables d'environnement par défaut pour Railway
ENV HEADLESS=true
ENV HEADLESS_SETUP=false
ENV DEBUG=false
ENV LOG_LEVEL=INFO
ENV USE_PERSISTENT_CONTEXT=true

# Commande de démarrage
CMD ["/app/start-railway.sh"] 