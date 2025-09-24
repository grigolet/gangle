#!/bin/bash
# Setup script for Gangle bot

echo "🎯 Setting up Gangle - Guess the Angle Bot..."

# Check Python version
python_version=$(python3 -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
echo "📍 Python version: $python_version"

if [[ $(echo "$python_version < 3.8" | bc -l) -eq 1 ]]; then
    echo "❌ Python 3.8 or higher is required"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Create .env file from template if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️ Creating .env file from template..."
    cp .env.example .env
    echo "📝 Please edit .env file and add your TELEGRAM_BOT_TOKEN"
fi

# Create data directories
echo "📁 Ensuring data directories exist..."
mkdir -p data/leaderboards data/games

# Make bot executable
chmod +x bot.py

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Edit .env file and add your Telegram bot token"
echo "2. Run the bot: python bot.py"
echo ""
echo "🎮 Have fun playing Gangle!"
