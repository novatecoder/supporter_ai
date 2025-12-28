from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # LLM
    VLLM_URL: str
    LLM_MODEL_NAME: str

    # Database
    POSTGRES_URL: str
    REDIS_HOST: str
    REDIS_PORT: int
    NEO4J_URI: str
    NEO4J_USER: str
    NEO4J_PASSWORD: str
    QDRANT_HOST: str
    QDRANT_PORT: int

    # App
    APP_PORT: int = 8000
    DEBUG: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()