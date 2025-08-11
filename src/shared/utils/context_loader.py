"""
Domain Context Loader for Seismic Navigation

This module loads domain-specific context that helps the AI understand
geological and geophysical terminology and translate it to specific coordinates.
"""

import json
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ContextLoader:
    """Load and manage domain-specific context for seismic navigation"""
    
    def __init__(self, context_path: Optional[str] = None):
        """
        Initialize context loader
        
        Args:
            context_path: Path to context.json file. If None, looks for context.json at project root
        """
        if context_path is None:
            # Get project root (4 levels up from src/shared/utils/context_loader.py)
            project_root = Path(__file__).parent.parent.parent.parent
            self.context_path = project_root / "context.json"
        else:
            self.context_path = Path(context_path)
        
        self.context = {}
        self.load_context()
    
    def load_context(self) -> bool:
        """
        Load context from file
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.context_path.exists():
                logger.warning(f"Context file not found: {self.context_path}")
                logger.info("Using empty context")
                self._create_default_context()
                return False
            
            with open(self.context_path, 'r', encoding='utf-8') as f:
                self.context = json.load(f)
            
            logger.info(f"Domain context loaded from {self.context_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading context: {e}")
            logger.info("Using empty context")
            self._create_default_context()
            return False
    
    def _create_default_context(self):
        """Create default empty context"""
        self.context = {
            "domain_context": ""
        }
    
    def get_domain_context(self) -> str:
        """
        Get domain-specific context string
        
        Returns:
            Domain context string for AI prompts
        """
        return self.context.get('domain_context', '')
    
    def get_full_context(self) -> Dict[str, Any]:
        """
        Get full context dictionary
        
        Returns:
            Complete context dictionary
        """
        return self.context.copy()
    
    def reload_context(self) -> bool:
        """
        Reload context from file
        
        Returns:
            bool: True if successful, False otherwise
        """
        return self.load_context()


# Global context loader instance
_context_loader = None

def get_context_loader() -> ContextLoader:
    """Get global context loader instance (singleton pattern)"""
    global _context_loader
    if _context_loader is None:
        _context_loader = ContextLoader()
    return _context_loader

def reload_context_loader() -> ContextLoader:
    """Reload context loader from file"""
    global _context_loader
    _context_loader = ContextLoader()
    return _context_loader

def get_domain_context() -> str:
    """Get domain context string (convenience function)"""
    return get_context_loader().get_domain_context()