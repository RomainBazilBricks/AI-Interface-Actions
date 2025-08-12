#!/usr/bin/env python3
"""
Script SIMPLE qui évite pip et force Chromium de Nix
"""
import os
import sys
import glob

def setup_environment():
    """Configuration directe de l'environnement"""
    print("🔧 Configuration directe de l'environnement...")
    
    # Variables d'environnement
    os.environ["MANUS_SESSION_TOKEN"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6InJvbWFpbi5iYXppbEBicmlja3MuY28iLCJleHAiOjE3NTc1OTA0OTUsImlhdCI6MTc1NDk5ODQ5NSwianRpIjoiWHV5M1I3QTY4dlRuemVGM21FdnpNRCIsIm5hbWUiOiJSb21haW4gQkFaSUwiLCJvcmlnaW5hbF91c2VyX2lkIjoiIiwidGVhbV91aWQiOiIiLCJ0eXBlIjoidXNlciIsInVzZXJfaWQiOiIzMTA0MTk2NjMwMjY4MjE4MjMifQ.4qoOLMhDNqO0B8zFSyYAgXzhBTy7UvO3QwXNuIGHIC0"
    os.environ["USE_PERSISTENT_CONTEXT"] = "false"
    os.environ["HEADLESS"] = "true"
    
    # Forcer Chromium de Nix
    chromium_paths = glob.glob("/nix/store/*/bin/chromium")
    if chromium_paths:
        chromium_path = chromium_paths[0]
        print(f"✅ Chromium forcé: {chromium_path}")
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"
        os.environ["PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"] = chromium_path
    else:
        print("❌ Aucun Chromium trouvé dans /nix/store")
        # Essayer dans PATH
        import subprocess
        try:
            result = subprocess.run(["which", "chromium"], capture_output=True, text=True)
            if result.returncode == 0:
                chromium_path = result.stdout.strip()
                print(f"✅ Chromium trouvé dans PATH: {chromium_path}")
                os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"
                os.environ["PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"] = chromium_path
        except:
            pass
    
    print("🚀 Démarrage de l'API SANS installation pip...")

def start_api():
    """Démarrer l'API directement"""
    try:
        # Ajouter le répertoire courant au PYTHONPATH
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        
        # Importer et démarrer l'API
        from ai_interface_actions.main import main
        main()
    except ImportError as e:
        print(f"❌ Erreur d'import: {e}")
        print("Les dépendances ne sont peut-être pas installées")
        sys.exit(1)

if __name__ == "__main__":
    setup_environment()
    start_api() 