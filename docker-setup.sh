#!/bin/bash
# Docker setup script for Shorts Engine

set -e

echo "🐳 Setting up Shorts Engine with Docker..."

# Clone the repository if not already done
if [ ! -d "shorts-engine" ]; then
    echo "📦 Cloning Shorts Engine repository..."
    git clone https://github.com/ous-sama22/shorts-engine.git
    cd shorts-engine
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit the .env file and add your API keys before running the container."
    echo "📍 You can edit it with: nano .env"
else
    echo "✅ .env file already exists"
fi

# Create necessary directories
echo "📁 Creating project directories..."
mkdir -p projects assets

# Build the Docker image
echo "🔨 Building Docker image..."
docker build -t shorts-engine .

echo "✅ Docker setup complete!"
echo ""
echo "🚀 You can now enter the application container by running:"
echo "   docker-compose run --rm shorts-engine --help"
echo ""
echo "📖 Or use these example commands:"
echo "   # Create a new project"
echo "   docker-compose run --rm shorts-engine new 'my_project' 'AI technology'"
echo ""
echo "   # Run the full pipeline"
echo "   docker-compose run --rm shorts-engine run-all 'my_project' 'AI technology'"
echo ""
echo "   # For development with live code changes:"
echo "   docker-compose --profile dev run --rm shorts-engine-dev --help"
