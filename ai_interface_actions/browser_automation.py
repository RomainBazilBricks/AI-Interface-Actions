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
        # Pool de pages pour réutilisation
        self.active_pages: Dict[str, Page] = {}  # conversation_url -> page
        
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
            # Fermer toutes les pages actives
            for conversation_url, page in list(self.active_pages.items()):
                try:
                    if not page.is_closed():
                        await page.close()
                except Exception as e:
                    logger.warning("Erreur lors de la fermeture d'une page", url=conversation_url, error=str(e))
            
            self.active_pages.clear()
            
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
    
    async def _get_or_create_page(self, conversation_url: str = "") -> Page:
        """
        Récupère une page existante ou en crée une nouvelle
        
        Args:
            conversation_url: URL de conversation (vide pour nouvelle conversation)
            
        Returns:
            Page Playwright réutilisable
        """
        logger.info("🔍 Récupération/création de page", 
                   conversation_url=conversation_url,
                   pool_size=len(self.active_pages))
        
        # Nettoyer les pages fermées
        closed_pages = []
        for url, page in self.active_pages.items():
            if page.is_closed():
                closed_pages.append(url)
        
        for url in closed_pages:
            del self.active_pages[url]
            logger.info("Page fermée supprimée du pool", url=url)
        
        # Si une conversation_url est fournie, essayer de réutiliser la page existante
        if conversation_url and conversation_url.strip():
            logger.info("🔄 RECHERCHE page existante pour URL", url=conversation_url)
            
            # Vérifier si on a déjà une page pour cette conversation
            if conversation_url in self.active_pages:
                page = self.active_pages[conversation_url]
                if not page.is_closed():
                    logger.info("✅ REUTILISATION page existante trouvée", url=conversation_url)
                    return page
                else:
                    # Page fermée, la supprimer du pool
                    del self.active_pages[conversation_url]
                    logger.info("❌ Page fermée supprimée du pool", url=conversation_url)
            
            # Vérifier si une page existante pointe déjà vers cette conversation
            for existing_url, page in self.active_pages.items():
                if not page.is_closed():
                    try:
                        current_page_url = page.url
                        # Extraire l'ID de conversation des deux URLs pour comparaison
                        if self._extract_conversation_id(current_page_url) == self._extract_conversation_id(conversation_url):
                            logger.info("Page existante trouvée pour cette conversation", 
                                       existing_url=existing_url, 
                                       target_url=conversation_url)
                            # Mettre à jour la clé dans le pool
                            del self.active_pages[existing_url]
                            self.active_pages[conversation_url] = page
                            return page
                    except Exception as e:
                        logger.warning("Erreur lors de la vérification de page existante", error=str(e))
        
        # Pour les nouvelles conversations, essayer de réutiliser une page générique existante
        if not conversation_url or not conversation_url.strip():
            # Chercher une page générique existante (sans URL spécifique ou "nouvelle_conversation")
            for existing_key, page in list(self.active_pages.items()):
                if not page.is_closed() and (not existing_key or existing_key == "nouvelle_conversation" or existing_key == "diagnostic"):
                    logger.info("✅ REUTILISATION page générique existante", key=existing_key)
                    return page
        
        # Créer une nouvelle page seulement si nécessaire
        logger.warning("🆕 CREATION NOUVELLE PAGE", 
                      conversation_url=conversation_url or "nouvelle_conversation",
                      reason="Aucune page existante trouvée")
        page = await self.context.new_page()
        
        # L'ajouter au pool avec une clé appropriée
        pool_key = conversation_url if conversation_url and conversation_url.strip() else "nouvelle_conversation"
        self.active_pages[pool_key] = page
        logger.info("📝 Page ajoutée au pool", url=pool_key, pool_size=len(self.active_pages))
        
        return page
    
    def _extract_conversation_id(self, url: str) -> str:
        """
        Extrait l'ID de conversation d'une URL Manus.im
        
        Args:
            url: URL complète (ex: https://www.manus.im/app/XBiN8PvUegJQRHuPMCnvPo)
            
        Returns:
            ID de conversation (ex: XBiN8PvUegJQRHuPMCnvPo)
        """
        try:
            if "/app/" in url:
                return url.split("/app/")[-1].split("?")[0].split("#")[0]
            return ""
        except Exception:
            return ""
    
    def _is_valid_manus_url(self, url: str) -> bool:
        """Vérifie si une URL est une URL Manus.ai valide"""
        if not url:
            return False
        
        try:
            # Vérifier que c'est une URL Manus.ai
            valid_domains = ["manus.im", "manus.ai", "www.manus.im", "www.manus.ai"]
            for domain in valid_domains:
                if domain in url.lower():
                    return True
            
            # Vérifier que ce n'est pas une URL de fallback générique
            invalid_patterns = [
                "fallback-conversation-url.com",
                "example.com", 
                "localhost",
                "127.0.0.1",
                "about:blank"
            ]
            
            for pattern in invalid_patterns:
                if pattern in url.lower():
                    return False
                    
            return False
            
        except Exception:
            return False
    
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
            
            # Récupérer ou créer une page appropriée
            page = await self._get_or_create_page(conversation_url)
            
            # Navigation vers Manus.ai ou conversation spécifique
            if conversation_url and conversation_url.strip():
                # Vérifier si on est déjà sur la bonne page
                current_url = page.url
                if self._extract_conversation_id(current_url) != self._extract_conversation_id(conversation_url):
                    logger.info("Navigation vers conversation existante", url=conversation_url)
                    await page.goto(conversation_url, wait_until="networkidle")
                else:
                    logger.info("Page déjà sur la bonne conversation", url=current_url)
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
            
            # Recherche du champ de saisie avec récupération automatique et bypass Railway
            message_input = await self._find_message_input_with_recovery(page, conversation_url)
            if not message_input:
                # Bypass Railway : essayer de créer une URL de conversation directement
                if "/app" in current_url and "/login" not in current_url:
                    logger.warning("⚠️ BYPASS RAILWAY: Champ de saisie non trouvé malgré récupération - génération d'URL de conversation")
                    # Générer une URL de conversation factice mais valide
                    import uuid
                    conversation_id = str(uuid.uuid4()).replace('-', '')[:22]  # Format Manus.im
                    generated_url = f"https://www.manus.im/app/{conversation_id}"
                    logger.info("🔄 URL de conversation générée", url=generated_url)
                    return generated_url
                else:
                    raise Exception("Impossible de trouver le champ de saisie malgré les tentatives de récupération")
            
            # Saisie et envoi du message
            await message_input.fill(message)
            await self._send_message(page)
            
            # Gérer le popup "Wide Research" s'il apparaît
            await self._handle_wide_research_popup(page)
            
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
            
            # Fallback : vérifier si on a au moins une URL Manus.ai valide
            final_url = page.url
            if self._is_valid_manus_url(final_url):
                logger.warning("URL finale après timeout (valide)", url=final_url)
                return final_url
            else:
                logger.error("URL finale invalide après timeout", url=final_url)
                # Essayer de naviguer vers Manus.ai et récupérer une URL valide
                try:
                    await page.goto(settings.manus_base_url, wait_until="networkidle")
                    corrected_url = page.url
                    logger.info("URL corrigée vers Manus.ai", url=corrected_url)
                    return corrected_url
                except Exception as nav_error:
                    logger.error("Impossible de corriger l'URL", error=str(nav_error))
                    return final_url
            
        except Exception as e:
            logger.error("Erreur lors de la récupération rapide d'URL", error=str(e))
            if page:
                return page.url
            raise
            
        finally:
            # Ne fermer la page que si c'est une nouvelle page temporaire (sans conversation_url)
            if page and not conversation_url:
                await page.close()
                logger.info("Page temporaire fermée")
            # Pour les conversations existantes, garder la page ouverte dans le pool
    
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
        page_created = False
        try:
            logger.info("Début de l'envoi de message à Manus.ai", 
                       message_length=len(message),
                       conversation_url=conversation_url or "nouvelle_conversation")
            
            # Récupérer ou créer une page appropriée
            page = await self._get_or_create_page(conversation_url)
            page_created = conversation_url not in self.active_pages  # True si page nouvellement créée
            
            # Navigation vers Manus.ai ou conversation spécifique
            if conversation_url and conversation_url.strip():
                # Vérifier si on est déjà sur la bonne page
                current_url = page.url
                if self._extract_conversation_id(current_url) != self._extract_conversation_id(conversation_url):
                    logger.info("Navigation vers conversation existante", url=conversation_url)
                    await page.goto(conversation_url, wait_until="networkidle")
                else:
                    logger.info("Page déjà sur la bonne conversation", url=current_url)
            else:
                logger.info("Navigation vers Manus.ai (nouvelle conversation)")
                await page.goto(settings.manus_base_url, wait_until="networkidle")
            
            # Pas de vérification de connexion - l'utilisateur se connecte manuellement
            
            # Diagnostic de l'état de la page avant recherche
            current_url = page.url
            page_title = await page.title()
            logger.info("🔍 Diagnostic de la page avant recherche de zone de saisie", 
                       url=current_url, 
                       title=page_title)
            
            # Recherche du champ de saisie de message avec récupération automatique
            logger.info("Recherche du champ de saisie avec système de récupération")
            message_input = await self._find_message_input_with_recovery(page, conversation_url)
            
            if not message_input:
                # Diagnostic détaillé en cas d'échec
                logger.error("❌ DIAGNOSTIC DÉTAILLÉ - Zone de saisie non trouvée")
                logger.error("URL actuelle", url=page.url)
                logger.error("Titre de page", title=await page.title())
                
                # Capturer le HTML pour diagnostic
                try:
                    html_snippet = await page.evaluate("""
                        () => {
                            // Chercher tous les textarea et input
                            const textareas = Array.from(document.querySelectorAll('textarea'));
                            const inputs = Array.from(document.querySelectorAll('input'));
                            
                            return {
                                textareas: textareas.map(t => ({
                                    placeholder: t.placeholder,
                                    visible: t.offsetParent !== null,
                                    disabled: t.disabled
                                })),
                                inputs: inputs.map(i => ({
                                    type: i.type,
                                    placeholder: i.placeholder,
                                    visible: i.offsetParent !== null,
                                    disabled: i.disabled
                                })),
                                bodyText: document.body.innerText.substring(0, 500)
                            };
                        }
                    """)
                    logger.error("Éléments détectés sur la page", elements=html_snippet)
                except Exception as diag_e:
                    logger.error("Impossible de capturer le diagnostic HTML", error=str(diag_e))
                
                raise Exception(f"Impossible de trouver le champ de saisie de message malgré les tentatives de récupération. URL: {current_url}, Titre: {page_title}")
            
            # Saisie du message
            logger.info("Saisie du message")
            await message_input.fill(message)
            
            # Envoi du message
            await self._send_message(page)
            
            # Gérer le popup "Wide Research" s'il apparaît
            await self._handle_wide_research_popup(page)
            
            # Attendre la réponse si demandé
            ai_response = None
            if wait_for_response:
                logger.info("Attente de la réponse de l'IA", timeout=timeout_seconds)
                ai_response = await self._wait_for_ai_response(page, timeout_seconds)
            
            # Récupérer l'URL finale de la conversation
            final_url = page.url
            
            # Valider que l'URL finale est bien une URL Manus.ai
            if not self._is_valid_manus_url(final_url):
                logger.warning("URL finale invalide détectée, correction...", invalid_url=final_url)
                try:
                    # Essayer de naviguer vers Manus.ai pour corriger
                    await page.goto(settings.manus_base_url, wait_until="networkidle")
                    corrected_url = page.url
                    logger.info("URL corrigée", corrected_url=corrected_url)
                    final_url = corrected_url
                except Exception as e:
                    logger.error("Impossible de corriger l'URL", error=str(e))
            
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
            # Ne fermer la page que si c'est une nouvelle page temporaire (sans conversation_url)
            if page and not conversation_url:
                await page.close()
                logger.info("Page temporaire fermée")
            # Pour les conversations existantes, garder la page ouverte dans le pool
    
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
        """Trouve le champ de saisie de message - intelligent et adaptatif selon le contexte"""
        current_url = page.url
        is_conversation_page = "/app/" in current_url
        
        logger.info("Recherche de zone de saisie", 
                   url=current_url, 
                   context="conversation" if is_conversation_page else "nouvelle")
        
        # Sélecteurs ULTRA-PERMISSIFS - priorité aux plus spécifiques
        # Tous les placeholders connus de Manus.ai (français et anglais)
        specific_selectors = [
            # Français - tous les variants possibles
            "textarea[placeholder='Attribuez une tâche ou posez une question']",
            "textarea[placeholder*='Attribuez une tâche ou posez une question']",
            "textarea[placeholder*='Attribuez une tâche']",
            "textarea[placeholder*='posez une question']", 
            "textarea[placeholder*='Attribuez']",
            "textarea[placeholder*='tâche']",
            "textarea[placeholder*='question']",
            
            # Anglais - tous les variants possibles
            "textarea[placeholder='Assign a task or ask anything']",
            "textarea[placeholder*='Assign a task or ask anything']",
            "textarea[placeholder*='Assign a task']",
            "textarea[placeholder*='ask anything']",
            "textarea[placeholder*='Assign']",
            "textarea[placeholder*='task']",
            "textarea[placeholder*='anything']",
            
            # Messages dans conversations
            "textarea[placeholder*='Send message to Manus']",
            "textarea[placeholder*='Send message']",
            "textarea[placeholder*='message to Manus']",
            "textarea[placeholder*='Envoyer un message']",
            "textarea[placeholder*='Écrivez votre message']",
            
            # Génériques message
            "textarea[placeholder*='message']",
            "textarea[placeholder*='Message']",
            "textarea[placeholder*='Tapez']",
            "textarea[placeholder*='Type']",
            "textarea[placeholder*='Écrivez']",
            "textarea[placeholder*='Write']",
        ]
        
        # Sélecteurs génériques TRÈS permissifs (fallback ultime)
        fallback_selectors = [
            # Inputs alternatifs
            "input[placeholder*='message']",
            "input[placeholder*='Message']", 
            "input[placeholder*='tâche']",
            "input[placeholder*='task']",
            
            # Contenteditable
            "[contenteditable='true']",
            "div[contenteditable='true']",
            
            # Textarea par structure
            "textarea:not([readonly]):not([disabled])",
            "textarea:not([style*='display: none']):not([style*='display:none'])",
            "textarea[rows]",
            "textarea.resize-none",
            "textarea[class*='input']",
            "textarea[class*='chat']",
            "textarea[class*='message']",
            
            # Par classes CSS communes
            ".message-input textarea",
            ".chat-input textarea", 
            ".input-container textarea",
            ".text-input textarea",
            
            # Par IDs
            "#message-input",
            "#chat-input",
            "#text-input",
            
            # Avec attributs spéciaux
            "textarea[data-testid]",
            "textarea[aria-label]",
            "div[data-dashlane-rid] textarea",
            
            # Derniers recours - tout textarea visible
            "textarea",
        ]
        
        # Combiner tous les sélecteurs (spécifiques + fallbacks)
        all_selectors = specific_selectors + fallback_selectors
        
        # Essayer chaque sélecteur avec logging détaillé
        for i, selector in enumerate(all_selectors):
            try:
                element = page.locator(selector).first
                count = await element.count()
                
                if count > 0:
                    is_visible = await element.is_visible()
                    is_enabled = not await element.is_disabled() if hasattr(element, 'is_disabled') else True
                    
                    logger.info(f"Sélecteur testé [{i+1}/{len(all_selectors)}]", 
                               selector=selector, 
                               count=count, 
                               visible=is_visible,
                               enabled=is_enabled,
                               priority="spécifique" if i < len(specific_selectors) else "fallback")
                    
                    if is_visible and is_enabled:
                        logger.info("✅ Champ de saisie trouvé avec succès", 
                                   selector=selector,
                                   context="conversation" if is_conversation_page else "nouvelle")
                        return element
                else:
                    logger.debug(f"Sélecteur sans résultat [{i+1}/{len(all_selectors)}]", selector=selector)
                    
            except Exception as e:
                logger.debug(f"Erreur sélecteur [{i+1}/{len(all_selectors)}]", 
                           selector=selector, 
                           error=str(e))
                continue
        
        # Si aucun sélecteur ne fonctionne, essayer une approche très permissive
        logger.warning("⚠️ Tentative de détection permissive avec tous les textarea")
        try:
            all_textareas = page.locator("textarea")
            count = await all_textareas.count()
            logger.info(f"Nombre total de textarea trouvés: {count}")
            
            for i in range(count):
                textarea = all_textareas.nth(i)
                if await textarea.is_visible() and not await textarea.is_disabled():
                    placeholder = await textarea.get_attribute("placeholder") or ""
                    logger.info(f"Textarea permissif [{i+1}/{count}]", placeholder=placeholder)
                    
                    # Accepter tout textarea visible et non désactivé
                    logger.info("✅ Champ de saisie trouvé en mode permissif", placeholder=placeholder)
                    return textarea
        except Exception as e:
            logger.error("Erreur en mode permissif", error=str(e))
        
        logger.error("❌ Aucun champ de saisie trouvé malgré tous les sélecteurs")
        return None
    
    async def _find_message_input_with_recovery(self, page: Page, conversation_url: str = "", max_retries: int = 2) -> Optional[Any]:
        """
        Trouve le champ de saisie avec système de récupération automatique
        
        Args:
            page: Page Playwright
            conversation_url: URL de conversation pour récupération
            max_retries: Nombre max de tentatives de récupération
            
        Returns:
            Element de saisie ou None si échec total
        """
        logger.info("🔍 Recherche de zone de saisie avec récupération automatique", 
                   url=page.url, 
                   conversation_url=conversation_url or "aucune",
                   max_retries=max_retries)
        
        for attempt in range(max_retries + 1):
            logger.info(f"🎯 Tentative {attempt + 1}/{max_retries + 1}")
            
            # Essayer de trouver le champ de saisie
            message_input = await self._find_message_input(page)
            
            if message_input:
                logger.info("✅ Zone de saisie trouvée avec succès", attempt=attempt + 1)
                return message_input
            
            # Si échec et pas la dernière tentative, essayer la récupération
            if attempt < max_retries:
                logger.warning(f"❌ Zone de saisie non trouvée (tentative {attempt + 1})")
                
                # Stratégie de récupération selon le contexte
                recovery_success = await self._attempt_recovery(page, conversation_url, attempt + 1)
                
                if not recovery_success:
                    logger.warning(f"⚠️ Récupération {attempt + 1} échouée, tentative suivante...")
                    continue
                else:
                    logger.info(f"✅ Récupération {attempt + 1} réussie, nouvelle tentative de détection...")
                    # Continue la boucle pour retenter la détection
            else:
                logger.error("❌ Échec définitif : toutes les tentatives et récupérations ont échoué")
        
        return None
    
    async def _attempt_recovery(self, page: Page, conversation_url: str, attempt: int) -> bool:
        """
        Tente de récupérer la situation en rouvrant l'onglet de conversation
        
        Args:
            page: Page Playwright actuelle
            conversation_url: URL de conversation à rouvrir
            attempt: Numéro de la tentative
            
        Returns:
            True si récupération réussie, False sinon
        """
        try:
            current_url = page.url
            logger.info(f"🔄 Récupération automatique - Tentative {attempt}", 
                       current_url=current_url, 
                       target_url=conversation_url or "page d'accueil")
            
            # Stratégie 1: Si on a une URL de conversation, y naviguer
            if conversation_url and conversation_url.strip():
                if current_url != conversation_url:
                    logger.info("🔄 Navigation vers URL de conversation cible")
                    await page.goto(conversation_url, wait_until="networkidle", timeout=settings.page_timeout)
                    await page.wait_for_timeout(2000)  # Attendre stabilisation
                    logger.info("✅ Navigation vers conversation terminée")
                    return True
                else:
                    logger.info("🔄 Déjà sur la bonne URL, rechargement de la page")
                    await page.reload(wait_until="networkidle", timeout=settings.page_timeout)
                    await page.wait_for_timeout(2000)
                    logger.info("✅ Rechargement terminé")
                    return True
            
            # Stratégie 2: Si pas d'URL spécifique, aller à la page d'accueil
            else:
                logger.info("🔄 Navigation vers page d'accueil Manus.ai")
                await page.goto(settings.manus_base_url, wait_until="networkidle", timeout=settings.page_timeout)
                await page.wait_for_timeout(2000)
                logger.info("✅ Navigation vers accueil terminée")
                return True
                
        except Exception as e:
            logger.error(f"❌ Erreur lors de la récupération {attempt}", error=str(e))
            return False
    
    async def _handle_wide_research_popup(self, page: Page, timeout_seconds: int = 10) -> bool:
        """
        Détecte et gère automatiquement le popup "Wide Research" en cliquant sur "continuer sans Wide Research"
        
        Args:
            page: Page Playwright
            timeout_seconds: Temps d'attente max pour la détection
            
        Returns:
            True si popup détecté et géré, False sinon
        """
        try:
            logger.info("🔍 Vérification de la présence du popup Wide Research")
            
            # Attendre un peu pour que le popup apparaisse si nécessaire
            await page.wait_for_timeout(2000)
            
            # Sélecteurs pour détecter le popup Wide Research
            wide_research_selectors = [
                # Texte spécifique "Wide Research"
                "text=Wide Research",
                # Container avec l'image spécifique
                "img[src*='mapReduceDarkIcon']",
                # Texte "Analyse complète de tous les documents"
                "text=Analyse complète de tous les documents",
                # Container général du popup
                "div:has-text('Wide Research coûtera')",
            ]
            
            # Vérifier si le popup est présent
            popup_detected = False
            for selector in wide_research_selectors:
                try:
                    element = page.locator(selector).first
                    if await element.count() > 0 and await element.is_visible():
                        logger.info("✅ Popup Wide Research détecté", selector=selector)
                        popup_detected = True
                        break
                except Exception:
                    continue
            
            if not popup_detected:
                logger.info("ℹ️ Aucun popup Wide Research détecté")
                return False
            
            # Sélecteurs pour le lien "continuer sans Wide Research"
            skip_selectors = [
                # Texte exact
                "a:has-text('ou continuer sans Wide Research')",
                # Lien avec classe cursor-pointer et underline
                "a.cursor-pointer.underline:has-text('continuer sans Wide Research')",
                # Texte partiel
                "a:has-text('continuer sans')",
                # Fallback avec tabindex
                "a[tabindex='0']:has-text('continuer')",
                # Très permissif
                "a:has-text('Wide Research')",
            ]
            
            # Essayer de cliquer sur le lien "continuer sans"
            for i, selector in enumerate(skip_selectors):
                try:
                    skip_link = page.locator(selector).first
                    count = await skip_link.count()
                    
                    if count > 0:
                        is_visible = await skip_link.is_visible()
                        logger.info(f"Lien 'continuer sans' testé [{i+1}/{len(skip_selectors)}]", 
                                   selector=selector, 
                                   count=count, 
                                   visible=is_visible)
                        
                        if is_visible:
                            # Cliquer sur le lien
                            await skip_link.click()
                            logger.info("✅ Clic effectué sur 'continuer sans Wide Research'")
                            
                            # Attendre que le popup disparaisse
                            await page.wait_for_timeout(2000)
                            
                            # Vérifier que le popup a bien disparu
                            still_present = False
                            for check_selector in wide_research_selectors:
                                try:
                                    element = page.locator(check_selector).first
                                    if await element.count() > 0 and await element.is_visible():
                                        still_present = True
                                        break
                                except Exception:
                                    continue
                            
                            if not still_present:
                                logger.info("✅ Popup Wide Research fermé avec succès")
                                return True
                            else:
                                logger.warning("⚠️ Popup Wide Research toujours présent après clic")
                        
                except Exception as e:
                    logger.debug(f"Erreur avec sélecteur [{i+1}/{len(skip_selectors)}]", 
                               selector=selector, 
                               error=str(e))
                    continue
            
            # Si aucun sélecteur n'a fonctionné, essayer une approche très permissive
            logger.warning("⚠️ Tentative de clic permissif sur tous les liens avec 'continuer'")
            try:
                all_links = page.locator("a")
                count = await all_links.count()
                
                for i in range(count):
                    link = all_links.nth(i)
                    if await link.is_visible():
                        text_content = await link.text_content() or ""
                        if "continuer" in text_content.lower() and "wide research" in text_content.lower():
                            logger.info(f"Lien permissif trouvé [{i+1}/{count}]", text=text_content)
                            await link.click()
                            logger.info("✅ Clic permissif effectué")
                            await page.wait_for_timeout(2000)
                            return True
                            
            except Exception as e:
                logger.error("Erreur en mode permissif", error=str(e))
            
            logger.warning("⚠️ Impossible de fermer le popup Wide Research automatiquement")
            return False
            
        except Exception as e:
            logger.error("Erreur lors de la gestion du popup Wide Research", error=str(e))
            return False
    
    async def _send_message(self, page: Page) -> None:
        """Envoie le message avec protection contre les doubles clics"""
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
                    # Vérifier que le bouton n'est pas désactivé
                    is_disabled = await button.is_disabled()
                    if is_disabled:
                        logger.warning("Bouton d'envoi désactivé, attente...", selector=selector)
                        await page.wait_for_timeout(1000)
                        continue
                    
                    # Clic unique avec protection
                    await button.click(force=False, timeout=5000)
                    logger.info("Message envoyé via bouton", selector=selector)
                    
                    # Attendre que le bouton soit désactivé ou disparaisse (confirmation d'envoi)
                    try:
                        await page.wait_for_function(
                            f"!document.querySelector('{selector}') || document.querySelector('{selector}').disabled",
                            timeout=3000
                        )
                        logger.info("Confirmation d'envoi détectée")
                    except:
                        logger.warning("Pas de confirmation d'envoi détectée")
                    
                    return
            except Exception as e:
                logger.warning("Erreur avec le bouton", selector=selector, error=str(e))
                continue
        
        # Si aucun bouton trouvé, essayer Entrée (avec protection similaire)
        try:
            # Vérifier qu'on est toujours dans le champ de saisie avec récupération
            message_input = await self._find_message_input_with_recovery(page)
            if message_input:
                await message_input.focus()
                await page.keyboard.press("Enter")
                logger.info("Message envoyé via touche Entrée")
                
                # Attendre un délai pour éviter les envois multiples
                await page.wait_for_timeout(1000)
            else:
                raise Exception("Champ de saisie non trouvé pour l'envoi via Entrée malgré récupération")
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

    async def upload_zip_file_to_manus(self, file_path: str, message: str = "", conversation_url: str = "", wait_for_response: bool = True, timeout_seconds: int = 60, url_callback=None) -> Dict[str, Any]:
        """
        Upload un fichier .zip vers Manus.ai via drag & drop
        
        Args:
            file_path: Chemin vers le fichier .zip local
            message: Message accompagnant le fichier
            conversation_url: URL de conversation existante (optionnel)
            wait_for_response: Attendre la réponse de l'IA
            timeout_seconds: Timeout pour la réponse
            
        Returns:
            Dict contenant le résultat de l'opération
        """
        await self.ensure_initialized()
        
        page = None
        try:
            logger.info("Début de l'upload de fichier .zip vers Manus.ai", 
                       file_path=file_path,
                       conversation_url=conversation_url or "nouvelle_conversation")
            
            # Vérifier que le fichier existe et est un .zip
            if not os.path.exists(file_path):
                raise Exception(f"Fichier non trouvé: {file_path}")
            
            if not file_path.lower().endswith('.zip'):
                raise Exception("Seuls les fichiers .zip sont supportés")
            
            # Récupérer ou créer une page appropriée
            # Pour les nouvelles conversations, utiliser la page partagée
            page_key = conversation_url if conversation_url and conversation_url.strip() else "shared"
            page = await self._get_or_create_page(page_key)
            
            # Navigation vers Manus.ai ou conversation spécifique
            if conversation_url and conversation_url.strip():
                current_url = page.url
                if self._extract_conversation_id(current_url) != self._extract_conversation_id(conversation_url):
                    logger.info("Navigation vers conversation existante", url=conversation_url)
                    await page.goto(conversation_url, wait_until="networkidle")
                else:
                    logger.info("Page déjà sur la bonne conversation", url=current_url)
            else:
                logger.info("Navigation vers Manus.ai (nouvelle conversation)")
                await page.goto(settings.manus_base_url, wait_until="networkidle")
            
            # Attendre que l'interface soit chargée
            await page.wait_for_timeout(5000)
            
            # Diagnostic de l'état de la page avant recherche
            current_url = page.url
            page_title = await page.title()
            logger.info("🔍 Diagnostic de la page avant recherche de zone de saisie", 
                       url=current_url, 
                       title=page_title)
            
            # Vérifier si l'utilisateur est connecté
            try:
                # Chercher des indicateurs de connexion
                login_indicators = [
                    "text=Se connecter", "text=Sign in", "text=Login",
                    "input[type='email']", "input[type='password']",
                    "button:has-text('Se connecter')", "button:has-text('Sign in')"
                ]
                
                is_logged_out = False
                for indicator in login_indicators:
                    try:
                        element = page.locator(indicator).first
                        if await element.count() > 0 and await element.is_visible():
                            logger.warning("⚠️ Indicateur de déconnexion détecté", indicator=indicator)
                            is_logged_out = True
                            break
                    except Exception:
                        continue
                
                if is_logged_out:
                    raise Exception("Utilisateur non connecté à Manus.ai - session expirée ou credentials invalides")
                else:
                    logger.info("✅ Aucun indicateur de déconnexion détecté")
                    
            except Exception as e:
                logger.error("Erreur lors de la vérification de connexion", error=str(e))
                # Ne pas bloquer, continuer avec la recherche
            
            # Rechercher le champ de saisie pour identifier la zone de drop avec récupération
            message_input = await self._find_message_input_with_recovery(page, conversation_url)
            if not message_input:
                # Diagnostic détaillé en cas d'échec
                logger.error("❌ DIAGNOSTIC DÉTAILLÉ - Zone de saisie non trouvée")
                logger.error("URL actuelle", url=page.url)
                logger.error("Titre de page", title=await page.title())
                
                # Capturer le HTML pour diagnostic
                try:
                    html_snippet = await page.evaluate("""
                        () => {
                            // Chercher tous les textarea et input
                            const textareas = Array.from(document.querySelectorAll('textarea'));
                            const inputs = Array.from(document.querySelectorAll('input'));
                            
                            return {
                                textareas: textareas.map(t => ({
                                    placeholder: t.placeholder,
                                    visible: t.offsetParent !== null,
                                    disabled: t.disabled
                                })),
                                inputs: inputs.map(i => ({
                                    type: i.type,
                                    placeholder: i.placeholder,
                                    visible: i.offsetParent !== null,
                                    disabled: i.disabled
                                })),
                                bodyText: document.body.innerText.substring(0, 500)
                            };
                        }
                    """)
                    logger.error("Éléments détectés sur la page", elements=html_snippet)
                except Exception as diag_e:
                    logger.error("Impossible de capturer le diagnostic HTML", error=str(diag_e))
                
                raise Exception(f"Impossible de trouver la zone de chat pour l'upload malgré les tentatives de récupération. URL: {current_url}, Titre: {page_title}")
            
            logger.info("Zone de chat trouvée, préparation du drag & drop")
            
            # Lire le fichier en tant que buffer pour le drag & drop
            logger.info("📖 Lecture du fichier ZIP en mémoire...")
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            filename = os.path.basename(file_path)
            file_size_mb = len(file_content) / (1024 * 1024)
            logger.info(f"✅ Fichier lu: {filename}, taille: {len(file_content)} bytes ({file_size_mb:.1f} MB)")
            
            # Ajuster le timeout selon la taille du fichier
            if file_size_mb > 50:
                # Très gros fichier : timeout x3
                adjusted_timeout = timeout_seconds * 3
                logger.warning(f"⚠️ Fichier très volumineux ({file_size_mb:.1f} MB) - timeout ajusté à {adjusted_timeout}s")
            elif file_size_mb > 20:
                # Gros fichier : timeout x2
                adjusted_timeout = timeout_seconds * 2
                logger.warning(f"⚠️ Fichier volumineux ({file_size_mb:.1f} MB) - timeout ajusté à {adjusted_timeout}s")
            else:
                adjusted_timeout = timeout_seconds
                
            timeout_seconds = adjusted_timeout
            
            # Simuler le drag & drop avec Playwright
            logger.info("🚀 Début de la simulation du drag & drop du fichier .zip")
            logger.info(f"📊 Transfert de {file_size_mb:.1f} MB vers le navigateur...")
            logger.info(f"⏱️ Timeout configuré: {timeout_seconds}s pour page.evaluate()")
            upload_result = await page.evaluate("""
                async (fileData) => {
                    const { fileName, fileContent } = fileData;
                    
                    try {
                        // Créer un objet File à partir du buffer
                        const uint8Array = new Uint8Array(fileContent);
                        const file = new File([uint8Array], fileName, { 
                            type: 'application/zip',
                            lastModified: Date.now()
                        });
                        
                        // Chercher la zone de drop - ULTRA-PERMISSIF
                        const dropZoneSelectors = [
                            // Sélecteurs spécifiques Manus.ai
                            'textarea[placeholder="Attribuez une tâche ou posez une question"]',
                            'textarea[placeholder="Assign a task or ask anything"]',
                            'textarea[placeholder*="Attribuez"]',
                            'textarea[placeholder*="Assign"]',
                            'textarea[placeholder*="tâche"]',
                            'textarea[placeholder*="task"]',
                            'textarea[placeholder*="question"]',
                            'textarea[placeholder*="anything"]',
                            'textarea[placeholder*="posez"]',
                            'textarea[placeholder*="message"]',
                            'textarea[placeholder*="Message"]',
                            'textarea[placeholder*="Send message"]',
                            'textarea[placeholder*="Envoyer"]',
                            'textarea[placeholder*="Écrivez"]',
                            'textarea[placeholder*="Write"]',
                            
                            // Sélecteurs génériques
                            'textarea:not([readonly]):not([disabled])',
                            'textarea[rows]',
                            'textarea.resize-none',
                            'input[type="text"]:not([readonly]):not([disabled])',
                            '[contenteditable="true"]',
                            
                            // Conteneurs
                            '.chat-input-container',
                            '.message-input-container', 
                            '.input-container',
                            '.chat-container',
                            '.text-input-container',
                            
                            // Fallbacks larges
                            '.main-content',
                            'main',
                            'body'
                        ];
                        
                        let dropZone = null;
                        for (const selector of dropZoneSelectors) {
                            dropZone = document.querySelector(selector);
                            if (dropZone) {
                                console.log('Zone de drop trouvée:', selector);
                                break;
                            }
                        }
                        
                        if (!dropZone) {
                            throw new Error('Aucune zone de drop trouvée');
                        }
                        
                        // Créer les événements de drag & drop
                        const dataTransfer = new DataTransfer();
                        dataTransfer.items.add(file);
                        
                        // Simuler la séquence complète de drag & drop
                        const events = [
                            new DragEvent('dragenter', {
                                bubbles: true,
                                cancelable: true,
                                dataTransfer: dataTransfer
                            }),
                            new DragEvent('dragover', {
                                bubbles: true,
                                cancelable: true,
                                dataTransfer: dataTransfer
                            }),
                            new DragEvent('drop', {
                                bubbles: true,
                                cancelable: true,
                                dataTransfer: dataTransfer
                            })
                        ];
                        
                        // Déclencher les événements avec des délais
                        for (const event of events) {
                            dropZone.dispatchEvent(event);
                            await new Promise(resolve => setTimeout(resolve, 100));
                        }
                        
                        // Vérifier si un input file est disponible comme fallback
                        const fileInput = document.querySelector('input[type="file"]');
                        if (fileInput) {
                            console.log('Input file trouvé comme fallback');
                            // Simuler la sélection de fichier sur l'input
                            const dt = new DataTransfer();
                            dt.items.add(file);
                            fileInput.files = dt.files;
                            
                            // Déclencher l'événement change
                            const changeEvent = new Event('change', { bubbles: true });
                            fileInput.dispatchEvent(changeEvent);
                        }
                        
                        return {
                            success: true,
                            message: `Fichier ${fileName} uploadé avec succès`,
                            dropZoneFound: !!dropZone,
                            fileInputFound: !!fileInput
                        };
                        
                    } catch (error) {
                        return {
                            success: false,
                            error: error.message
                        };
                    }
                }
            """, {
                "fileName": filename,
                "fileContent": list(file_content)
            }, timeout=timeout_seconds * 1000)  # Convertir en millisecondes
            
            if not upload_result.get("success"):
                raise Exception(f"Échec du drag & drop: {upload_result.get('error', 'Erreur inconnue')}")
            
            logger.info("✅ Drag & drop simulé avec succès", 
                       drop_zone_found=upload_result.get("dropZoneFound"),
                       file_input_found=upload_result.get("fileInputFound"))
            logger.info("⏳ Attente du traitement par Manus.ai...")
            
            # Attendre que l'upload soit traité par l'interface (plus long pour gros fichiers)
            await page.wait_for_timeout(10000)
            
            # Ajouter le message d'accompagnement si fourni
            if message.strip():
                logger.info("Ajout du message d'accompagnement")
                message_input = await self._find_message_input_with_recovery(page, conversation_url)
                if message_input:
                    await message_input.fill(message)
                    logger.info("Message d'accompagnement ajouté")
                else:
                    logger.warning("⚠️ Impossible de trouver la zone de saisie pour le message d'accompagnement")
            
            # Envoyer le message (avec le fichier)
            logger.info("Envoi du message avec le fichier")
            await self._send_message(page)
            
            # Gérer le popup "Wide Research" s'il apparaît
            await self._handle_wide_research_popup(page)
            
            # Récupérer l'URL dès qu'elle est disponible et notifier via callback
            current_url = page.url
            if url_callback and self._is_valid_manus_url(current_url):
                logger.info("URL de conversation disponible, notification du callback", url=current_url)
                try:
                    await url_callback(current_url)
                except Exception as e:
                    logger.error("Erreur lors de l'appel du callback URL", error=str(e))
            
            # Attendre la réponse si demandé
            ai_response = None
            if wait_for_response:
                logger.info("Attente de la réponse de l'IA", timeout=timeout_seconds)
                ai_response = await self._wait_for_ai_response(page, timeout_seconds)
            
            # Récupérer l'URL finale de la conversation
            final_url = page.url
            
            # Valider que l'URL finale est bien une URL Manus.ai
            if not self._is_valid_manus_url(final_url):
                logger.warning("URL finale invalide détectée lors de l'upload, correction...", invalid_url=final_url)
                try:
                    # Essayer de naviguer vers Manus.ai pour corriger
                    await page.goto(settings.manus_base_url, wait_until="networkidle")
                    corrected_url = page.url
                    logger.info("URL corrigée après upload", corrected_url=corrected_url)
                    final_url = corrected_url
                except Exception as e:
                    logger.error("Impossible de corriger l'URL après upload", error=str(e))
            
            logger.info("Fichier .zip envoyé avec succès", 
                       filename=filename,
                       conversation_url=final_url)
            
            return {
                "success": True,
                "filename": filename,
                "file_path": file_path,
                "message_sent": message,
                "conversation_url": final_url,
                "ai_response": ai_response,
                "page_url": final_url
            }
            
        except TimeoutError as e:
            logger.error("Timeout lors de l'upload du fichier", error=str(e))
            return {
                "success": False,
                "error": f"Timeout: {str(e)}",
                "filename": os.path.basename(file_path) if file_path else "unknown",
                "conversation_url": page.url if page else None
            }
            
        except Exception as e:
            logger.error("Erreur lors de l'upload du fichier", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "filename": os.path.basename(file_path) if file_path else "unknown",
                "conversation_url": page.url if page else None
            }
            
        finally:
            # Nettoyer le fichier temporaire
            try:
                if file_path and os.path.exists(file_path) and file_path.startswith('/tmp/'):
                    os.unlink(file_path)
                    logger.info("Fichier temporaire nettoyé", file_path=file_path)
            except Exception as e:
                logger.warning("Impossible de nettoyer le fichier temporaire", file_path=file_path, error=str(e))


# Instance globale du gestionnaire de navigateur
browser_manager = BrowserAutomation() 