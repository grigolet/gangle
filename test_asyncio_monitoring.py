#!/usr/bin/env python3
"""
Test script to verify that asyncio-based completion monitoring works correctly.
"""

import time
from game_manager import game_manager

# Test chat and user IDs
CHAT_ID = -1001234567890  # Test group ID
USER1_ID = 123456789
USER2_ID = 987654321

def main():
    """Test the asyncio completion monitoring."""
    print("🔍 Testing asyncio completion monitoring...")
    
    # 1. Create a round
    print("\n1️⃣ Creating test round...")
    round_obj = game_manager.create_round(CHAT_ID, 100, USER1_ID)
    if not round_obj:
        print("❌ Failed to create round")
        return
    
    print("✅ Round created: {}°".format(round_obj.angle))
    
    # 2. Add players to the round 
    print("\n2️⃣ Adding players...")
    game_manager.add_player(CHAT_ID, USER1_ID, "testuser1", "Test User 1")
    game_manager.add_player(CHAT_ID, USER2_ID, "testuser2", "Test User 2")
    print("✅ Added 2 players")
    
    # 3. Check initial status
    print("\n3️⃣ Checking initial status...")
    status = game_manager.get_round_status(CHAT_ID)
    if status:
        print("   Status: all_submitted={}, can_complete={}".format(
            status['all_submitted'], status['can_complete']))
        print("   Time elapsed: {:.1f}s".format(status['time_elapsed']))
    else:
        print("   No status available")
    
    # 4. Submit guess from one player
    print("\n4️⃣ Submitting guess from player 1...")
    success = game_manager.submit_guess(CHAT_ID, USER1_ID, 45)
    print("✅ Player 1 guess submitted: {}".format(success))
    
    # 5. Check status after one guess
    print("\n5️⃣ Checking status after one guess...")
    status = game_manager.get_round_status(CHAT_ID)
    if status:
        print("   Status keys: {}".format(list(status.keys())))
        print("   Status: all_submitted={}, can_complete={}".format(
            status['all_submitted'], status['can_complete']))
        print("   Time elapsed: {:.1f}s".format(status['time_elapsed']))
        print("   Active players: {}".format(status['active_players']))
        if 'total_players' in status:
            print("   Total players: {}".format(status['total_players']))
    else:
        print("   No status available")
    
    # 6. Wait for minimum time to pass
    print("\n6️⃣ Testing timing conditions...")
    print("   Waiting 31 seconds for minimum wait time...")
    time.sleep(31)
    
    status = game_manager.get_round_status(CHAT_ID)
    if status:
        print("   Status after wait: all_submitted={}, can_complete={}".format(
            status['all_submitted'], status['can_complete']))
        print("   Time elapsed: {:.1f}s".format(status['time_elapsed']))
    else:
        print("   No status available")
    
    # 7. Submit second guess to trigger completion
    print("\n7️⃣ Submitting guess from player 2...")
    success = game_manager.submit_guess(CHAT_ID, USER2_ID, 90)
    print("✅ Player 2 guess submitted: {}".format(success))
    
    # 8. Check final status 
    print("\n8️⃣ Checking final status...")
    status = game_manager.get_round_status(CHAT_ID)
    if status:
        print("   Status: all_submitted={}, can_complete={}".format(
            status['all_submitted'], status['can_complete']))
        print("   Time elapsed: {:.1f}s".format(status['time_elapsed']))
        
        if status['can_complete']:
            print("✅ Round is ready for completion!")
            
            # Test completion
            print("\n9️⃣ Testing round completion...")
            results = game_manager.complete_round(CHAT_ID)
            if results:
                print("✅ Round completed successfully!")
                print("   Correct angle: {}°".format(results['angle']))
                print("   Participants: {}/{}".format(
                    results['players_participated'], results['total_players']))
                print("   Winners: {} players scored".format(len(results['scores'])))
                if results['scores']:
                    winner = results['scores'][0][0]
                    print("   Winner: {} with guess {}°".format(
                        winner.first_name, winner.guess))
            else:
                print("❌ Failed to complete round")
        else:
            print("⏳ Round not yet ready for completion")
    else:
        print("   No status available")
    
    print("\n🎉 Test completed!")

if __name__ == "__main__":
    main()
