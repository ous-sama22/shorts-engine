# src/shorts_engine/core/blueprint_manager.py

import json
from pathlib import Path
from random import random, choice
import shutil
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from ..config import settings
from .models import Blueprint, DraftBlueprint, KenBurnsStyle, TTSModelId, ViralFormula, Shot, VoiceSettings, TextStyle, Scene
import pyperclip

class BlueprintManager:
    """
    Manages the creation of video blueprints.
    This class handles the interactive process of generating a script and visual plan
    by creating a prompt for an LLM and providing it to the user and getting the response (DraftBlueprint), then validating its response and saving it as draft_{Version}.json.
    loop through the visuals and prompting the user the visual prompt from draft_{Version}.json and the user will generate the assets and save them in the assets folder of the project and input back the filename of the asset.
    """

    def __init__(self, console: Console):
        self.console = console

    def _generate_master_prompt(
        self,
        topic: str,
        project_name: str,
        version: str,
        formula: ViralFormula,
        promotion: bool
    ) -> str:
        """
        Generates the master "system prompt" to be given to the LLM.

        This prompt instructs the LLM on its role, the desired JSON output format,
        and the constraints for script and visual generation.
        """
        prompt = f"""
You are an expert YouTube Shorts scriptwriter and creative director. Your task is to generate a complete creative plan for a short video based on the user's topic. You must output your response as a single, valid JSON object and nothing else.

**Video Details:**
- **Project Name:** "{project_name}"
- **Version:** "{version}" (For A/B Testing)
- **Topic:** "{topic}"
- **Script Formula:** "{formula.value}"
- **Promotion:** {promotion}

**JSON Output Schema:**
You must adhere strictly to the following JSON structure. Do not add any extra keys or deviate from the types.

{{
  "project_name": "{project_name}",
  "version": "{version}",
  "video_title": "A compelling title for the video, under 60 characters.",
  "video_description": "A brief description of the video content, under 150 characters.",
  "script_formula": "{formula.value}",
  "shots": [
    {{
      "script_text": "A block of 1-3 sentences for the narration of this scene.",
      "visual": {{
        "visual_type": "ai_image | stock_asset",
        "prompt_or_filename": "A detailed, cinematic prompt for an AI model (like Google image generation, or ChatGPT image generation, or DALL-E) OR a descriptive filename for a pre-existing stock asset."
      }}
    }},
    ...
    {{
      "script_text": "A clear, compelling Call-to-Action for the end of the video.",
      "visual": {{
        "visual_type": "ai_image | stock_asset",
        "prompt_or_filename": "A detailed, cinematic prompt for an AI model (like Google image generation, or ChatGPT image generation, or DALL-E) OR a descriptive filename for a pre-existing stock asset."
      }}
    }}
  ],
}}

**CRITICAL INSTRUCTIONS:**

1.  **video_title**:
    - Must be under 60 characters.
    - Based on the script_formula.

2.  **video_description**:
    - Must be under 150 characters.
    - Based on the script_formula.
    - Include relevant hashtags like #Shorts, #Viral, etc.
    - Always include the hashtag "#YassineProducts" in the description IF the promotion is True.

3.  **`visual_type`**:
    - Use `'ai_image'` for static shots that can be animated with a Ken Burns effect. Prefer male personas over female ones.
    - Use `'stock_asset'` when promotion is True, for when a real product image or pre-existing media is best. Use a descriptive placeholder filename like `'moroccan_herb_close_up.png'`.

4.  **`prompt_or_filename`**:
    - For `'ai_image'`, write a rich, cinematic prompt. Describe the scene, lighting, camera angle, and mood. Insure to prompt for 1080×1920 resolution, 9:16.  Example: "Cinematic close-up of a rare, glowing herb on an ancient wooden table, dust motes dancing in a single sunbeam, mysterious and magical. Resolution: 1080x1920, Aspect Ratio: 9:16.".
    - For `'stock_asset'`, just provide the filename.

5.  **`script_text`**:
    - Write engaging, natural-sounding narration.
    - Do not include any reference citations or source numbers (like [1], [2], [2, 4] etc.) in the script.
    - The total video length should be under 40 seconds. A good target is 5-8 shots.

6.  **`Call-to-Action`**:
    - Always include a clear, compelling Call-to-Action at the end of the video. UNLESS the script_formula is `'{ViralFormula.INFINITE_LOOP}'`, in which case the Call-to-Action is omitted.

**EXAMPLE OUTPUT:**

{{
  "project_name": "Henna",
  "version": "A",
  "video_title": "How Moroccans Use Henna Traditionally",
  "video_description": "Discover how henna is used in Morocco's culture and rituals. #Shorts #Morocco #Henna #YassineProducts",
  "script_formula": "Pre-Hook, Hook, Story, End",
  "shots": [
    {{
      "script_text": "Ever wondered what secrets Moroccan henna holds?",
      "visual": {{
        "visual_type": "ai_image",
        "prompt_or_filename": "A mysterious shot of a Berber woman preparing a henna paste under candlelight, shadows flickering on the mud-brick wall. Resolution: 1080x1920, Aspect Ratio: 9:16."
      }}
    }},
    {{
      "script_text": "In Morocco, henna isn't just decoration. It's tradition, healing, and protection.",
      "visual": {{
        "visual_type": "ai_image",
        "prompt_or_filename": "A cinematic scene of Moroccan women applying henna during a wedding ceremony, joyful atmosphere, natural lighting, 9:16, 1080x1920."
      }}
    }},
    {{
      "script_text": "From celebrations to spiritual rituals, henna marks life's most sacred moments.",
      "visual": {{
        "visual_type": "ai_image",
        "prompt_or_filename": "Top-down shot of an ornate Moroccan henna design freshly applied to hands, surrounded by rose petals and herbs. Warm lighting. 1080x1920, 9:16"
      }}
    }},
    {{
      "script_text": "And yes, we use the finest organic henna—just like our ancestors did.",
      "visual": {{
        "visual_type": "stock_asset",
        "prompt_or_filename": "moroccan_herb_close_up.png"
      }}
    }},
    {{
      "script_text": "Henna in Morocco isn't a trend—it's heritage.",
      "visual": {{
        "visual_type": "ai_image",
        "prompt_or_filename": "Portrait of an elderly Moroccan woman smiling with henna-stained hands, traditional Amazigh jewelry, warm sunlight hitting her face. 1080x1920, 9:16"
      }}
    }},
    {{
      "script_text": "So, next time you see henna, remember its rich history and cultural significance.",
      "visual": {{
        "visual_type": "ai_image",
        "prompt_or_filename": "A beautiful arrangement of henna plants and traditional Moroccan tools on a wooden table. 1080x1920, 9:16"
      }}
    }},
    {{
      "script_text": "Get your own Moroccan henna—link in description and first comment!",
      "visual": {{
        "visual_type": "ai_image",
        "prompt_or_filename": "A vibrant, eye-catching graphic with the text 'Get Your Authentic Moroccan Henna!' in bold, traditional Arabic calligraphy style, set against a rich, textured background of Moroccan patterns. 1080x1920, 9:16"
      }}
    }}
  ]
}}
"""
        return prompt.strip()

    def _create_project_directory(self, project_name: str) -> Path:
        """Creates the necessary directory structure for a new project."""
        project_dir = settings.PROJECTS_ROOT_DIR / project_name
        project_dir.mkdir(exist_ok=True)
        (project_dir / "assets").mkdir(exist_ok=True)
        (project_dir / "audio").mkdir(exist_ok=True)
        (project_dir / "blueprints").mkdir(exist_ok=True)
        (project_dir / "output").mkdir(exist_ok=True)
        self.console.log(f"Project directory structure ensured at [cyan]'{project_dir}'[/cyan]")
        return project_dir

    def _generate_assets_from_draft_and_final_blueprint(
        self,
        draft_blueprint: DraftBlueprint,
        TTS_voice_id: str,
        TTS_model_id: TTSModelId,
        promotion: bool
    ) -> bool:
        """
        Processes the draft blueprint to prompt the user for visual assets.
        This method will read the draft blueprint, prompt the user for each visual, and expect the user to generate the assets manually and save them in the assets folder, getting the filenames back,
        Save the final blueprints in the blueprints folder.
        """
        
        self.console.print(f"\n[bold]💧 Processing Draft Blueprint '{draft_blueprint.project_name}' - Version '{draft_blueprint.version}'[/bold]\n")

        # ask the user to enter the folder to look for the assets
        initial_asset_folder = Prompt.ask(f"[yellow]▶[/yellow] Enter default download folder path where the assets will be downloaded after you generate them. (default: {str(Path.home() / 'Downloads')})", default= str(Path.home() / "Downloads"))
        initial_asset_folder_path = initial_asset_folder

        Shots = []
        for i, shot in enumerate(draft_blueprint.shots):
            self.console.print(f"\n[bold yellow]Shot {i+1}[/bold yellow]: {shot.script_text}")
            visual = shot.visual
            self.console.print(Panel(
                "[bold]1. The prompt had copied, paste the entire text block below (between the dashed lines. It already being copied, no need to copy it again).\n2. Paste it into your preferred asset generation tool.[/bold]",
                title=f"[bold yellow]Type: {visual.visual_type}[/bold yellow]",
                border_style="yellow",
                padding=(1, 2)
            ))

            # Copy the prompt to the clipboard
            pyperclip.copy(visual.prompt_or_filename)

            # Print the actual prompt as clean text, framed by separators for clarity.
            # This is the prompt for the user to see.
            self.console.print("\n" + "-"*80)
            self.console.print(visual.prompt_or_filename)
            self.console.print("-" * 80 + "\n")

            self.console.print("\n[bold green]Waiting for your input...[/bold green]")
            self.console.print("\n[bold green]Waiting for your input...[/bold green]")
                    
            generation_completed = Prompt.ask(
                f"[yellow]▶[/yellow] When you complete the asset generation, click any key to continue or 'N' To cancel the process.",
            )

            if generation_completed.lower() == 'n':
                self.console.print("[bold red]Process cancelled by user.[/bold red]")
                # confirm if the user wants to cancel the process
                if Prompt.ask("[yellow]▶[/yellow] Are you sure you want to cancel the process? (y/n)", default="n").lower() != 'y':
                    self.console.print("[bold green]Process resumed.[/bold green]")
                    return False
            
            # check the files in the initial asset folder and sort them by creation time and get the last file. Required the file to be not more than 1 minute old. 
            asset_files = list(Path(initial_asset_folder_path).glob("*.png"))
            asset_files = [f for f in asset_files if f.stat().st_mtime > (Path(initial_asset_folder_path).stat().st_mtime - 60)]
            if not asset_files:
                self.console.print(f"[bold red]Error:[/bold red] No assets found in the folder '{initial_asset_folder_path}'. Please ensure you have generated the assets and saved them in the folder.")
                # prompt the user to put new assets in the folder
                generation_completed = Prompt.ask(
                    f"[yellow]▶[/yellow] No assets found in the folder '{initial_asset_folder_path}'. Please ensure you have generated the assets and saved them in the folder. Type 'y' to continue or 'N' To cancel the process.",
                )

                if generation_completed.lower() != 'y':
                    self.console.print("[bold red]Process cancelled by user.[/bold red]")
                    # confirm if the user wants to cancel the process
                    if Prompt.ask("[yellow]▶[/yellow] Are you sure you want to cancel the process? (y/n)", default="n").lower() != 'y':
                        self.console.print("[bold green]Process resumed.[/bold green]")
                        return False
            
            # Sort files by creation time and get the last one
            asset_files.sort(key=lambda f: f.stat().st_mtime, reverse=True) 
            asset_file = asset_files[0]  # Get the most recent file
            final_filename = asset_file.name
            new_filename = "visual_" + str(i+1) + "_" + draft_blueprint.version + Path(final_filename).suffix

            shutil.copy2(asset_file, settings.PROJECTS_ROOT_DIR / draft_blueprint.project_name / "assets" / new_filename)

            # He check if the file exists
            asset_path = settings.PROJECTS_ROOT_DIR / draft_blueprint.project_name / "assets" / new_filename
            if not asset_path.exists():
                self.console.print(f"[bold red]Error:[/bold red] Asset file [cyan]{final_filename}[/cyan] does not exist in the assets folder.")
                # prompt the user to re-enter the filename
                final_filename = Prompt.ask(
                    f"[yellow]▶[/yellow] Asset file not found. Please ensure the asset exists in the assets folder for the project and re-enter the final filename (e.g., visual_{i+1}.mp4)"
                )
                asset_path = settings.PROJECTS_ROOT_DIR / draft_blueprint.project_name / "assets" / final_filename
            if not asset_path.exists():
                self.console.print(f"[bold red]Error:[/bold red] Asset file [cyan]{final_filename}[/cyan] still does not exist in the assets folder.")
                return False
            
            shot = Shot(
                shot_id=f"shot_{i+1}_{draft_blueprint.version}",
                asset_path=str(asset_path),
                script=shot.script_text,
                ken_burns_style=KenBurnsStyle(
                    media_type='video' if visual.visual_type == 'ai_video' else 'image',
                    start_scale=1.0,
                    end_scale=1.0 + random() * 0.20,  # Randomly between 0.25 and 0.50 vary the end scale slightly
                    easing_function=choice([
                        'linear', 'ease_in_quad', 'ease_out_quad', 'ease_in_out_quad',
                        'ease_in_cubic', 'ease_out_cubic', 'ease_in_out_cubic'
                    ])
                )
            )

            Shots.append(shot)

            self.console.print(f"\n[bold green]Asset generation complete successfully for shot {i+1}![/bold green]")

        self.console.print("\n[bold green]Asset generation complete successfully for all shots![/bold green]")

        scene = Scene(
            scene_id=f"scene_{draft_blueprint.version}",
            shots=Shots
        )
        blueprint = Blueprint(
            project_name=draft_blueprint.project_name,
            TTS_voice_id=TTS_voice_id,
            TTS_model_id=TTS_model_id,
            video_title=draft_blueprint.video_title,
            video_description=draft_blueprint.video_description,
            scene=scene,
            script_formula=draft_blueprint.script_formula,
            promotion=promotion,
            version=draft_blueprint.version,
            output_path=None  # This will be set later when rendering
        )
        output_path = settings.PROJECTS_ROOT_DIR / draft_blueprint.project_name / "blueprints" / f"final_{draft_blueprint.version}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(blueprint.model_dump_json(indent=2))

        self.console.log(f"[bold green]✓ Final Blueprint saved to [cyan]{output_path}[/cyan][/bold green]")
        return True
    def _get_existing_blueprint(self, project_name: str, version: str) -> Blueprint | None:
        """
        Checks if a blueprint already exists for the given project name and version.
        Returns the existing Blueprint object if found, otherwise None.
        """
        blueprint_path = settings.PROJECTS_ROOT_DIR / project_name / "blueprints" / f"final_{version}.json"
        if blueprint_path.exists():
            with open(blueprint_path, 'r', encoding='utf-8') as f:
                return Blueprint.model_validate_json(f.read())
        return None
    def generate_blueprint_and_assets(
        self,
        project_name: str,
        topic: str,
        version: str = "A",
        formula: ViralFormula = ViralFormula.SECRET_VALUE,
        promotion: bool = False,
        TTS_voice_id: str = settings.DEFAULT_TTS_VOICE_ID,
        TTS_model_id: TTSModelId = settings.DEFAULT_TTS_MODEL_ID
    ) -> bool:
        """
        Orchestrates the interactive process of creating a final blueprint.
        """
        # return early if the project with the same version already exists
        existing_blueprint = self._get_existing_blueprint(project_name, version)
        if existing_blueprint:
            self.console.print(f"[yellow]Blueprint for project '{project_name}' (version {version}) already exists.[/yellow]")
            return True

        master_prompt = self._generate_master_prompt(
            topic=topic,
            project_name=project_name,
            version=version,
            formula=formula,
            promotion=promotion
        )

        self.console.print(Panel(
            "[bold]1. Paste the entire text block below (between the dashed lines).\n2. Paste it into your preferred LLM as the system prompt.[/bold]",
            title="[bold yellow]ACTION REQUIRED[/bold yellow]",
            border_style="yellow",
            padding=(1, 2)
        ))

        # Copy the prompt to the clipboard
        pyperclip.copy(master_prompt)

        # Print the actual prompt as clean text, framed by separators for clarity.
        # This is the part the user WILL copy.
        self.console.print("\n" + "-"*80)
        self.console.print(master_prompt)
        self.console.print("-" * 80 + "\n")

        self.console.print("\n[bold green]Waiting for your input...[/bold green]")
        llm_json_response = Prompt.ask(
            "[yellow]▶[/yellow] Paste the full JSON response from the LLM here"
        )

        try:
            # Validate the received JSON against our DraftBlueprint Pydantic model
            draft_blueprint = DraftBlueprint.model_validate_json(llm_json_response)
            
            self.console.log(f"[bold green]✓ Success![/bold green] Validated draft blueprint, creating the project folder and processing the assets...")
            # Create the project directory structure
            self._create_project_directory(project_name)

            assets_generated = self._generate_assets_from_draft_and_final_blueprint(
                draft_blueprint=draft_blueprint,
                TTS_voice_id=TTS_voice_id,
                TTS_model_id=TTS_model_id,
                promotion=promotion
            )
            if not assets_generated:
                self.console.print("[bold red]Error:[/bold red] Asset generation failed. Please try again.")
                raise

            self.console.log(f"[bold green]✓ Success![/bold green] blueprint & assets generated successfully.")

        except json.JSONDecodeError:
            self.console.print("[bold red]Error:[/bold red] The provided text is not valid JSON.")
            raise
        except Exception as e:
            self.console.print(f"[bold red]Validation Error:[/bold red] The JSON does not match the required schema. Details: {e}")
            raise

        return True