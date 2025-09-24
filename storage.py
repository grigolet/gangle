"""
Storage layer for persisting game state and leaderboards.
Uses JSON files for simple, reliable persistence.
"""
import json
import logging
from typing import Dict, Optional, Any
from datetime import datetime

from config import config

logger = logging.getLogger(__name__)


class StorageManager:
    """Manages file-based storage for game data."""
    
    def __init__(self):
        """Initialize the storage manager."""
        self.leaderboards_dir = config.leaderboards_dir
        self.games_dir = config.games_dir
    
    def load_leaderboard(self, group_id: int) -> Dict[int, Dict[str, Any]]:
        """
        Load leaderboard data for a group.
        
        Args:
            group_id: The Telegram group ID
            
        Returns:
            Dictionary mapping user_id to player stats:
            {
                user_id: {
                    'username': str,
                    'first_name': str,
                    'total_points': int,
                    'rounds_played': int,
                    'best_guess': int (closest guess in degrees),
                    'last_played': str (ISO timestamp)
                }
            }
        """
        file_path = config.get_leaderboard_file(group_id)
        
        if not file_path.exists():
            logger.info(f"No leaderboard file found for group {group_id}, returning empty")
            return {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert string keys back to integers
            return {int(k): v for k, v in data.items()}
        
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load leaderboard for group {group_id}: {e}")
            return {}
    
    def save_leaderboard(self, group_id: int, leaderboard: Dict[int, Dict[str, Any]]) -> bool:
        """
        Save leaderboard data for a group.
        
        Args:
            group_id: The Telegram group ID
            leaderboard: The leaderboard data to save
            
        Returns:
            True if saved successfully, False otherwise
        """
        file_path = config.get_leaderboard_file(group_id)
        
        try:
            # Convert integer keys to strings for JSON serialization
            json_data = {str(k): v for k, v in leaderboard.items()}
            
            # Create a backup if file exists
            if file_path.exists():
                backup_path = file_path.with_suffix('.json.bak')
                file_path.rename(backup_path)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Leaderboard saved for group {group_id}")
            return True
        
        except (IOError, OSError) as e:
            logger.error(f"Failed to save leaderboard for group {group_id}: {e}")
            return False
    
    def load_active_game(self, group_id: int) -> Optional[Dict[str, Any]]:
        """
        Load active game state for a group.
        
        Args:
            group_id: The Telegram group ID
            
        Returns:
            Game state dictionary or None if no active game:
            {
                'angle': int,
                'message_id': int,
                'start_time': str (ISO timestamp),
                'players': Dict[int, str],  # user_id -> username
                'guesses': Dict[int, int],  # user_id -> guess
                'forfeited': List[int],     # list of forfeited user_ids
                'status': str ('waiting_for_guesses' | 'completed')
            }
        """
        file_path = config.get_game_file(group_id)
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert string keys back to integers where needed
            if 'players' in data:
                data['players'] = {int(k): v for k, v in data['players'].items()}
            if 'guesses' in data:
                data['guesses'] = {int(k): v for k, v in data['guesses'].items()}
            
            return data
        
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load active game for group {group_id}: {e}")
            return None
    
    def save_active_game(self, group_id: int, game_state: Dict[str, Any]) -> bool:
        """
        Save active game state for a group.
        
        Args:
            group_id: The Telegram group ID
            game_state: The game state to save
            
        Returns:
            True if saved successfully, False otherwise
        """
        file_path = config.get_game_file(group_id)
        
        try:
            # Convert integer keys to strings for JSON serialization
            json_data = game_state.copy()
            if 'players' in json_data:
                json_data['players'] = {str(k): v for k, v in json_data['players'].items()}
            if 'guesses' in json_data:
                json_data['guesses'] = {str(k): v for k, v in json_data['guesses'].items()}
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Game state saved for group {group_id}")
            return True
        
        except (IOError, OSError) as e:
            logger.error(f"Failed to save game state for group {group_id}: {e}")
            return False
    
    def clear_active_game(self, group_id: int) -> bool:
        """
        Remove active game file for a group.
        
        Args:
            group_id: The Telegram group ID
            
        Returns:
            True if cleared successfully, False otherwise
        """
        file_path = config.get_game_file(group_id)
        
        try:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Active game cleared for group {group_id}")
            return True
        
        except OSError as e:
            logger.error(f"Failed to clear active game for group {group_id}: {e}")
            return False
    
    def update_player_stats(self, group_id: int, user_id: int, username: str, 
                          first_name: str, points: int, guess_accuracy: int) -> bool:
        """
        Update a player's statistics in the leaderboard.
        
        Args:
            group_id: The Telegram group ID
            user_id: The player's user ID
            username: The player's username
            first_name: The player's first name
            points: Points earned in the round
            guess_accuracy: How close the guess was (0 = perfect)
            
        Returns:
            True if updated successfully, False otherwise
        """
        leaderboard = self.load_leaderboard(group_id)
        
        # Initialize player stats if not exists
        if user_id not in leaderboard:
            leaderboard[user_id] = {
                'username': username,
                'first_name': first_name,
                'total_points': 0,
                'rounds_played': 0,
                'best_guess': 180,  # Start with worst possible accuracy
                'last_played': None
            }
        
        # Update stats
        player_stats = leaderboard[user_id]
        player_stats['username'] = username  # Update in case it changed
        player_stats['first_name'] = first_name
        player_stats['total_points'] += points
        player_stats['rounds_played'] += 1
        player_stats['best_guess'] = min(player_stats['best_guess'], guess_accuracy)
        player_stats['last_played'] = datetime.utcnow().isoformat()
        
        return self.save_leaderboard(group_id, leaderboard)
    
    def reset_leaderboard(self, group_id: int) -> bool:
        """
        Reset the leaderboard for a group.
        
        Args:
            group_id: The Telegram group ID
            
        Returns:
            True if reset successfully, False otherwise
        """
        file_path = config.get_leaderboard_file(group_id)
        
        try:
            if file_path.exists():
                # Create backup before deleting
                backup_path = file_path.with_suffix(f'.json.backup_{int(datetime.utcnow().timestamp())}')
                file_path.rename(backup_path)
                logger.info(f"Leaderboard reset for group {group_id}, backup saved as {backup_path.name}")
            return True
        
        except OSError as e:
            logger.error(f"Failed to reset leaderboard for group {group_id}: {e}")
            return False


# Global storage manager instance
storage = StorageManager()
