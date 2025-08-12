#!/usr/bin/env python3
"""
Installation manuelle des dépendances - à exécuter séparément si besoin
"""
import subprocess
import sys
import os

def install_dependencies():
    """Installation manuelle des dépendances"""
    print("📦 Installation manuelle des dépendances...")
    
    # Essayer pip3 d'abord
    pip_commands = ["pip3", "pip", "python3 -m pip", "python -m pip"]
    
    for pip_cmd in pip_commands:
        try:
            print(f"Tentative avec: {pip_cmd}")
            if " -m " in pip_cmd:
                parts = pip_cmd.split()
                result = subprocess.run([*parts, "install", "-r", "requirements.txt"], 
                                      capture_output=True, text=True, timeout=60)
            else:
                result = subprocess.run([pip_cmd, "install", "-r", "requirements.txt"], 
                                      capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print(f"✅ Installation réussie avec {pip_cmd}")
                return True
            else:
                print(f"❌ Échec avec {pip_cmd}: {result.stderr[:200]}...")
                
        except Exception as e:
            print(f"❌ Erreur avec {pip_cmd}: {e}")
            continue
    
    print("❌ Toutes les tentatives d'installation ont échoué")
    return False

def install_playwright():
    """Installation de Playwright"""
    print("🎭 Installation de Playwright...")
    
    playwright_commands = [
        ["python3", "-m", "playwright", "install-deps"],
        ["python", "-m", "playwright", "install-deps"],
        ["playwright", "install-deps"]
    ]
    
    for cmd in playwright_commands:
        try:
            print(f"Tentative: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                print("✅ Playwright install-deps réussi")
                return True
            else:
                print(f"❌ Échec: {result.stderr[:200]}...")
        except Exception as e:
            print(f"❌ Erreur: {e}")
            continue
    
    print("⚠️ Installation Playwright échouée, mais on continue...")
    return False

if __name__ == "__main__":
    print("🔧 Installation manuelle démarrée")
    install_dependencies()
    install_playwright()
    print("✅ Installation terminée (avec ou sans erreurs)")
    print("Vous pouvez maintenant exécuter: python start_simple.py") 