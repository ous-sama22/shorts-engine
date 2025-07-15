# src/shorts_engine/video/effects.py

import math
from pathlib import Path
import subprocess
from tempfile import NamedTemporaryFile
import numpy as np
from PIL import Image
from PIL.Image import Resampling
from typing import Callable, Dict, Literal, Optional, cast
from moviepy.video.VideoClip import VideoClip, ImageClip
from..core.models import Blueprint, Shot, Timestamp
from moviepy.video.io.VideoFileClip import VideoFileClip
from ..config import settings
from rich.console import Console
import ffmpeg
from moviepy.video.fx.Crop import Crop
from moviepy.video.fx.Resize import Resize

class EffectManager:
    """
    Manages video effects such as Ken Burns for shots in a video project.
    This class provides methods to apply effects based on the KenBurnsStyle model.
    """
    EasingFunctionName = Literal[
        'linear', 'ease_in_quad', 'ease_out_quad', 'ease_in_out_quad',
        'ease_in_cubic', 'ease_out_cubic', 'ease_in_out_cubic'
    ]
    def __init__(self, console: Console):
        self.console = console

        self.EASING_FUNCTIONS: Dict[EffectManager.EasingFunctionName, Callable[[float], float]] = {
            'linear': self._linear,
            'ease_in_quad': self._ease_in_quad,
            'ease_out_quad': self._ease_out_quad,
            'ease_in_out_quad': self._ease_in_out_quad,
            'ease_in_cubic': self._ease_in_cubic,
            'ease_out_cubic': self._ease_out_cubic,
            'ease_in_out_cubic': self._ease_in_out_cubic,
        }

    # ==============================================================================
    # EASING FUNCTIONS
    # ==============================================================================
    # A collection of easing functions that take a float `t` from 0.0 to 1.0
    # and return a transformed float. Based on standard easing equations.
    # Source: https://easings.net/ and https://github.com/robweychert/python-easing-function
    # ==============================================================================

    def _linear(self, t: float) -> float:
        return t

    def _ease_in_quad(self, t: float) -> float:
        return t * t

    def _ease_out_quad(self, t: float) -> float:
        return -t * (t - 2)

    def _ease_in_out_quad(self, t: float) -> float:
        t *= 2
        if t < 1:
            return 0.5 * t * t
        t -= 1
        return -0.5 * (t * (t - 2) - 1)

    def _ease_in_cubic(self, t: float) -> float:
        return t * t * t

    def _ease_out_cubic(self, t: float) -> float:
        t -= 1
        return t * t * t + 1

    def _ease_in_out_cubic(self, t: float) -> float:
        t *= 2
        if t < 1:
            return 0.5 * t * t * t
        t -= 2
        return 0.5 * (t * t * t + 2)

    # ==============================================================================
    # KEN BURNS EFFECT IMPLEMENTATION
    # ==============================================================================

    def _apply_ken_burns_and_audio(self, shot: Shot) -> bool:
        """
        Applies a Ken Burns (pan and zoom) effect to a Shot, adding a new audio track.

        This function transforms a static Shot (video or image) into an animated video,
        replaces its audio with the track from `shot.audio_path`, and saves it in the
        project's assets folder.

        Args:
            shot: The input Shot to animate, containing the new audio path.

        Returns:
            bool: True if the effect was applied and file saved successfully, False otherwise.
        """
        try:
            asset_path = Path(shot.asset_path)
            if not asset_path.exists():
                self.console.print(f"[red]❌ Asset file not found: {asset_path}[/red]")
                return False

            ken_burns_style = shot.ken_burns_style
            is_video = ken_burns_style.media_type == 'video'

            project_name = asset_path.parts[-3]
            assets_dir = settings.PROJECTS_ROOT_DIR / project_name / "assets"
            output_filename = f"{asset_path.stem}_animated.mp4"
            output_path = assets_dir / output_filename

            fps = 30
            progress_expr = self._generate_easing_expression(shot.duration_seconds, ken_burns_style.easing_function, fps)

            zoom_range = ken_burns_style.end_scale - ken_burns_style.start_scale
            zoom_expr = f"min({ken_burns_style.start_scale}+{zoom_range}*({progress_expr}), {ken_burns_style.end_scale})"
            
            start_x_norm, start_y_norm = ken_burns_style.start_position
            end_x_norm, end_y_norm = ken_burns_style.end_position
            pan_x_range = end_x_norm - start_x_norm
            pan_y_range = end_y_norm - start_y_norm
            x_base = f"(iw/2-(iw/zoom/2)) + ({start_x_norm}*(iw-iw/zoom))"
            y_base = f"(ih/2-(ih/zoom/2)) + ({start_y_norm}*(ih-ih/zoom))"
            x_expr = f"{x_base} + ({pan_x_range}*(iw-iw/zoom)*({progress_expr}))"
            y_expr = f"{y_base} + ({pan_y_range}*(ih-ih/zoom)*({progress_expr}))"

            # --- Corrected FFmpeg Command Builder ---
            cmd = ['ffmpeg']

            # 1. Declare ALL INPUTS first
            # Video/Image input
            if is_video:
                input_video_info = ffmpeg.probe(str(asset_path))
                input_duration = float(input_video_info['format']['duration'])
                if input_duration < shot.duration_seconds:
                    cmd.extend(['-stream_loop', '-1'])
                cmd.extend(['-i', str(asset_path)])
            else:  # is_image
                cmd.extend(['-loop', '1', '-i', str(asset_path)])

            # Audio input
            audio_path = shot.audio_path if shot.audio_path else False
            has_audio_input = audio_path and Path(audio_path).exists()
            if has_audio_input:
                cmd.extend(['-i', str(audio_path)])

            # 2. Declare FILTERS, MAPPING, and CODECS next
            # Video Filter
            if is_video:
                filter_str = f"zoompan=z='{zoom_expr}':x='{x_expr}':y='{y_expr}':d=1:s=1080x1920"
                cmd.extend(['-vf', filter_str])
            else:  # is_image
                total_frames = int(shot.duration_seconds * fps)
                filter_str = f"zoompan=z='{zoom_expr}':x='{x_expr}':y='{y_expr}':d={total_frames}:s=1080x1920"
                cmd.extend(['-vf', filter_str])

            # Stream Mapping and Audio Codec
            if has_audio_input:
                cmd.extend(['-map', '0:v:0', '-map', '1:a:0'])
                cmd.extend(['-c:a', 'aac', '-shortest'])
            else:
                cmd.append('-an')
            
            # Video Codec
            cmd.extend(['-c:v', 'libx264'])

            # 3. Declare OUTPUT options last
            # Image-specific output options
            if not is_video:
                cmd.extend(['-r', str(fps), '-pix_fmt', 'yuv420p'])

            cmd.extend([
                '-t', str(shot.duration_seconds),
                '-crf', '18',
                '-y', str(output_path)
            ])

            self.console.print(f"[blue]🎬 Applying Ken Burns Effect to {asset_path.name}:[/blue]")
            self.console.print(f"   Audio: {'Adding ' + Path(audio_path).name if audio_path and Path(audio_path).exists() else 'Removing original audio'}")

            # Log the effect being applied
            self.console.print(f"[blue]🎬 Applying Ken Burns Effect to {asset_path.name}:[/blue]")
            self.console.print(f"   Media Type: {ken_burns_style.media_type}")
            self.console.print(f"   Scale: {ken_burns_style.start_scale:.2f}x → {ken_burns_style.end_scale:.2f}x")
            self.console.print(f"   Position: ({start_x_norm:.2f}, {start_y_norm:.2f}) → ({end_x_norm:.2f}, {end_y_norm:.2f})")
            self.console.print(f"   Easing: {ken_burns_style.easing_function}")
            self.console.print(f"   Duration: {shot.duration_seconds:.2f}s")
            self.console.print(f"   Filter: {filter_str}")

            # Execute FFmpeg command
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                # Update the shot with the new animated video path
                shot.asset_path = str(output_path)
                shot.applyed_ken_burns = True

                self.console.print(f"[green]✅ Ken Burns effect applied successfully![/green]")
                self.console.print(f"   Output saved to: {output_path}")
                return True
            else:
                self.console.print(f"[red]❌ FFmpeg error: {result.stderr}[/red]")
                return False

        except Exception as e:
            self.console.print(f"[red]❌ Error applying Ken Burns effect: {e}[/red]")
            return False

    def _generate_easing_expression(self, duration_seconds: float, easing_function: str, fps: int = 30) -> str:
        """
        Generate FFmpeg expression with easing function for Ken Burns effect.

        Args:
            duration_seconds: Duration of the effect in seconds
            easing_function: Name of the easing function to use
            fps: Frames per second for the animation

        Returns:
            str: FFmpeg expression for the easing function
        """
        total_frames = int(duration_seconds * fps)

        # Generate expression based on easing type
        if easing_function == 'linear':
            progress = f"on/{total_frames}"
        elif 'quad' in easing_function:
            if 'in_out' in easing_function:
                progress = f"if(lt(on,{total_frames/2}), 0.5*pow(2*on/{total_frames}, 2), 1-0.5*pow(2*(1-on/{total_frames}), 2))"
            elif 'in' in easing_function:
                progress = f"pow(on/{total_frames}, 2)"
            else: # out
                progress = f"1-pow(1-on/{total_frames}, 2)"
        elif 'cubic' in easing_function:
            if 'in_out' in easing_function:
                progress = f"if(lt(on,{total_frames/2}), 0.5*pow(2*on/{total_frames}, 3), 1-0.5*pow(2*(1-on/{total_frames}), 3))"
            elif 'in' in easing_function:
                progress = f"pow(on/{total_frames}, 3)"
            else: # out
                progress = f"1-pow(1-on/{total_frames}, 3)"
        else:
            # Default to linear if unknown easing function
            progress = f"on/{total_frames}"

        return progress
    
    def _resize_video(self, clip: VideoClip, size: tuple[int, int]) -> VideoClip:
        """
        Resizes the given video clip to the specified size.

        Args:
            clip: The input VideoClip to resize.
            size: A tuple (width, height) specifying the target size.

        Returns:
            A resized VideoClip.
        """
        if clip.size == size:
            return clip
        return cast(VideoClip, clip.resized(new_size=size))
    
    def _create_ass_file_for_shot(self, timestamp_file: Optional[Path], output_dir: Optional[Path]) -> Path | None:
        """
        Creates an ASS file for the given shot's timestamp_file, displaying
        subtitles three words at a time with a karaoke effect.

        Args:
            timestamp_file: The path to the timestamp file for the shot.
            output_dir: The directory where the ASS file will be saved.

        Returns:
            The path to the created ASS file, or None if an error occurred.
        """
        if not timestamp_file or not output_dir:
            return None

        # Read the timestamp json file
        try:
            with open(timestamp_file, 'r', encoding='utf-8') as f:
                # Assuming Timestamp has a model_validate_json method
                timestamp = Timestamp.model_validate_json(f.read())
        except Exception as e:
            self.console.log(f"[red]Error reading or parsing timestamp file {timestamp_file}: {e}[/red]")
            return None

        # Combine characters into words and get their start/end times
        words = []
        word_start_indices = []
        word_end_indices = []
        current_word = ""
        current_start = None

        for i, char in enumerate(timestamp.characters):
            if char != " ":
                if not current_word:
                    current_start = i
                current_word += char
            else:
                if current_word:
                    words.append(current_word)
                    word_start_indices.append(current_start)
                    word_end_indices.append(i - 1)
                    current_word = ""
                    current_start = None
        
        # Handle the last word if the text doesn't end with a space
        if current_word:
            words.append(current_word)
            word_start_indices.append(current_start)
            word_end_indices.append(len(timestamp.characters) - 1)

        # Create word-level timestamps
        word_timestamps = []
        for idx, word in enumerate(words):
            start_idx = word_start_indices[idx]
            end_idx = word_end_indices[idx]
            word_timestamps.append({
                "word": word,
                "start": timestamp.character_start_times_seconds[start_idx],
                "end": timestamp.character_end_times_seconds[end_idx]
            })

        if not word_timestamps:
            self.console.log(f"[yellow]No words found in {timestamp_file}. ASS file not created.[/yellow]")
            return None

        # ASS file header
        ass_header = """[Script Info]
    Title: Generated by Shorts Engine
    ScriptType: v4.00+
    WrapStyle: 0
    PlayResX: 1080
    PlayResY: 1920
    ScaledBorderAndShadow: yes
    YCbCr Matrix: TV.709

    [V4+ Styles]
    Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
    Style: Default,Roboto Bold,62,&H0000FFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1.5,2,30,30,70,1

    [Events]
    Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
    """

        def format_ass_time(seconds: float) -> str:
            """Converts seconds to H:MM:SS.ss format for ASS."""
            if seconds < 0:
                seconds = 0
            h = int(seconds / 3600)
            m = int((seconds % 3600) / 60)
            s = seconds % 60
            return f"{h:d}:{m:02d}:{s:05.2f}"

        # Process words in chunks of two
        dialogue_lines = []
        chunk_size = 2
        for i in range(0, len(word_timestamps), chunk_size):
            chunk = word_timestamps[i:i + chunk_size]
            
            if not chunk:
                continue

            # Determine start and end time for the entire chunk
            chunk_start_time = chunk[0]["start"]
            chunk_end_time = chunk[-1]["end"]
            
            start_str = format_ass_time(chunk_start_time)
            end_str = format_ass_time(chunk_end_time)

            # Build the karaoke text for the current chunk
            dialogue_parts = []
            for j, word_info in enumerate(chunk):
                start_time = word_info["start"]
                
                # The duration of the highlight is until the next word starts
                if j < len(chunk) - 1:
                    next_word_start = chunk[j + 1]["start"]
                    duration_cs = max(0, int((next_word_start - start_time) * 100))
                else:
                    # For the last word in the chunk, use its own end time
                    duration_cs = max(0, int((word_info["end"] - start_time) * 100))

                dialogue_parts.append(f"{{\\K{duration_cs}}}{word_info['word']}")
            
            # Join the words for the current chunk
            chunk_text = " ".join(dialogue_parts)
            
            # Create the dialogue line for this chunk
            # Using {\q2} to prevent line breaking by the renderer
            full_text_line = f"{{\\q2}}{chunk_text}"
            dialogue_line = f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{full_text_line}"
            dialogue_lines.append(dialogue_line)

        ass_content = ass_header + "\n".join(dialogue_lines)
        
        # Write the content to the .ass file
        output_filename = timestamp_file.with_suffix('.ass').name
        output_path = output_dir / output_filename
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(ass_content)
            self.console.log(f"  [green]Successfully created ASS file:[/] {output_path.name}")
            return output_path
        except IOError as e:
            self.console.log(f"[red]Error writing ASS file to {output_path}: {e}[/red]")
            return None

    def add_effects_and_captions_and_audio_to_project_shots(self, project_name: str, version: str) -> bool:
        """
        Applies the Ken Burns effect, captions, and audio to the shots for a given project.

        Args:
            project_name: The name of the project.
            version: The version of the project.

        Returns:
            A boolean indicating whether the all shots in the project were processed successfully.
        """
        self.console.log(f"Applying Ken Burns effect to all shots in project: [cyan]{project_name}[/cyan]")

        # Load the blueprint for the project
        blueprint_path = settings.PROJECTS_ROOT_DIR / project_name / "blueprints" / f"final_{version}.json"
        if not blueprint_path.exists():
            self.console.log(f"[red]Blueprint file not found: {blueprint_path}[/red]")
            return False

        with open(blueprint_path, 'r', encoding='utf-8') as f:
            blueprint = Blueprint.model_validate_json(f.read())

        if not blueprint.scene or not blueprint.scene.shots:
            self.console.log(f"[red]No shots found in the blueprint for project: {project_name}[/red]")
            return False
        

        # Process each shot
        for i, shot in enumerate(blueprint.scene.shots):
            self.console.log(f"Processing Shot {i+1}/{len(blueprint.scene.shots)}: [cyan]{shot.script[:50]}...[/cyan]")
            output_dir = settings.PROJECTS_ROOT_DIR / project_name / "output"
            output_path = output_dir / f"{project_name}_{version}_shot_{i+1}.mp4"

            if shot.final_shot_video_generated:
                self.console.log(f"Shot {i+1} already has a final video: [cyan]{shot.asset_path}[/cyan]")
                continue

            # Apply Ken Burns effect
            try:
                if not shot.applyed_ken_burns:
                    self.console.log(f"  Ken Burns effect not applied for Shot {i+1}, applying now.")

                    animated_clip_generated = self._apply_ken_burns_and_audio(shot)

                    if not animated_clip_generated:
                        self.console.log(f"[red]Error applying Ken Burns effect for Shot {i+1}[/red]")
                        return False
                    
                    animated_clip = VideoFileClip(shot.asset_path).with_duration(shot.duration_seconds, change_end=True)

                    shot.applyed_ken_burns = True
                    shot.asset_path = str(output_path)

                    with open(blueprint_path, 'w', encoding='utf-8') as f:
                        f.write(blueprint.model_dump_json(indent=2))
                        self.console.log(f"Blueprint updated for project: [cyan]{project_name}[/cyan]")

                else:
                    self.console.log(f"  Ken Burns effect already applied for Shot {i+1}, using existing.")

                    try:
                        animated_clip = VideoFileClip(shot.asset_path)

                    except Exception as e:
                        self.console.log(f"[red]Error loading video file for Shot {i+1}: {e}[/red]")
                        return False
                
                if not shot.ass_file_generated:

                    self.console.log(f"  .ass file not generated yet for Shot {i+1}, generating now.")

                    ass_file_path = self._create_ass_file_for_shot(Path(shot.audio_path).with_suffix('.json') if shot.audio_path else None, settings.PROJECTS_ROOT_DIR / project_name / "audio" )

                    if not ass_file_path:
                        self.console.log(f"[red]Error creating ASS file for Shot {i+1}[/red]")
                        return False

                    shot.ass_file_generated = True
                    shot.ass_file_path = str(ass_file_path)

                    with open(blueprint_path, 'w', encoding='utf-8') as f:
                        f.write(blueprint.model_dump_json(indent=2))
                        self.console.log(f"Blueprint updated for project: [cyan]{project_name}[/cyan]")

                else:
                    self.console.log(f"   .ass file already generated for Shot {i+1}, using existing.")
                    ass_file_path = shot.ass_file_path

                # Resize the video to 1080x1920 (portrait)
                resized_clip = self._resize_video(animated_clip, (1080, 1920))

                # Escape the ASS file path for ffmpeg
                escaped_ass_path = str(ass_file_path).replace('\\', '/')

                resized_clip.write_videofile(
                    str(output_path),
                    fps=24,
                    codec='libx264',
                    audio=shot.audio_path if shot.audio_path else False,
                    audio_codec='aac',
                    threads=8,
                    preset='ultrafast',
                    ffmpeg_params=['-vf', f"ass={escaped_ass_path}"]
                )

                shot.asset_path = str(output_path)
                shot.final_shot_video_generated = True

                self.console.log(f"  Video generated and ASS file burned successfully for Shot {i+1}")

            except Exception as e:
                self.console.log(f"[red]Error applying Ken Burns effect for Shot {i+1}: {e}[/red]")
                return False
            

        blueprint.final_shots_videos_generated = True
        with open(blueprint_path, 'w', encoding='utf-8') as f:
                    f.write(blueprint.model_dump_json(indent=2))
        return True



