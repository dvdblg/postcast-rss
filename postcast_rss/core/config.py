# from dotenv import load_dotenv
import os
from pathlib import Path

from appdirs import user_config_dir
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )
    APP_NAME: str = "postcast-rss"

    PROJECT_NAME: str = "Postcast RSS"
    ILPOST_USERNAME: SecretStr
    ILPOST_PASSWORD: SecretStr

    # IL Post URLs
    ILPOST_BASE_URL: str = "https://www.ilpost.it"
    ILPOST_API_BASE_URL: str = "https://api-prod.ilpost.it"

    # API endpoints
    ILPOST_API_ROUTE_PODCASTS: str = "podcast/v1/podcast"
    ILPOST_API_ROUTE_USERS: str = "user/v2"

    # Cache settings
    CACHE_TTL: int = 3600  # Cache data for 1 hour
    ILPOST_SUBSCRIPTION_CACHE_FILE_NAME: str = "ilpost_cache.json"

    # RSS feed settings
    FEED_AUTHOR: str = "IL Post"
    FEED_LANGUAGE: str = "it"

    @property
    def APP_DIR(self) -> str:
        """Get the application directory path."""
        return user_config_dir(self.APP_NAME)

    @property
    def ILPOST_SUBSCRIPTION_CACHE_FILE(self) -> Path:
        """Get the subscription cache file path."""
        return Path(self.APP_DIR) / self.ILPOST_SUBSCRIPTION_CACHE_FILE_NAME


settings = Settings()
