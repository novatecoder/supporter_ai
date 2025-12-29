from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # LLM
    VLLM_URL: str
    LLM_MODEL_NAME: str

    # 에러 방지를 위한 헬퍼 프로퍼티
    @property
    def LLM_BASE_URL(self) -> str:
        return self.VLLM_URL

    @property
    def LLM_API_KEY(self) -> str:
        return "EMPTY"

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

    # [Sensory - STT]
    WHISPER_MODEL_NAME: str = "base"
    WHISPER_DEVICE: str = "cuda"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()