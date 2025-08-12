#!/usr/bin/env python3
"""
Script de debug pour analyser l'environnement Replit
"""
import os
import subprocess
import glob

def debug_environment():
    """Analyser l'environnement Replit"""
    print("🔍 Debug environnement Replit")
    print("=" * 50)
    
    # Variables d'environnement importantes
    print("\n📋 Variables d'environnement:")
    for var in ["PATH", "NIX_PATH", "PLAYWRIGHT_BROWSERS_PATH", "PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"]:
        value = os.environ.get(var, "NON DÉFINIE")
        print(f"  {var}: {value}")
    
    # Chercher Chromium
    print("\n🔍 Recherche de Chromium:")
    
    # Dans /nix/store
    chromium_paths = glob.glob("/nix/store/*/bin/chromium")
    print(f"  Dans /nix/store: {len(chromium_paths)} trouvé(s)")
    for path in chromium_paths[:5]:  # Limiter à 5 résultats
        print(f"    - {path}")
    
    # Dans PATH
    try:
        result = subprocess.run(["which", "chromium"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  Dans PATH: {result.stdout.strip()}")
        else:
            print("  Dans PATH: Non trouvé")
    except:
        print("  Dans PATH: Erreur lors de la recherche")
    
    # Tester l'exécution
    if chromium_paths:
        test_path = chromium_paths[0]
        print(f"\n🧪 Test d'exécution: {test_path}")
        try:
            result = subprocess.run([test_path, "--version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"  ✅ Version: {result.stdout.strip()}")
            else:
                print(f"  ❌ Erreur: {result.stderr.strip()}")
        except Exception as e:
            print(f"  ❌ Exception: {e}")
    
    # Structure des répertoires
    print("\n📁 Structure des répertoires:")
    for path in ["/nix/store", "/home/runner", "/tmp"]:
        if os.path.exists(path):
            try:
                count = len(os.listdir(path))
                print(f"  {path}: {count} éléments")
            except:
                print(f"  {path}: Accès refusé")
        else:
            print(f"  {path}: N'existe pas")

if __name__ == "__main__":
    debug_environment() 