#!/bin/bash

echo "🚀 Démarrage de AI Interface Actions sur Railway"

# Vérification et installation de Playwright si nécessaire
echo "🔍 Vérification de l'installation Playwright..."

# Tenter d'installer les navigateurs si ils n'existent pas
if [ ! -d "$HOME/.cache/ms-playwright/chromium-"* ] 2>/dev/null; then
    echo "⚠️  Navigateurs Playwright manquants, installation..."
    python -m playwright install chromium --with-deps || {
        echo "❌ Échec de l'installation complète, tentative sans dépendances système..."
        python -m playwright install chromium || {
            echo "⚠️  Installation de Playwright échouée, l'application démarrera en mode dégradé"
        }
    }
else
    echo "✅ Navigateurs Playwright déjà installés"
fi

# Démarrage de l'application
echo "🎯 Démarrage du serveur API..."
exec python -m ai_interface_actions.main 