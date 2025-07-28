#!/usr/bin/env python3
"""
Test Decisive NLP Behavior

Tests that the system is more decisive and doesn't ask too many clarification questions.
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from nlp.gemini_command_parser import GeminiCommandParser
from test_utils import get_test_api_key
from firebase.firebase_config import FirebaseConfig


def test_decisive_behavior():
    """Test that system makes reasonable assumptions instead of endless questions"""
    print("🧪 TESTING DECISIVE NLP BEHAVIOR")
    print("="*60)
    
    # Get API key
    api_key = get_test_api_key()
    if not api_key:
        return False
    
    # Initialize system
    firebase_config = FirebaseConfig()
    if not firebase_config.initialize_firebase():
        return False
    
    parser = GeminiCommandParser(api_key, firebase_config)
    time.sleep(2)  # Wait for state sync
    
    # Test commands that should be decisive
    decisive_tests = [
        {
            "command": "shift it to the bottom right",
            "expected_type": "command",
            "expected_method": "update_shift",
            "description": "Should assume medium shift to bottom right"
        },
        {
            "command": "move left a bit",
            "expected_type": "command", 
            "expected_method": "update_position",
            "description": "Should assume crossline movement"
        },
        {
            "command": "turn it around",
            "expected_type": "command",
            "expected_method": "update_orientation", 
            "description": "Should assume 180 degree rotation"
        },
        {
            "command": "make it bigger",
            "expected_type": "command",
            "expected_method": "update_scale",
            "description": "Should assume zoom in/scale up"
        },
        {
            "command": "hide the slice",
            "expected_type": "command",
            "expected_method": "update_slice_visibility",
            "description": "Should assume crossline slice"
        }
    ]
    
    results = []
    
    for i, test in enumerate(decisive_tests, 1):
        print(f"\n{i}. Testing: {test['description']}")
        print(f"   Command: '{test['command']}'")
        
        try:
            result = parser.parse_command(test['command'])
            result_type = result.get('type')
            method = result.get('method', '')
            
            print(f"   Result: {result_type}")
            if result_type == 'command':
                print(f"   Method: {method}")
                print(f"   Params: {result.get('params', {})}")
                
            # Check if it's decisive (command) vs asking questions (clarification)
            if result_type == 'command':
                print(f"   ✅ DECISIVE - Made assumption and executed")
                success = True
            elif result_type == 'clarification':
                print(f"   ⚠️ ASKING - Still asking for clarification")
                success = False
            else:
                print(f"   ❓ OTHER - Got {result_type}")
                success = False
                
            results.append({
                "test": test['description'],
                "command": test['command'],
                "success": success,
                "result_type": result_type,
                "method": method
            })
            
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            results.append({
                "test": test['description'],
                "command": test['command'], 
                "success": False,
                "error": str(e)
            })
    
    return results


def test_multi_function_calls():
    """Test support for multiple function calls in one command"""
    print("\n🧪 TESTING MULTI-FUNCTION CALLS")
    print("="*60)
    
    # Get API key
    api_key = get_test_api_key()
    if not api_key:
        return False
    
    # Initialize system
    firebase_config = FirebaseConfig()
    if not firebase_config.initialize_firebase():
        return False
    
    parser = GeminiCommandParser(api_key, firebase_config)
    time.sleep(2)  # Wait for state sync
    
    # Test commands that should trigger multiple functions
    multi_tests = [
        {
            "command": "no, I want to move the crossline instead",
            "expected_functions": ["undo_last_action", "update_position"],
            "description": "Should undo then move crossline"
        },
        {
            "command": "zoom in and increase the gain",
            "expected_functions": ["update_scale", "update_gain"],
            "description": "Should zoom and adjust gain"
        },
        {
            "command": "reset the view and show only seismic",
            "expected_functions": ["reset_view", "update_visibility"],
            "description": "Should reset then set visibility"
        }
    ]
    
    print("Note: Multi-function calls may not be fully implemented yet")
    print("Testing to see current behavior...")
    
    for i, test in enumerate(multi_tests, 1):
        print(f"\n{i}. Testing: {test['description']}")
        print(f"   Command: '{test['command']}'")
        
        try:
            result = parser.parse_command(test['command'])
            result_type = result.get('type')
            
            print(f"   Result: {result_type}")
            if result_type == 'command':
                method = result.get('method', '')
                print(f"   Method: {method}")
                print(f"   Params: {result.get('params', {})}")
                
                # Check if it matches expected functions
                if method in test['expected_functions']:
                    print(f"   ✅ PARTIAL - Got one expected function: {method}")
                else:
                    print(f"   ⚠️ DIFFERENT - Got {method}, expected one of {test['expected_functions']}")
            else:
                print(f"   ❓ Got {result_type} instead of command")
                
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
    
    return True


def test_clarification_limits():
    """Test that clarification questions are limited"""
    print("\n🧪 TESTING CLARIFICATION LIMITS")
    print("="*60)
    
    # Get API key
    api_key = get_test_api_key()
    if not api_key:
        return False
    
    # Initialize system
    firebase_config = FirebaseConfig()
    if not firebase_config.initialize_firebase():
        return False
    
    parser = GeminiCommandParser(api_key, firebase_config)
    time.sleep(2)  # Wait for state sync
    
    print("Testing with a very ambiguous command...")
    print("Command: 'do something with that thing over there'")
    
    try:
        result = parser.parse_command("do something with that thing over there")
        
        if result.get('type') == 'clarification':
            print("   ✅ APPROPRIATE - Asked for clarification on truly ambiguous command")
            print(f"   Question: {result.get('question', '')}")
            
            # Test follow-up to see if it limits questions
            print("\n   Testing follow-up with still ambiguous response...")
            print("   Response: 'you know, the usual'")
            
            followup = parser.handle_clarification_response("you know, the usual")
            
            if followup.get('type') == 'command':
                print("   ✅ DECISIVE - Made assumption after unclear response")
            elif followup.get('type') == 'clarification':
                print("   ⚠️ STILL ASKING - Asked another clarification")
            else:
                print(f"   ❓ Got {followup.get('type')}")
                
        elif result.get('type') == 'command':
            print("   ⚠️ TOO DECISIVE - Made assumption on very ambiguous command")
        else:
            print(f"   ❓ Got {result.get('type')}")
            
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
    
    return True


def main():
    """Run decisive behavior tests"""
    print("🚀 TESTING DECISIVE NLP BEHAVIOR")
    print("="*70)
    print("Testing that system is more decisive and user-friendly...")
    print()
    
    try:
        # Test decisive behavior
        decisive_results = test_decisive_behavior()
        
        # Test multi-function calls
        multi_success = test_multi_function_calls()
        
        # Test clarification limits
        clarification_success = test_clarification_limits()
        
        # Summary
        print("\n" + "="*70)
        print("🎯 DECISIVE BEHAVIOR TEST RESULTS")
        print("="*70)
        
        if decisive_results:
            decisive_count = sum(1 for r in decisive_results if r['success'])
            total_decisive = len(decisive_results)
            
            print(f"Decisive Commands: {decisive_count}/{total_decisive} ({decisive_count/total_decisive*100:.1f}%)")
            
            for result in decisive_results:
                if result['success']:
                    print(f"   ✅ {result['test']}")
                else:
                    print(f"   ❌ {result['test']} - {result.get('result_type', 'error')}")
        
        print(f"Multi-Function Support: {'✅ Tested' if multi_success else '❌ Failed'}")
        print(f"Clarification Limits: {'✅ Tested' if clarification_success else '❌ Failed'}")
        
        print(f"\n💡 RECOMMENDATIONS:")
        print(f"   1. System should make reasonable assumptions")
        print(f"   2. Max 2 clarification questions per conversation")
        print(f"   3. Better to act and let user undo than ask endless questions")
        print(f"   4. Support multiple function calls for complex requests")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()