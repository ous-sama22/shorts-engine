@echo off
REM Docker setup script for Shorts Engine (Windows)

echo 🐳 Setting up Shorts Engine with Docker...

REM Check if Docker is installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker is not installed. Please install Docker Desktop first.
    exit /b 1
)

REM Check if Docker Compose is available
docker compose version >nul 2>&1
if %errorlevel% neq 0 (
    docker-compose --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo ❌ Docker Compose is not available. Please install Docker Desktop with Compose.
        exit /b 1
    )
)

REM Create .env file if it doesn't exist
if not exist .env (
    echo 📝 Creating .env file from template...
    copy .env.example .env
    echo ⚠️  Please edit the .env file and add your API keys before running the container.
    echo 📍 You can edit it with: notepad .env
) else (
    echo ✅ .env file already exists
)

REM Create necessary directories
echo 📁 Creating project directories...
if not exist projects mkdir projects
if not exist assets mkdir assets

REM Build the Docker image
echo 🔨 Building Docker image...
docker build -t shorts-engine .

echo ✅ Docker setup complete!
echo.
echo 🚀 You can now run the application using:
echo    docker-compose run --rm shorts-engine --help
echo.
echo 📖 Or use these example commands:
echo    # Create a new project
echo    docker-compose run --rm shorts-engine new "my_project" "AI technology"
echo.
echo    # Run the full pipeline
echo    docker-compose run --rm shorts-engine run-all "my_project" "AI technology"
echo.
echo    # For development with live code changes:
echo    docker-compose --profile dev run --rm shorts-engine-dev --help
