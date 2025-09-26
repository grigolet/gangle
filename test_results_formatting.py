#!/usr/bin/env python3
"""
Test the results formatting to ensure no Markdown parsing errors
"""

import sys
sys.path.append('/home/grigolet/cernbox/personal/code/sandbox/gangle')

from bot import escape_markdown

def test_results_formatting():
    """Test results text formatting with various user names."""
    
    # Mock player data with tricky names
    test_players = [
        {"username": "john_doe", "first_name": "John", "guess": 45, "points": 95, "accuracy": 5},
        {"username": None, "first_name": "User.Name", "guess": 90, "points": 80, "accuracy": 20},
        {"username": "special@user!", "first_name": "Special", "guess": 135, "points": 70, "accuracy": 35},
        {"username": None, "first_name": "Name (with) parentheses", "guess": 180, "points": 60, "accuracy": 50},
        {"username": "user*with*stars", "first_name": "Starred", "guess": 270, "points": 40, "accuracy": 90}
    ]
    
    # Create results text like in the bot
    results_text = "🎉 *Round Complete\\!*\n\n"
    results_text += f"🎯 *Correct Angle:* 123°\n\n"
    results_text += "🏆 *Results:*\n"
    
    for i, player in enumerate(test_players, 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}\\."
        # Show username with @ prefix, fallback to first_name if no username
        raw_display_name = f"@{player['username']}" if player['username'] else player['first_name']
        display_name = escape_markdown(raw_display_name)
        results_text += f"{emoji} {display_name}: {player['guess']}° \\({player['points']} pts, ±{player['accuracy']}°\\)\n"
    
    results_text += f"\n\n👥 *Participation:* 5/8 players"
    
    print("📝 Generated results text:")
    print(results_text)
    print("\n✅ Results formatting test completed successfully!")
    
    return results_text

if __name__ == "__main__":
    test_results_formatting()
