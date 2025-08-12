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
    use_persistent_context: bool = Field(default=False, description="Utiliser un contexte persistant (garde la session) - False recommandé pour l'intégration API")
    window_width: int = Field(default=1440, description="Largeur de fenêtre en mode visible (0 = taille standard)")
    window_height: int = Field(default=900, description="Hauteur de fenêtre en mode visible (0 = taille standard)")
    disable_javascript: bool = Field(default=False, description="Désactiver JavaScript (pour debug)")
    browser_timeout: int = Field(default=30000, description="Timeout global du navigateur (ms)")
    page_timeout: int = Field(default=15000, description="Timeout de chargement des pages (ms)")
    
    # Configuration Manus.ai
    manus_base_url: str = Field(default="https://www.manus.im", description="URL de base de Manus.im")
    
    # API Credentials externe (votre interface web)
    credentials_api_url: str = Field(default="http://localhost:3001/api/ai-credentials", description="URL de l'API de gestion des credentials")
    credentials_api_token: str = Field(default="", description="Clé API (X-API-Key) pour l'authentification avec l'API de credentials")
    credentials_api_timeout: int = Field(default=30, description="Timeout pour les requêtes vers l'API de credentials (secondes)")
    
    # Session refresh périodique
    session_refresh_enabled: bool = Field(default=False, description="Activer le refresh automatique de session")
    session_refresh_interval_hours: int = Field(default=72, description="Intervalle de refresh de session (heures)")
    session_manual_refresh_url: str = Field(default="", description="URL webhook pour demander un refresh manuel")
    
    # Fallback: Variables d'environnement directes pour Manus.ai (si API credentials indisponible)
    manus_cookies: str = Field(default="", description="Cookies Manus.ai au format JSON (fallback)")
    manus_session_token: str = Field(default="", description="Token de session Manus.ai (fallback)")
    manus_auth_token: str = Field(default="", description="Token d'authentification Manus.ai (fallback)")
    manus_local_storage: str = Field(default="", description="localStorage Manus.ai au format JSON (fallback)")
    
    # Logging
    log_level: str = Field(default="INFO", description="Niveau de logging (DEBUG, INFO, WARNING, ERROR)")
    
    # Rate limiting
    rate_limit_per_minute: int = Field(default=10, description="Limite de requêtes par minute par IP")


# Instance globale des paramètres
settings = Settings() 