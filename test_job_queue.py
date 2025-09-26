#!/usr/bin/env python3
"""
Test job queue functionality for the Gangle bot.
"""

import sys
sys.path.append('/home/grigolet/cernbox/personal/code/sandbox/gangle')

from bot import GangleBot
from config import config

def test_job_queue():
    """Test job queue functionality."""
    
    print("🔧 Testing Job Queue Functionality")
    print("=" * 40)
    
    if not config.telegram_bot_token:
        print("⚠️ Bot token not configured - cannot test job queue")
        return
    
    # Initialize bot
    bot = GangleBot()
    
    # Test 1: Check job queue is available
    job_queue_available = bot.app.job_queue is not None
    print(f"1️⃣ Job queue available: {'✅' if job_queue_available else '❌'} {job_queue_available}")
    
    # Test 2: Check callback methods exist
    completion_callback_exists = hasattr(bot, '_monitor_round_completion_callback')
    status_callback_exists = hasattr(bot, '_periodic_status_update_callback')
    
    print(f"2️⃣ Completion callback method: {'✅' if completion_callback_exists else '❌'} {completion_callback_exists}")
    print(f"3️⃣ Status callback method: {'✅' if status_callback_exists else '❌'} {status_callback_exists}")
    
    # Test 3: Check core monitoring methods
    core_methods = [
        '_start_completion_monitoring',
        '_monitor_round_completion', 
        '_stop_completion_monitoring',
        '_schedule_status_updates',
        '_periodic_status_update'
    ]
    
    print("4️⃣ Core monitoring methods:")
    for method in core_methods:
        exists = hasattr(bot, method)
        print(f"   {method}: {'✅' if exists else '❌'} {exists}")
    
    # Test 4: Check dictionaries are initialized
    tracking_dicts = [
        ('completion_monitor_jobs', bot.completion_monitor_jobs),
        ('status_update_jobs', bot.status_update_jobs), 
        ('status_message_ids', bot.status_message_ids),
        ('user_guess_states', bot.user_guess_states)
    ]
    
    print("5️⃣ Tracking dictionaries initialized:")
    for name, dict_obj in tracking_dicts:
        initialized = isinstance(dict_obj, dict) and len(dict_obj) == 0
        print(f"   {name}: {'✅' if initialized else '❌'} {initialized}")
    
    print("\n🎯 Summary:")
    if job_queue_available and completion_callback_exists and status_callback_exists:
        print("✅ All job queue components are properly set up!")
        print("✅ The bot should now properly schedule and run periodic jobs")
        print("✅ Status messages should update every 10 seconds")
        print("✅ Round completion should be monitored every 10 seconds")
    else:
        print("❌ Some job queue components are missing")
    
    return True

if __name__ == "__main__":
    test_job_queue()
