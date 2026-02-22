from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://brain:secret@localhost/brain"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # WhatsApp Go REST
    whatsapp_api_url: str = "http://localhost:3000"
    webhook_secret: str = ""

    # Anthropic
    anthropic_api_key: str = ""

    # Alexa
    alexa_skill_id: str = ""
    alexa_client_id: str = ""
    alexa_client_secret: str = ""
    alexa_user_id: str = ""

    # Media
    media_dir: str = "/data/media"
    public_base_url: str = "http://localhost:8000"

    # Whisper
    whisper_enabled: bool = True
    whisper_model: str = "small"


settings = Settings()
