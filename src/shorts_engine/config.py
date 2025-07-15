# src/shorts_engine/config.py

import os
from pathlib import Path
from typing import List, Union, Optional

from pydantic import Field, field_validator, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.shorts_engine.core.models import TTSModelId

class Settings(BaseSettings):
    """
    Manages application-wide settings, loading from a.env file.
    It uses Pydantic for robust validation and type-hinting.
    """
    # --- ElevenLabs API Configuration ---
    # A list of your API keys for the ElevenLabs Text-to-Speech service.
    # The app will expect a comma-separated string in the.env file.
    ELEVENLABS_API_KEYS: str = ""
    # The default TTS model ID to use if not specified.
    DEFAULT_TTS_MODEL_ID: TTSModelId = TTSModelId.ELEVEN_MULTILINGUAL_V2
    # The default voice ID to use for TTS generation.
    DEFAULT_TTS_VOICE_ID: str = "68RUZBDjLe2YBQvv8zFx"

    # --- Google API Configuration ---
    # Your API key for Google services, such as the YouTube Data API.
    GOOGLE_API_KEY: SecretStr = SecretStr("")

    # --- Project Directory Configuration ---
    # The root directory where all video project folders will be stored.
    PROJECTS_ROOT_DIR: Path = Path("projects")
    # The root directory for global static assets like fonts or watermarks.
    ASSETS_ROOT_DIR: Path = Path("assets")

    def get_api_keys(self) -> List[str]:
        """Returns the API keys as a list."""
        if not self.ELEVENLABS_API_KEYS:
            return []
        # Remove quotes if they exist and split by commas
        cleaned = self.ELEVENLABS_API_KEYS.strip('"\'')
        return [key.strip() for key in cleaned.split(',') if key.strip()]

    # --- Pydantic Model Configuration ---
    # Configures the settings model to read from a.env file.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )

# Create a single, importable instance of the settings.
# Application modules can import this 'settings' object directly.
settings = Settings()

# --- Optional: Verification logic to run on import ---
def verify_directories():
    """
    Ensures that the essential project directories exist.
    If they don't, it creates them.
    """
    settings.PROJECTS_ROOT_DIR.mkdir(parents=True, exist_ok=True)
    settings.ASSETS_ROOT_DIR.mkdir(parents=True, exist_ok=True)

# Run verification when the module is first imported.
verify_directories()