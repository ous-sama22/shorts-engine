# src/shorts_engine/services/tts_client.py

import hashlib
import itertools
import logging
from pathlib import Path
from typing import Iterator, Optional

from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
from rich.console import Console

from..core.models import Sentence
from..config import settings

# Initialize a console for rich logging
console = Console()

class AllAPIKeysExhaustedError(Exception):
    """Custom exception raised when all ElevenLabs API keys have failed."""
    pass

class TTSClient:
    """
    A client for interacting with the ElevenLabs Text-to-Speech API.

    This class manages API key rotation and caching of generated audio files
    to optimize performance and cost.
    """

    def __init__(self):
        """Initializes the TTSClient with API keys from settings."""
        if not settings.ELEVENLABS_API_KEYS:
            raise ValueError("No ElevenLabs API keys found in configuration.")
        self._key_cycle: Iterator[str] = itertools.cycle(settings.ELEVENLABS_API_KEYS)
        self._active_client: ElevenLabs
        self._current_key: str = ""
        self._reinitialize_client()

    def _reinitialize_client(self):
        """Initializes or re-initializes the ElevenLabs client with the next API key."""
        self._current_key = next(self._key_cycle)
        self._active_client = ElevenLabs(api_key=self._current_key)
        console.log(f"TTSClient initialized with a new API key.")

    def generate_and_cache_audio(
        self,
        sentence: Sentence,
        project_name: str,
        previous_text: Optional[str] = None,
        next_text: Optional[str] = None,
    ) -> Path:
        """
        Generates audio for a given sentence and caches it, using context for quality.

        If a cached file for the exact same sentence, settings, and context exists,
        it returns the path to the cached file without making an API call.

        Args:
            sentence: The Sentence object containing text and voice settings.
            project_name: The name of the project, used for caching directory.
            previous_text: The text of the preceding sentence for context.
            next_text: The text of the following sentence for context.

        Returns:
            The Path object pointing to the generated (or cached) audio file.

        Raises:
            AllAPIKeysExhaustedError: If all configured API keys fail.
        """
        cache_dir = settings.PROJECTS_ROOT_DIR / project_name / "audio_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Create a unique hash including context for precise caching
        unique_content = (
            f"{sentence.text}-"
            f"{sentence.voice_settings.model_dump_json()}-"
            f"prev:{previous_text}-next:{next_text}"
        )
        content_hash = hashlib.sha256(unique_content.encode("utf-8")).hexdigest()
        audio_path = cache_dir / f"{content_hash}.mp3"

        if audio_path.exists():
            console.log(f"Cache hit for audio file: [cyan]{audio_path.name}[/cyan]")
            return audio_path

        console.log(f"Cache miss. Generating new audio for: '{sentence.text[:50]}...'")

        # Create the VoiceSettings object for the API call from our Pydantic model
        api_voice_settings = VoiceSettings(
            stability=sentence.voice_settings.stability,
            similarity_boost=sentence.voice_settings.similarity_boost,
            style=sentence.voice_settings.style,
            use_speaker_boost=sentence.voice_settings.use_speaker_boost,
            speed=sentence.voice_settings.speed
        )

        # Attempt to generate audio, cycling through keys on failure
        for _ in range(len(settings.ELEVENLABS_API_KEYS)):
            try:
                audio_iterator = self._active_client.text_to_speech.convert(
                    voice_id=sentence.voice_settings.voice_id,
                    text=sentence.text,
                    model_id=sentence.voice_settings.model_id,
                    voice_settings=api_voice_settings,
                    output_format=sentence.voice_settings.output_format,
                    seed=sentence.voice_settings.seed,
                    previous_text=previous_text,
                    next_text=next_text,
                    language_code=sentence.voice_settings.language_code,
                )

                with open(audio_path, "wb") as f:
                    for chunk in audio_iterator:
                        f.write(chunk)

                console.log(f"[green]Successfully generated and cached audio:[/green] {audio_path.name}")
                return audio_path

            except Exception as e:
                console.log(f"[yellow]API call failed with key ending in '...{self._current_key[-4:]}'. Error: {e}. Trying next key.[/yellow]")
                self._reinitialize_client()
                continue

        raise AllAPIKeysExhaustedError(
            "All ElevenLabs API keys failed or were exhausted. Please check your keys and quotas."
        )