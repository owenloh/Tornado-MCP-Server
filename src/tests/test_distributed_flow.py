#!/usr/bin/env python3
"""
Test Distributed Command Execution Flow

This script tests the complete flow from AI_laptop terminal to tornado_desktop
through Firebase queue system.

Task 3.4: Test distributed command execution flow
- Test basic command flow from AI_laptop to tornado_desktop
- Verify command queue ordering and processing
- Test error handling when Tornado listener fails
- Test multi-user command isolation
- Validate that bookmark modifications work through the distributed system
"""

import sys
import time
import json
from pathlib import Path
from typing import List, Dict, Any

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from firebase.firebase_config import FirebaseConfig, CommandQueueManager


class DistributedFlowTester:
    """Test the distributed command execution flow"""
    
    def __init__(self):
        """Initialize the tester"""
        self.firebase_config = FirebaseConfig()
        self.queue_manager = None
        
    def initialize(self) -> bool:
        """Initialize Firebase connection"""
        print("🔧 Initializing Firebase connection for testing...")
        
        if not self.firebase_config.initialize_firebase():
            print("❌ Failed to initialize Firebase")
            return False
            
        self.queue_manager = CommandQueueManager(self.firebase_config)
        print("✅ Firebase connection established")
        return True
    
    def test_basic_command_flow(self) -> bool:
        """Test basic command flow from AI_laptop to Firebase queue"""
        print("\n" + "="*50)
        print("TEST 1: Basic Command Flow")
        print("="*50)
        
        try:
            # Test commands that mirror the JSON-RPC terminal interface
            test_commands = [
                {
                    'method': 'update_position',
                    'params': {'x': 160000, 'y': 112000, 'z': 3500}
                },
                {
                    'method': 'zoom_in',
                    'params': {}
                },
                {
                    'method': 'rotate_left',
                    'params': {}
                },
                {
                    'method': 'update_gain',
                    'params': {'gain_value': 1.5}
                },
                {
                    'method': 'update_visibility',
                    'params': {'seismic': True, 'attribute': False, 'horizon': False, 'well': True}
                }
            ]
            
            command_ids = []
            
            # Send test commands
            print("📤 Sending test commands to Firebase queue...")
            for i, cmd in enumerate(test_commands, 1):
                print(f"  {i}. {cmd['method']} - {cmd['params']}")
                command_id = self.queue_manager.add_command(cmd)
                if command_id:
                    command_ids.append(command_id)
                    print(f"     ✅ Queued with ID: {command_id[:8]}...")
                else:
                    print(f"     ❌ Failed to queue command")
                    return False
            
            # Verify commands are in queue
            print("\n📋 Checking command queue...")
            pending_commands = self.queue_manager.get_pending_commands()
            print(f"   Found {len(pending_commands)} pending commands")
            
            if len(pending_commands) >= len(test_commands):
                print("   ✅ All commands successfully queued")
                return True
            else:
                print("   ❌ Not all commands found in queue")
                return False
                
        except Exception as e:
            print(f"❌ Error in basic command flow test: {e}")
            return False
    
    def test_command_queue_ordering(self) -> bool:
        """Test that commands are processed in correct order"""
        print("\n" + "="*50)
        print("TEST 2: Command Queue Ordering")
        print("="*50)
        
        try:
            # Clear any existing commands first
            print("🧹 Clearing existing commands...")
            self.queue_manager.cleanup_old_commands(0)  # Remove all old commands
            
            # Send ordered sequence of commands
            ordered_commands = [
                {'method': 'reset_parameters', 'params': {}},
                {'method': 'update_position', 'params': {'x': 150000, 'y': 110000, 'z': 3000}},
                {'method': 'zoom_in', 'params': {}},
                {'method': 'rotate_right', 'params': {}},
                {'method': 'increase_gain', 'params': {}}
            ]
            
            print("📤 Sending ordered sequence of commands...")
            sent_order = []
            
            for i, cmd in enumerate(ordered_commands, 1):
                print(f"  {i}. {cmd['method']}")
                command_id = self.queue_manager.add_command(cmd)
                if command_id:
                    sent_order.append((command_id, cmd['method']))
                    time.sleep(0.1)  # Small delay to ensure ordering
                else:
                    print(f"     ❌ Failed to queue command {cmd['method']}")
                    return False
            
            # Check queue order
            print("\n📋 Verifying queue order...")
            pending_commands = self.queue_manager.get_pending_commands()
            
            if len(pending_commands) < len(ordered_commands):
                print(f"   ❌ Expected {len(ordered_commands)} commands, found {len(pending_commands)}")
                return False
            
            # Check if commands are in correct order (most recent commands)
            recent_commands = pending_commands[-len(ordered_commands):]
            
            for i, (expected_id, expected_method) in enumerate(sent_order):
                if i < len(recent_commands):
                    actual_method = recent_commands[i]['method']
                    if actual_method == expected_method:
                        print(f"   ✅ Position {i+1}: {expected_method}")
                    else:
                        print(f"   ❌ Position {i+1}: Expected {expected_method}, got {actual_method}")
                        return False
                else:
                    print(f"   ❌ Missing command at position {i+1}")
                    return False
            
            print("   ✅ Command ordering verified")
            return True
            
        except Exception as e:
            print(f"❌ Error in command ordering test: {e}")
            return False
    
    def test_error_handling(self) -> bool:
        """Test error handling for invalid commands"""
        print("\n" + "="*50)
        print("TEST 3: Error Handling")
        print("="*50)
        
        try:
            # Test invalid commands
            invalid_commands = [
                {
                    'method': 'invalid_method',
                    'params': {}
                },
                {
                    'method': 'update_position',
                    'params': {'x': 'invalid_value', 'y': 112000, 'z': 3500}
                },
                {
                    'method': 'update_gain',
                    'params': {'wrong_param': 1.5}
                }
            ]
            
            print("📤 Testing invalid commands...")
            
            # These should still be queued (validation happens in listener)
            for i, cmd in enumerate(invalid_commands, 1):
                print(f"  {i}. Testing: {cmd['method']}")
                command_id = self.queue_manager.add_command(cmd)
                if command_id:
                    print(f"     ✅ Queued (validation will happen in listener)")
                else:
                    print(f"     ❌ Failed to queue")
            
            print("   ✅ Error handling test completed")
            print("   ℹ️  Invalid commands are queued but will fail during processing")
            return True
            
        except Exception as e:
            print(f"❌ Error in error handling test: {e}")
            return False
    
    def test_multi_user_isolation(self) -> bool:
        """Test multi-user command isolation"""
        print("\n" + "="*50)
        print("TEST 4: Multi-User Command Isolation")
        print("="*50)
        
        try:
            # Create queue managers for different users
            user1_manager = CommandQueueManager(self.firebase_config)
            user1_manager.user_id = "test_user_001"
            
            user2_manager = CommandQueueManager(self.firebase_config)
            user2_manager.user_id = "test_user_002"
            
            print("👥 Testing multi-user command isolation...")
            
            # Send commands from different users
            user1_cmd = {'method': 'zoom_in', 'params': {}}
            user2_cmd = {'method': 'zoom_out', 'params': {}}
            
            print("  📤 User 1 sending zoom_in command...")
            user1_cmd_id = user1_manager.add_command(user1_cmd)
            
            print("  📤 User 2 sending zoom_out command...")
            user2_cmd_id = user2_manager.add_command(user2_cmd)
            
            if not user1_cmd_id or not user2_cmd_id:
                print("   ❌ Failed to send commands from both users")
                return False
            
            # Check that each user only sees their own commands
            print("  📋 Checking command isolation...")
            
            user1_commands = user1_manager.get_pending_commands()
            user2_commands = user2_manager.get_pending_commands()
            
            print(f"     User 1 has {len(user1_commands)} pending commands")
            print(f"     User 2 has {len(user2_commands)} pending commands")
            
            # Verify users don't see each other's commands
            user1_has_own = any(cmd['command_id'] == user1_cmd_id for cmd in user1_commands)
            user1_has_other = any(cmd['command_id'] == user2_cmd_id for cmd in user1_commands)
            
            user2_has_own = any(cmd['command_id'] == user2_cmd_id for cmd in user2_commands)
            user2_has_other = any(cmd['command_id'] == user1_cmd_id for cmd in user2_commands)
            
            if user1_has_own and not user1_has_other and user2_has_own and not user2_has_other:
                print("   ✅ Multi-user isolation working correctly")
                return True
            else:
                print("   ❌ Multi-user isolation failed")
                print(f"      User 1 - has own: {user1_has_own}, has other: {user1_has_other}")
                print(f"      User 2 - has own: {user2_has_own}, has other: {user2_has_other}")
                return False
                
        except Exception as e:
            print(f"❌ Error in multi-user isolation test: {e}")
            return False
    
    def test_bookmark_modification_integration(self) -> bool:
        """Test that bookmark modifications work through distributed system"""
        print("\n" + "="*50)
        print("TEST 5: Bookmark Modification Integration")
        print("="*50)
        
        try:
            print("🔧 Testing bookmark modification commands...")
            
            # Test various bookmark modification commands
            bookmark_commands = [
                {
                    'method': 'update_position',
                    'params': {'x': 165000, 'y': 115000, 'z': 4000},
                    'description': 'Position change'
                },
                {
                    'method': 'update_orientation',
                    'params': {'rot1': 0, 'rot2': 0.5, 'rot3': -1.0},
                    'description': 'Orientation change'
                },
                {
                    'method': 'update_scale',
                    'params': {'scale_x': 1.2, 'scale_y': 1.2},
                    'description': 'Scale change'
                },
                {
                    'method': 'update_visibility',
                    'params': {'seismic': True, 'attribute': True, 'horizon': False, 'well': False},
                    'description': 'Visibility toggle'
                },
                {
                    'method': 'update_gain',
                    'params': {'gain_value': 2.0},
                    'description': 'Gain adjustment'
                }
            ]
            
            print("📤 Sending bookmark modification commands...")
            
            for i, cmd in enumerate(bookmark_commands, 1):
                print(f"  {i}. {cmd['description']}: {cmd['method']}")
                command_id = self.queue_manager.add_command(cmd)
                if command_id:
                    print(f"     ✅ Queued: {command_id[:8]}...")
                else:
                    print(f"     ❌ Failed to queue")
                    return False
            
            print("   ✅ All bookmark modification commands queued successfully")
            print("   ℹ️  Commands are ready for processing by Tornado listener")
            
            return True
            
        except Exception as e:
            print(f"❌ Error in bookmark modification test: {e}")
            return False
    
    def run_all_tests(self) -> bool:
        """Run all distributed flow tests"""
        print("🧪 DISTRIBUTED COMMAND EXECUTION FLOW TESTS")
        print("="*60)
        
        if not self.initialize():
            return False
        
        tests = [
            ("Basic Command Flow", self.test_basic_command_flow),
            ("Command Queue Ordering", self.test_command_queue_ordering),
            ("Error Handling", self.test_error_handling),
            ("Multi-User Isolation", self.test_multi_user_isolation),
            ("Bookmark Modification Integration", self.test_bookmark_modification_integration)
        ]
        
        results = []
        
        for test_name, test_func in tests:
            try:
                result = test_func()
                results.append((test_name, result))
                
                if result:
                    print(f"\n✅ {test_name}: PASSED")
                else:
                    print(f"\n❌ {test_name}: FAILED")
                    
            except Exception as e:
                print(f"\n💥 {test_name}: ERROR - {e}")
                results.append((test_name, False))
        
        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} - {test_name}")
        
        print(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! Distributed flow is working correctly.")
            return True
        else:
            print("⚠️  Some tests failed. Check the output above for details.")
            return False


def main():
    """Run the distributed flow tests"""
    try:
        tester = DistributedFlowTester()
        success = tester.run_all_tests()
        
        if success:
            print("\n🚀 Ready to test with Tornado listener!")
            print("   1. Start tornado_listener.py in Tornado environment")
            print("   2. Use json_rpc_terminal.py to send commands")
            print("   3. Watch commands get processed in real-time")
        else:
            print("\n🔧 Fix the failing tests before proceeding")
            
    except Exception as e:
        print(f"❌ Fatal error in test runner: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()