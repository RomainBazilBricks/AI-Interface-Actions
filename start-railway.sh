#!/bin/bash

echo "🚀 Démarrage de AI Interface Actions sur Railway"

# Vérification de l'installation Playwright
echo "🔍 Vérification de l'installation Playwright..."

# Vérifier si les navigateurs sont disponibles
if [ -d "/ms-playwright/chromium-"* ] 2>/dev/null || [ -d "$HOME/.cache/ms-playwright/chromium-"* ] 2>/dev/null; then
    echo "✅ Navigateurs Playwright trouvés"
else
    echo "⚠️  Navigateurs Playwright non trouvés, mais continuons..."
fi

# Afficher les informations de démarrage
echo "🎯 Configuration:"
echo "   - HEADLESS: ${HEADLESS:-true}"
echo "   - DEBUG: ${DEBUG:-false}"
echo "   - PLAYWRIGHT_BROWSERS_PATH: ${PLAYWRIGHT_BROWSERS_PATH:-default}"

# Démarrage de l'application
echo "🎯 Démarrage du serveur API..."
exec python -m ai_interface_actions.main 