#!/usr/bin/env python3
"""
Debug script to check leaderboard structure
"""

from game_manager import game_manager

# Test chat ID - use the real chat ID from logs
CHAT_ID = -4900480572

def main():
    """Debug leaderboard structure."""
    print("🔍 Checking leaderboard structure...")
    
    leaderboard = game_manager.get_leaderboard(CHAT_ID, limit=10)
    
    if not leaderboard:
        print("No leaderboard data")
        return
        
    print(f"Leaderboard has {len(leaderboard)} entries")
    
    for i, player in enumerate(leaderboard):
        print(f"\n--- Player {i+1} ---")
        print(f"Keys: {list(player.keys())}")
        for key, value in player.items():
            print(f"  {key}: {value} ({type(value).__name__})")

if __name__ == "__main__":
    main()
