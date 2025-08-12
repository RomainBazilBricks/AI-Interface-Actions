#!/bin/bash

echo "🚀 Installation et démarrage AI Interface Actions"

# Installer les dépendances Python
echo "📦 Installation des dépendances Python..."
pip install -r requirements.txt

# Installer Playwright
echo "🎭 Installation de Playwright..."
python -m playwright install chromium

# Variables d'environnement
export MANUS_SESSION_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6InJvbWFpbi5iYXppbEBicmlja3MuY28iLCJleHAiOjE3NTc1OTA0OTUsImlhdCI6MTc1NDk5ODQ5NSwianRpIjoiWHV5M1I3QTY4dlRuemVGM21FdnpNRCIsIm5hbWUiOiJSb21haW4gQkFaSUwiLCJvcmlnaW5hbF91c2VyX2lkIjoiIiwidGVhbV91aWQiOiIiLCJ0eXBlIjoidXNlciIsInVzZXJfaWQiOiIzMTA0MTk2NjMwMjY4MjE4MjMifQ.4qoOLMhDNqO0B8zFSyYAgXzhBTy7UvO3QwXNuIGHIC0"
export USE_PERSISTENT_CONTEXT="false"
export PYTHONPATH="/home/runner/AI-Interface-Actions"

# Démarrer l'API
echo "🎯 Démarrage de l'API..."
python -m ai_interface_actions.main 