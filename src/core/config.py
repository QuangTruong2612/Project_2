from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    GROQ_API_KEY: Optional[str] = None
    URL_SUPABASE: Optional[str] = None
    ANON_KEY_SUPABASE: Optional[str] = None
    PUBLISH_KEY_SUPABASE: Optional[str] = None
    
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

settings = Settings()