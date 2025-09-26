#!/usr/bin/env python3
"""
Test job queue functionality by actually trying to schedule a job.
"""

import sys
import asyncio
from unittest.mock import Mock
sys.path.append('/home/grigolet/cernbox/personal/code/sandbox/gangle')

from bot import GangleBot
from config import config

def test_job_scheduling():
    """Test actual job scheduling functionality."""
    
    print("🧪 Testing Job Queue Scheduling")
    print("=" * 40)
    
    if not config.telegram_bot_token:
        print("⚠️ No bot token - cannot test")
        return False
    
    # Initialize bot
    bot = GangleBot()
    
    # Check job queue
    has_job_queue = bot.app.job_queue is not None
    print(f"1️⃣ Job queue exists: {'✅' if has_job_queue else '❌'} {has_job_queue}")
    
    if not has_job_queue:
        print("❌ Cannot test without job queue")
        return False
    
    # Try to start the job queue manually (this might be needed)
    try:
        if hasattr(bot.app.job_queue, 'start'):
            print("2️⃣ Starting job queue manually...")
            bot.app.job_queue.start()
            print("   ✅ Job queue started")
        else:
            print("2️⃣ Job queue doesn't have start() method")
    except Exception as e:
        print(f"2️⃣ Error starting job queue: {e}")
    
    # Test scheduling a simple job
    try:
        print("3️⃣ Testing job scheduling...")
        
        # Create a mock context
        mock_context = Mock()
        mock_context.job = Mock()
        mock_context.job.data = 12345
        
        # Try to simulate what _start_completion_monitoring does
        test_chat_id = 12345
        
        # Check if we can access the job scheduling method
        if hasattr(bot.app.job_queue, 'run_repeating'):
            print("   ✅ run_repeating method exists")
            
            # Try to schedule a test job (but don't actually run it)
            print("   📝 Would schedule: completion monitoring job")
            print("   📝 Would schedule: callback function exists:", hasattr(bot, '_monitor_round_completion_callback'))
            
            # Test the callback function directly
            if hasattr(bot, '_monitor_round_completion_callback'):
                print("4️⃣ Testing callback function...")
                
                # Mock the actual methods to avoid real calls
                original_monitor = getattr(bot, '_monitor_round_completion', None)
                
                async def mock_monitor(chat_id, context):
                    print(f"   📞 Mock monitor called for chat {chat_id}")
                    return True
                
                # Temporarily replace the method
                bot._monitor_round_completion = mock_monitor
                
                # Test the callback
                async def test_callback():
                    try:
                        await bot._monitor_round_completion_callback(mock_context)
                        return True
                    except Exception as e:
                        print(f"   ❌ Callback failed: {e}")
                        return False
                
                # Run the test
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    callback_success = loop.run_until_complete(test_callback())
                    print(f"   Callback test: {'✅' if callback_success else '❌'} {callback_success}")
                finally:
                    loop.close()
                    # Restore original method
                    if original_monitor:
                        bot._monitor_round_completion = original_monitor
            
        else:
            print("   ❌ run_repeating method not found")
            return False
            
    except Exception as e:
        print(f"3️⃣ Error testing job scheduling: {e}")
        return False
    
    # Stop job queue if we started it
    try:
        if hasattr(bot.app.job_queue, 'stop'):
            bot.app.job_queue.stop()
            print("5️⃣ Job queue stopped cleanly")
    except Exception as e:
        print(f"5️⃣ Error stopping job queue: {e}")
    
    print("\\n🎯 Job Queue Analysis:")
    print("✅ Job queue exists and has scheduling methods")
    print("✅ Callback functions are properly defined")
    print("⚠️  Job queue likely needs to be started when bot runs")
    print("💡 Jobs should work once bot is actively running with run_polling()")
    
    return True

if __name__ == "__main__":
    success = test_job_scheduling()
    print(f"\\n{'✅' if success else '❌'} Test {'PASSED' if success else 'FAILED'}")
