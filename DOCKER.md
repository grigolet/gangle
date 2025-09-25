# Docker Deployment Guide

## Quick Start

### Prerequisites
- Docker and Docker Compose installed
- Telegram bot token (get one from @BotFather)

### Setup Steps

1. **Clone the repository and navigate to the project directory:**
   ```bash
   git clone <repository-url>
   cd gangle
   ```

2. **Create environment file:**
   ```bash
   cp .env.example .env
   ```

3. **Edit the `.env` file and add your bot token:**
   ```bash
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   ```

4. **Build and run with Docker Compose:**
   ```bash
   docker-compose up -d
   ```

## Manual Docker Commands

### Build the image:
```bash
docker build -t gangle-bot .
```

### Run the container:
```bash
docker run -d \
  --name gangle-bot \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/gangle.log:/app/gangle.log \
  --restart unless-stopped \
  gangle-bot
```

## Management Commands

### View logs:
```bash
# Docker Compose
docker-compose logs -f

# Direct Docker
docker logs -f gangle-bot
```

### Stop the bot:
```bash
# Docker Compose
docker-compose down

# Direct Docker
docker stop gangle-bot
```

### Restart the bot:
```bash
# Docker Compose
docker-compose restart

# Direct Docker
docker restart gangle-bot
```

### Update the bot:
```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose up -d --build
```

## Configuration

### Environment Variables
All configuration is done through environment variables in the `.env` file:

- `TELEGRAM_BOT_TOKEN` - Your Telegram bot token (required)
- `LOG_LEVEL` - Logging level (default: INFO)
- `MAX_PLAYERS_PER_ROUND` - Maximum players per round (default: 50)
- `POINTS_MAX` - Maximum points for perfect guess (default: 100)
- `MIN_WAIT_TIME` - Minimum wait time before round can end (default: 30 seconds)
- `MAX_WAIT_TIME` - Maximum wait time before round force ends (default: 120 seconds)

### Data Persistence
The bot stores game data in the `data/` directory:
- `data/games/` - Active game sessions
- `data/leaderboards/` - Player statistics and leaderboards

This directory is mounted as a Docker volume to persist data between container restarts.

### Logs
Application logs are written to `gangle.log` in the project directory and are also mounted into the container.

## Production Deployment

For production deployment, consider:

1. **Security**: Never commit your `.env` file with real tokens
2. **Monitoring**: Set up log monitoring and alerting
3. **Backups**: Regular backups of the `data/` directory
4. **Updates**: Implement a proper CI/CD pipeline for updates
5. **Resource limits**: Monitor memory and CPU usage, adjust limits in docker-compose.yml if needed

## Troubleshooting

### Bot not starting:
1. Check logs: `docker-compose logs`
2. Verify bot token is correct in `.env`
3. Ensure no other instance is running with the same token

### Data not persisting:
1. Check volume mounts in docker-compose.yml
2. Verify file permissions on host `data/` directory
3. Ensure proper shutdown to flush data: `docker-compose down`

### Performance issues:
1. Monitor resource usage: `docker stats gangle-bot`
2. Adjust memory/CPU limits in docker-compose.yml
3. Check for log file size growth

## Development

For development with live code changes:
```bash
# Mount source code as volume for development
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

Create `docker-compose.dev.yml`:
```yaml
version: '3.8'
services:
  gangle-bot:
    volumes:
      - .:/app
    command: python -u bot.py
```
