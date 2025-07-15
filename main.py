# main.py (Example of how to use the new manager)

import typer
from rich.console import Console

from src.shorts_engine.core.models import TTSModelId
from src.shorts_engine.video.assembler import VideoAssembler
from src.shorts_engine.services.tts_client import TTSClient
from src.shorts_engine.video.EffectManager import EffectManager
from src.shorts_engine.core.blueprint_manager import BlueprintManager, ViralFormula

# Initialize components
console = Console()
app = typer.Typer()
blueprint_manager = BlueprintManager(console)
tts_client = TTSClient()
effect_manager = EffectManager(console)
video_assembler = VideoAssembler(console)



@app.command()
def new(
    project_name: str = typer.Argument(..., help="The name for the new project."),
    topic: str = typer.Argument(..., help="The central topic for the video."),
    version: str = typer.Option("A", "--version", "-v", help="The A/B test version identifier (e.g., A, B)."),
    formula: ViralFormula = typer.Option(
        ViralFormula.SECRET_VALUE, 
        "--formula", 
        "-f", 
        case_sensitive=False,
        help="The viral script formula to use."
    ),
    promotion: bool = typer.Option(True, "--promotion", "-p", help="Enable promotion for the project."),
    voice_model: TTSModelId = typer.Option(TTSModelId.ELEVEN_MULTILINGUAL_V2, "--voice-model", "-vm", case_sensitive=False, help="The voice model to use for TTS generation.")
):
    """
    Starts the interactive process to create a new project with its blueprint and assets.
    """
    console.print(f"\n[bold]🚀 Starting new blueprint generation for project: '{project_name}'[/bold]\n")
    try:
        return blueprint_manager.generate_blueprint_and_assets(
            project_name=project_name,
            topic=topic,
            version=version,
            formula=formula,
            promotion=promotion,
            TTS_model_id=voice_model
        )
    except Exception as e:
        console.print(f"\n[bold red]An error occurred during blueprint generation. Aborting.[/bold red]")
        return False
        

@app.command()
def generate_audio(
    project_name: str = typer.Argument(..., help="The name of the project to generate audio for."),
    version: str = typer.Option(..., "--version", "-v", help="The video version for the project (e.g., A, B).")
):
    """
    Generates audio files for the specified project and version.
    """
    console.print(f"\n[bold]🎤 Generating audio for project: '{project_name}', version: '{version}'[/bold]\n")
    try:
        if tts_client.generate_and_save_audio_for_project(project_name, version):
            console.print(f"[green]Audio successfully generated for project: {project_name}[/green]")
        else:
            console.print(f"[red]Failed to generate audio for project: {project_name}[/red]")
            return False
    except Exception as e:
        console.print(f"\n[bold red]An error occurred during audio generation: {e}[/bold red]")
        return False
    return True

@app.command()
def add_effect(
    project_name: str = typer.Argument(..., help="The name of the project to add effects to its shots."),
    version: str = typer.Option(..., "--version", "-v", help="The video version for the project to add effects to (e.g., A, B).")
):
    """
    Adds visual effects to the shots in the specified project.
    """
    console.print(f"\n[bold]🎬 Adding effects to project: '{project_name}', version: '{version}'[/bold]\n")
    try:
        if effect_manager.add_effects_and_captions_and_audio_to_project_shots(project_name, version):
            console.print(f"[green]Effects successfully applied to project: {project_name}[/green]")
        else:
            console.print(f"[red]Failed to apply effects to project: {project_name}[/red]")
            return False
    except Exception as e:
        console.print(f"\n[bold red]An error occurred during the build process: {e}[/bold red]")
        return False

    return True

@app.command()
def assemble(
    project_name: str = typer.Argument(..., help="The name of the project to assemble pre-rendered shots."),
    version: str = typer.Option(..., "--version", "-v", help="The video version for the project to assemble (e.g., A, B).")
):
    """
    Assembles pre-rendered shots into a final video for the specified project and version.
    """
    console.print(f"\n[bold]🔧 Assembling pre-rendered shots for project: '{project_name}', version: '{version}'[/bold]\n")
    try:
        if video_assembler.assemble(project_name, version):
            console.print(f"[green]Final video successfully assembled for project: {project_name}[/green]")
        else:
            console.print(f"[red]Failed to assemble final video for project: {project_name}[/red]")
            return False
    except Exception as e:
        console.print(f"\n[bold red]An error occurred during final assembly: {e}[/bold red]")
        return False
    return True

@app.command()
def run_all(
    project_name: str = typer.Argument(..., help="The name of the project to run all processes for."),
    topic: str = typer.Argument(..., help="The central topic for the video."),
    version: str = typer.Option("A", "--version", "-v", help="The A/B test version identifier (e.g., A, B)."),
    formula: ViralFormula = typer.Option(
        ViralFormula.SECRET_VALUE, 
        "--formula", 
        "-f", 
        case_sensitive=False,
        help="The viral script formula to use."
    ),
    promotion: bool = typer.Option(False, "--promotion", "-p", help="Enable promotion for the project."),
    voice_model: TTSModelId = typer.Option(TTSModelId.ELEVEN_MULTILINGUAL_V2, "--voice-model", "-vm", case_sensitive=False, help="The voice model to use for TTS generation.")
):
    """
    Runs all processes for the specified project: blueprint generation, audio generation, effect application, and final assembly.
    """
    if not new(project_name, topic, version, formula, promotion, voice_model):
        return

    if not generate_audio(project_name, version):
        return

    if not add_effect(project_name, version):
        return

    if not assemble(project_name, version):
        return

if __name__ == "__main__":
    app()