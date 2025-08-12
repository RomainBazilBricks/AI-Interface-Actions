FROM python:3.11-slim

# Variables d'environnement
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Installation des dépendances système nécessaires pour Playwright
RUN apt-get update && apt-get install -y \
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
    libgtk-3-0 \
    libxss1 \
    libgconf-2-4 \
    && rm -rf /var/lib/apt/lists/*

# Création de l'utilisateur non-root avec son répertoire home
RUN groupadd -r appuser && useradd -r -g appuser -d /home/appuser -m appuser

# Répertoire de travail
WORKDIR /app

# Copie et installation des dépendances Python
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Installation des navigateurs Playwright en tant que root avec répertoire correct
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN playwright install chromium \
    && playwright install-deps chromium \
    && chmod -R 755 /ms-playwright

# Copie du code source et scripts
COPY ai_interface_actions/ ./ai_interface_actions/
COPY start-railway.sh ./
COPY .env.example .env

# Création des répertoires nécessaires et changement de propriétaire
RUN mkdir -p /app/logs /home/appuser/.cache \
    && chown -R appuser:appuser /app /home/appuser \
    && chmod +x /app/start-railway.sh

# Changement vers l'utilisateur non-root
USER appuser

# Exposition du port
EXPOSE 8000

# Variables d'environnement par défaut
ENV HEADLESS=true
ENV DEBUG=false
ENV LOG_LEVEL=INFO
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Commande de démarrage avec script amélioré
CMD ["./start-railway.sh"] 