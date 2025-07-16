# Shorts Engine

A powerful toolkit for creating and producing viral short-form video content. This engine automates the end-to-end process of generating, assembling, and preparing short videos optimized for platforms like YouTube Shorts and TikTok.

## Overview

Shorts Engine streamlines the creation of short-form videos through a series of interconnected modules that handle everything from script generation to final video assembly. The system uses a blueprint-based approach where each video project follows a defined structure, with support for A/B testing different versions.

## Features

- **Blueprint Generation**: Create comprehensive blueprints for video projects based on topics and viral formulas
- **Asset Management**: Integrate AI-generated images and stock assets into your videos
- **Text-to-Speech Integration**: Automate voiceover generation using ElevenLabs API
- **Visual Effects**: Apply professional effects like Ken Burns, captions, and transitions
- **Video Assembly**: Automatically combine all elements into final videos optimized for vertical formats (9:16)
- **A/B Testing**: Create multiple versions of videos to test different approaches

## Installation

### Option 1: Docker Installation (Recommended)

Docker provides an isolated environment with all dependencies pre-installed, including FFmpeg.

#### Prerequisites
- Docker Desktop (Windows/Mac) or Docker Engine (Linux)
- Docker Compose

#### Quick Setup
```bash
# Clone the repository
git clone https://github.com/ous-sama22/shorts-engine.git
cd shorts-engine

# Run the setup script
# On Linux/Mac:
chmod +x docker-setup.sh && ./docker-setup.sh

# On Windows:
docker-setup.bat

# Edit the .env file with your API keys
# Linux/Mac: nano .env
# Windows: notepad .env

# Test the installation
docker-compose run --rm shorts-engine --help
```

#### Docker Usage Examples
```bash
# Create a new project
docker-compose run --rm shorts-engine new "my_project" "AI technology"

# Generate audio for existing project
docker-compose run --rm shorts-engine generate-audio "my_project" --version A

# Run the complete pipeline
docker-compose run --rm shorts-engine run-all "my_project" "AI technology" --version A

# Development mode (live code changes)
docker-compose --profile dev run --rm shorts-engine-dev --help
```

### Option 2: Local Installation

For local development or if you prefer not to use Docker:

##### Prerequisites
- Python 3.10+
- FFmpeg (required for video processing)

#### Setup
```bash
# Clone the repository
git clone https://github.com/ous-sama22/shorts-engine.git
cd shorts-engine

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template and configure
cp .env.example .env
# Edit .env with your API keys
```

## Usage

Shorts Engine is designed to be used as a command-line tool:

```bash
# Create a new project
python main.py new "project_name" "topic" --version A --formula SECRET_VALUE --promotion

# Generate audio for a project
python main.py generate-audio "project_name" --version A

# Add visual effects to a project
python main.py add-effect "project_name" --version A

# Assemble the final video
python main.py assemble "project_name" --version A

# Run the entire pipeline in one command
python main.py run-all "project_name" "topic" --version A --formula SECRET_VALUE --promotion
```

## Project Structure

```
project_name/
├── assets/       # Contains visual assets for each shot
├── audio/        # Contains generated audio files and metadata
├── blueprints/   # Contains draft and final blueprint JSON files
└── output/       # Contains rendered shot videos and final assembled video
```

## Blueprint Structure

Each video project is defined by a blueprint JSON file that includes:

- Project metadata (name, version, title, description)
- Script formula used
- List of shots, each with:
  - Script text for narration
  - Visual asset details
  - Voice settings
  - Ken Burns effect settings

## Workflow

1. **Blueprint Generation**:
   - User provides a topic and formula
   - System generates a master prompt for an LLM
   - User obtains JSON response and validates it
   - System saves as a draft blueprint

2. **Asset Generation**:
   - System presents prompts for each shot's visual
   - User generates assets using their preferred tool
   - Assets are saved in the project's assets folder

3. **Audio Generation**:
   - System converts script text to speech using ElevenLabs
   - Audio files are saved with metadata

4. **Effect Application**:
   - Ken Burns effects are applied to static images
   - Captions are generated and added
   - Audio is synchronized

5. **Final Assembly**:
   - Individual shots are combined into a final video
   - Output is optimized for vertical viewing (9:16)

## Configuration

Environment variables can be set in a `.env` file for API keys and other settings.

## Dependencies

- typer: Command-line interface framework
- rich: Terminal formatting and display
- pydantic: Data validation and settings management
- elevenlabs: Text-to-speech API client
- moviepy: Video editing and processing
- ffmpeg-python: FFmpeg integration for advanced video operations

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.