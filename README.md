# Gangle - Guess the Angle Game Bot 🎯

Gangle is a fun Telegram bot game where players compete to guess angles in group chats. Players view an angle image and submit their best guess, with points awarded based on accuracy!

## Features

- **Group-based gameplay**: Designed specifically for Telegram group chats
- **Interactive guessing**: Players use inline buttons to submit private guesses
- **Point system**: Rewards accuracy with a scaled scoring system (max 100 points)
- **Leaderboard**: Tracks player performance across rounds  
- **Admin controls**: Forfeit players or reset leaderboards
- **Clean interface**: Uses callback queries to avoid chat clutter

## How to Play

1. Type `/start_round` to begin a new round
2. The bot posts an angle image with a "Guess" button
3. Click the button to submit your guess privately (0-359 degrees)
4. Wait for all players to submit or admin to forfeit inactive players
5. View results with the correct angle, all guesses, and updated scores!

## Commands

- `/start_round` - Start a new game round (any player)
- `/leaderboard` - View current leaderboard (any player)  
- `/help` - Show commands and rules (any player)
- `/forfeit @username` - Remove player from current round (admin only)
- `/reset_leaderboard` - Reset all scores (admin only)

## Setup Instructions

### Prerequisites
- Python 3.8+
- A Telegram Bot Token (get one from @BotFather)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd gangle
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env and add your TELEGRAM_BOT_TOKEN
```

5. Run the bot:
```bash
python bot.py
```

## Configuration

Create a `.env` file with the following variables:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
LOG_LEVEL=INFO
DATA_DIR=./data
```

## Project Structure

```
gangle/
├── bot.py              # Main bot application
├── rendering.py        # Angle image generation
├── game_manager.py     # Game state and logic
├── storage.py          # Data persistence
├── config.py           # Configuration management
├── requirements.txt    # Python dependencies
├── .env.example        # Environment template
├── README.md           # This file
├── LICENSE             # MIT License
└── data/              # Game data storage
    ├── leaderboards/  # Group leaderboards
    └── games/         # Active game states
```

## Development

### Running Tests
```bash
python -m pytest tests/
```

### Code Style
This project follows PEP 8 guidelines. Format code with:
```bash
black .
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

If you encounter any issues or have questions, please open an issue on GitHub.

---

**Have fun guessing angles! 📐✨**
