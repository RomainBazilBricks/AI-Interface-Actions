#!/bin/bash

echo "🚀 Configuration automatique Paperspace pour AI Interface Actions"
echo "================================================================="

# Mise à jour du système
echo "📦 Mise à jour du système..."
sudo apt-get update -y
sudo apt-get upgrade -y

# Installation des dépendances de base
echo "🔧 Installation des dépendances de base..."
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    wget \
    unzip \
    firefox \
    xvfb \
    x11vnc \
    fluxbox

# Installation des dépendances Playwright
echo "🎭 Installation des dépendances Playwright..."
sudo apt-get install -y \
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxcb1 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2

# Installation de ngrok
echo "🌐 Installation de ngrok..."
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt-get update
sudo apt-get install -y ngrok

# Clonage du projet
echo "📁 Clonage du projet..."
cd ~
git clone https://github.com/romain-bricks/AI-Interface-Actions.git
cd AI-Interface-Actions

# Installation des dépendances Python
echo "🐍 Installation des dépendances Python..."
python3 -m pip install --user -r requirements.txt

# Installation de Playwright
echo "🎭 Installation de Playwright..."
python3 -m playwright install chromium
python3 -m playwright install-deps

# Création du script de démarrage
echo "🚀 Création du script de démarrage..."
cat > ~/start_api.sh << 'EOF'
#!/bin/bash

echo "🚀 Démarrage AI Interface Actions"

# Variables d'environnement
export MANUS_SESSION_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6InJvbWFpbi5iYXppbEBicmlja3MuY28iLCJleHAiOjE3NTc1OTA0OTUsImlhdCI6MTc1NDk5ODQ5NSwianRpIjoiWHV5M1I3QTY4dlRuemVGM21FdnpNRCIsIm5hbWUiOiJSb21haW4gQkFaSUwiLCJvcmlnaW5hbF91c2VyX2lkIjoiIiwidGVhbV91aWQiOiIiLCJ0eXBlIjoidXNlciIsInVzZXJfaWQiOiIzMTA0MTk2NjMwMjY4MjE4MjMifQ.4qoOLMhDNqO0B8zFSyYAgXzhBTy7UvO3QwXNuIGHIC0"
export USE_PERSISTENT_CONTEXT="false"
export HEADLESS="false"
export DISPLAY=:99

# Démarrage de Xvfb (affichage virtuel)
echo "🖥️ Démarrage de l'affichage virtuel..."
Xvfb :99 -screen 0 1024x768x24 &
sleep 2

# Démarrage de l'API
echo "🎯 Démarrage de l'API..."
cd ~/AI-Interface-Actions
python3 -m ai_interface_actions.main
EOF

chmod +x ~/start_api.sh

# Création du script ngrok
echo "🌐 Création du script ngrok..."
cat > ~/start_ngrok.sh << 'EOF'
#!/bin/bash

echo "🌐 Démarrage de ngrok..."
echo "Configurez d'abord votre token ngrok avec: ngrok config add-authtoken YOUR_TOKEN"
echo "Puis lancez: ngrok http 8000"

# Décommenter la ligne suivante après avoir configuré votre token
# ngrok http 8000
EOF

chmod +x ~/start_ngrok.sh

echo ""
echo "✅ Configuration terminée !"
echo ""
echo "🎯 ÉTAPES SUIVANTES :"
echo "1. Configurez ngrok: ngrok config add-authtoken YOUR_TOKEN"
echo "2. Démarrez l'API: ~/start_api.sh"
echo "3. Dans un autre terminal: ~/start_ngrok.sh"
echo ""
echo "🌐 L'API sera accessible via l'URL ngrok !"
echo "🖥️ Le navigateur s'ouvrira dans l'affichage virtuel" 