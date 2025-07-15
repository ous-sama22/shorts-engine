# src/shorts_engine/video/assembler.py
from anyio import Path
from moviepy.video.compositing.CompositeVideoClip import concatenate_videoclips
from moviepy.video.io.VideoFileClip import VideoFileClip

from ..core.models import Blueprint
from ..config import settings
from rich.console import Console

class VideoAssembler:
    def __init__(self, console: Console):
        self.console = console

    def assemble(self, project_name: str, version: str) -> bool:
        """
        Assembles pre-rendered video shots into a single final video file.

        This function reads a blueprint, collects the asset paths for each shot,
        and concatenates them in order.

        Args:
            project_name: The name of the project.
            version: The version of the video in the project.

        Returns:
            bool: True if the assembly was successful, False otherwise.
        """
        self.console.log(f"[blue]Assembling pre-rendered shots for project: {project_name}, version: {version}[/blue]")

        # Load the blueprint for the project
        blueprint_path = settings.PROJECTS_ROOT_DIR / project_name / "blueprints" / f"final_{version}.json"
        if not blueprint_path.exists():
            self.console.log(f"[red]Blueprint file not found: {blueprint_path}[/red]")
            return False

        with open(blueprint_path, 'r', encoding='utf-8') as f:
            blueprint = Blueprint.model_validate_json(f.read())

        shots = blueprint.scene.shots
        if not blueprint.final_shots_videos_generated:
            self.console.log(f"[red]Final shots videos not generated for {project_name} version {version}.[/red]")
            return False
        
        if blueprint.rendered:
            self.console.log(f"[yellow]Project {project_name} version {version} has already been rendered.[/yellow]")
            return True
        
        if not shots:
            self.console.log(f"[red]No shots found in blueprint for {project_name} version {version}.[/red]")
            return False

        output_path = settings.PROJECTS_ROOT_DIR / project_name / "output" / f"{project_name}_{version}_final_video.mp4"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        clips_to_load = []
        try:
            # Collect paths of all shot assets
            for shot in shots:
                asset_path = Path(shot.asset_path)
                if not asset_path.exists():
                    self.console.log(f"[red]Asset file not found for shot {shot.shot_id}: {asset_path}[/red]")
                    return False
                clips_to_load.append(str(asset_path))

            self.console.log(f"Found {len(clips_to_load)} shots to concatenate.")

            # Load clips using a list comprehension and concatenate
            final_clip = concatenate_videoclips([VideoFileClip(c) for c in clips_to_load], method="compose")

            # Write the final assembled video
            self.console.log(f"Writing final video to: {output_path}")
            final_clip.write_videofile(
                str(output_path),
                codec="libx264",
                audio_codec="aac"
            )

            self.console.log(f"[green]✅ Successfully assembled final video![/green]")

            # Update the blueprint to mark it as rendered
            blueprint.rendered = True
            blueprint.output_path = str(output_path)
            with open(blueprint_path, 'w', encoding='utf-8') as f:
                f.write(blueprint.model_dump_json(indent=2))
            return True

        except Exception as e:
            self.console.log(f"[bold red]An unexpected error occurred during final assembly: {e}[/bold red]")
            return False
        finally:
            # Close the final clip to release file handles
            if 'final_clip' in locals():
                final_clip.close()