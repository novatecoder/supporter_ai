# src/supporter_ai/common/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # --- [LLM Settings] ---
    LLM_URL: str
    LLM_MODEL_NAME: str
    LLM_API_KEY: str = "EMPTY"  # .env의 LLM_API_KEY 값을 주입받음

    # --- [Database Settings] ---
    POSTGRES_URL: str
    REDIS_HOST: str
    REDIS_PORT: int
    
    NEO4J_URI: str
    NEO4J_USER: str
    NEO4J_PASSWORD: str
    
    QDRANT_HOST: str
    QDRANT_PORT: int

    # --- [App Settings] ---
    APP_PORT: int = 8080
    DEBUG: bool = True

    # --- [Sensory - STT Settings] ---
    WHISPER_MODEL_NAME: str = "base"
    WHISPER_DEVICE: str = "cuda"

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()