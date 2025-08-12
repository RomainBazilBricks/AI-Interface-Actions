#!/bin/bash

echo "🚀 Démarrage de AI Interface Actions sur Render.com"

# Démarrer Xvfb pour l'affichage virtuel
echo "🖥️  Démarrage de l'affichage virtuel..."
Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &
export DISPLAY=:99

# Attendre que Xvfb soit prêt
sleep 2

# Vérifier que Playwright est installé
echo "🔍 Vérification de Playwright..."
python -c "import playwright; print('✅ Playwright OK')" || {
    echo "❌ Erreur Playwright"
    exit 1
}

# Démarrer l'API
echo "🎯 Démarrage du serveur API..."
exec python -m ai_interface_actions.main 