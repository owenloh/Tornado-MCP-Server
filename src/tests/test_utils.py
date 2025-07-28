#!/usr/bin/env python3
"""
Test Utilities for NLP System Tests

Common utilities and helpers for test files.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from utils.env_config import EnvConfig


def get_test_api_key():
    """Get API key for testing with proper error handling"""
    env_config = EnvConfig(silent=True)  # Silent mode for tests
    api_key = env_config.gemini_api_key
    
    if not api_key:
        print("❌ Cannot run tests without valid API key")
        print("💡 Please update your .env file with:")
        print("   GEMINI_API_KEY=your_actual_gemini_api_key")
        return None
    
    return api_key


def validate_test_environment():
    """Validate that test environment is properly configured"""
    env_config = EnvConfig()
    return env_config.validate_required_vars()