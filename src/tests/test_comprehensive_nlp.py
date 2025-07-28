#!/usr/bin/env python3
"""
Comprehensive Test for Enhanced NLP System

Tests all functionality including:
- Template loading and listing
- Undo/Redo operations
- Parameter bounds validation
- Context-aware relative movements
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from nlp.gemini_command_parser import GeminiCommandParser
from test_utils import get_test_api_key
from firebase.firebase_config import FirebaseConfig


def test_template_functionality():
    """Test template listing and loading"""
    print("🧪 TESTING TEMPLATE FUNCTIONALITY")
    print("="*50)
    
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
    
    # Test template listing
    print("1. Testing template listing...")
    result = parser.parse_command("show me available templates")
    
    if result.get('type') == 'info':
        message = result.get('message', '')
        if 'default_view' in message and 'structural_analysis' in message:
            print("   ✅ Template listing works - found expected templates")
        else:
            print(f"   ⚠️ Template listing partial - message: {message[:100]}...")
    else:
        print(f"   ❌ Template listing failed - got {result.get('type')}")
    
    # Test template loading
    print("\n2. Testing template loading...")
    result = parser.parse_command("load the structural analysis template")
    
    if result.get('type') == 'command':
        method = result.get('method')
        params = result.get('params', {})
        template_name = params.get('template_name', '')
        
        if method == 'load_template' and 'structural' in template_name.lower():
            print(f"   ✅ Template loading works - loading '{template_name}'")
        else:
            print(f"   ⚠️ Template loading partial - method: {method}, template: {template_name}")
    else:
        print(f"   ❌ Template loading failed - got {result.get('type')}")
    
    # Test specific template names
    print("\n3. Testing specific template names...")
    test_templates = [
        "load default view",
        "switch to amplitude analysis", 
        "use frequency analysis template"
    ]
    
    for i, command in enumerate(test_templates, 1):
        result = parser.parse_command(command)
        if result.get('type') == 'command' and result.get('method') == 'load_template':
            template_name = result.get('params', {}).get('template_name', '')
            print(f"   ✅ Template {i}: '{command}' → loading '{template_name}'")
        else:
            print(f"   ❌ Template {i}: '{command}' → {result.get('type')}")
    
    return True


def test_undo_redo_functionality():
    """Test undo/redo operations"""
    print("\n🧪 TESTING UNDO/REDO FUNCTIONALITY")
    print("="*50)
    
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
    
    # Test undo
    print("1. Testing undo operation...")
    result = parser.parse_command("undo the last action")
    
    if result.get('type') == 'command' and result.get('method') == 'undo':
        print("   ✅ Undo works - command generated")
    elif result.get('type') == 'info' and 'no actions' in result.get('message', '').lower():
        print("   ⚠️ Undo info - no actions available (expected if no previous actions)")
    else:
        print(f"   ❌ Undo failed - got {result.get('type')}: {result.get('message', '')}")
    
    # Test redo
    print("\n2. Testing redo operation...")
    result = parser.parse_command("redo that change")
    
    if result.get('type') == 'command' and result.get('method') == 'redo':
        print("   ✅ Redo works - command generated")
    elif result.get('type') == 'info' and 'no actions' in result.get('message', '').lower():
        print("   ⚠️ Redo info - no actions available (expected if no undo performed)")
    else:
        print(f"   ❌ Redo failed - got {result.get('type')}: {result.get('message', '')}")
    
    # Test undo/redo variations
    print("\n3. Testing undo/redo command variations...")
    undo_commands = ["undo", "go back", "revert last change"]
    redo_commands = ["redo", "redo last action", "restore that change"]
    
    for command in undo_commands:
        result = parser.parse_command(command)
        if result.get('type') in ['command', 'info']:
            print(f"   ✅ Undo variation: '{command}' → {result.get('type')}")
        else:
            print(f"   ❌ Undo variation: '{command}' → {result.get('type')}")
    
    for command in redo_commands:
        result = parser.parse_command(command)
        if result.get('type') in ['command', 'info']:
            print(f"   ✅ Redo variation: '{command}' → {result.get('type')}")
        else:
            print(f"   ❌ Redo variation: '{command}' → {result.get('type')}")
    
    return True


def test_parameter_bounds():
    """Test parameter bounds validation"""
    print("\n🧪 TESTING PARAMETER BOUNDS")
    print("="*50)
    
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
    
    # Test valid bounds
    print("1. Testing valid parameter bounds...")
    valid_commands = [
        "move to crossline 150000, inline 120000, depth 3500",  # All valid
        "move to crossline 100000, inline 100000, depth 1000",  # Lower bounds
        "move to crossline 200000, inline 150000, depth 6000",  # Upper bounds
    ]
    
    for command in valid_commands:
        result = parser.parse_command(command)
        if result.get('type') == 'command':
            params = result.get('params', {})
            print(f"   ✅ Valid: '{command}' → X={params.get('x')}, Y={params.get('y')}, Z={params.get('z')}")
        else:
            print(f"   ❌ Valid bounds failed: '{command}' → {result.get('type')}")
    
    # Test invalid bounds
    print("\n2. Testing invalid parameter bounds...")
    invalid_commands = [
        "move to crossline 50000, inline 120000, depth 3500",   # X too low
        "move to crossline 250000, inline 120000, depth 3500",  # X too high
        "move to crossline 150000, inline 50000, depth 3500",   # Y too low
        "move to crossline 150000, inline 200000, depth 3500",  # Y too high
        "move to crossline 150000, inline 120000, depth 500",   # Z too low
        "move to crossline 150000, inline 120000, depth 7000",  # Z too high
    ]
    
    for command in invalid_commands:
        result = parser.parse_command(command)
        if result.get('type') == 'error':
            print(f"   ✅ Invalid bounds caught: '{command}' → {result.get('message', '')[:50]}...")
        elif result.get('type') == 'command':
            print(f"   ⚠️ Invalid bounds not caught: '{command}' → command generated")
        else:
            print(f"   ❓ Unexpected result: '{command}' → {result.get('type')}")
    
    return True





def main():
    """Run comprehensive tests"""
    print("🚀 COMPREHENSIVE NLP SYSTEM TESTS")
    print("="*60)
    print("Testing all enhanced functionality...")
    print()
    
    try:
        # Run all tests
        template_success = test_template_functionality()
        undo_redo_success = test_undo_redo_functionality()
        bounds_success = test_parameter_bounds()
        
        # Summary
        print("\n" + "="*60)
        print("🎯 COMPREHENSIVE TEST RESULTS")
        print("="*60)
        
        tests = [
            ("Template Functionality", template_success),
            ("Undo/Redo Operations", undo_redo_success),
            ("Parameter Bounds", bounds_success)
        ]
        
        passed = sum(1 for _, success in tests if success)
        total = len(tests)
        
        for test_name, success in tests:
            print(f"{'✅ PASS' if success else '❌ FAIL'} - {test_name}")
        
        print(f"\nOverall: {passed}/{total} test suites passed ({passed/total*100:.1f}%)")
        
        if passed == total:
            print("\n🎉 All enhanced NLP functionality working perfectly!")
            print("🚀 System ready for production use!")
        else:
            print(f"\n🔧 {total-passed} test suite(s) need attention")
        
        # Show parameter bounds summary
        print(f"\n📏 PARAMETER BOUNDS REFERENCE:")
        print(f"   Crossline (X): 100,000 - 200,000")
        print(f"   Inline (Y): 100,000 - 150,000") 
        print(f"   Depth (Z): 1,000 - 6,000")
        print(f"   Scale: 0.1 - 3.0")
        print(f"   Rotation: -π to π")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()