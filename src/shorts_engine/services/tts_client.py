# src/shorts_engine/services/tts_client.py

from email.mime import audio
import hashlib
import itertools
import logging
from pathlib import Path
import random
from typing import Iterator, Optional
import base64 
import json
import os
import subprocess
import tempfile

from elevenlabs import VoiceSettings as ElevenLabsVoiceSettings
from elevenlabs.client import ElevenLabs
from rich.console import Console

from..core.models import Blueprint, TTSModelId, VoiceSettings
from..config import settings
from pydub import AudioSegment
from .docker_sandbox import DockerSandboxManager

# Initialize a console for rich logging
console = Console()

class AllAPIKeysExhaustedError(Exception):
    """Custom exception raised when all ElevenLabs API keys have failed."""
    pass

class TTSClient:
    """
    A client for interacting with the ElevenLabs Text-to-Speech API.

    This class manages API key rotation and caching of generated audio files
    to optimize performance and cost. Each API key runs in its own Docker sandbox.
    """

    def __init__(self):
        """Initializes the TTSClient with API keys from settings and Docker sandbox manager."""
        api_keys = settings.get_api_keys()
        if not api_keys:
            raise ValueError("No ElevenLabs API keys found in configuration.")
        self._key_cycle: Iterator[str] = itertools.cycle(api_keys)
        self._active_client: ElevenLabs
        self._current_key: str = ""
        self._sandbox_manager = DockerSandboxManager()
        self._reinitialize_client()

    def _reinitialize_client(self):
        """
        Initializes or re-initializes the ElevenLabs client with the next API key
        and creates a new Docker sandbox for isolation.
        """
        self._current_key = next(self._key_cycle)
        
        # Create a new sandbox for this API key
        self._sandbox_manager.switch_to_api_key(self._current_key)
        
        # Initialize the ElevenLabs client with the new API key
        self._active_client = ElevenLabs(api_key=self._current_key)
        console.log(f"TTSClient initialized with a new API key in a fresh sandbox.")

    def __del__(self):
        """Clean up Docker resources when the TTSClient is destroyed."""
        if hasattr(self, '_sandbox_manager'):
            self._sandbox_manager.cleanup()

    def generate_and_save_audio_for_project(
        self,
        project_name: str,
        video_version: str,
    ) -> bool:
        """
        Generates audios for a given project and saves them.

        Args:
            project_name: The name of the project, used for audio saving directory.

        Returns:
            True if audio for all the shots in the project was all generated, False otherwise.

        Raises:
            AllAPIKeysExhaustedError: If all configured API keys fail.
        """
        audio_dir = settings.PROJECTS_ROOT_DIR / project_name / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)

        console.log(f"Generating audio for project: [cyan]{project_name}[/cyan]")

        # Read the final blueprint for the project
        blueprint_path = settings.PROJECTS_ROOT_DIR / project_name / "blueprints" / f"final_{video_version}.json"
        if not blueprint_path.exists():
            console.log(f"[red]Blueprint file not found: {blueprint_path}, for version {video_version}[/red]")
            return False
        
        # Read the blueprint from json file

        with open(blueprint_path, 'r', encoding='utf-8') as f:
            final_blueprint = Blueprint.model_validate_json(f.read())
        console.log(f"Loaded final blueprint for project: [cyan]{project_name}[/cyan]")

        if not final_blueprint.scene or not final_blueprint.scene.shots:
            console.log(f"[red]No shots found in the blueprint for project: {project_name}[/red]")
            return False
        
        scene = final_blueprint.scene
        for i, shot in enumerate(scene.shots):
            # Skip if the shot already has audio
            if shot.audio_path:
                console.log(f"Shot {i+1}/{len(scene.shots)} already has audio: [cyan]{shot.audio_path}[/cyan]")
                continue
            console.log(f"Processing Shot {i+1}/{len(scene.shots)}: [cyan]{shot.script[:50]}...[/cyan]")

            # Generate audio for the script in the shot
            console.log(f"  Generating audio for Script")

            # Generate and save the audio file
            audio_path = self._generate_audio_for_script(
                shot_number=i+1,
                voice_id=final_blueprint.TTS_voice_id,
                script=shot.script,
                voice_settings=shot.voice_settings,
                audio_dir=audio_dir,
                previous_text=shot.script[i-1] if i > 0 else None,
                next_text=shot.script[i+1] if i < len(shot.script) - 1 else None
            )
            if not audio_path:
                console.log(f"[red]Failed to generate audio for Script in Shot {i+1}[/red]")
                return False
            
            # Update the shot with the audio path and duration
            shot.audio_path = str(audio_path)
            try:
                audio = AudioSegment.from_file(str(audio_path), format=audio_path.suffix[1:])  # Remove the '.' from extension
                shot.duration_seconds = len(audio) / 1000.0
            except Exception as e:
                console.log(f"[red]Error reading audio file: {e}[/red]")
                return False
        
        final_blueprint.scene = scene
        final_blueprint.audio_generated = True
        console.log(f"All audio files generated successfully for project: [cyan]{project_name}[/cyan] saving blueprint...")

        # Save the updated blueprint with audio paths
        with open(blueprint_path, 'w', encoding='utf-8') as f:
            f.write(final_blueprint.model_dump_json(indent=2))

        console.log(f"Blueprint updated with audio paths and saved to: [cyan]{blueprint_path}[/cyan]")
        return True

    def _generate_audio_for_script(
        self,
        shot_number: int,
        voice_id: str,
        script: str,
        voice_settings: VoiceSettings,
        audio_dir: Path,
        previous_text: Optional[str] = None,
        next_text: Optional[str] = None,
        model_id: TTSModelId = settings.DEFAULT_TTS_MODEL_ID,
    ) -> Path | None:
        """
        Generates audio for a given script using the TTS client.

        Args:
            shot_number: The number of the shot being processed.
            voice_id: The ID of the voice to use for TTS.
            script: The script text to convert to audio.
            voice_settings: The voice settings to use for the TTS conversion.
            audio_dir: The directory to save the audio file.
            previous_text: The text of the previous shot (if any).
            next_text: The text of the next shot (if any).

        Returns:
            The path to the generated audio file, or None if generation failed.
        """
        audio_path = audio_dir / f"{shot_number}_{hash(script[:10])}_{random.randint(0, 9999)}.mp3"
        if audio_path.exists():
            console.log(f"Cache hit for audio file: [cyan]{audio_path.name}[/cyan]")
            return audio_path

        console.log(f"Cache miss. Generating new audio for: '{script[:50]}...'")

        # Create the VoiceSettings object for the API call from our Pydantic model
        api_voice_settings = ElevenLabsVoiceSettings(
            # stability=voice_settings.stability,
            # similarity_boost=voice_settings.similarity_boost,
            # style=voice_settings.style,
            # use_speaker_boost=voice_settings.use_speaker_boost,
            speed=voice_settings.speed,
        )
        
        # Attempt to generate audio, cycling through keys on failure
        for _ in range(len(settings.get_api_keys())):
            try:
                # Create a temporary script file in the current directory
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as script_file:
                    script_file_path = script_file.name
                    script_file.write(f"""
import json
import base64
from elevenlabs import VoiceSettings, Client

# Initialize client with API key (provided by Docker environment)
api_key = "{self._current_key}"
client = Client(api_key=api_key)

# Prepare request parameters
voice_id = "{voice_id}"
text = {json.dumps(script)}  # JSON encode to handle special characters
model_id = "{model_id.value}"
previous_text = {json.dumps(previous_text) if previous_text else "None"}
next_text = {json.dumps(next_text) if next_text else "None"}

voice_settings = VoiceSettings(
    speed={voice_settings.speed}
)

# Make the API call
response = client.text_to_speech.convert_with_timestamps(
    voice_id=voice_id,
    text=text,
    voice_settings=voice_settings,
    model_id=model_id,
    previous_text=previous_text,
    next_text=next_text
)

# Prepare the result
result = {{
    "audio_base_64": base64.b64encode(response.audio).decode('utf-8'),
    "alignment": response.alignment.model_dump() if response.alignment else None
}}

# Print the result as JSON
print(json.dumps(result))
""")

                # Execute the script in the sandbox
                result_json = self._sandbox_manager.execute_in_sandbox(
                    self._current_key, 
                    f"python {script_file_path}"
                )
                
                # Clean up the temporary file
                os.unlink(script_file_path)
                
                # Parse the result
                try:
                    result = json.loads(result_json)
                    audio_data = base64.b64decode(result["audio_base_64"])
                    timestamps_data = result["alignment"] if result["alignment"] else {}
                    
                    # Save the audio file
                    with open(audio_path, "wb") as f:
                        f.write(audio_data)
                    
                    # Save the timestamps to a corresponding json file
                    timestamps_path = audio_path.with_suffix(".json")
                    with open(timestamps_path, "w", encoding='utf-8') as f:
                        json.dump(timestamps_data, f, indent=2)
                    
                    console.log(f"[green]Successfully generated and cached audio:[/green] {audio_path.name}")
                    console.log(f"[green]Successfully saved timestamps to:[/green] {timestamps_path.name}")
                    return audio_path
                except json.JSONDecodeError:
                    console.log(f"[yellow]Failed to parse result JSON: {result_json}[/yellow]")
                    self._reinitialize_client()
                    continue

            except Exception as e:
                console.log(f"[yellow]API call failed with key ending in '...{self._current_key[-4:]}'. Error: {e}. Trying next key.[/yellow]")
                self._reinitialize_client()
                continue

        raise AllAPIKeysExhaustedError(
            "All ElevenLabs API keys failed or were exhausted. Please check your keys and quotas."
        )