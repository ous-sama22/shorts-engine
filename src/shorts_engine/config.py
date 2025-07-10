# src/shorts_engine/config.py

import os
from pathlib import Path
from typing import List, Union

from pydantic import field_validator, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Manages application-wide settings, loading from a.env file.
    It uses Pydantic for robust validation and type-hinting.
    """
    # --- ElevenLabs API Configuration ---
    # A list of your API keys for the ElevenLabs Text-to-Speech service.
    # The app will expect a comma-separated string in the.env file.
    ELEVENLABS_API_KEYS: List

    # --- Google API Configuration ---
    # Your API key for Google services, such as the YouTube Data API.
    GOOGLE_API_KEY: SecretStr

    # --- Project Directory Configuration ---
    # The root directory where all video project folders will be stored.
    PROJECTS_ROOT_DIR: Path = Path("projects")
    # The root directory for global static assets like fonts or watermarks.
    ASSETS_ROOT_DIR: Path = Path("assets")

    @field_validator('ELEVENLABS_API_KEYS', mode='before')
    @classmethod
    def assemble_api_keys(cls, v: Union[str, List[str]]) -> List[str]:
        """Parses a comma-separated string of API keys into a list."""
        if isinstance(v, str):
            # Split the string by commas and strip whitespace from each key
            return [key.strip() for key in v.split(',') if key.strip()]
        # If it's already a list (e.g., from non-env source), return it
        return v

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