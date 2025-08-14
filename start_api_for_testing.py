#!/usr/bin/env python3
"""
Script pour démarrer l'API en mode développement pour les tests
"""

import subprocess
import sys
import os

def main():
    """Démarre l'API AI Interface Actions"""
    
    print("🚀 Démarrage de l'API AI Interface Actions pour les tests")
    print("=" * 60)
    
    # Vérifier qu'on est dans le bon répertoire
    if not os.path.exists("ai_interface_actions"):
        print("❌ Erreur: Le dossier 'ai_interface_actions' n'existe pas")
        print("Assurez-vous d'être dans le répertoire racine du projet")
        sys.exit(1)
    
    # Vérifier que le module principal existe
    if not os.path.exists("ai_interface_actions/main.py"):
        print("❌ Erreur: Le fichier 'ai_interface_actions/main.py' n'existe pas")
        sys.exit(1)
    
    try:
        print("Démarrage du serveur...")
        print("L'API sera accessible sur http://localhost:8000")
        print("Documentation interactive: http://localhost:8000/docs")
        print("\nPour arrêter le serveur, appuyez sur Ctrl+C")
        print("-" * 60)
        
        # Démarrer l'API
        subprocess.run([
            sys.executable, "-m", "ai_interface_actions.main"
        ], check=True)
        
    except KeyboardInterrupt:
        print("\n\n✅ Serveur arrêté par l'utilisateur")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Erreur lors du démarrage: {e}")
        print("Vérifiez que toutes les dépendances sont installées:")
        print("pip install -r requirements.txt")
    except Exception as e:
        print(f"\n❌ Erreur inattendue: {e}")

if __name__ == "__main__":
    main()
