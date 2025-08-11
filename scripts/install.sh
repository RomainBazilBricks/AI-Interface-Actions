#!/bin/bash

# Script d'installation pour AI Interface Actions
# Usage: ./scripts/install.sh

set -e  # Arrêter en cas d'erreur

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonctions d'affichage
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "\n${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}\n"
}

# Vérification des prérequis
check_requirements() {
    print_header "Vérification des prérequis"
    
    # Vérifier Python
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        print_info "Python trouvé : $PYTHON_VERSION"
        
        # Vérifier la version minimale (3.11)
        if python3 -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)"; then
            print_success "Version Python compatible"
        else
            print_error "Python 3.11+ requis. Version actuelle : $PYTHON_VERSION"
            exit 1
        fi
    else
        print_error "Python 3 non trouvé. Veuillez l'installer."
        exit 1
    fi
    
    # Vérifier pip
    if command -v pip3 &> /dev/null; then
        print_success "pip3 trouvé"
    else
        print_error "pip3 non trouvé. Veuillez l'installer."
        exit 1
    fi
    
    # Vérifier git (optionnel)
    if command -v git &> /dev/null; then
        print_success "git trouvé"
    else
        print_warning "git non trouvé. Installation manuelle requise."
    fi
}

# Création de l'environnement virtuel
setup_venv() {
    print_header "Configuration de l'environnement virtuel"
    
    if [ -d "venv" ]; then
        print_warning "Environnement virtuel existant détecté"
        read -p "Voulez-vous le recréer ? (y/N): " recreate
        if [[ $recreate =~ ^[Yy]$ ]]; then
            print_info "Suppression de l'ancien environnement virtuel"
            rm -rf venv
        else
            print_info "Utilisation de l'environnement virtuel existant"
            return 0
        fi
    fi
    
    print_info "Création de l'environnement virtuel"
    python3 -m venv venv
    
    print_info "Activation de l'environnement virtuel"
    source venv/bin/activate
    
    print_info "Mise à jour de pip"
    pip install --upgrade pip
    
    print_success "Environnement virtuel configuré"
}

# Installation des dépendances
install_dependencies() {
    print_header "Installation des dépendances Python"
    
    source venv/bin/activate
    
    if [ -f "requirements.txt" ]; then
        print_info "Installation via requirements.txt"
        pip install -r requirements.txt
    elif [ -f "pyproject.toml" ]; then
        print_info "Installation via pyproject.toml"
        pip install -e .
    else
        print_error "Aucun fichier de dépendances trouvé"
        exit 1
    fi
    
    print_success "Dépendances Python installées"
}

# Installation des navigateurs Playwright
install_browsers() {
    print_header "Installation des navigateurs Playwright"
    
    source venv/bin/activate
    
    print_info "Installation du navigateur Chromium"
    playwright install chromium
    
    print_info "Installation des dépendances système pour Chromium"
    playwright install-deps chromium
    
    print_success "Navigateurs Playwright installés"
}

# Configuration des variables d'environnement
setup_config() {
    print_header "Configuration des variables d'environnement"
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            print_info "Copie du fichier .env.example vers .env"
            cp .env.example .env
            print_success "Fichier .env créé"
            
            print_warning "IMPORTANT: Éditez le fichier .env avec vos paramètres :"
            echo -e "  - ${YELLOW}MANUS_LOGIN_EMAIL${NC}: Votre email Manus.ai"
            echo -e "  - ${YELLOW}MANUS_LOGIN_PASSWORD${NC}: Votre mot de passe Manus.ai"
            echo -e "  - ${YELLOW}API_SECRET_KEY${NC}: Une clé secrète pour l'API"
        else
            print_error "Fichier .env.example non trouvé"
            exit 1
        fi
    else
        print_info "Fichier .env existant détecté"
    fi
}

# Test de l'installation
test_installation() {
    print_header "Test de l'installation"
    
    source venv/bin/activate
    
    print_info "Test d'importation des modules"
    python3 -c "
import ai_interface_actions
from ai_interface_actions.config import settings
from ai_interface_actions.api import app
print('✅ Modules importés avec succès')
print(f'Version: {ai_interface_actions.__version__}')
"
    
    print_info "Vérification de la configuration Playwright"
    python3 -c "
from playwright.async_api import async_playwright
import asyncio

async def test_playwright():
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    await browser.close()
    await playwright.stop()
    print('✅ Playwright fonctionne correctement')

asyncio.run(test_playwright())
"
    
    print_success "Installation testée avec succès"
}

# Affichage des instructions finales
show_final_instructions() {
    print_header "Installation terminée !"
    
    echo -e "${GREEN}L'outil AI Interface Actions est prêt à être utilisé.${NC}\n"
    
    echo -e "${BLUE}Prochaines étapes :${NC}"
    echo -e "1. ${YELLOW}Configurez vos identifiants${NC} dans le fichier .env :"
    echo -e "   nano .env"
    echo -e ""
    echo -e "2. ${YELLOW}Activez l'environnement virtuel${NC} :"
    echo -e "   source venv/bin/activate"
    echo -e ""
    echo -e "3. ${YELLOW}Démarrez l'application${NC} :"
    echo -e "   python -m ai_interface_actions.main"
    echo -e ""
    echo -e "4. ${YELLOW}Accédez à l'interface Swagger${NC} :"
    echo -e "   http://localhost:8000/docs"
    echo -e ""
    
    echo -e "${BLUE}Commandes utiles :${NC}"
    echo -e "• ${YELLOW}Démarrage en mode développement${NC} :"
    echo -e "  uvicorn ai_interface_actions.api:app --reload"
    echo -e ""
    echo -e "• ${YELLOW}Démarrage avec Docker${NC} :"
    echo -e "  docker-compose up -d"
    echo -e ""
    echo -e "• ${YELLOW}Test de santé${NC} :"
    echo -e "  curl http://localhost:8000/health"
    echo -e ""
    
    echo -e "${GREEN}Pour plus d'informations, consultez le README.md${NC}"
}

# Fonction principale
main() {
    clear
    echo -e "${BLUE}"
    echo "  _____ _____   _____       _             __                   "
    echo " |  _  |     | |     |___ _| |_ ___ ___ _|  |___ ___ ___        "
    echo " |     |-   -| |-   -|   | . | -_|  _|  _  | . |  _| -_|       "
    echo " |__|__|_____| |_____|_|_|___|___|_| |___|___|___|___|___|      "
    echo "                                                               "
    echo "            Actions - Installation automatique                 "
    echo -e "${NC}"
    
    print_info "Début de l'installation..."
    
    # Vérifier si on est dans le bon répertoire
    if [ ! -f "pyproject.toml" ] && [ ! -f "requirements.txt" ]; then
        print_error "Ce script doit être exécuté depuis la racine du projet AI Interface Actions"
        exit 1
    fi
    
    # Étapes d'installation
    check_requirements
    setup_venv
    install_dependencies
    install_browsers
    setup_config
    test_installation
    show_final_instructions
    
    print_success "Installation terminée avec succès ! 🎉"
}

# Gestion des erreurs
trap 'print_error "Installation interrompue"; exit 1' INT TERM

# Exécution du script principal
main "$@" 