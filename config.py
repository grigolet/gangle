"""
Configuration management for the Gangle bot.
Loads settings from environment variables and .env file.
"""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""
    
    def __init__(self):
        """Initialize configuration with default values and environment overrides."""
        # Bot configuration
        self.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not self.telegram_bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
        
        # Logging configuration
        self.log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        
        # Data storage configuration
        self.data_dir = Path(os.getenv('DATA_DIR', './data'))
        self.leaderboards_dir = self.data_dir / 'leaderboards'
        self.games_dir = self.data_dir / 'games'
        
        # Game configuration
        self.max_players_per_round = int(os.getenv('MAX_PLAYERS_PER_ROUND', '50'))
        self.round_timeout_minutes = int(os.getenv('ROUND_TIMEOUT_MINUTES', '10'))
        self.points_max = int(os.getenv('POINTS_MAX', '100'))
        
        # Ensure data directories exist
        self._ensure_directories()
        
        # Setup logging
        self._setup_logging()
    
    def _ensure_directories(self):
        """Create necessary directories if they don't exist."""
        self.data_dir.mkdir(exist_ok=True)
        self.leaderboards_dir.mkdir(exist_ok=True)
        self.games_dir.mkdir(exist_ok=True)
    
    def _setup_logging(self):
        """Configure logging for the application."""
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        logging.basicConfig(
            level=getattr(logging, self.log_level),
            format=log_format,
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(self.data_dir / 'gangle.log')
            ]
        )
    
    def get_leaderboard_file(self, group_id: int) -> Path:
        """Get the leaderboard file path for a specific group."""
        return self.leaderboards_dir / f"group_{group_id}.json"
    
    def get_game_file(self, group_id: int) -> Path:
        """Get the active game file path for a specific group."""
        return self.games_dir / f"game_{group_id}.json"


# Global configuration instance
config = Config()

# Logger for the module
logger = logging.getLogger(__name__)
