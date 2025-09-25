#!/usr/bin/env python3

import asyncio
import sys
from game_manager import game_manager
from storage import storage
from config import config

async def test_completion_logic():
    """Test the round completion logic to identify the bug."""
    
    print("Testing round completion logic...")
    
    # Test chat ID
    chat_id = -1001234567890
    
    print(f"\nStep 1: Creating a round...")
    
    # Clean up any existing round
    storage.clear_active_game(chat_id)
    
    # Create a round
    round_obj = game_manager.create_round(chat_id, 12345, 67890)
    if not round_obj:
        print("❌ Failed to create round")
        return
    
    print(f"✅ Round created with angle: {round_obj.angle}°")
    
    # Get initial status
    status = game_manager.get_round_status(chat_id)
    print(f"\nInitial status:")
    print(f"  Active players: {status['active_players']}")
    print(f"  All submitted: {status['all_submitted']}")
    print(f"  Can complete: {status['can_complete']}")
    print(f"  Time elapsed: {status['time_elapsed']}")
    
    print(f"\nStep 2: Adding a player...")
    
    # Add a player
    game_manager.add_player(chat_id, 111, "Player1", "player1")
    
    # Get status after adding player
    status = game_manager.get_round_status(chat_id)
    print(f"\nAfter adding player:")
    print(f"  Active players: {status['active_players']}")
    print(f"  Players submitted: {status['players_submitted']}")
    print(f"  Players pending: {status['players_pending']}")
    print(f"  All submitted: {status['all_submitted']}")
    print(f"  Can complete: {status['can_complete']}")
    
    print(f"\nStep 3: Player submitting guess...")
    
    # Submit a guess
    result = game_manager.submit_guess(chat_id, 111, 180)
    print(f"Guess submitted: {result}")
    
    # Get status after guess
    status = game_manager.get_round_status(chat_id)
    print(f"\nAfter guess submitted:")
    print(f"  Active players: {status['active_players']}")
    print(f"  Players submitted: {status['players_submitted']}")
    print(f"  Players pending: {status['players_pending']}")
    print(f"  All submitted: {status['all_submitted']}")
    print(f"  Can complete: {status['can_complete']}")
    print(f"  Can complete in: {status['can_complete_in']}")
    print(f"  Time elapsed: {status['time_elapsed']}")
    
    if status['all_submitted']:
        print("\n✅ All players have submitted!")
        
        print(f"\nStep 4: Testing completion logic...")
        
        # Wait a bit and check again
        print(f"Waiting {config.min_wait_time} seconds for min_wait_time...")
        await asyncio.sleep(config.min_wait_time + 1)
        
        status = game_manager.get_round_status(chat_id)
        print(f"\nAfter waiting min_wait_time:")
        print(f"  All submitted: {status['all_submitted']}")
        print(f"  Can complete: {status['can_complete']}")
        print(f"  Can complete in: {status['can_complete_in']}")
        print(f"  Time elapsed: {status['time_elapsed']}")
        
        if status['can_complete']:
            print("\n✅ Round should be ready to complete!")
            
            # Try to complete the round
            results = game_manager.complete_round(chat_id)
            if results:
                print(f"\n✅ Round completed successfully!")
                print(f"  Correct angle: {results['angle']}°")
                print(f"  Players participated: {results['players_participated']}")
                print(f"  Total players: {results['total_players']}")
                if results['scores']:
                    print(f"  Best score: {results['scores'][0][2]}° accuracy")
            else:
                print("\n❌ Round completion failed!")
        else:
            print(f"\n❌ Round not ready to complete after min_wait_time")
            print(f"    This might be the bug!")
    else:
        print(f"\n❌ Not all players submitted, cannot test completion")
    
    # Clean up
    storage.clear_active_game(chat_id)
    print(f"\nTest completed.")

if __name__ == "__main__":
    asyncio.run(test_completion_logic())
