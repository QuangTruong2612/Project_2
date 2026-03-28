from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    GROQ_API_KEY: str

    URL_SUPABASE: str
    PUBLISH_KEY_SUPABASE: str
    ANON_KEY_SUPABASE: str
    
    # Config to load from file .env
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()