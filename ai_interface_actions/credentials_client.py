"""
Client API pour communiquer avec l'API de gestion des credentials IA
"""
import httpx
import json
import structlog
from typing import Optional, Dict, Any, List
from pathlib import Path

from ai_interface_actions.config import settings

logger = structlog.get_logger(__name__)


class CredentialsAPIClient:
    """Client pour l'API de gestion des credentials IA"""
    
    def __init__(self):
        self.base_url = settings.credentials_api_url
        self.api_token = settings.credentials_api_token
        self.timeout = settings.credentials_api_timeout
        
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_token}" if self.api_token else ""
        }
    
    async def get_credential_for_platform(self, platform: str, user_identifier: str) -> Optional[Dict[str, Any]]:
        """
        Récupère le credential actif pour une plateforme et un utilisateur
        
        Args:
            platform: Nom de la plateforme (ex: 'manus')
            user_identifier: Identifiant utilisateur (ex: email)
            
        Returns:
            Données du credential ou None si non trouvé
        """
        try:
            if not self.base_url or not self.api_token:
                logger.warning("API credentials non configurée, utilisation du fallback local")
                return None
            
            url = f"{self.base_url}/platform/{platform}/user/{user_identifier}"
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=self.headers)
                
                if response.status_code == 200:
                    credential = response.json()
                    logger.info("Credential récupéré depuis l'API", 
                              platform=platform, 
                              user_identifier=user_identifier,
                              credential_id=credential.get('id'))
                    return credential
                elif response.status_code == 404:
                    logger.info("Aucun credential trouvé pour cette plateforme/utilisateur",
                              platform=platform, user_identifier=user_identifier)
                    return None
                else:
                    logger.error("Erreur API lors de la récupération du credential",
                               status_code=response.status_code,
                               response=response.text)
                    return None
                    
        except Exception as e:
            logger.error("Erreur lors de la communication avec l'API credentials", error=str(e))
            return None
    
    async def create_credential(self, credential_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Crée un nouveau credential
        
        Args:
            credential_data: Données du credential à créer
            
        Returns:
            Credential créé ou None si erreur
        """
        try:
            if not self.base_url or not self.api_token:
                logger.warning("API credentials non configurée")
                return None
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.base_url,
                    headers=self.headers,
                    json=credential_data
                )
                
                if response.status_code == 200:
                    credential = response.json()
                    logger.info("Credential créé avec succès", credential_id=credential.get('id'))
                    return credential
                else:
                    logger.error("Erreur lors de la création du credential",
                               status_code=response.status_code,
                               response=response.text)
                    return None
                    
        except Exception as e:
            logger.error("Erreur lors de la création du credential", error=str(e))
            return None
    
    async def update_credential(self, credential_id: int, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Met à jour un credential existant
        
        Args:
            credential_id: ID du credential à mettre à jour
            update_data: Données à mettre à jour
            
        Returns:
            Credential mis à jour ou None si erreur
        """
        try:
            if not self.base_url or not self.api_token:
                logger.warning("API credentials non configurée")
                return None
            
            url = f"{self.base_url}/{credential_id}/update"
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=update_data
                )
                
                if response.status_code == 200:
                    credential = response.json()
                    logger.info("Credential mis à jour avec succès", credential_id=credential_id)
                    return credential
                else:
                    logger.error("Erreur lors de la mise à jour du credential",
                               credential_id=credential_id,
                               status_code=response.status_code,
                               response=response.text)
                    return None
                    
        except Exception as e:
            logger.error("Erreur lors de la mise à jour du credential", error=str(e))
            return None
    
    async def list_credentials(self, platform: Optional[str] = None, 
                             user_identifier: Optional[str] = None,
                             is_active: bool = True,
                             limit: int = 10) -> List[Dict[str, Any]]:
        """
        Liste les credentials avec filtres
        
        Args:
            platform: Filtrer par plateforme (optionnel)
            user_identifier: Filtrer par utilisateur (optionnel)
            is_active: Filtrer par statut actif
            limit: Limite de résultats
            
        Returns:
            Liste des credentials
        """
        try:
            if not self.base_url or not self.api_token:
                logger.warning("API credentials non configurée")
                return []
            
            params = {
                "isActive": is_active,
                "limit": limit
            }
            
            if platform:
                params["platform"] = platform
            if user_identifier:
                params["userIdentifier"] = user_identifier
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    self.base_url,
                    headers=self.headers,
                    params=params
                )
                
                if response.status_code == 200:
                    result = response.json()
                    credentials = result.get("items", [])
                    logger.info("Credentials listés avec succès", count=len(credentials))
                    return credentials
                else:
                    logger.error("Erreur lors de la liste des credentials",
                               status_code=response.status_code,
                               response=response.text)
                    return []
                    
        except Exception as e:
            logger.error("Erreur lors de la liste des credentials", error=str(e))
            return []
    
    def get_storage_state_from_credential(self, credential: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Convertit un credential de l'API au format storage_state Playwright
        
        Args:
            credential: Credential depuis l'API
            
        Returns:
            Storage state au format Playwright ou None
        """
        try:
            session_data = credential.get("sessionData", {})
            
            if not session_data:
                logger.warning("Pas de sessionData dans le credential")
                return None
            
            # Construire le storage state Playwright
            storage_state = {
                "cookies": [],
                "origins": []
            }
            
            # Convertir les cookies
            cookies_data = session_data.get("cookies", {})
            for name, value in cookies_data.items():
                storage_state["cookies"].append({
                    "name": name,
                    "value": value,
                    "domain": ".manus.ai",
                    "path": "/",
                    "httpOnly": name in ["session_id", "auth_token"],
                    "secure": True,
                    "sameSite": "Lax"
                })
            
            # Convertir le localStorage
            local_storage = session_data.get("local_storage", {})
            if local_storage:
                storage_state["origins"] = [{
                    "origin": "https://www.manus.ai",
                    "localStorage": [
                        {"name": k, "value": v} for k, v in local_storage.items()
                    ]
                }]
            
            logger.info("Storage state généré depuis credential",
                       cookies_count=len(storage_state["cookies"]),
                       origins_count=len(storage_state["origins"]))
            
            return storage_state
            
        except Exception as e:
            logger.error("Erreur lors de la conversion du credential", error=str(e))
            return None
    
    def is_configured(self) -> bool:
        """Vérifie si l'API est configurée"""
        return bool(self.base_url and self.api_token)


# Instance globale du client
credentials_client = CredentialsAPIClient() 