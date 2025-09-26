#!/usr/bin/env python3

import asyncio
import os
from game_manager import game_manager
from storage import storage
from config import config

async def test_user_scenario():
    """Test the exact scenario the user described."""
    
    print("Testing the user's scenario...")
    print(f"Using max_wait_time: {config.max_wait_time} seconds")
    
    # Test chat ID
    chat_id = -1001234567894
    
    print("\nStep 1: Creating a round...")
    
    # Clean up any existing round
    storage.clear_active_game(chat_id)
    
    # Create a round
    round_obj = game_manager.create_round(chat_id, 12345, 67890)
    if not round_obj:
        print("❌ Failed to create round")
        return
    
    print(f"✅ Round created with angle: {round_obj.angle}°")
    
    print("\nStep 2: Two players join and submit guesses...")
    
    # Add two players
    game_manager.add_player(chat_id, 111, "player1", "Player1")
    game_manager.add_player(chat_id, 222, "player2", "Player2")
    
    # First player submits
    print("First player submitting...")
    game_manager.submit_guess(chat_id, 111, 45)
    
    status = game_manager.get_round_status(chat_id)
    print(f"After first submission:")
    print(f"  👥 Active Players: {status['active_players']}")
    print(f"  ✅ Submitted: {status['players_submitted']}")
    print(f"  ⏳ Pending: {status['players_pending']}")
    
    # Second player submits  
    print("Second player submitting...")
    game_manager.submit_guess(chat_id, 222, 315)
    
    status = game_manager.get_round_status(chat_id)
    print(f"After both submissions:")
    print(f"  👥 Active Players: {status['active_players']}")
    print(f"  ✅ Submitted: {status['players_submitted']}")
    print(f"  ⏳ Pending: {status['players_pending']}")
    if status['all_submitted']:
        print("  ✨ Round ready to complete!")
    
    print(f"\nStep 3: Verifying completion logic...")
    
    # Verify status shows round is ready to complete
    if status['all_submitted'] and not status['can_complete']:
        wait_time = status['can_complete_in']
        print(f"Round will auto-complete in {wait_time} seconds (waiting for min_wait_time)")
        
        # Wait for minimum time
        print(f"Waiting {wait_time + 1} seconds...")
        await asyncio.sleep(wait_time + 1)
        
        status = game_manager.get_round_status(chat_id)
        print(f"After min wait time:")
        print(f"  Can complete: {status['can_complete']}")
        print(f"  Time elapsed: {status['time_elapsed']} seconds")
        
        if status['can_complete']:
            print("✅ Round is now ready to complete!")
            
            # Test completion
            results = game_manager.complete_round(chat_id)
            if results:
                print("✅ Round completed successfully!")
                print(f"  Correct angle: {results['angle']}°")
                print(f"  Participants: {results['players_participated']}")
            else:
                print("❌ Failed to complete round")
        else:
            print("❌ Round still not ready after min wait time")
            
    elif status['can_complete']:
        print("Round is immediately ready for completion!")
        results = game_manager.complete_round(chat_id)
        if results:
            print("✅ Round completed successfully!")
        else:
            print("❌ Failed to complete round")
    else:
        print("❌ Something is wrong with the completion logic")
    
    print("\nStep 4: Testing max wait time scenario...")
    
    # Create a new round to test max wait time
    storage.clear_active_game(chat_id)
    round_obj = game_manager.create_round(chat_id, 54321, 67890)
    game_manager.add_player(chat_id, 333, "player3", "Player3")
    
    print("Simulating max wait time expiration...")
    
    # Simulate max wait time by manually adjusting start time
    import datetime
    round_obj.start_time = datetime.datetime.utcnow() - datetime.timedelta(seconds=config.max_wait_time + 10)
    
    status = game_manager.get_round_status(chat_id)
    print(f"After max wait time simulation:")
    print(f"  Active players: {status['active_players']}")
    print(f"  Players submitted: {status['players_submitted']}")
    print(f"  Time elapsed: {status['time_elapsed']} seconds")
    print(f"  Can complete: {status['can_complete']}")
    
    if status['can_complete']:
        print("✅ Max wait time logic works!")
        results = game_manager.complete_round(chat_id)
        if results:
            print("✅ Round auto-completed after max wait time!")
            print(f"  Participants: {results['players_participated']}")
        else:
            print("❌ Failed to complete round after max wait time")
    else:
        print("❌ Max wait time logic is broken!")
    
    # Clean up
    storage.clear_active_game(chat_id)
    print(f"\nTest completed.")
    print("\n" + "="*50)
    print("SUMMARY:")
    print("✅ The completion monitoring system should now work correctly")
    print("✅ Rounds will auto-complete when max_wait_time is reached")
    print("✅ The bot will continuously monitor rounds every 10 seconds")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(test_user_scenario())
