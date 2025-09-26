#!/usr/bin/env python3

import asyncio
from game_manager import game_manager
from storage import storage
from config import config

async def test_completion_monitoring():
    """Test the completion monitoring logic works correctly."""
    
    print("Testing completion monitoring functionality...")
    
    # Test chat ID
    chat_id = -1001234567893
    
    print("\nStep 1: Creating a round...")
    
    # Clean up any existing round
    storage.clear_active_game(chat_id)
    
    # Create a round
    round_obj = game_manager.create_round(chat_id, 12345, 67890)
    if not round_obj:
        print("❌ Failed to create round")
        return
    
    print(f"✅ Round created with angle: {round_obj.angle}°")
    
    print("\nStep 2: Adding two players...")
    
    # Add two players
    game_manager.add_player(chat_id, 111, "player1", "Player1")
    game_manager.add_player(chat_id, 222, "player2", "Player2")
    
    # Check initial status
    status = game_manager.get_round_status(chat_id)
    print(f"After adding players:")
    print(f"  Active players: {status['active_players']}")
    print(f"  Players submitted: {status['players_submitted']}")
    print(f"  Can complete: {status['can_complete']}")
    
    print("\nStep 3: First player submits guess...")
    
    # First player submits
    game_manager.submit_guess(chat_id, 111, 180)
    
    status = game_manager.get_round_status(chat_id)
    print(f"After first submission:")
    print(f"  Active players: {status['active_players']}")
    print(f"  Players submitted: {status['players_submitted']}")
    print(f"  Players pending: {status['players_pending']}")
    print(f"  All submitted: {status['all_submitted']}")
    print(f"  Can complete: {status['can_complete']}")
    
    print("\nStep 4: Second player submits guess...")
    
    # Second player submits
    game_manager.submit_guess(chat_id, 222, 90)
    
    status = game_manager.get_round_status(chat_id)
    print(f"After both submissions:")
    print(f"  Active players: {status['active_players']}")
    print(f"  Players submitted: {status['players_submitted']}")
    print(f"  Players pending: {status['players_pending']}")
    print(f"  All submitted: {status['all_submitted']}")
    print(f"  Can complete: {status['can_complete']}")
    print(f"  Can complete in: {status['can_complete_in']} seconds")
    
    if status['all_submitted'] and not status['can_complete']:
        print(f"\nStep 5: Waiting for min_wait_time ({config.min_wait_time}s)...")
        await asyncio.sleep(config.min_wait_time + 1)
        
        status = game_manager.get_round_status(chat_id)
        print(f"After min wait time:")
        print(f"  All submitted: {status['all_submitted']}")
        print(f"  Can complete: {status['can_complete']}")
        print(f"  Time elapsed: {status['time_elapsed']} seconds")
        
        if status['can_complete']:
            print("✅ Round is ready for completion by monitoring system!")
        else:
            print("❌ Round should be ready but isn't - bug in timing logic")
    elif status['can_complete']:
        print("✅ Round is immediately ready for completion!")
    else:
        print("❌ Something went wrong - round should be completable")
    
    # Test the max wait time behavior by simulating time passage
    print(f"\nStep 6: Testing max wait time ({config.max_wait_time}s) behavior...")
    
    # Create fresh round for max wait time test
    storage.clear_active_game(chat_id)
    round_obj = game_manager.create_round(chat_id, 54321, 67890)
    game_manager.add_player(chat_id, 333, "player3", "Player3")
    
    # Don't submit a guess, just check if it would complete after max time
    print("Simulating max wait time passage...")
    
    # Manually adjust the start time to simulate max wait time passage
    import datetime
    round_obj.start_time = datetime.datetime.utcnow() - datetime.timedelta(seconds=config.max_wait_time + 10)
    
    status = game_manager.get_round_status(chat_id)
    print(f"After simulated max wait time:")
    print(f"  Active players: {status['active_players']}")
    print(f"  Players submitted: {status['players_submitted']}")
    print(f"  Can complete: {status['can_complete']}")
    print(f"  Time elapsed: {status['time_elapsed']} seconds")
    
    if status['can_complete']:
        print("✅ Max wait time logic works correctly!")
        
        # Test actual completion
        results = game_manager.complete_round(chat_id)
        if results:
            print("✅ Round completed successfully after max wait time!")
        else:
            print("❌ Failed to complete round after max wait time")
    else:
        print("❌ Max wait time logic is broken!")
    
    # Clean up
    storage.clear_active_game(chat_id)
    print(f"\nTest completed.")

if __name__ == "__main__":
    asyncio.run(test_completion_monitoring())
