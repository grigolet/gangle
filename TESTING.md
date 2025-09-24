# Testing and Deployment Guide

## Quick Start Testing

### 1. Setup
```bash
# Make sure you're in the project directory
cd /path/to/gangle

# Run the setup script
./setup.sh

# Edit .env file with your bot token
cp .env.example .env
nano .env  # Add your TELEGRAM_BOT_TOKEN
```

### 2. Test Bot Locally
```bash
# Activate virtual environment
source venv/bin/activate

# Test imports and basic functionality
python -c "
from config import config
from game_manager import game_manager
from storage import storage
from rendering import render_angle
print('✅ All imports successful!')
print('✅ Config loaded')
print('✅ Game manager initialized')
print('✅ Storage system ready')
print('✅ Rendering system working')
"

# Start the bot (requires valid TELEGRAM_BOT_TOKEN)
python bot.py
```

### 3. Bot Commands to Test

1. **In a Telegram group chat:**
   - Add your bot to a group
   - Type `/help` to see all commands
   - Type `/start_round` to begin a game
   - Click the "Guess" button and submit a guess
   - Type `/leaderboard` to view scores

2. **Admin commands (group admins only):**
   - `/forfeit @username` to remove a player
   - `/reset_leaderboard` to clear all scores

## Configuration Options

### Environment Variables (.env file)
```env
# Required
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Optional (with defaults)
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR
DATA_DIR=./data                   # Where to store game data
MAX_PLAYERS_PER_ROUND=50          # Maximum players per round
ROUND_TIMEOUT_MINUTES=10          # Round timeout (not yet implemented)
POINTS_MAX=100                    # Maximum points for perfect guess
```

## Game Flow Testing Checklist

### Round Creation
- [ ] `/start_round` creates new round successfully
- [ ] Angle image is generated and displayed
- [ ] Inline "Guess" button appears
- [ ] Cannot start multiple rounds simultaneously

### Player Interaction
- [ ] Clicking "Guess" button opens private message
- [ ] Submitting valid guess (0-359) works
- [ ] Invalid guesses (negative, >359, non-numeric) are rejected
- [ ] Player can see their submitted guess
- [ ] Group shows "Player X has submitted" message

### Round Completion
- [ ] Round ends when all players submit or are forfeited
- [ ] Results show correct angle with label
- [ ] Leaderboard is updated correctly
- [ ] Points are calculated accurately (closer guess = more points)

### Leaderboard
- [ ] `/leaderboard` shows ranking by total points
- [ ] Player stats include: points, rounds played, best guess
- [ ] Empty leaderboard shows appropriate message

### Admin Features
- [ ] Only admins can use `/forfeit` and `/reset_leaderboard`
- [ ] Forfeiting works correctly
- [ ] Leaderboard reset creates backup and clears scores

### Error Handling
- [ ] Bot handles network errors gracefully
- [ ] Invalid commands show helpful messages
- [ ] Bot recovers from crashes (persistent storage)
- [ ] Private messages to bot are ignored (unless waiting for guess)

## Deployment Options

### Simple Server Deployment
```bash
# Copy project to server
scp -r gangle/ user@server:/path/to/

# On server
cd /path/to/gangle
./setup.sh
# Edit .env with production token

# Run with screen/tmux for persistence
screen -S gangle
source venv/bin/activate
python bot.py
# Ctrl+A+D to detach
```

### Docker Deployment
```dockerfile
# Create Dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN mkdir -p data/games data/leaderboards

CMD ["python", "bot.py"]
```

### Systemd Service
```ini
# /etc/systemd/system/gangle.service
[Unit]
Description=Gangle Telegram Bot
After=network.target

[Service]
Type=simple
User=gangle
WorkingDirectory=/opt/gangle
Environment=PATH=/opt/gangle/venv/bin
ExecStart=/opt/gangle/venv/bin/python bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## Monitoring and Logs

### Log Files
- Main log: `data/gangle.log`
- Console output shows real-time activity
- Log levels: DEBUG, INFO, WARNING, ERROR

### Key Metrics to Monitor
- Number of active groups
- Rounds played per day
- Player participation rates
- Error frequency
- Storage file sizes

## Troubleshooting

### Common Issues

1. **Import errors**
   - Ensure virtual environment is activated
   - Check all dependencies installed: `pip list`

2. **Bot doesn't respond**
   - Verify TELEGRAM_BOT_TOKEN is correct
   - Check bot is added to group and has proper permissions
   - Check logs for connection errors

3. **Storage issues**
   - Ensure `data/` directory has write permissions
   - Check disk space
   - Verify JSON files aren't corrupted

4. **Game state problems**
   - Check `data/games/` for stuck game files
   - Clear with: `rm data/games/game_*.json`
   - Bot will start fresh rounds

### Performance Considerations

- File-based storage is simple but may not scale to hundreds of concurrent groups
- Consider Redis or database for high-traffic deployments
- Monitor memory usage for matplotlib rendering
- Consider image caching for frequently used angles

## Security Notes

- Bot token should be kept secure
- File permissions on data directory should restrict access
- Consider rate limiting for production deployment
- Admin commands are protected by Telegram group admin status
- No sensitive data is stored (only usernames and scores)
