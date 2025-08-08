#!/usr/bin/env python3
"""
Configuration loader for Tornado MCP system

Loads configuration from config.json at project root
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

class ConfigLoader:
    """Load and manage configuration from config.json"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize config loader
        
        Args:
            config_path: Path to config file. If None, looks for config.json at project root
        """
        if config_path is None:
            # Get project root (3 levels up from src/utils/config_loader.py)
            project_root = Path(__file__).parent.parent.parent
            self.config_path = project_root / "config.json"
        else:
            self.config_path = Path(config_path)
        
        self.config = {}
        self.load_config()
    
    def load_config(self) -> bool:
        """
        Load configuration from file
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.config_path.exists():
                print(f"Config file not found: {self.config_path}")
                print("Using default configuration")
                self._create_default_config()
                return False
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            
            print(f"Configuration loaded from {self.config_path}")
            return True
            
        except Exception as e:
            print(f"Error loading config: {e}")
            print("Using default configuration")
            self._create_default_config()
            return False
    
    def _create_default_config(self):
        """Create default configuration"""
        self.config = {
            "seismic": {
                "data_path": "a:eamea::trutl07:/seisml_miniproject/original_seismic_w_dipxy",
                "default_template": "default_bookmark.html"
            }
        }
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation
        
        Args:
            key_path: Dot-separated path to config value (e.g., 'seismic.data_path')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        try:
            keys = key_path.split('.')
            value = self.config
            
            for key in keys:
                value = value[key]
            
            return value
            
        except (KeyError, TypeError):
            return default
    
    def get_seismic_path(self) -> str:
        """Get seismic data path"""
        return self.get('seismic.data_path', 'a:eamea::trutl07:/seisml_miniproject/original_seismic_w_dipxy')
    
    def get_default_template(self) -> str:
        """Get default template name"""
        return self.get('seismic.default_template', 'default_bookmark.html')
    

# Global config instance
_config_instance = None

def get_config() -> ConfigLoader:
    """Get global config instance (singleton pattern)"""
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigLoader()
    return _config_instance

def reload_config() -> ConfigLoader:
    """Reload configuration from file"""
    global _config_instance
    _config_instance = ConfigLoader()
    return _config_instance