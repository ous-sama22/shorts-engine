# src/shorts_engine/core/models.py

from typing import List, Optional, Literal
from pydantic import BaseModel, Field, PositiveFloat

class VoiceSettings(BaseModel):
    """
    Encapsulates all configurable settings for a Text-to-Speech (TTS) generation
    call to the ElevenLabs API. This allows for fine-grained, per-sentence control
    over the voice delivery.
    """
    stability: Optional[float] = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Controls the randomness of the generation. Lower values introduce more emotional range."
    )
    similarity_boost: Optional[float] = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Determines how closely the AI should adhere to the original voice."
    )
    style: Optional[float] = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Amplifies the style of the original speaker. Higher values can increase latency."
    )
    speed: Optional[float] = Field(
        default=1.0,
        ge=0.7,
        le=1.2,
        description="Adjusts the speed of the voice. 1.0 is default, <1.0 is slower, >1.0 is faster."
    )
    use_speaker_boost: Optional[bool] = Field(
        default=True,
        description="Boosts the similarity to the original speaker, slightly increasing latency."
    )
    model_id: str = Field(
        default="eleven_multilingual_v2",
        description="The ID of the ElevenLabs model to use for TTS generation."
    )
    voice_id: str = Field(
      ..., # This field is required
        description="The ID of the specific voice to be used for generation."
    )
    output_format: str = Field(
        default="mp3_44100_128",
        description="Output format for the generated audio, e.g., 'mp3_44100_128'."
    )
    seed: Optional[int] = Field(
        default=None,
        ge=0,
        le=4294967295,
        description="A seed for deterministic generation, ensuring repeatable results."
    )
    language_code: Optional[str] = Field(
        default=None,
        description="Language code (e.g., 'en-US') to enforce for specific models."
    )

class Sentence(BaseModel):
    """
    Represents a single sentence in the video script, complete with its own
    dedicated voice settings. This enables the 'Interactive Revision Mandate' by
    allowing for targeted regeneration of individual lines.
    """
    text: str = Field(..., description="The text content of the sentence.")
    voice_settings: VoiceSettings = Field(..., description="The TTS settings for this specific sentence.")

class KenBurnsEffect(BaseModel):
    """
    Defines the parameters for a Ken Burns effect (pan and zoom) to be applied
    to a still image, creating a sense of motion.
    """
    zoom: float = Field(default=1.1, description="The zoom factor to apply over the duration of the shot.")
    direction: str = Field(default="center", description="The direction of the pan (e.g., 'center', 'top_left').")

class Caption(BaseModel):
    """
    Defines an animated text overlay (caption) to be displayed during a shot.
    This model provides detailed control over the caption's content, timing,
    and appearance.
    """
    text: str = Field(..., description="The text content of the caption.")
    start_time_seconds: float = Field(..., ge=0, description="The time in seconds (relative to the shot's start) when the caption should appear.")
    end_time_seconds: float = Field(..., ge=0, description="The time in seconds (relative to the shot's start) when the caption should disappear.")
    position: str = Field(default="center", description="Position of the caption on the screen (e.g., 'center', 'bottom', ('center', 150)).")
    font_size: int = Field(default=50, description="Font size of the caption text.")
    font_color: str = Field(default="white", description="Color of the caption text.")
    bg_color: Optional[str] = Field(default="black", description="Background color of the caption's text box.")
    bg_opacity: Optional[float] = Field(default=0.6, ge=0.0, le=1.0, description="Opacity of the caption's background box.")

class Shot(BaseModel):
    """
    Represents a single visual element in a scene, defined by a visual prompt
    and its duration. It can optionally include animation effects and captions.
    """
    visual_prompt: str = Field(..., description="A detailed, cinematic prompt for manual visual asset generation.")
    duration_seconds: PositiveFloat = Field(..., description="The duration this shot should appear on screen.")
    ken_burns_effect: Optional[KenBurnsEffect] = Field(
        default=None,
        description="Optional Ken Burns effect to apply if the visual is a still image."
    )
    captions: Optional[List[Caption]] = Field(
        default=None,
        description="A list of timed captions to overlay on this shot."
    )

class Scene(BaseModel):
    """
    A logical grouping of script sentences and their corresponding visual shots.
    A video is composed of one or more scenes.
    """
    script: List = Field(..., description="A list of sentences that form the narrative of this scene.")
    shots: List = Field(..., description="A list of visual shots that correspond to the script.")

class Blueprint(BaseModel):
    """
    The top-level Pydantic model representing the complete, validated plan for a
    single YouTube Short. It is the 'single source of truth' that the Assembler
    module will use to construct the final video file.
    """
    project_name: str = Field(..., description="The name of the project this blueprint belongs to.")
    version: str = Field(..., description="The version identifier for A/B testing (e.g., 'A', 'B', 'A_rev1').")
    script_formula: str = Field(..., description="The viral script formula used (e.g., 'Secret Value', 'Curiosity Peak').")
    scenes: List = Field(..., description="The sequence of scenes that make up the video.")
    cta_text: str = Field(..., description="The Call-to-Action text to be displayed at the end of the video.")