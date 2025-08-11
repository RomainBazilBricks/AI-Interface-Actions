"""
Routes d'administration pour la gestion de session sur Railway
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import asyncio
from typing import Optional
from pathlib import Path
import os

from ai_interface_actions.browser_automation import browser_manager
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/admin", tags=["Administration"])

class SessionSetupResponse(BaseModel):
    success: bool
    message: str
    vnc_info: Optional[dict] = None
    instructions: Optional[list] = None

class SessionStatusResponse(BaseModel):
    session_exists: bool
    session_size: int
    browser_initialized: bool
    vnc_available: bool
    railway_url: Optional[str] = None

@router.post("/setup-session", response_model=SessionSetupResponse)
async def setup_session_endpoint(background_tasks: BackgroundTasks):
    """
    Lance le processus de configuration de session avec VNC
    """
    try:
        logger.info("🔧 Démarrage du setup de session via VNC")
        
        # Ouvrir la page de connexion en mode visible (VNC)
        url = await browser_manager.open_login_page()
        
        # Programmer la sauvegarde automatique en arrière-plan
        background_tasks.add_task(auto_save_session_after_delay, minutes=10)
        
        # Obtenir l'URL Railway depuis les variables d'environnement
        railway_url = os.getenv("RAILWAY_PUBLIC_DOMAIN", "votre-app.railway.app")
        
        instructions = [
            "1. Connectez-vous via VNC au port 5900",
            "2. Utilisez un client VNC (RealVNC, TightVNC, etc.)",
            "3. Connectez-vous à Manus.ai dans le navigateur visible",
            "4. La session sera automatiquement sauvegardée",
            "5. Vérifiez le statut avec GET /admin/session-status"
        ]
        
        return SessionSetupResponse(
            success=True,
            message=f"Page de connexion ouverte sur {url}",
            vnc_info={
                "host": railway_url,
                "port": 5900,
                "password": None,  # Pas de mot de passe configuré
                "protocol": "VNC"
            },
            instructions=instructions
        )
        
    except Exception as e:
        logger.error("Erreur setup session", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/session-status", response_model=SessionStatusResponse)
async def check_session_status():
    """Vérifie le statut de la session et du VNC"""
    try:
        session_file = Path("session_state.json")
        railway_url = os.getenv("RAILWAY_PUBLIC_DOMAIN", "votre-app.railway.app")
        
        # Vérifier si VNC est disponible
        vnc_available = check_vnc_process()
        
        return SessionStatusResponse(
            session_exists=session_file.exists(),
            session_size=session_file.stat().st_size if session_file.exists() else 0,
            browser_initialized=browser_manager.is_initialized,
            vnc_available=vnc_available,
            railway_url=f"vnc://{railway_url}:5900"
        )
        
    except Exception as e:
        logger.error("Erreur vérification session", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/force-save-session")
async def force_save_session():
    """Force la sauvegarde immédiate de la session"""
    try:
        if not browser_manager.is_initialized:
            raise HTTPException(status_code=400, detail="Navigateur non initialisé")
        
        success = await browser_manager.wait_for_login_and_save_session(timeout_minutes=1)
        
        return {
            "success": success,
            "message": "Session sauvegardée" if success else "Échec de la sauvegarde"
        }
        
    except Exception as e:
        logger.error("Erreur sauvegarde forcée", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/vnc-info")
async def get_vnc_info():
    """Informations de connexion VNC"""
    railway_url = os.getenv("RAILWAY_PUBLIC_DOMAIN", "votre-app.railway.app")
    
    return {
        "vnc_url": f"vnc://{railway_url}:5900",
        "host": railway_url,
        "port": 5900,
        "protocol": "VNC",
        "password_required": False,
        "instructions": [
            "Utilisez un client VNC pour vous connecter",
            "Clients recommandés: RealVNC Viewer, TightVNC, VNC Viewer",
            "Aucun mot de passe requis",
            "Résolution: 1920x1080"
        ]
    }

def check_vnc_process() -> bool:
    """Vérifie si le processus VNC est en cours d'exécution"""
    try:
        import subprocess
        result = subprocess.run(
            ["pgrep", "-f", "x11vnc"], 
            capture_output=True, 
            text=True
        )
        return result.returncode == 0
    except:
        return False

async def auto_save_session_after_delay(minutes: int = 10):
    """Sauvegarde automatique de la session après un délai"""
    logger.info(f"⏰ Sauvegarde automatique programmée dans {minutes} minutes")
    await asyncio.sleep(minutes * 60)
    
    try:
        if browser_manager.is_initialized:
            success = await browser_manager.wait_for_login_and_save_session(timeout_minutes=2)
            logger.info("💾 Sauvegarde automatique terminée", success=success)
        else:
            logger.warning("Navigateur non initialisé pour la sauvegarde automatique")
    except Exception as e:
        logger.error("Erreur sauvegarde automatique", error=str(e)) 