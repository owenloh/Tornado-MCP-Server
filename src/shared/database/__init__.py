#!/usr/bin/env python3
"""
Database Package

SQLite-based replacement for Firebase functionality.
Provides identical interfaces for seamless replacement.
"""

from .database_config import DatabaseConfig
from .command_queue_manager import CommandQueueManager
from .state_manager import TornadoStateManager, EnhancedCommandQueueManager
from .sqlite_manager import SQLiteManager, get_database

# Backward compatibility alias
FirebaseConfig = DatabaseConfig

__all__ = [
    'DatabaseConfig',
    'FirebaseConfig',  # Backward compatibility alias
    'CommandQueueManager', 
    'TornadoStateManager',
    'EnhancedCommandQueueManager',
    'SQLiteManager',
    'get_database'
]