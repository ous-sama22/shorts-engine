# src/shorts_engine/core/models.py

from typing import List, Optional, Literal, Tuple, Union
from pydantic import BaseModel, Field, NonNegativeFloat, PositiveFloat, model_validator
from enum import Enum

# NEW: Enum for viral script formulas, as requested.
class ViralFormula(str, Enum):
    """Enumeration of the supported viral script formulas."""
    SECRET_VALUE = "Secret Value"
    CURIOSITY_PEAK = "Curiosity Peak"
    PRE_HOOK_STORY_END = "Pre-Hook, Hook, Story, End"
    PROBLEM_AGITATE_SOLVE = "Problem, Agitate, Solve"
    MYTH_BUSTING = "Myth Busting"
    INFINITE_LOOP = "Infinite Loop"

class TTSModelId(str, Enum):
    """Enumeration of the supported TTS model IDs."""
    ELEVEN_MULTILINGUAL_V2 = "eleven_multilingual_v2"
    ELEVEN_V2 = "eleven_v3"

# --------------------------------------------------------------------------
# Draft Models - For validating raw LLM output
# These models capture the creative intent before technical details
# like timing are determined.
# --------------------------------------------------------------------------

class DraftVisual(BaseModel):
    """Represents a visual concept from the LLM before asset creation."""
    visual_type: Literal['ai_video', 'ai_image', 'stock_asset'] = Field(
        ...,
        description="The type of visual to be generated or used. 'ai_video' for VEO, 'ai_image' for DALL-E, etc., 'stock_asset' for a pre-existing file."
    )
    prompt_or_filename: str = Field(
        ...,
        description="The detailed generation prompt for an AI visual, or the name of the file for a 'stock_asset'."
    )

class DraftShot(BaseModel):
    """Represents a scene's raw script and visual concepts from the LLM."""
    script_text: str = Field(
        ...,
        description="The complete block of text for this scene's narration (multiple sentences)."
    )
    visual: DraftVisual = Field(
        ...,
        description="A visual concept that will visually represent this scene."
    )

class DraftBlueprint(BaseModel):
    """
    The top-level model for validating the raw, untimed JSON response from the LLM.
    This is the output of the initial creative generation step.
    """
    project_name: str = Field(..., description="The name of the project this blueprint belongs to.")
    version: str = Field(..., description="The version identifier for A/B testing (e.g., 'A', 'B').")
    video_title: str = Field(
        ...,
        description="The title of the video, used for metadata and user interface."
    )
    video_description: str = Field(
        ...,
        description="A brief description of the video content, used for metadata."
    )

    script_formula: ViralFormula = Field(..., description="The viral script formula used.")
    shots: List[DraftShot] = Field(..., description="The sequence of shots that make up the video.")


# ==============================================================================
# AUDIO MODELS
# ==============================================================================

class VoiceSettings(BaseModel):
    """
    Represents the detailed voice settings for the ElevenLabs API.
    This model exposes all key parameters to allow for maximum creative control
    over the audio generation, as per the project's core design principle.
    """
    speed: PositiveFloat = Field(
        default=0.98,
        description="Speed of the speech. 1.0 is normal speed, < 1.0 is slower, > 1.0 is faster."
    )


# ==============================================================================
# VISUAL STYLE MODELS
# ==============================================================================

class Timestamp(BaseModel):
    """
    Represents the start and end time (in seconds) for all characters for a shot.
    """
    characters: List[str] = Field(..., description="List of all characters for the shot's audio.")
    character_start_times_seconds: List[float] = Field(..., description="Start time in seconds for each character, same index like characters.")
    character_end_times_seconds: List[float] = Field(..., description="End time in seconds for each character, same index like characters.")

class TextStyle(BaseModel):
    """
    Comprehensive model for styling text captions using MoviePy's TextClip.
    Designed to expose all useful parameters for maximum creative control over
    text rendering, from font and color to advanced layout and typography.
    """
    font: str = Field(
        default="assets/fonts/Roboto-Bold.ttf",
        description="Path to the TTF or OTF font file."
    )
    font_size: Optional[int] = Field(
        default=72,
        description="Font size in points. Can be auto-set if method is 'caption'."
    )
    color: str = Field(
        default="white",
        description="Primary color of the text (e.g., 'white', '#FFFFFF')."
    )
    bg_color: Optional[str] = Field(
        default=None,
        description="Background color of the text clip. 'transparent' if None."
    )
    size: Optional[tuple] = Field(
        default=(800, None),
        description="(width, height) of the text canvas. Width is required for 'caption' method for auto-wrapping."
    )
    method: Literal["label", "caption"] = Field(
        default="caption",
        description="'caption' wraps text within 'size', 'label' autosizes the clip to the text."
    )
    align: Literal["center", "left", "right"] = Field(
        default="center",
        alias="text_align",
        description="Alignment of text lines within the clip (like CSS text-align)."
    )
    stroke_color: Optional[str] = Field(
        default="black",
        description="Color of the text outline (stroke)."
    )
    stroke_width: int = Field(
        default=2,
        description="Width of the text outline in pixels."
    )

    kerning: Optional[float] = Field(
        default=None,
        description="Adjusts spacing between characters. Negative values bring them closer."
    )
    interline: Optional[float] = Field(
        default=10,
        description="Spacing between lines of text in pixels."
    )
    horizontal_align: Literal["center", "left", "right"] = Field(
        default="center",
        description="Horizontal alignment of the text block within its canvas."
    )
    vertical_align: Literal["center", "top", "bottom"] = Field(
        default="center",
        description="Vertical alignment of the text block within its canvas."
    )
    transparent: bool = Field(
        default=True,
        description="If True, the background is transparent (unless bg_color is set)."
    )

    @model_validator(mode='after')
    def check_caption_requires_size(self) -> 'TextStyle':
        if self.method == 'caption' and (self.size is None):
            raise ValueError("The 'size' field with a defined width must be provided when method is 'caption'.")
        return self

    class Config:
        populate_by_name = True # Allows using 'text_align' as an alias for 'align'

