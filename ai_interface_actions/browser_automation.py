"""
Module d'automatisation du navigateur avec Playwright
"""
import asyncio
import structlog
from pathlib import Path
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError

from ai_interface_actions.config import settings

logger = structlog.get_logger(__name__)


class BrowserAutomation:
    """Gestionnaire d'automatisation du navigateur"""
    
    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.is_initialized = False
        
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
                user_data_dir = Path.home() / ".ai-interface-actions" / "browser-data"
                user_data_dir.mkdir(parents=True, exist_ok=True)
                
                # IMPORTANT: launch_persistent_context utilise le profil utilisateur
                self.context = await self.playwright.chromium.launch_persistent_context(
                    user_data_dir=str(user_data_dir),
                    headless=use_headless,
                    **context_options
                )
                # Pas de browser séparé avec launch_persistent_context
                self.browser = None
                logger.info("Contexte persistant créé avec profil utilisateur (PAS navigation privée)")
            else:
                # Mode session temporaire (navigation privée avec sauvegarde)
                self.browser = await self.playwright.chromium.launch(
                    headless=use_headless,
                    args=context_options["args"]
                )
                
                # Préparer les options pour new_context
                new_context_options = {
                    "user_agent": context_options["user_agent"],
                    "locale": context_options["locale"],
                    "timezone_id": context_options["timezone_id"],
                    "storage_state": "session_state.json" if Path("session_state.json").exists() else None
                }
                
                # Ajouter viewport seulement s'il est défini
                if context_options["viewport"] is not None:
                    new_context_options["viewport"] = context_options["viewport"]
                
                self.context = await self.browser.new_context(**new_context_options)
                logger.info("Contexte temporaire créé (navigation privée avec sauvegarde)")
            
            # Configuration des timeouts
            self.context.set_default_timeout(settings.page_timeout)
            
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
            
            # Vérifier le statut de connexion
            if not await self._check_login_status(page):
                raise Exception("Utilisateur non connecté")
            
            # Recherche du champ de saisie
            message_input = await self._find_message_input(page)
            if not message_input:
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
            
            # Vérifier le statut de connexion
            if not await self._check_login_status(page):
                raise Exception(
                    "Utilisateur non connecté. Veuillez vous connecter manuellement à Manus.ai dans votre navigateur. "
                    "La session durera 30 jours."
                )
            
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
    
    async def _check_login_status(self, page: Page) -> bool:
        """Vérifie si l'utilisateur est connecté"""
        try:
            # Vérifier la présence d'indicateurs de connexion
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
            
            logger.info("Session utilisateur active")
            return True
                    
        except Exception as e:
            logger.warning("Impossible de vérifier le statut de connexion", error=str(e))
            return False
    
    async def _find_message_input(self, page: Page) -> Optional[Any]:
        """Trouve le champ de saisie de message"""
        # Sélecteurs possibles pour le champ de message
        selectors = [
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


# Instance globale du gestionnaire de navigateur
browser_manager = BrowserAutomation() 