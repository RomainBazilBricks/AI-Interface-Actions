#!/usr/bin/env python3
"""
Script de démarrage simple pour Replit
"""
import os
import subprocess
import sys
import glob

def install_dependencies():
    """Installer les dépendances Python"""
    print("📦 Installation des dépendances Python...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)

def install_playwright():
    """Installer Playwright SANS les navigateurs (on utilise Chromium de Nix)"""
    print("🎭 Installation de Playwright...")
    # Ne pas installer les navigateurs, utiliser celui de Nix
    try:
        subprocess.run([sys.executable, "-m", "playwright", "install-deps"], check=True)
    except subprocess.CalledProcessError:
        print("⚠️ install-deps failed, continuing anyway...")

def find_chromium_path():
    """Trouver le chemin vers Chromium de Nix"""
    # Chercher dans /nix/store
    chromium_paths = glob.glob("/nix/store/*/bin/chromium")
    if chromium_paths:
        return chromium_paths[0]
    
    # Fallback: chercher dans le PATH
    try:
        result = subprocess.run(["which", "chromium"], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    
    return None

def set_environment():
    """Configurer les variables d'environnement"""
    os.environ["MANUS_SESSION_TOKEN"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6InJvbWFpbi5iYXppbEBicmlja3MuY28iLCJleHAiOjE3NTc1OTA0OTUsImlhdCI6MTc1NDk5ODQ5NSwianRpIjoiWHV5M1I3QTY4dlRuemVGM21FdnpNRCIsIm5hbWUiOiJSb21haW4gQkFaSUwiLCJvcmlnaW5hbF91c2VyX2lkIjoiIiwidGVhbV91aWQiOiIiLCJ0eXBlIjoidXNlciIsInVzZXJfaWQiOiIzMTA0MTk2NjMwMjY4MjE4MjMifQ.4qoOLMhDNqO0B8zFSyYAgXzhBTy7UvO3QwXNuIGHIC0"
    os.environ["USE_PERSISTENT_CONTEXT"] = "false"
    os.environ["HEADLESS"] = "true"
    
    # Trouver et configurer Chromium
    chromium_path = find_chromium_path()
    if chromium_path:
        print(f"✅ Chromium trouvé: {chromium_path}")
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"
        os.environ["PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"] = chromium_path
    else:
        print("⚠️ Chromium non trouvé, utilisation par défaut")

def start_api():
    """Démarrer l'API"""
    print("🚀 Démarrage de l'API...")
    from ai_interface_actions.main import main
    main()

if __name__ == "__main__":
    try:
        install_dependencies()
        install_playwright()
        set_environment()
        start_api()
    except Exception as e:
        print(f"❌ Erreur: {e}")
        sys.exit(1) 