#!/usr/bin/env python3
"""
Environment Configuration Utility

Clean, focused utility for loading and accessing environment variables
from .env file. Handles only application configuration, not infrastructure.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv


class EnvConfig:
    """Clean environment configuration manager focused on application settings"""
    
    # Required environment variables for application
    REQUIRED_VARS = {'GEMINI_API_KEY'}
    
    # Default values for optional settings
    DEFAULTS = {
        'DEBUG': 'false',
        'LOG_LEVEL': 'INFO'
    }
    
    def __init__(self, env_file: Optional[str] = None, silent: bool = False):
        """
        Initialize environment configuration
        
        Args:
            env_file: Optional path to .env file (defaults to project root)
            silent: If True, suppress loading messages
        """
        self._silent = silent
        self._load_env_file(env_file)
    
    def _load_env_file(self, env_file: Optional[str]) -> None:
        """Load environment variables from .env file"""
        env_path = self._get_env_path(env_file)
        
        if env_path.exists():
            load_dotenv(env_path)
            if not self._silent:
                print(f"✅ Loaded environment variables from {env_path}")
        elif not self._silent:
            print(f"⚠️ .env file not found at {env_path}")
    
    def _get_env_path(self, env_file: Optional[str]) -> Path:
        """Get path to .env file"""
        if env_file:
            return Path(env_file)
        
        # Look for .env in project root (2 levels up from src/utils/)
        project_root = Path(__file__).parent.parent.parent
        return project_root / ".env"
    
    @property
    def gemini_api_key(self) -> Optional[str]:
        """Get Gemini API key from environment"""
        api_key = os.getenv('GEMINI_API_KEY')
        
        if not api_key or api_key.startswith('your_'):
            if not self._silent:
                print("❌ GEMINI_API_KEY not set in .env file")
                print("💡 Please add your Gemini API key to .env file:")
                print("   GEMINI_API_KEY=your_actual_api_key_here")
            return None
        
        return api_key
    
    @property
    def debug_mode(self) -> bool:
        """Get debug mode setting"""
        return os.getenv('DEBUG', self.DEFAULTS['DEBUG']).lower() == 'true'
    
    @property
    def log_level(self) -> str:
        """Get log level setting"""
        return os.getenv('LOG_LEVEL', self.DEFAULTS['LOG_LEVEL']).upper()
    
    def get_all_config(self) -> Dict[str, Any]:
        """Get all configuration as dictionary"""
        return {
            'gemini_api_key': self.gemini_api_key,
            'debug_mode': self.debug_mode,
            'log_level': self.log_level
        }
    
    def validate_required_vars(self) -> bool:
        """Validate that all required environment variables are set"""
        missing_vars = []
        
        for var in self.REQUIRED_VARS:
            value = os.getenv(var)
            if not value or value.startswith('your_'):
                missing_vars.append(var)
        
        if missing_vars:
            if not self._silent:
                print("❌ Missing required environment variables:")
                for var in missing_vars:
                    print(f"   - {var}")
                print("\n💡 Please update your .env file with actual values")
            return False
        
        if not self._silent:
            print("✅ All required environment variables are set")
        return True
    
    # Backward compatibility methods (deprecated)
    def get_gemini_api_key(self) -> Optional[str]:
        """Deprecated: Use .gemini_api_key property instead"""
        return self.gemini_api_key
    
    def get_debug_mode(self) -> bool:
        """Deprecated: Use .debug_mode property instead"""
        return self.debug_mode
    
    def get_log_level(self) -> str:
        """Deprecated: Use .log_level property instead"""
        return self.log_level


def main():
    """Test environment configuration"""
    print("🧪 Testing Clean Environment Configuration...")
    
    # Initialize config
    config = EnvConfig()
    
    # Test modern property-based API
    if config.gemini_api_key:
        print(f"✅ Gemini API Key: {config.gemini_api_key[:10]}...{config.gemini_api_key[-4:]}")
    else:
        print("❌ Gemini API Key not available")
    
    print(f"🔧 Debug Mode: {config.debug_mode}")
    print(f"📝 Log Level: {config.log_level}")
    
    # Test configuration dictionary
    all_config = config.get_all_config()
    print(f"📋 All Config: {all_config}")
    
    # Validate required variables
    config.validate_required_vars()


if __name__ == "__main__":
    main()