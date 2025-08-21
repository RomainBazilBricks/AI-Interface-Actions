#!/usr/bin/env python3
"""
Script de lancement local pour debug
"""

import os
import sys
from pathlib import Path

# Ajouter le répertoire racine au PYTHONPATH
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

# Charger les variables d'environnement locales
from dotenv import load_dotenv
load_dotenv('.env.local')

# Lancer l'application
if __name__ == "__main__":
    print("🚀 Lancement de l'API en mode debug local...")
    print(f"📍 URL: http://127.0.0.1:8000")
    print(f"📖 Docs: http://127.0.0.1:8000/docs")
    print(f"🔍 Session Status: http://127.0.0.1:8000/debug/session-status")
    print()
    
    # Importer et lancer
    from ai_interface_actions.main import main
    main()
