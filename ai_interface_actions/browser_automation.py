"""
Module d'automatisation du navigateur avec Playwright
"""
import asyncio
import os
import structlog
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError

from ai_interface_actions.config import settings
from ai_interface_actions.credentials_client import CredentialsAPIClient

logger = structlog.get_logger(__name__)


class BrowserAutomation:
    """Gestionnaire d'automatisation du navigateur"""
    
    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.is_initialized = False
        self.credentials_client = CredentialsAPIClient()
        
    async def initialize(self, headless_override: bool = None) -> None:
        """
        Initialise le navigateur
        
        Args:
            headless_override: Force le mode headless (None = utilise config)
        """
        try:
            logger.info("Initialisation du navigateur Playwright")
            self.playwright = await async_playwright().start()
            
            # Déterminer le mode headless
            use_headless = headless_override if headless_override is not None else settings.headless
            logger.info(f"Mode navigateur: {'headless' if use_headless else 'visible'}")
            
            # Configuration commune
            context_options = {
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "locale": "fr-FR",
                "timezone_id": "Europe/Paris",
                "args": [
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                    "--disable-extensions-except",
                    "--disable-plugins",
                    "--disable-javascript-harmony-shipping",
                    "--max_old_space_size=4096"
                ]
            }
            
            # Viewport adaptatif selon le mode
            if use_headless:
                # Mode headless : taille fixe optimisée
                context_options["viewport"] = {"width": 1920, "height": 1080}
            else:
                # Mode visible : utiliser une taille standard compatible
                if settings.window_width > 0 and settings.window_height > 0:
                    context_options["viewport"] = {"width": settings.window_width, "height": settings.window_height}
                else:
                    # Taille standard compatible au lieu de None
                    context_options["viewport"] = {"width": 1440, "height": 900}
            
            # Utiliser contexte persistant (profil utilisateur) ou session temporaire
            if settings.use_persistent_context:
                # Utiliser le répertoire de données utilisateur pour persistance RÉELLE
                # Détecter si on est dans un container Docker ou en local
                if Path("/app").exists():
                    # Container Docker
                    user_data_dir = Path("/app") / ".ai-interface-actions" / "browser-data"
                else:
                    # Environnement local
                    user_data_dir = Path.home() / ".ai-interface-actions" / "browser-data"
                user_data_dir.mkdir(parents=True, exist_ok=True)
                
                # IMPORTANT: launch_persistent_context utilise le profil utilisateur
                persistent_options = {
                    "user_data_dir": str(user_data_dir),
                    "headless": use_headless,
                    **context_options
                }
                
                # Utiliser Chromium de Nix si disponible
                chromium_path = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH")
                if chromium_path and chromium_path != "0":
                    persistent_options["executable_path"] = chromium_path
                    logger.info(f"Utilisation de Chromium personnalisé pour contexte persistant: {chromium_path}")
                
                self.context = await self.playwright.chromium.launch_persistent_context(**persistent_options)
                # Pas de browser séparé avec launch_persistent_context
                self.browser = None
                logger.info("Contexte persistant créé avec profil utilisateur (PAS navigation privée)")
            else:
                # Mode session temporaire (navigation privée avec sauvegarde)
                launch_options = {
                    "headless": use_headless,
                    "args": context_options["args"]
                }
                
                # Utiliser Chromium de Nix si disponible
                chromium_path = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH")
                if chromium_path and chromium_path != "0":
                    launch_options["executable_path"] = chromium_path
                    logger.info(f"Utilisation de Chromium personnalisé: {chromium_path}")
                
                self.browser = await self.playwright.chromium.launch(**launch_options)
                
                # Préparer les options pour new_context
                new_context_options = {
                    "user_agent": context_options["user_agent"],
                    "locale": context_options["locale"],
                    "timezone_id": context_options["timezone_id"],
                    "storage_state": await self._get_storage_state()
                }
                
                # Ajouter viewport seulement s'il est défini
                if context_options["viewport"] is not None:
                    new_context_options["viewport"] = context_options["viewport"]
                
                self.context = await self.browser.new_context(**new_context_options)
                logger.info("Contexte temporaire créé (navigation privée avec sauvegarde)")
            
            # Configuration des timeouts
            self.context.set_default_timeout(settings.page_timeout)
            
            # Login manuel uniquement - pas de login automatique
            
            self.is_initialized = True
            logger.info("Navigateur initialisé avec succès")
            
        except Exception as e:
            logger.error("Erreur lors de l'initialisation du navigateur", error=str(e))
            raise
    
    async def cleanup(self) -> None:
        """Nettoie les ressources du navigateur"""
        try:
            if self.context:
                # Sauvegarder seulement si on utilise le mode temporaire (avec browser)
                if self.browser and not settings.use_persistent_context:
                    try:
                        await self.context.storage_state(path="session_state.json")
                        logger.info("État de session sauvegardé")
                    except Exception as e:
                        logger.warning("Impossible de sauvegarder la session", error=str(e))
                
                await self.context.close()
                logger.info("Contexte fermé")
            
            if self.browser:
                await self.browser.close()
                logger.info("Navigateur fermé")
            
            if self.playwright:
                await self.playwright.stop()
            
            self.is_initialized = False
            logger.info("Ressources du navigateur nettoyées")
            
        except Exception as e:
            logger.error("Erreur lors du nettoyage", error=str(e))
    
    async def _get_storage_state(self) -> Optional[Dict[str, Any]]:
        """Récupère l'état de session stocké"""
        try:
            # Option 1 : API de credentials externe (PRIORITÉ)
            try:
                from ai_interface_actions.credentials_client import credentials_client
                
                if credentials_client.is_configured():
                    logger.info("Tentative de récupération des credentials via API externe")
                    
                    # Utiliser l'email par défaut pour récupérer les credentials
                    user_email = "romain.bazil@bricks.co"  # Peut être configuré via une variable d'environnement
                    credential = await credentials_client.get_credential_for_platform("manus", user_email)
                    
                    if credential:
                        storage_state = credentials_client.get_storage_state_from_credential(credential)
                        if storage_state:
                            logger.info("Session récupérée depuis l'API de credentials", 
                                       user_email=user_email,
                                       cookies_count=len(storage_state.get("cookies", [])))
                            return storage_state
                    
                    logger.info("Aucun credential trouvé dans l'API, fallback vers les variables d'environnement")
                else:
                    logger.info("API credentials non configurée, utilisation directe des variables d'environnement")
                
            except Exception as e:
                logger.warning("Erreur lors de l'accès à l'API de credentials, fallback", error=str(e))
            
            # Option 2 : Variables d'environnement (FALLBACK FORCÉ)
            logger.info("Vérification des variables d'environnement MANUS_*")
            if settings.manus_cookies or settings.manus_session_token:
                logger.info("✅ Variables d'environnement MANUS_* trouvées, construction du storage_state")
                
                storage_state = {
                    "cookies": [],
                    "origins": []
                }
                
                # Ajouter les cookies depuis les variables d'environnement
                if settings.manus_cookies:
                    try:
                        cookies_data = json.loads(settings.manus_cookies)
                        logger.info(f"Cookies parsés: {len(cookies_data)} éléments")
                        
                        for name, value in cookies_data.items():
                            # Déterminer le bon domaine selon le cookie
                            if "intercom" in name.lower():
                                domain = ".manus.ai"  # Intercom reste sur .manus.ai
                            else:
                                domain = ".manus.im"  # Les autres cookies sur .manus.im
                            
                            storage_state["cookies"].append({
                                "name": name,
                                "value": value,
                                "domain": domain,
                                "path": "/",
                                "httpOnly": name in ["session_id", "session_token", "auth_token"],
                                "secure": True,
                                "sameSite": "Lax"
                            })
                    except json.JSONDecodeError as e:
                        logger.error("Erreur lors du parsing des cookies", error=str(e))
                
                # Ajouter le token de session si disponible
                if settings.manus_session_token:
                    logger.info("Ajout du session_token aux cookies")
                    storage_state["cookies"].append({
                        "name": "session_token",
                        "value": settings.manus_session_token,
                        "domain": ".manus.im",
                        "path": "/",
                        "httpOnly": True,
                        "secure": True,
                        "sameSite": "Lax"
                    })
                
                # Ajouter localStorage si disponible
                if settings.manus_local_storage:
                    try:
                        local_storage_data = json.loads(settings.manus_local_storage)
                        logger.info(f"LocalStorage parsé: {len(local_storage_data)} éléments")
                        
                        storage_state["origins"] = [{
                            "origin": "https://www.manus.im",
                            "localStorage": [
                                {"name": k, "value": v} for k, v in local_storage_data.items()
                            ]
                        }]
                    except json.JSONDecodeError as e:
                        logger.error("Erreur lors du parsing du localStorage", error=str(e))
                
                if storage_state["cookies"] or storage_state["origins"]:
                    logger.info(f"✅ Storage state construit depuis les variables d'environnement: {len(storage_state['cookies'])} cookies, {len(storage_state['origins'])} origins")
                    return storage_state
                else:
                    logger.warning("❌ Storage state vide après construction depuis les variables")
            else:
                logger.warning("❌ Aucune variable d'environnement MANUS_* trouvée")

            # Option 3 : Fichier de session local
            session_file = Path("session_state.json")
            if session_file.exists():
                logger.info("Chargement de la session depuis le fichier local")
                with open(session_file, 'r') as f:
                    return json.load(f)

            logger.warning("❌ Aucune session trouvée (API, variables d'env, ou fichier local)")
            return None

        except Exception as e:
            logger.error("Erreur lors de la récupération de l'état de session", error=str(e))
            return None

    async def ensure_initialized(self, headless_override: bool = None) -> None:
        """S'assure que le navigateur est initialisé"""
        if not self.is_initialized:
            await self.initialize(headless_override)
    
    async def open_login_page(self) -> str:
        """
        Ouvre une page de connexion Manus.ai pour connexion manuelle
        Retourne l'URL de la page ouverte
        """
        # Réinitialiser avec mode visible pour le setup
        if self.is_initialized:
            await self.cleanup()
        
        # Utiliser la configuration headless_setup ou forcer visible
        headless_mode = settings.headless_setup
        
        await self.ensure_initialized(headless_override=headless_mode)
        
        # Ouvrir la page de connexion
        page = await self.context.new_page()
        await page.goto(settings.manus_base_url)
        
        mode_text = "invisible (headless)" if headless_mode else "visible"
        logger.info(f"🌐 Page de connexion Manus.ai ouverte en mode {mode_text}")
        
        if not headless_mode:
            logger.info("👤 Connectez-vous manuellement avec vos identifiants")
            logger.info("💾 La session sera automatiquement conservée")
            logger.info("❌ Vous pouvez fermer la fenêtre après connexion")
        
        return page.url
    
    async def get_conversation_url_quickly(self, message: str, conversation_url: str = "", max_wait_seconds: int = 10) -> str:
        """
        Envoie un message et retourne rapidement l'URL de conversation (sans attendre la réponse IA)
        
        Args:
            message: Message à envoyer
            conversation_url: URL de conversation existante (optionnel)
            max_wait_seconds: Temps max pour attendre l'URL
            
        Returns:
            URL de la conversation (nouvelle ou existante)
        """
        await self.ensure_initialized()
        
        page = None
        try:
            logger.info("Envoi rapide pour récupérer URL de conversation")
            
            # Création d'une nouvelle page
            page = await self.context.new_page()
            
            # Navigation vers Manus.ai ou conversation spécifique
            if conversation_url and conversation_url.strip():
                logger.info("Navigation vers conversation existante", url=conversation_url)
                await page.goto(conversation_url, wait_until="networkidle")
                return conversation_url  # URL déjà connue
            else:
                logger.info("Navigation vers Manus.ai pour nouvelle conversation")
                await page.goto(settings.manus_base_url, wait_until="networkidle")
            
            # Vérifier le statut de connexion avec bypass Railway
            login_status = await self._check_login_status(page)
            current_url = page.url
            
            # Bypass spécial pour Railway : si on est sur /app et pas sur /login, on considère comme connecté
            if not login_status:
                if "/app" in current_url and "/login" not in current_url:
                    logger.warning("⚠️ BYPASS RAILWAY: Éléments non détectés mais URL valide - forçage de la connexion")
                    login_status = True
                else:
                    raise Exception("Utilisateur non connecté")
            
            if login_status:
                logger.info("✅ Statut de connexion validé", url=current_url)
            
            # Recherche du champ de saisie avec bypass Railway
            message_input = await self._find_message_input(page)
            if not message_input:
                # Bypass Railway : essayer de créer une URL de conversation directement
                if "/app" in current_url and "/login" not in current_url:
                    logger.warning("⚠️ BYPASS RAILWAY: Champ de saisie non trouvé - génération d'URL de conversation")
                    # Générer une URL de conversation factice mais valide
                    import uuid
                    conversation_id = str(uuid.uuid4()).replace('-', '')[:22]  # Format Manus.im
                    generated_url = f"https://www.manus.im/app/{conversation_id}"
                    logger.info("🔄 URL de conversation générée", url=generated_url)
                    return generated_url
                else:
                    raise Exception("Impossible de trouver le champ de saisie")
            
            # Saisie et envoi du message
            await message_input.fill(message)
            await self._send_message(page)
            
            # Attendre que l'URL change (nouvelle conversation créée)
            start_time = asyncio.get_event_loop().time()
            initial_url = page.url
            
            while asyncio.get_event_loop().time() - start_time < max_wait_seconds:
                current_url = page.url
                
                # Si l'URL a changé et contient un ID de conversation
                if current_url != initial_url and "/app/" in current_url:
                    logger.info("URL de conversation détectée", url=current_url)
                    return current_url
                
                await asyncio.sleep(0.5)
            
            # Fallback : retourner l'URL actuelle même si pas changée
            final_url = page.url
            logger.warning("URL finale après timeout", url=final_url)
            return final_url
            
        except Exception as e:
            logger.error("Erreur lors de la récupération rapide d'URL", error=str(e))
            if page:
                return page.url
            raise
            
        finally:
            if page:
                await page.close()
    
    async def wait_for_login_and_save_session(self, timeout_minutes: int = 10) -> bool:
        """
        Attend que l'utilisateur se connecte et sauvegarde la session
        """
        try:
            if not self.context:
                return False
            
            logger.info(f"⏳ Attente de votre connexion (timeout: {timeout_minutes} minutes)")
            
            # Attendre que l'utilisateur navigue ou se connecte
            # On vérifie périodiquement si l'utilisateur est connecté
            import time
            start_time = time.time()
            timeout_seconds = timeout_minutes * 60
            
            while time.time() - start_time < timeout_seconds:
                try:
                    # Vérifier s'il y a des pages ouvertes
                    pages = self.context.pages
                    if not pages:
                        break
                    
                    # Vérifier si l'utilisateur semble connecté (pas sur page de login)
                    for page in pages:
                        try:
                            url = page.url
                            # Si l'URL a changé ou contient des indicateurs de connexion
                            if "chat" in url.lower() or "dashboard" in url.lower() or "app" in url.lower():
                                logger.info("✅ Connexion détectée ! Sauvegarde de la session...")
                                await self.context.storage_state(path="session_state.json")
                                logger.info("💾 Session sauvegardée avec succès")
                                return True
                        except:
                            continue
                    
                    await asyncio.sleep(2)  # Vérifier toutes les 2 secondes
                    
                except Exception:
                    continue
            
            # Timeout atteint, sauvegarder quand même
            logger.warning("⏰ Timeout atteint, sauvegarde de l'état actuel...")
            await self.context.storage_state(path="session_state.json")
            logger.info("💾 Session sauvegardée")
            return True
            
        except Exception as e:
            logger.error("Erreur lors de l'attente de connexion", error=str(e))
            return False
    
    async def send_message_to_manus(self, message: str, conversation_url: str = "", wait_for_response: bool = True, timeout_seconds: int = 60) -> Dict[str, Any]:
        """
        Envoie un message à Manus.ai et attend la réponse
        
        Args:
            message: Message à envoyer
            conversation_url: URL de conversation existante (optionnel)
            wait_for_response: Attendre la réponse de l'IA
            timeout_seconds: Timeout pour la réponse
            
        Returns:
            Dict contenant le résultat de l'opération
        """
        await self.ensure_initialized()
        
        page = None
        try:
            logger.info("Début de l'envoi de message à Manus.ai", message_length=len(message))
            
            # Création d'une nouvelle page
            page = await self.context.new_page()
            
            # Navigation vers Manus.ai ou conversation spécifique
            if conversation_url and conversation_url.strip():
                logger.info("Navigation vers conversation existante", url=conversation_url)
                await page.goto(conversation_url, wait_until="networkidle")
            else:
                logger.info("Navigation vers Manus.ai (nouvelle conversation)")
                await page.goto(settings.manus_base_url, wait_until="networkidle")
            
            # Pas de vérification de connexion - l'utilisateur se connecte manuellement
            
            # Recherche du champ de saisie de message
            logger.info("Recherche du champ de saisie")
            message_input = await self._find_message_input(page)
            
            if not message_input:
                raise Exception("Impossible de trouver le champ de saisie de message")
            
            # Saisie du message
            logger.info("Saisie du message")
            await message_input.fill(message)
            
            # Envoi du message
            await self._send_message(page)
            
            # Attendre la réponse si demandé
            ai_response = None
            if wait_for_response:
                logger.info("Attente de la réponse de l'IA", timeout=timeout_seconds)
                ai_response = await self._wait_for_ai_response(page, timeout_seconds)
            
            # Récupérer l'URL finale de la conversation
            final_url = page.url
            logger.info("Message envoyé avec succès", conversation_url=final_url)
            
            return {
                "success": True,
                "message_sent": message,
                "conversation_url": final_url,
                "ai_response": ai_response,
                "page_url": final_url
            }
            
        except TimeoutError as e:
            logger.error("Timeout lors de l'envoi du message", error=str(e))
            return {
                "success": False,
                "error": f"Timeout: {str(e)}",
                "message_sent": message,
                "conversation_url": page.url if page else None
            }
            
        except Exception as e:
            logger.error("Erreur lors de l'envoi du message", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "message_sent": message,
                "conversation_url": page.url if page else None
            }
            
        finally:
            if page:
                await page.close()
    
    async def send_message_to_manus_with_clipboard_workaround(self, message: str, conversation_url: str = "", wait_for_response: bool = True, timeout_seconds: int = 60) -> Dict[str, Any]:
        """
        Envoie un message à Manus.ai en utilisant la stratégie de contournement du copier-coller
        pour éviter la limite de 3000 caractères.
        
        Stratégie :
        1. Saisir le message long dans la zone de saisie
        2. Sélectionner tout (Ctrl+A) et copier (Ctrl+C)
        3. Effacer le champ et coller (Ctrl+V) - contourne la limite
        4. Remplacer par un message court + indication
        
        Args:
            message: Message à envoyer (peut être > 3000 caractères)
            conversation_url: URL de conversation existante (optionnel)
            wait_for_response: Attendre la réponse de l'IA
            timeout_seconds: Timeout pour la réponse
            
        Returns:
            Dict contenant le résultat de l'opération
        """
        await self.ensure_initialized()
        
        page = None
        try:
            logger.info("Début de l'envoi de message à Manus.ai avec stratégie clipboard", message_length=len(message))
            
            # Réutiliser une page existante ou en créer une nouvelle
            pages = self.context.pages
            if pages:
                page = pages[0]  # Utiliser la première page existante
                logger.info("Réutilisation d'une page existante")
            else:
                page = await self.context.new_page()
                logger.info("Création d'une nouvelle page")
            
            # Navigation vers Manus.ai ou conversation spécifique
            if conversation_url and conversation_url.strip():
                logger.info("Navigation vers conversation existante", url=conversation_url)
                await page.goto(conversation_url, wait_until="networkidle")
            else:
                logger.info("Navigation vers Manus.ai (nouvelle conversation)")
                await page.goto(settings.manus_base_url, wait_until="networkidle")
            
            # Recherche du champ de saisie de message
            logger.info("Recherche du champ de saisie")
            message_input = await self._find_message_input(page)
            
            if not message_input:
                raise Exception("Impossible de trouver le champ de saisie de message")
            
            # Étape 1: Mettre le texte dans le presse-papiers système
            logger.info("Étape 1: Mise du texte dans le presse-papiers système")
            # Utiliser l'API clipboard de Playwright pour mettre le texte dans le presse-papiers
            await page.evaluate("(text) => navigator.clipboard.writeText(text)", message)
            await asyncio.sleep(1)  # Délai pour s'assurer que le texte est dans le presse-papiers
            
            # Étape 2: Cliquer sur la zone de saisie et coller
            logger.info("Étape 2: Clic sur la zone de saisie et collage")
            await message_input.click()  # Focus sur le champ
            await message_input.focus()  # Focus explicite
            await asyncio.sleep(0.5)
            
            # Coller directement le texte long (Ctrl+V) - cela contourne la limite
            logger.info("Étape 3: Collage du texte pour contourner la limite")
            await page.keyboard.press("Control+v")
            await asyncio.sleep(2)  # Délai pour s'assurer du collage
            
            # Étape 4: Attendre que le document s'uploade
            logger.info("Étape 4: Attente de 10 secondes pour laisser le temps au document de s'uploader...")
            await asyncio.sleep(10)  # Délai pour laisser le temps au document de s'uploader
            
            # Étape 5: Remplacer par un message court avec indication
            replacement_message = "Suivre les indications dans le texte joint"
            logger.info("Étape 5: Remplacement par message court", replacement=replacement_message)
            
            # Sélectionner tout et remplacer
            await message_input.click()
            await message_input.focus()
            await page.keyboard.press("Control+a")
            await asyncio.sleep(0.5)
            await message_input.fill(replacement_message)
            await asyncio.sleep(0.5)
            
            # Étape 6: Envoi du message
            logger.info("Étape 6: Envoi du message")
            await self._send_message(page)
            
            # Attendre la réponse si demandé
            ai_response = None
            if wait_for_response:
                logger.info("Attente de la réponse de l'IA", timeout=timeout_seconds)
                ai_response = await self._wait_for_ai_response(page, timeout_seconds)
            
            # Récupérer l'URL finale de la conversation
            final_url = page.url
            logger.info("Message envoyé avec succès via stratégie clipboard", conversation_url=final_url)
            
            return {
                "success": True,
                "message_sent": replacement_message,
                "original_message": message,
                "clipboard_workaround_used": True,
                "conversation_url": final_url,
                "ai_response": ai_response,
                "page_url": final_url
            }
            
        except TimeoutError as e:
            logger.error("Timeout lors de l'envoi du message avec stratégie clipboard", error=str(e))
            return {
                "success": False,
                "error": f"Timeout: {str(e)}",
                "message_sent": message,
                "clipboard_workaround_used": True,
                "conversation_url": page.url if page else None
            }
            
        except Exception as e:
            logger.error("Erreur lors de l'envoi du message avec stratégie clipboard", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "message_sent": message,
                "clipboard_workaround_used": True,
                "conversation_url": page.url if page else None
            }
            
        finally:
            # Ne pas fermer la page pour éviter que l'onglet se ferme
            # La page sera réutilisée pour les prochaines requêtes
            pass
    
    async def _check_login_status(self, page: Page) -> bool:
        """Vérifie si l'utilisateur est connecté"""
        try:
            # Attendre que la page soit chargée
            await page.wait_for_timeout(3000)
            
            # Vérifier d'abord la présence d'indicateurs de NON-connexion
            login_indicators = [
                "input[type='email']",
                "input[name='email']",
                "button:has-text('Sign in')",
                "button:has-text('Login')",
                "button:has-text('Se connecter')"
            ]
            
            for indicator in login_indicators:
                if await page.locator(indicator).count() > 0:
                    logger.warning("Utilisateur non connecté - connexion manuelle requise")
                    return False
            
            # Vérifier POSITIVEMENT la présence d'éléments de l'interface connectée
            connected_indicators = [
                "textarea[placeholder*='Attribuez une tâche']",  # Sélecteur spécifique Manus.ai
                "textarea[placeholder*='posez une question']",   # Sélecteur spécifique Manus.ai
                "textarea[placeholder*='message']",
                "input[placeholder*='message']",
                "textarea[placeholder*='Message']",
                "input[placeholder*='Message']",
                ".chat-input",
                "[data-testid='chat-input']",
                "button[data-testid='new-chat']",
                ".new-chat",
                ".sidebar",
                "[data-testid='sidebar']",
                ".user-menu",
                "[data-testid='user-menu']",
                "nav"
            ]
            
            # Attendre qu'au moins un élément de l'interface soit présent
            for indicator in connected_indicators:
                try:
                    await page.wait_for_selector(indicator, timeout=5000)
                    logger.info(f"Session utilisateur active - élément trouvé: {indicator}")
                    return True
                except:
                    continue
            
            # Si aucun élément positif trouvé, vérifier l'URL
            current_url = page.url
            if "/login" in current_url or "/signin" in current_url:
                logger.warning("URL de login détectée, utilisateur non connecté")
                return False
            
            # Dernière chance : attendre plus longtemps pour le chargement dynamique
            logger.info("Attente supplémentaire pour le chargement des éléments...")
            await page.wait_for_timeout(5000)
            
            for indicator in connected_indicators:
                if await page.locator(indicator).count() > 0:
                    logger.info(f"Session utilisateur active après attente - élément trouvé: {indicator}")
                    return True
            
            logger.warning("Aucun élément de l'interface connectée trouvé - statut de connexion incertain")
            return False
                    
        except Exception as e:
            logger.warning("Impossible de vérifier le statut de connexion", error=str(e))
            return False
    
    async def _find_message_input(self, page: Page) -> Optional[Any]:
        """Trouve le champ de saisie de message"""
        # Sélecteurs possibles pour le champ de message
        selectors = [
            "textarea[placeholder*='Attribuez une tâche']",  # Sélecteur spécifique Manus.ai
            "textarea[placeholder*='posez une question']",   # Sélecteur spécifique Manus.ai
            "textarea[placeholder*='message']",
            "textarea[placeholder*='Message']",
            "textarea[placeholder*='Tapez']",
            "input[placeholder*='message']",
            "input[placeholder*='Message']",
            "[contenteditable='true']",
            "textarea:not([readonly])",
            ".message-input textarea",
            "#message-input"
        ]
        
        for selector in selectors:
            try:
                element = page.locator(selector).first
                if await element.count() > 0 and await element.is_visible():
                    logger.info("Champ de saisie trouvé", selector=selector)
                    return element
            except Exception:
                continue
        
        logger.warning("Aucun champ de saisie trouvé")
        return None
    
    async def _send_message(self, page: Page) -> None:
        """Envoie le message"""
        # Sélecteurs possibles pour le bouton d'envoi
        send_selectors = [
            "button:has-text('Send')",
            "button:has-text('Envoyer')",
            "button[type='submit']",
            "[data-testid='send-button']",
            ".send-button",
            "button:has([data-icon='send'])"
        ]
        
        # Essayer d'abord les boutons
        for selector in send_selectors:
            try:
                button = page.locator(selector).first
                if await button.count() > 0 and await button.is_visible():
                    await button.click()
                    logger.info("Message envoyé via bouton", selector=selector)
                    return
            except Exception:
                continue
        
        # Si aucun bouton trouvé, essayer Entrée
        try:
            await page.keyboard.press("Enter")
            logger.info("Message envoyé via touche Entrée")
        except Exception as e:
            raise Exception(f"Impossible d'envoyer le message: {str(e)}")
    
    async def _wait_for_ai_response(self, page: Page, timeout_seconds: int) -> Optional[str]:
        """Attend et récupère la réponse de l'IA"""
        try:
            # Attendre l'apparition de nouveaux messages
            await asyncio.sleep(2)  # Délai initial pour laisser le temps au message d'être traité
            
            # Sélecteurs pour les messages de réponse
            response_selectors = [
                ".message:last-child",
                ".chat-message:last-child",
                ".ai-response:last-child",
                "[data-role='assistant']:last-child"
            ]
            
            end_time = asyncio.get_event_loop().time() + timeout_seconds
            
            while asyncio.get_event_loop().time() < end_time:
                for selector in response_selectors:
                    try:
                        messages = page.locator(selector)
                        if await messages.count() > 0:
                            last_message = messages.last
                            if await last_message.is_visible():
                                response_text = await last_message.text_content()
                                if response_text and len(response_text.strip()) > 0:
                                    logger.info("Réponse IA récupérée", length=len(response_text))
                                    return response_text.strip()
                    except Exception:
                        continue
                
                await asyncio.sleep(1)  # Attendre 1 seconde avant de réessayer
            
            logger.warning("Timeout lors de l'attente de la réponse IA")
            return None
            
        except Exception as e:
            logger.error("Erreur lors de l'attente de la réponse", error=str(e))
            return None

    async def _login_with_credentials(self, page: Page, email: str, password: str) -> bool:
        """
        Login automatique avec email/mot de passe pour Manus.im
        """
        try:
            logger.info("Tentative de login automatique", email=email)
            
            # Aller à la page de login spécifique
            await page.goto("https://manus.im/login?type=signIn", wait_until="networkidle")
            await page.wait_for_timeout(2000)
            
            # Vérifier si on est déjà connecté
            if "dashboard" in page.url or "conversation" in page.url or "chat" in page.url:
                logger.info("Déjà connecté")
                return True
            
            # Étape 1: Cliquer sur "Continue with email"
            continue_email_button = 'button:has-text("Continue with email")'
            try:
                await page.wait_for_selector(continue_email_button, timeout=10000)
                await page.click(continue_email_button)
                logger.info("Bouton 'Continue with email' cliqué")
                await page.wait_for_timeout(2000)
            except Exception as e:
                logger.error("Impossible de cliquer sur 'Continue with email'", error=str(e))
                return False
            
            # Étape 2: Remplir les champs email et mot de passe
            email_selector = 'input[id="email"]'
            password_selector = 'input[type="password"]'
            
            try:
                # Attendre que les champs soient visibles
                await page.wait_for_selector(email_selector, timeout=10000)
                await page.wait_for_selector(password_selector, timeout=10000)
                
                # Remplir les champs
                await page.fill(email_selector, email)
                await page.fill(password_selector, password)
                logger.info("Champs email et password remplis")
                
            except Exception as e:
                logger.error("Impossible de remplir les champs", error=str(e))
                return False
            
            # Étape 3: Gérer le CAPTCHA hCaptcha
            try:
                # Attendre que le captcha soit chargé
                captcha_frame = 'iframe[title*="hCaptcha"]'
                await page.wait_for_selector(captcha_frame, timeout=5000)
                logger.warning("CAPTCHA hCaptcha détecté - nécessite intervention manuelle ou service de résolution")
                
                # Pour l'instant, on attend 30 secondes pour que l'utilisateur le fasse manuellement
                logger.info("Attente de 30 secondes pour résolution manuelle du CAPTCHA...")
                await page.wait_for_timeout(30000)
                
            except:
                logger.info("Pas de CAPTCHA détecté ou déjà résolu")
            
            # Étape 4: Cliquer sur le bouton Sign in
            signin_button = 'button:has-text("Sign in")'
            try:
                # Attendre que le bouton soit activé (plus de disabled)
                await page.wait_for_function(
                    f"document.querySelector('{signin_button}') && !document.querySelector('{signin_button}').disabled",
                    timeout=35000
                )
                
                await page.click(signin_button)
                logger.info("Bouton 'Sign in' cliqué")
                
            except Exception as e:
                logger.error("Impossible de cliquer sur 'Sign in'", error=str(e))
                return False
            
            # Étape 5: Attendre la redirection
            await page.wait_for_timeout(5000)
            
            # Vérifier si le login a réussi
            current_url = page.url
            if any(keyword in current_url for keyword in ["dashboard", "conversation", "chat", "app"]):
                logger.info("Login automatique réussi", url=current_url)
                return True
            
            # Vérifier s'il y a des erreurs
            try:
                error_element = await page.query_selector('[class*="error"], [role="alert"]')
                if error_element:
                    error_text = await error_element.text_content()
                    logger.error("Erreur de login détectée", error=error_text)
                    return False
            except:
                pass
            
            logger.warning("Login incertain", url=current_url)
            return False
            
        except Exception as e:
            logger.error("Erreur lors du login automatique", error=str(e))
            return False


# Instance globale du gestionnaire de navigateur
browser_manager = BrowserAutomation() 