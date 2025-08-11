#!/bin/bash

echo "🚂 Démarrage de AI Interface Actions sur Railway avec VNC..."

# Créer les répertoires de logs s'ils n'existent pas
mkdir -p /app/logs

# Afficher les informations de connexion VNC
echo "📺 VNC Server sera accessible sur le port 5900"
echo "🌐 API sera accessible sur le port 8000"

# Vérifier les variables d'environnement importantes
echo "🔧 Configuration:"
echo "   - HEADLESS: ${HEADLESS:-true}"
echo "   - HEADLESS_SETUP: ${HEADLESS_SETUP:-false}"
echo "   - USE_PERSISTENT_CONTEXT: ${USE_PERSISTENT_CONTEXT:-true}"

# Initialiser le display X11
export DISPLAY=:1

# Démarrer supervisord pour gérer tous les services
echo "🎯 Démarrage de Supervisor..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf 