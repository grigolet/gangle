#!/usr/bin/env python3

import asyncio
import os
from game_manager import game_manager
from storage import storage
from config import config

async def test_quick_completion():
    """Test completion with a very short min_wait_time."""
    
    # Set very short timing for testing
    original_min = config.min_wait_time
    original_max = config.max_wait_time
    
    # Temporarily override the timing
    config.min_wait_time = 2  # 2 seconds
    config.max_wait_time = 5  # 5 seconds
    
    try:
        print("Testing round completion logic with quick timing...")
        
        # Test chat ID
        chat_id = -1001234567891
        
        print("\nStep 1: Creating a round...")
        
        # Clean up any existing round
        storage.clear_active_game(chat_id)
        
        # Create a round
        round_obj = game_manager.create_round(chat_id, 12345, 67890)
        if not round_obj:
            print("❌ Failed to create round")
            return
        
        print(f"✅ Round created with angle: {round_obj.angle}°")
        
        print("\nStep 2: Adding a player and submitting guess...")
        
        # Add a player and submit guess immediately
        game_manager.add_player(chat_id, 111, "Player1", "player1")
        game_manager.submit_guess(chat_id, 111, 180)
        
        # Check status immediately after guess
        status = game_manager.get_round_status(chat_id)
        if not status:
            print("❌ Failed to get round status")
            return
            
        print("\nAfter guess submitted:")
        print(f"  Active players: {status['active_players']}")
        print(f"  All submitted: {status['all_submitted']}")
        print(f"  Can complete: {status['can_complete']}")
        print(f"  Can complete in: {status['can_complete_in']} seconds")
        
        if status['all_submitted'] and not status['can_complete']:
            print(f"\nStep 3: Waiting {config.min_wait_time} seconds for min_wait_time...")
            await asyncio.sleep(config.min_wait_time + 0.5)  # Wait a bit extra to be sure
            
            # Check status again
            status = game_manager.get_round_status(chat_id)
            if not status:
                print("❌ Failed to get round status after waiting")
                return
                
            print("\nAfter waiting:")
            print(f"  All submitted: {status['all_submitted']}")
            print(f"  Can complete: {status['can_complete']}")
            print(f"  Time elapsed: {status['time_elapsed']} seconds")
            
            if status['can_complete']:
                print("\n✅ Round should be ready to complete!")
                
                # Try to complete the round
                results = game_manager.complete_round(chat_id)
                if results:
                    print(f"\n🎉 Round completed successfully!")
                    print(f"  Correct angle: {results['angle']}°")
                    print(f"  Players participated: {results['players_participated']}")
                    print(f"  Total players: {results['total_players']}")
                    if results['scores']:
                        print(f"  Best score: {results['scores'][0][2]}° accuracy")
                else:
                    print("\n❌ Round completion failed!")
            else:
                print(f"\n❌ Round STILL not ready to complete!")
                print(f"    This indicates the bug is not fixed")
        else:
            print(f"\n❌ Unexpected status: all_submitted={status['all_submitted']}, can_complete={status['can_complete']}")
        
        # Clean up
        storage.clear_active_game(chat_id)
        print(f"\nTest completed.")
        
    finally:
        # Restore original timing
        config.min_wait_time = original_min
        config.max_wait_time = original_max
        print(f"Restored timing: min_wait={original_min}s, max_wait={original_max}s")

if __name__ == "__main__":
    asyncio.run(test_quick_completion())
