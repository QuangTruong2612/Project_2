import logging
from supabase import create_client, Client
from src.core import settings

logger = logging.getLogger(__name__)

def get_supabase_client() -> Client:
    """
    Create and return  Supabase Client.
    Use env from file src.core.config.
    """
    if not settings.URL_SUPABASE or not settings.PUBLISH_KEY_SUPABASE:
        logger.error("NOT HAVE SUPABASE_URL OR SUPABASE_KEY IN file .env!")
        raise ValueError("Database configuration is missing.")

    try:
        # create connection
        client = create_client(settings.URL_SUPABASE, settings.PUBLISH_KEY_SUPABASE)
        return client
    except Exception as e:
        logger.error(f"Error when create Supabase Client: {str(e)}")
        raise

supabase: Client = get_supabase_client()
