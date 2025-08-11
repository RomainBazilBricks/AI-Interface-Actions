#!/usr/bin/env python3
"""
Script de configuration de session Manus.ai pour Railway
Exécute la connexion localement puis sauvegarde la session
"""
import asyncio
import sys
from pathlib import Path

# Ajouter le répertoire du projet au path
sys.path.insert(0, str(Path(__file__).parent))

from ai_interface_actions.browser_automation import browser_manager
from ai_interface_actions.config import settings
import structlog

# Configuration du logging pour le script
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

def print_banner():
    """Affiche le banner du script"""
    print("\n" + "="*70)
    print("🔧 CONFIGURATION SESSION MANUS.AI POUR RAILWAY")
    print("="*70)
    print("Ce script va :")
    print("1. Ouvrir Manus.ai dans votre navigateur local")
    print("2. Vous permettre de vous connecter manuellement")
    print("3. Sauvegarder votre session pour Railway")
    print("4. Vous donner les étapes suivantes")
    print("="*70)

async def setup_session_locally():
    """Configure la session Manus.ai localement"""
    try:
        print_banner()
        
        logger.info("🚀 Initialisation du setup de session")
        
        # Forcer la configuration pour le setup local
        logger.info("⚙️ Configuration du navigateur pour setup local")
        
        # Ouvrir la page de connexion en mode visible
        logger.info("🌐 Ouverture de Manus.ai...")
        url = await browser_manager.open_login_page()
        logger.info(f"✅ Page ouverte : {url}")
        
        print("\n" + "🔑 CONNEXION MANUELLE REQUISE")
        print("-" * 50)
        print("1. Une fenêtre de navigateur s'est ouverte sur Manus.ai")
        print("2. Connectez-vous avec vos identifiants")
        print("3. Naviguez jusqu'au tableau de bord principal")
        print("4. Laissez la fenêtre ouverte et revenez ici")
        print("-" * 50)
        
        input("🔵 Appuyez sur ENTRÉE une fois connecté sur Manus.ai...")
        
        # Sauvegarder la session
        logger.info("💾 Sauvegarde de la session...")
        success = await browser_manager.wait_for_login_and_save_session(timeout_minutes=1)
        
        if success:
            session_file = Path("session_state.json")
            if session_file.exists():
                file_size = session_file.stat().st_size
                logger.info("✅ Session sauvegardée avec succès !", 
                          file="session_state.json", size_bytes=file_size)
                
                print("\n" + "🎉 SUCCÈS ! SESSION CONFIGURÉE")
                print("=" * 50)
                print("📁 Fichier créé : session_state.json")
                print(f"📊 Taille : {file_size} bytes")
                print("\n🚀 PROCHAINES ÉTAPES :")
                print("1. git add session_state.json")
                print("2. git commit -m 'Add Manus.ai session for Railway'")
                print("3. git push origin main")
                print("4. Déployez sur Railway (Dockerfile simple)")
                print("5. La session durera ~30 jours")
                print("=" * 50)
                
                return True
            else:
                logger.error("❌ Fichier session non créé")
                return False
        else:
            logger.error("❌ Échec de la sauvegarde de session")
            return False
            
    except KeyboardInterrupt:
        logger.info("🛑 Arrêt demandé par l'utilisateur")
        return False
    except Exception as e:
        logger.error("💥 Erreur lors du setup", error=str(e))
        return False
    finally:
        logger.info("🧹 Nettoyage...")
        await browser_manager.cleanup()

def main():
    """Fonction principale"""
    try:
        result = asyncio.run(setup_session_locally())
        if result:
            print("\n✅ Setup terminé avec succès !")
            sys.exit(0)
        else:
            print("\n❌ Setup échoué")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Erreur fatale : {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 