#!/usr/bin/env python3

import asyncio
from game_manager import game_manager
from storage import storage

async def test_button_disable():
    """Test that the angle image message ID is properly stored and retrieved."""
    
    print("Testing button disable functionality...")
    
    # Test chat ID
    chat_id = -1001234567892
    
    print("\nStep 1: Creating a round...")
    
    # Clean up any existing round
    storage.clear_active_game(chat_id)
    
    # Create a round
    round_obj = game_manager.create_round(chat_id, 12345, 67890)
    if not round_obj:
        print("❌ Failed to create round")
        return
    
    print(f"✅ Round created with angle: {round_obj.angle}°")
    print(f"Initial angle_image_message_id: {round_obj.angle_image_message_id}")
    
    print("\nStep 2: Setting angle image message ID...")
    
    # Simulate setting the angle image message ID (as the bot would do)
    test_message_id = 98765
    success = game_manager.set_angle_image_message_id(chat_id, test_message_id)
    
    if success:
        print(f"✅ Set angle image message ID to {test_message_id}")
        
        # Verify it was stored
        updated_round = game_manager.get_active_round(chat_id)
        if updated_round and updated_round.angle_image_message_id == test_message_id:
            print(f"✅ Angle image message ID correctly stored: {updated_round.angle_image_message_id}")
        else:
            print(f"❌ Angle image message ID not correctly stored")
    else:
        print("❌ Failed to set angle image message ID")
    
    print("\nStep 3: Testing round completion...")
    
    # Add a player and submit guess to complete the round quickly
    game_manager.add_player(chat_id, 111, "player1", "Player1")
    game_manager.submit_guess(chat_id, 111, 180)
    
    # Wait for minimum time and complete the round
    from config import config
    print(f"Waiting {config.min_wait_time} seconds for min_wait_time...")
    await asyncio.sleep(config.min_wait_time + 0.5)
    
    # Complete the round
    results = game_manager.complete_round(chat_id)
    if results:
        print(f"✅ Round completed successfully!")
        
        # Verify the round is no longer active
        final_round = game_manager.get_active_round(chat_id)
        if final_round is None:
            print("✅ Round properly cleaned up after completion")
        else:
            print(f"❌ Round still active after completion: status={final_round.status}")
    else:
        print("❌ Failed to complete round")
    
    # Clean up
    storage.clear_active_game(chat_id)
    print(f"\nTest completed.")

if __name__ == "__main__":
    asyncio.run(test_button_disable())
