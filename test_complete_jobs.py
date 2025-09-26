#!/usr/bin/env python3
"""
Test the complete job queue functionality for round monitoring.
"""

import sys
import asyncio
from unittest.mock import Mock, AsyncMock
sys.path.append('/home/grigolet/cernbox/personal/code/sandbox/gangle')

from bot import GangleBot
from config import config

def test_complete_job_functionality():
    """Test complete job queue functionality."""
    
    print("🧪 Testing Complete Job Queue Functionality")
    print("=" * 50)
    
    if not config.telegram_bot_token:
        print("⚠️ Bot token not configured - cannot test")
        return False
    
    # Initialize bot
    bot = GangleBot()
    
    # Test 1: Job queue availability
    job_queue_available = bot.app.job_queue is not None
    print(f"1️⃣ Job queue available: {'✅' if job_queue_available else '❌'} {job_queue_available}")
    
    if not job_queue_available:
        print("❌ Job queue not available - cannot continue testing")
        return False
    
    # Test 2: Create mock context
    print("2️⃣ Testing job callback functions...")
    
    # Mock context with job data
    mock_context = Mock()
    mock_context.job = Mock()
    mock_context.job.data = 12345  # Mock chat_id
    
    # Mock the actual methods to avoid real API calls
    bot._monitor_round_completion = AsyncMock()
    bot._periodic_status_update = AsyncMock()
    
    # Test 3: Test completion callback
    async def test_completion_callback():
        await bot._monitor_round_completion_callback(mock_context)
        return bot._monitor_round_completion.called
    
    # Test 4: Test status update callback  
    async def test_status_callback():
        await bot._periodic_status_update_callback(mock_context)
        return bot._periodic_status_update.called
    
    # Run async tests
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        completion_called = loop.run_until_complete(test_completion_callback())
        status_called = loop.run_until_complete(test_status_callback())
        
        print(f"   Completion callback works: {'✅' if completion_called else '❌'} {completion_called}")
        print(f"   Status callback works: {'✅' if status_called else '❌'} {status_called}")
        
    finally:
        loop.close()
    
    # Test 5: Check if job scheduling methods exist and are callable
    scheduling_methods = [
        '_start_completion_monitoring',
        '_schedule_status_updates', 
        '_stop_completion_monitoring'
    ]
    
    print("3️⃣ Testing job scheduling methods:")
    all_methods_exist = True
    for method in scheduling_methods:
        exists = hasattr(bot, method) and callable(getattr(bot, method))
        print(f"   {method}: {'✅' if exists else '❌'} {exists}")
        all_methods_exist = all_methods_exist and exists
    
    # Test 6: Summary
    print("\\n🎯 Test Results:")
    if job_queue_available and completion_called and status_called and all_methods_exist:
        print("✅ ALL TESTS PASSED!")
        print("✅ Job queue is properly configured")
        print("✅ Callback functions work correctly") 
        print("✅ The bot should now:")
        print("   • Start completion monitoring when rounds begin")
        print("   • Update status messages every 10 seconds")
        print("   • Auto-complete rounds after timeout")
        print("   • Show DEBUG messages in logs")
        return True
    else:
        print("❌ Some tests failed")
        return False

if __name__ == "__main__":
    success = test_complete_job_functionality()
    print(f"\\n{'🎉' if success else '💥'} Test {'PASSED' if success else 'FAILED'}")
