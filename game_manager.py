"""
Game state management for Gangle bot rounds.
Handles round creation, player management, scoring, and leaderboards.
"""
import logging
import random
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from config import config
from storage import storage

logger = logging.getLogger(__name__)


@dataclass
class Player:
    """Represents a player in the game."""
    user_id: int
    username: str
    first_name: str
    guess: Optional[int] = None
    is_forfeited: bool = False


@dataclass
class GameRound:
    """Represents a single game round."""
    group_id: int
    angle: int
    message_id: int
    start_time: datetime
    players: Dict[int, Player]
    status: str  # 'waiting_for_guesses' or 'completed'
    angle_image_message_id: Optional[int] = None  # Message ID of the angle image with guess button
    starter_user_id: Optional[int] = None  # User who started this round
    estimated_players: int = 2  # Estimated number of potential players in the group
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert round to dictionary for storage."""
        return {
            'angle': self.angle,
            'message_id': self.message_id,
            'angle_image_message_id': self.angle_image_message_id,
            'start_time': self.start_time.isoformat(),
            'players': {str(uid): p.username for uid, p in self.players.items()},
            'guesses': {str(uid): p.guess for uid, p in self.players.items() if p.guess is not None},
            'forfeited': [uid for uid, p in self.players.items() if p.is_forfeited],
            'status': self.status,
            'starter_user_id': self.starter_user_id,
            'estimated_players': self.estimated_players
        }
    
    @classmethod
    def from_dict(cls, group_id: int, data: Dict[str, Any]) -> 'GameRound':
        """Create round from dictionary loaded from storage."""
        players = {}
        
        # Reconstruct players
        player_data = data.get('players', {})
        guesses = data.get('guesses', {})
        forfeited = data.get('forfeited', [])
        
        for user_id_str, username in player_data.items():
            user_id = int(user_id_str)
            guess = guesses.get(user_id_str)
            is_forfeited = user_id in forfeited
            
            players[user_id] = Player(
                user_id=user_id,
                username=username,
                first_name="",  # We'll update this when player interacts
                guess=guess,
                is_forfeited=is_forfeited
            )
        
        return cls(
            group_id=group_id,
            angle=data['angle'],
            message_id=data['message_id'],
            start_time=datetime.fromisoformat(data['start_time']),
            players=players,
            status=data['status'],
            angle_image_message_id=data.get('angle_image_message_id'),
            starter_user_id=data.get('starter_user_id'),
            estimated_players=data.get('estimated_players', 2)
        )


class GameManager:
    """Manages game rounds and player interactions."""
    
    def __init__(self):
        """Initialize the game manager."""
        self.active_rounds: Dict[int, GameRound] = {}
        self._load_active_rounds()
    
    def _load_active_rounds(self):
        """Load any existing active rounds from storage."""
        # This would be called on bot startup to restore state
        logger.info("Loading active rounds from storage...")
        # Implementation would scan the games directory and load active rounds
    
    def create_round(self, group_id: int, message_id: int, starter_user_id: Optional[int] = None) -> GameRound:
        """
        Create a new game round.
        
        Args:
            group_id: The Telegram group ID
            message_id: The message ID of the round announcement
            starter_user_id: The user ID of who started this round
            
        Returns:
            The created GameRound
            
        Raises:
            ValueError: If a round is already active for this group
        """
        if group_id in self.active_rounds:
            raise ValueError(f"Round already active for group {group_id}")
        
        # Generate random angle (0-359 degrees)
        angle = random.randint(0, 359)
        
        round_obj = GameRound(
            group_id=group_id,
            angle=angle,
            message_id=message_id,
            start_time=datetime.utcnow(),
            players={},
            status='waiting_for_guesses',
            starter_user_id=starter_user_id
        )
        
        self.active_rounds[group_id] = round_obj
        storage.save_active_game(group_id, round_obj.to_dict())
        
        logger.info(f"Created new round for group {group_id} with angle {angle}°")
        return round_obj
    
    def get_active_round(self, group_id: int) -> Optional[GameRound]:
        """Get the active round for a group."""
        if group_id in self.active_rounds:
            return self.active_rounds[group_id]
        
        # Try loading from storage
        game_data = storage.load_active_game(group_id)
        if game_data and game_data.get('status') == 'waiting_for_guesses':
            round_obj = GameRound.from_dict(group_id, game_data)
            self.active_rounds[group_id] = round_obj
            return round_obj
        
        return None
    
    def set_estimated_players(self, group_id: int, estimated_count: int):
        """Set the estimated number of players for an active round."""
        round_obj = self.get_active_round(group_id)
        if round_obj:
            round_obj.estimated_players = max(2, estimated_count)
            storage.save_active_game(group_id, round_obj.to_dict())
            logger.info(f"Set estimated players to {round_obj.estimated_players} for group {group_id}")
    
    def set_angle_image_message_id(self, group_id: int, message_id: int) -> bool:
        """
        Set the angle image message ID for the active round.
        
        Args:
            group_id: The Telegram group ID  
            message_id: The message ID of the angle image with guess button
            
        Returns:
            True if set successfully, False otherwise
        """
        round_obj = self.get_active_round(group_id)
        if not round_obj:
            return False
        
        round_obj.angle_image_message_id = message_id
        storage.save_active_game(group_id, round_obj.to_dict())
        logger.info(f"Set angle image message ID to {message_id} for group {group_id}")
        return True
    
    def add_player(self, group_id: int, user_id: int, username: str, first_name: str) -> bool:
        """
        Add a player to the current round.
        
        Args:
            group_id: The Telegram group ID
            user_id: The player's user ID
            username: The player's username
            first_name: The player's first name
            
        Returns:
            True if player was added successfully, False otherwise
        """
        round_obj = self.get_active_round(group_id)
        if not round_obj or round_obj.status != 'waiting_for_guesses':
            return False
        
        if user_id in round_obj.players:
            # Update player info in case it changed
            round_obj.players[user_id].username = username
            round_obj.players[user_id].first_name = first_name
        else:
            # Add new player
            round_obj.players[user_id] = Player(
                user_id=user_id,
                username=username,
                first_name=first_name
            )
        
        storage.save_active_game(group_id, round_obj.to_dict())
        logger.info(f"Player {username} ({user_id}) added to round in group {group_id}")
        return True
    
    def submit_guess(self, group_id: int, user_id: int, guess: int) -> bool:
        """
        Submit a guess for a player.
        
        Args:
            group_id: The Telegram group ID
            user_id: The player's user ID
            guess: The guess in degrees (0-359)
            
        Returns:
            True if guess was submitted successfully, False otherwise
        """
        round_obj = self.get_active_round(group_id)
        if not round_obj or round_obj.status != 'waiting_for_guesses':
            return False
        
        if user_id not in round_obj.players:
            return False
        
        if round_obj.players[user_id].is_forfeited:
            return False
        
        # Validate guess range
        if not 0 <= guess <= 359:
            return False
        
        round_obj.players[user_id].guess = guess
        storage.save_active_game(group_id, round_obj.to_dict())
        
        logger.info(f"Player {user_id} submitted guess {guess}° in group {group_id}")
        return True
    
    def forfeit_player(self, group_id: int, user_id: int) -> bool:
        """
        Forfeit a player from the current round.
        
        Args:
            group_id: The Telegram group ID
            user_id: The player's user ID to forfeit
            
        Returns:
            True if player was forfeited successfully, False otherwise
        """
        round_obj = self.get_active_round(group_id)
        if not round_obj or round_obj.status != 'waiting_for_guesses':
            return False
        
        if user_id not in round_obj.players:
            return False
        
        round_obj.players[user_id].is_forfeited = True
        storage.save_active_game(group_id, round_obj.to_dict())
        
        logger.info(f"Player {user_id} forfeited in group {group_id}")
        return True
    
    def get_round_status(self, group_id: int) -> Optional[Dict[str, Any]]:
        """
        Get the status of the current round.
        
        Returns:
            Dictionary with round status information or None if no active round
        """
        round_obj = self.get_active_round(group_id)
        if not round_obj:
            return None
        
        active_players = len(round_obj.players)  # Players who clicked "Guess"
        players_submitted = len([p for p in round_obj.players.values() if p.guess is not None])
        players_forfeited = len([p for p in round_obj.players.values() if p.is_forfeited])
        players_pending = active_players - players_submitted - players_forfeited
        
        # Calculate time elapsed
        time_elapsed = datetime.utcnow() - round_obj.start_time
        time_elapsed_seconds = time_elapsed.total_seconds()
        
        # Smart completion logic:
        # 1. If less than min_wait_time seconds have passed, never end (give people time to join)
        # 2. After min_wait_time seconds, end if all active players submitted
        # 3. After max_wait_time seconds, end regardless (reasonable waiting time)
        min_wait_time = config.min_wait_time  # seconds (configurable)
        max_wait_time = config.max_wait_time  # seconds (configurable)
        
        can_complete = False
        if time_elapsed_seconds >= max_wait_time:
            # After max wait time, always complete
            can_complete = True
        elif time_elapsed_seconds >= min_wait_time and players_pending == 0 and active_players > 0:
            # After min wait time, complete if all active players finished
            can_complete = True
        
        return {
            'active_players': active_players,  # Players who clicked "Guess" 
            'estimated_players': round_obj.estimated_players,  # Total estimated group members
            'players_submitted': players_submitted,
            'players_forfeited': players_forfeited,
            'players_pending': players_pending,
            'all_submitted': players_pending == 0 and active_players > 0,  # True if all active players submitted
            'can_complete': can_complete,  # True if round can be completed based on timing rules
            'time_elapsed': time_elapsed_seconds,
            'can_complete_in': max(0, min_wait_time - time_elapsed_seconds) if not can_complete else 0,
            'start_time': round_obj.start_time,
            'angle': round_obj.angle,  # Only for reveal phase
            'message_id': round_obj.message_id
        }
    
    def calculate_scores(self, group_id: int) -> Optional[List[Tuple[Player, int, int]]]:
        """
        Calculate scores for all players in the round.
        
        Args:
            group_id: The Telegram group ID
            
        Returns:
            List of tuples (Player, points, accuracy) sorted by points descending,
            or None if no active round
        """
        round_obj = self.get_active_round(group_id)
        if not round_obj:
            return None
        
        results = []
        
        for player in round_obj.players.values():
            if player.guess is None or player.is_forfeited:
                continue
            
            # Calculate angular distance (shortest path around circle)
            diff = abs(player.guess - round_obj.angle)
            accuracy = min(diff, 360 - diff)
            
            # Calculate points (100 for perfect, scaled down by accuracy)
            if accuracy == 0:
                points = config.points_max
            else:
                # Linear scaling: 100 points at 0° difference, 0 points at 180° difference
                points = max(0, int(config.points_max * (1 - accuracy / 180)))
            
            results.append((player, points, accuracy))
        
        # Sort by points (descending), then by accuracy (ascending) for ties
        results.sort(key=lambda x: (-x[1], x[2]))
        
        return results
    
    def complete_round(self, group_id: int) -> Optional[Dict[str, Any]]:
        """
        Complete the current round and update leaderboards.
        
        Args:
            group_id: The Telegram group ID
            
        Returns:
            Round results dictionary or None if no active round
        """
        round_obj = self.get_active_round(group_id)
        if not round_obj:
            return None
        
        scores = self.calculate_scores(group_id)
        if scores is None:
            return None
        
        # Update leaderboards
        for player, points, accuracy in scores:
            storage.update_player_stats(
                group_id=group_id,
                user_id=player.user_id,
                username=player.username,
                first_name=player.first_name,
                points=points,
                guess_accuracy=accuracy
            )
        
        # Mark round as completed
        round_obj.status = 'completed'
        storage.save_active_game(group_id, round_obj.to_dict())
        
        # Remove from active rounds and clean up storage
        del self.active_rounds[group_id]
        storage.clear_active_game(group_id)
        
        # Prepare results
        results = {
            'angle': round_obj.angle,
            'scores': scores,
            'total_players': len(round_obj.players),
            'players_participated': len(scores),
            'duration': datetime.utcnow() - round_obj.start_time
        }
        
        logger.info(f"Round completed for group {group_id}, {len(scores)} players participated")
        return results
    
    def end_round(self, group_id: int, ended_by_user_id: int, is_admin: bool = False) -> Optional[Dict[str, Any]]:
        """
        End the current round prematurely (admin/starter only).
        
        Args:
            group_id: The Telegram group ID
            ended_by_user_id: The user ID of who is ending the round
            is_admin: Whether the user ending the round is an admin
            
        Returns:
            Round results dictionary or None if no active round or unauthorized
        """
        round_obj = self.get_active_round(group_id)
        if not round_obj or round_obj.status != 'waiting_for_guesses':
            return None
        
        # Check if user is the starter of the round or an admin
        if not is_admin and round_obj.starter_user_id != ended_by_user_id:
            logger.warning(f"User {ended_by_user_id} attempted to end round in group {group_id} but is not authorized")
            return None
        
        logger.info(f"Round ended prematurely by user {ended_by_user_id} in group {group_id}")
        return self.complete_round(group_id)
    
    def get_leaderboard(self, group_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the leaderboard for a group.
        
        Args:
            group_id: The Telegram group ID
            limit: Maximum number of players to return
            
        Returns:
            List of player stats sorted by total points
        """
        leaderboard = storage.load_leaderboard(group_id)
        
        # Convert to list and sort by points
        players = []
        for user_id, stats in leaderboard.items():
            players.append({
                'user_id': user_id,
                'rank': 0,  # Will be filled below
                **stats
            })
        
        # Sort by total points (descending), then by best guess (ascending)
        players.sort(key=lambda x: (-x['total_points'], x['best_guess']))
        
        # Assign ranks
        for i, player in enumerate(players[:limit]):
            player['rank'] = i + 1
        
        return players[:limit]
    
    def reset_leaderboard(self, group_id: int) -> bool:
        """Reset the leaderboard for a group."""
        return storage.reset_leaderboard(group_id)


# Global game manager instance
game_manager = GameManager()
