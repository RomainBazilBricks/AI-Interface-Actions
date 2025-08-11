"""
Point d'entrée principal de l'application AI Interface Actions
"""
import asyncio
import signal
import sys
from typing import Optional

import uvicorn
import structlog

from ai_interface_actions.config import settings
from ai_interface_actions.api import app
from ai_interface_actions.browser_automation import browser_manager
from ai_interface_actions.task_manager import task_manager

logger = structlog.get_logger(__name__)


class GracefulShutdown:
    """Gestionnaire d'arrêt propre de l'application"""
    
    def __init__(self):
        self.shutdown_event = asyncio.Event()
        self.setup_signal_handlers()
    
    def setup_signal_handlers(self):
        """Configure les gestionnaires de signaux"""
        if sys.platform != "win32":
            # Unix/Linux/MacOS
            loop = asyncio.get_event_loop()
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, self.signal_handler, sig)
        else:
            # Windows
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum: int, frame: Optional[any] = None):
        """Gestionnaire de signal pour arrêt propre"""
        logger.info("Signal d'arrêt reçu", signal=signum)
        self.shutdown_event.set()
    
    async def wait_for_shutdown(self):
        """Attend le signal d'arrêt"""
        await self.shutdown_event.wait()


async def cleanup_resources():
    """Nettoie les ressources de l'application"""
    try:
        logger.info("Nettoyage des ressources...")
        
        # Nettoyage des anciennes tâches
        task_manager.cleanup_old_tasks(max_age_hours=1)
        
        # Nettoyage du navigateur
        await browser_manager.cleanup()
        
        logger.info("Ressources nettoyées avec succès")
        
    except Exception as e:
        logger.error("Erreur lors du nettoyage", error=str(e))


def main():
    """Fonction principale"""
    try:
        logger.info("Démarrage de AI Interface Actions", version="0.1.0")
        
        # Configuration Uvicorn
        config = uvicorn.Config(
            app,
            host=settings.api_host,
            port=settings.api_port,
            reload=settings.debug,
            log_level=settings.log_level.lower(),
            access_log=True,
            use_colors=True
        )
        
        server = uvicorn.Server(config)
        
        logger.info(
            "Serveur configuré",
            host=settings.api_host,
            port=settings.api_port,
            debug=settings.debug
        )
        
        # Démarrage du serveur
        server.run()
        
    except KeyboardInterrupt:
        logger.info("Arrêt demandé par l'utilisateur")
    except Exception as e:
        logger.error("Erreur fatale", error=str(e))
        sys.exit(1)
    finally:
        logger.info("Application arrêtée")


if __name__ == "__main__":
    main() 