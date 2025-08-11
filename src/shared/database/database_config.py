#!/usr/bin/env python3
"""
Database Configuration for Command Queue System

This module provides SQLite database configuration and initialization
to replace Firebase functionality with local database storage.
"""

import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import uuid
from .sqlite_manager import SQLiteManager, get_database


class DatabaseConfig:
    """Database configuration and setup for command queuing (replaces FirebaseConfig)"""
    
    def __init__(self, db_path: str = None):
        """
        Initialize Database configuration
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.db = None
        self.app = None  # Kept for compatibility with existing code
        self.initialized = False
        
    def initialize_database(self) -> bool:
        """
        Initialize SQLite database
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            if self.db_path:
                self.db = SQLiteManager(self.db_path)
            else:
                self.db = get_database()
            
            self.initialized = True
            print("Database initialized successfully")
            return True
            
        except Exception as e:
            print(f"Error initializing database: {e}")
            self.initialized = False
            return False
    
    def is_initialized(self) -> bool:
        """Check if database is initialized"""
        return getattr(self, 'initialized', False) and self.db is not None
    
    def create_database_structure(self) -> bool:
        """
        Create the initial database structure for command queuing
        
        Database Schema:
        - command_queue: Command queuing with status tracking
        - tornado_state: Current state synchronization
        - tornado_requests: State/template requests
        - system_status: System health monitoring
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Database structure is created automatically by SQLiteManager
            return True
            
        except Exception as e:
            print(f"Error creating database structure: {e}")
            return False


class CommandQueueManager:
    """Command queue manager for SQLite database (replaces Firebase CommandQueueManager)"""
    
    def __init__(self, database_config: DatabaseConfig):
        """
        Initialize command queue manager
        
        Args:
            database_config: Database configuration instance
        """
        self.db = database_config.db
        if not self.db:
            self.db = get_database()
    
    def add_command(self, user_id: str, method: str, params: Dict[str, Any] = None, 
                   command_id: str = None) -> str:
        """
        Add a command to the queue
        
        Args:
            user_id: User identifier
            method: Command method name
            params: Command parameters
            command_id: Optional command ID (generated if not provided)
            
        Returns:
            str: Command ID
        """
        if command_id is None:
            command_id = str(uuid.uuid4())
        
        success = self.db.insert_command(command_id, user_id, method, params)
        if success:
            print(f"Command {command_id} added to queue: {method}")
        else:
            print(f"Failed to add command {command_id} to queue")
        
        return command_id
    
    def get_pending_commands(self, user_id: str) -> list:
        """
        Get pending commands for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            list: List of pending commands
        """
        return self.db.get_pending_commands(user_id)
    
    def update_command_status(self, command_id: str, status: str, 
                            result: Dict[str, Any] = None, error: str = None) -> bool:
        """
        Update command status
        
        Args:
            command_id: Command identifier
            status: New status ('processing', 'executed', 'failed')
            result: Command result data
            error: Error message if failed
            
        Returns:
            bool: True if successful
        """
        success = self.db.update_command_status(command_id, status, result, error)
        if success:
            print(f"Command {command_id} status updated to: {status}")
        else:
            print(f"Failed to update command {command_id} status")
        
        return success
    
    def cleanup_old_commands(self, hours: int = 24) -> int:
        """
        Clean up old completed commands
        
        Args:
            hours: Age threshold in hours
            
        Returns:
            int: Number of commands cleaned up
        """
        return self.db.cleanup_old_commands(hours)


def main():
    """Test database configuration"""
    print("Testing SQLite Database Configuration...")
    
    # Initialize database
    config = DatabaseConfig()
    if not config.initialize_database():
        print("Failed to initialize database")
        return
    
    # Test command queue
    queue_manager = CommandQueueManager(config)
    
    # Add a test command
    command_id = queue_manager.add_command(
        user_id="test_user_001",
        method="test_command",
        params={"test": "data"}
    )
    
    # Get pending commands
    pending = queue_manager.get_pending_commands("test_user_001")
    print(f"Pending commands: {len(pending)}")
    
    # Update command status
    queue_manager.update_command_status(command_id, "executed", {"result": "success"})
    
    # Check pending again
    pending = queue_manager.get_pending_commands("test_user_001")
    print(f"Pending commands after update: {len(pending)}")
    
    print("Database configuration test completed")


if __name__ == "__main__":
    main()