class KenBurnsStyle(BaseModel):
    """
    Defines the parameters for a Ken Burns (pan and zoom) effect on media (images or videos).
    Provides control over the start and end scale, position, and the motion's
    easing function for a more cinematic feel.
    """
    media_type: Literal['image', 'video'] = Field(
        default='image',
        description="Type of media the effect will be applied to"
    )
    start_scale: float = Field(
        default=1.0,
        description="Initial scale of the image (1.0 is original size)."
    )
    end_scale: float = Field(
        default=1.2,
        description="Final scale of the image. > start_scale for zoom-in."
    )
    start_position: Tuple[float, float] = Field(
        default=(0.0, 0.0),
        description="Initial center point of the frame as a fraction of image dimensions (e.g., (0.5, 0.5) is center)."
    )
    end_position: Tuple[float, float] = Field(
        default=(0.5, 0.5),
        description="Final center point of the frame as a fraction of image dimensions."
    )
    easing_function: Literal[
        'linear', 'ease_in_quad', 'ease_out_quad', 'ease_in_out_quad',
        'ease_in_cubic', 'ease_out_cubic', 'ease_in_out_cubic'
    ] = Field(
        default='ease_in_out_quad',
        description="The easing function to control the animation's acceleration and deceleration."
    )

# ==============================================================================
# CORE BLUEPRINT MODELS
# ==============================================================================

class Shot(BaseModel):
    """
    Represents a single visual unit in a scene, corresponding to one image or
    video clip and a segment of the script.
    """
    shot_id: str
    asset_path: str
    audio_path: Optional[str] = None
    ass_file_path: Optional[str] = None
    duration_seconds: NonNegativeFloat = Field(
        default=0,
        description="Duration of the shot in seconds."
    )
    applyed_ken_burns: bool = Field(
        default=False,
        description="Indicates whether the Ken Burns effect has been applied to the shot."
    )
    applyed_captions: bool = Field(
        default=False,
        description="Indicates whether captions have been applied to the shot."
    )
    ass_file_generated: bool = Field(
        default=False,
        description="Indicates whether an ASS file has been generated for the shot."
    )
    script: str
    voice_settings: VoiceSettings = Field(
        default_factory=VoiceSettings,
        description="Voice settings for audio generation."
    )
    ken_burns_style: KenBurnsStyle = Field(
        default_factory=KenBurnsStyle,
        description="Ken Burns style settings for the shot."
    )
    final_shot_video_generated: bool = Field(
        default=False,
        description="Indicates whether the final shot video has been generated."
    )

class Scene(BaseModel):
    """
    A collection of shots that form a coherent sequence in the video.
    """
    scene_id: str
    shots: List[Shot]

class Blueprint(BaseModel):
    """
    The master data model for a single video project. It contains all the
    information necessary to generate the audio, assemble the video, and
    upload the final product.
    """
    project_name: str
    video_title: str
    video_description: str
    TTS_voice_id: str = Field(
        default="68RUZBDjLe2YBQvv8zFx",
        description="The default voice ID used for TTS audio generation."
    )
    TTS_model_id: TTSModelId = Field(
        default=TTSModelId.ELEVEN_MULTILINGUAL_V2,
        description="The default model ID used for TTS audio generation."
    )
    scene: Scene
    version: str = Field(
        default="A",
        description="The version of the blueprint."
    )
    script_formula: ViralFormula = Field(
        default=ViralFormula.SECRET_VALUE,
        description="The viral script formula used for this blueprint."
    )
    promotion: bool = Field(
        default=False,
        description="Indicates whether promotion is enabled for the video."
    )
    audio_generated: bool = Field(
        default=False,
        description="Indicates whether audio has been generated for the blueprint."
    )
    final_shots_videos_generated: bool = Field(
        default=False,
        description="Indicates whether the final shots videos have been generated."
    )
    output_path: Optional[str] = None
    rendered: bool = False
