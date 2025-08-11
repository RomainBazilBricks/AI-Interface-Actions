#!/usr/bin/env python3
"""
Script de test pour vérifier les variables d'environnement de session
"""
import os
import sys
from pathlib import Path

# Ajouter le répertoire du projet au path
sys.path.insert(0, str(Path(__file__).parent))

from ai_interface_actions.config import settings
from ai_interface_actions.browser_automation import browser_manager
import structlog

# Configuration du logging
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

def test_session_config():
    """Teste la configuration de session"""
    print("\n" + "="*60)
    print("🧪 TEST CONFIGURATION SESSION MANUS.AI")
    print("="*60)
    
    # Vérifier les variables d'environnement
    print("\n📋 Variables d'environnement détectées :")
    session_vars = [
        ("MANUS_SESSION_TOKEN", settings.manus_session_token),
        ("MANUS_AUTH_TOKEN", settings.manus_auth_token), 
        ("MANUS_USER_ID", settings.manus_user_id),
        ("MANUS_CSRF_TOKEN", settings.manus_csrf_token),
        ("MANUS_COOKIES", settings.manus_cookies),
        ("MANUS_LOCAL_STORAGE", settings.manus_local_storage)
    ]
    
    has_session_vars = False
    for var_name, var_value in session_vars:
        if var_value:
            print(f"✅ {var_name}: {var_value[:20]}{'...' if len(var_value) > 20 else ''}")
            has_session_vars = True
        else:
            print(f"❌ {var_name}: Non défini")
    
    # Vérifier le fichier session
    session_file = Path("session_state.json")
    print(f"\n📁 Fichier session_state.json: {'✅ Existe' if session_file.exists() else '❌ Absent'}")
    if session_file.exists():
        print(f"📊 Taille: {session_file.stat().st_size} bytes")
    
    # Test de la méthode _get_storage_state
    print(f"\n🔍 Test de récupération de l'état de stockage...")
    try:
        storage_state = browser_manager._get_storage_state()
        if storage_state:
            if isinstance(storage_state, str):
                print(f"✅ Utilisation du fichier: {storage_state}")
            elif isinstance(storage_state, dict):
                cookies_count = len(storage_state.get("cookies", []))
                origins_count = len(storage_state.get("origins", []))
                print(f"✅ Variables d'environnement: {cookies_count} cookies, {origins_count} origins")
            else:
                print(f"⚠️ Type inattendu: {type(storage_state)}")
        else:
            print("❌ Aucune session configurée")
    except Exception as e:
        print(f"💥 Erreur: {e}")
    
    # Recommandations
    print(f"\n💡 Recommandations :")
    if has_session_vars:
        print("✅ Variables d'environnement configurées - Prêt pour Railway !")
        print("🚀 Vous pouvez déployer sur Railway avec ces variables")
    elif session_file.exists():
        print("⚠️ Seul le fichier session existe")
        print("💡 Considérez l'extraction manuelle pour plus de flexibilité")
    else:
        print("❌ Aucune session configurée")
        print("📖 Suivez le guide EXTRACT_SESSION_GUIDE.md")
    
    print("="*60)

if __name__ == "__main__":
    test_session_config() 