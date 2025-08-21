"""
Module pour télécharger des fichiers .zip depuis des URLs
"""
import tempfile
import os
import requests
import structlog
from typing import Tuple, Optional
from urllib.parse import urlparse

logger = structlog.get_logger(__name__)

class ZipDownloader:
    """Gestionnaire de téléchargement de fichiers .zip"""
    
    def __init__(self, timeout: int = 120, max_size: int = 1000 * 1024 * 1024):  # 1GB par défaut
        self.timeout = timeout
        self.max_size = max_size
    
    def download_zip_from_url(self, zip_url: str) -> Tuple[str, str]:
        """
        Télécharge un fichier .zip depuis une URL
        
        Args:
            zip_url: URL du fichier .zip à télécharger
            
        Returns:
            Tuple[str, str]: (chemin_fichier_temporaire, nom_fichier)
            
        Raises:
            Exception: En cas d'erreur de téléchargement
        """
        logger.info("Début du téléchargement de fichier .zip", url=zip_url)
        
        try:
            # Valider l'URL
            parsed_url = urlparse(zip_url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise ValueError(f"URL invalide: {zip_url}")
            
            # Extraire le nom de fichier depuis l'URL
            filename = os.path.basename(parsed_url.path)
            if not filename or not filename.lower().endswith('.zip'):
                filename = "downloaded_file.zip"
            
            logger.info("Téléchargement en cours", filename=filename, url=zip_url)
            
            # Télécharger le fichier avec streaming pour gérer les gros fichiers
            response = requests.get(
                zip_url,
                stream=True,
                timeout=self.timeout,
                headers={
                    'User-Agent': 'AI-Interface-Actions/1.0',
                    'Accept': 'application/zip, application/octet-stream, */*'
                }
            )
            response.raise_for_status()
            
            # Vérifier le Content-Type si disponible
            content_type = response.headers.get('content-type', '').lower()
            if content_type and 'zip' not in content_type and 'octet-stream' not in content_type:
                logger.warning("Type de contenu suspect", content_type=content_type)
            
            # Vérifier la taille du fichier
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > self.max_size:
                raise ValueError(f"Fichier trop volumineux: {content_length} bytes (max: {self.max_size})")
            
            # Créer un fichier temporaire
            temp_fd, temp_path = tempfile.mkstemp(suffix='.zip', prefix='downloaded_')
            
            try:
                with os.fdopen(temp_fd, 'wb') as temp_file:
                    downloaded_size = 0
                    
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            downloaded_size += len(chunk)
                            
                            # Vérifier la taille pendant le téléchargement
                            if downloaded_size > self.max_size:
                                raise ValueError(f"Fichier trop volumineux: {downloaded_size} bytes (max: {self.max_size})")
                            
                            temp_file.write(chunk)
                
                logger.info("Téléchargement terminé avec succès", 
                           filename=filename,
                           size_bytes=downloaded_size,
                           temp_path=temp_path)
                
                return temp_path, filename
                
            except Exception as e:
                # Nettoyer le fichier temporaire en cas d'erreur
                try:
                    os.unlink(temp_path)
                except:
                    pass
                raise e
                
        except requests.exceptions.Timeout:
            logger.error("Timeout lors du téléchargement", url=zip_url, timeout=self.timeout)
            raise Exception(f"Timeout lors du téléchargement (max: {self.timeout}s)")
            
        except requests.exceptions.ConnectionError:
            logger.error("Erreur de connexion lors du téléchargement", url=zip_url)
            raise Exception(f"Impossible de se connecter à {zip_url}")
            
        except requests.exceptions.HTTPError as e:
            logger.error("Erreur HTTP lors du téléchargement", 
                        url=zip_url, 
                        status_code=e.response.status_code if e.response else None)
            raise Exception(f"Erreur HTTP {e.response.status_code if e.response else 'inconnue'}: {zip_url}")
            
        except Exception as e:
            logger.error("Erreur lors du téléchargement", url=zip_url, error=str(e))
            raise Exception(f"Erreur de téléchargement: {str(e)}")
    
    def validate_zip_url(self, zip_url: str) -> bool:
        """
        Valide qu'une URL pointe vers un fichier .zip
        
        Args:
            zip_url: URL à valider
            
        Returns:
            bool: True si l'URL semble valide
        """
        try:
            parsed_url = urlparse(zip_url)
            
            # Vérifier le schéma
            if parsed_url.scheme not in ['http', 'https']:
                return False
            
            # Vérifier qu'il y a un domaine
            if not parsed_url.netloc:
                return False
            
            # Vérifier l'extension (optionnel, car certaines URLs n'ont pas d'extension visible)
            path = parsed_url.path.lower()
            if path and not (path.endswith('.zip') or 'zip' in path):
                logger.warning("URL ne semble pas pointer vers un fichier .zip", url=zip_url)
            
            return True
            
        except Exception as e:
            logger.error("Erreur lors de la validation de l'URL", url=zip_url, error=str(e))
            return False


# Instance globale du téléchargeur
zip_downloader = ZipDownloader()
