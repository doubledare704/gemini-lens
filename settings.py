from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    
    # Model IDs
    MAIN_MODEL_ID: str = "gemini-3-flash-preview"
    IMAGEN_MODEL_ID: str = "imagen-4.0-fast-generate-001"
    VEO_MODEL_ID: str = "veo-3.1-fast-generate-preview"
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # genai config
    API_VERSION: str = "v1beta"

settings = Settings()
