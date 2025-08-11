"""
Configuration de l'application avec validation Pydantic
"""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration de l'application"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Configuration API
    api_host: str = Field(default="0.0.0.0", description="Adresse d'écoute de l'API")
    api_port: int = Field(default=8000, description="Port d'écoute de l'API")
    debug: bool = Field(default=False, description="Mode debug")
    api_secret_key: str = Field(default="dev-secret-key", description="Clé secrète pour l'API")
    
    # Configuration Playwright
    headless: bool = Field(default=True, description="Mode headless du navigateur")
    headless_setup: bool = Field(default=False, description="Mode headless pour le setup (False = fenêtre visible)")
    use_persistent_context: bool = Field(default=True, description="Utiliser un contexte persistant (garde la session)")
    window_width: int = Field(default=1440, description="Largeur de fenêtre en mode visible (0 = taille standard)")
    window_height: int = Field(default=900, description="Hauteur de fenêtre en mode visible (0 = taille standard)")
    disable_javascript: bool = Field(default=False, description="Désactiver JavaScript (pour debug)")
    browser_timeout: int = Field(default=30000, description="Timeout global du navigateur (ms)")
    page_timeout: int = Field(default=15000, description="Timeout de chargement des pages (ms)")
    
    # Configuration Manus.ai
    manus_base_url: str = Field(default="https://www.manus.ai", description="URL de base de Manus.ai")
    
    # API Credentials externe
    credentials_api_url: str = Field(default="http://localhost:3001/api/ai-credentials", description="URL de l'API de gestion des credentials")
    credentials_api_token: str = Field(default="", description="Token JWT pour l'API de credentials")
    credentials_api_timeout: int = Field(default=30, description="Timeout API en secondes")
    credentials_user_identifier: str = Field(default="romain.bazil@bricks.co", description="Identifiant utilisateur pour récupérer les credentials")
    
    # Session Manus.ai via variables d'environnement (FALLBACK si API non disponible)
    manus_session_token: str = Field(default="", description="Token de session Manus.ai extrait du navigateur")
    manus_auth_token: str = Field(default="", description="Token d'authentification Manus.ai")
    manus_user_id: str = Field(default="", description="ID utilisateur Manus.ai")
    manus_csrf_token: str = Field(default="", description="Token CSRF Manus.ai")
    manus_cookies: str = Field(default="", description="Cookies Manus.ai au format JSON")
    manus_local_storage: str = Field(default="", description="LocalStorage Manus.ai au format JSON")
    
    # Sécurité et rate limiting
    rate_limit_per_minute: int = Field(default=10, description="Limite de requêtes par minute")
    
    # Logging
    log_level: str = Field(default="INFO", description="Niveau de log")


# Instance globale des paramètres
settings = Settings() 