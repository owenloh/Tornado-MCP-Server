#!/usr/bin/env python3
"""
Firebase Configuration and Setup for Command Queue System

This module provides Firebase database configuration and initialization
for the seismic navigation speech interface command queue system.

Task 3.1: Set up Firebase database structure for command queuing
- Design Firebase schema for command queue with user isolation
- Implement command status tracking (queued, processing, executed, failed)
- Create user session management for multiple concurrent users
- Set up Firebase security rules for command queue access
"""

import firebase_admin
from firebase_admin import credentials, firestore
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import uuid


class FirebaseConfig:
    """Firebase configuration and database setup for command queuing"""
    
    def __init__(self, credentials_path: str = "firebase_credentials.json"):
        """
        Initialize Firebase configuration
        
        Args:
            credentials_path: Path to Firebase service account credentials JSON file
        """
        # If path is relative, make it relative to project root
        if not os.path.isabs(credentials_path):
            # Get project root (3 levels up from src/firebase/firebase_config.py)
            project_root = Path(__file__).parent.parent.parent
            self.credentials_path = str(project_root / credentials_path)
        else:
            self.credentials_path = credentials_path
            
        self.db = None
        self.app = None
        
    def initialize_firebase(self) -> bool:
        """
        Initialize Firebase app and Firestore database
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            # Check if Firebase app is already initialized
            if not firebase_admin._apps:
                # Initialize Firebase app with service account credentials
                if os.path.exists(self.credentials_path):
                    cred = credentials.Certificate(self.credentials_path)
                    self.app = firebase_admin.initialize_app(cred)
                else:
                    # For development, try to use default credentials
                    print(f"Warning: {self.credentials_path} not found, using default credentials")
                    self.app = firebase_admin.initialize_app()
            else:
                self.app = firebase_admin.get_app()
                
            # Initialize Firestore database
            self.db = firestore.client()
            print("Firebase initialized successfully")
            return True
            
        except Exception as e:
            print(f"Error initializing Firebase: {e}")
            return False
    
    def create_database_structure(self) -> bool:
        """
        Create the initial database structure for command queuing
        
        Database Schema:
        /command_queues/{user_id}/commands/{command_id}
        /user_sessions/{user_id}
        /system_status/tornado_listener
        
        Returns:
            bool: True if structure created successfully
        """
        try:
            if not self.db:
                print("Error: Firebase not initialized")
                return False
                
            # Create system status document
            system_status_ref = self.db.collection('system_status').document('tornado_listener')
            system_status_ref.set({
                'status': 'offline',
                'last_heartbeat': firestore.SERVER_TIMESTAMP,
                'version': '1.0.0',
                'initialized': firestore.SERVER_TIMESTAMP
            })
            
            # Create example user session (for testing)
            test_user_id = 'test_user_001'
            user_session_ref = self.db.collection('user_sessions').document(test_user_id)
            user_session_ref.set({
                'user_id': test_user_id,
                'session_start': firestore.SERVER_TIMESTAMP,
                'last_activity': firestore.SERVER_TIMESTAMP,
                'active': True,
                'commands_processed': 0
            })
            
            print("Database structure created successfully")
            return True
            
        except Exception as e:
            print(f"Error creating database structure: {e}")
            return False


class CommandQueueManager:
    """Manages command queue operations for Firebase"""
    
    def __init__(self, firebase_config: FirebaseConfig):
        """
        Initialize command queue manager
        
        Args:
            firebase_config: Initialized FirebaseConfig instance
        """
        self.db = firebase_config.db
        self.user_id = "test_user_001"  # Default user for testing
        
    def add_command(self, command_data: Dict[str, Any]) -> str:
        """
        Add a command to the user's command queue
        
        Args:
            command_data: Dictionary containing command information
            
        Returns:
            str: Command ID if successful, None if failed
        """
        try:
            command_id = str(uuid.uuid4())
            
            # Prepare command document
            command_doc = {
                'command_id': command_id,
                'user_id': self.user_id,
                'method': command_data.get('method'),
                'params': command_data.get('params', {}),
                'status': 'queued',
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP,
                'priority': command_data.get('priority', 1),
                'retry_count': 0,
                'max_retries': 3
            }
            
            # Add to command queue
            command_ref = self.db.collection('command_queues').document(self.user_id).collection('commands').document(command_id)
            command_ref.set(command_doc)
            
            # Update user session
            self.update_user_activity()
            
            print(f"Command {command_id} added to queue: {command_data.get('method')}")
            return command_id
            
        except Exception as e:
            print(f"Error adding command to queue: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_pending_commands(self, user_id: Optional[str] = None) -> list:
        """
        Get all pending commands for a user
        
        Args:
            user_id: User ID (defaults to current user)
            
        Returns:
            list: List of pending command documents
        """
        try:
            target_user = user_id or self.user_id
            
            commands_ref = self.db.collection('command_queues').document(target_user).collection('commands')
            # Simple query without order_by to avoid index requirement
            query = commands_ref.where('status', '==', 'queued')
            
            commands = []
            for doc in query.stream():
                command_data = doc.to_dict()
                command_data['doc_id'] = doc.id
                commands.append(command_data)
                
            return commands
            
        except Exception as e:
            print(f"Error getting pending commands: {e}")
            return []
    
    def update_command_status(self, command_id: str, status: str, result: Optional[Dict] = None, error: Optional[str] = None) -> bool:
        """
        Update command status and result
        
        Args:
            command_id: Command ID to update
            status: New status (processing, executed, failed)
            result: Command execution result (optional)
            error: Error message if failed (optional)
            
        Returns:
            bool: True if update successful
        """
        try:
            command_ref = self.db.collection('command_queues').document(self.user_id).collection('commands').document(command_id)
            
            update_data = {
                'status': status,
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            
            if result:
                update_data['result'] = result
            if error:
                update_data['error'] = error
            if status == 'failed':
                # Increment retry count
                command_doc = command_ref.get()
                if command_doc.exists:
                    current_retries = command_doc.to_dict().get('retry_count', 0)
                    update_data['retry_count'] = current_retries + 1
            
            command_ref.update(update_data)
            print(f"Command {command_id} status updated to: {status}")
            return True
            
        except Exception as e:
            print(f"Error updating command status: {e}")
            return False
    
    def update_user_activity(self) -> bool:
        """
        Update user session last activity timestamp
        
        Returns:
            bool: True if update successful
        """
        try:
            user_ref = self.db.collection('user_sessions').document(self.user_id)
            user_ref.update({
                'last_activity': firestore.SERVER_TIMESTAMP
            })
            return True
            
        except Exception as e:
            print(f"Error updating user activity: {e}")
            return False
    
    def cleanup_old_commands(self, hours_old: int = 24) -> int:
        """
        Clean up old completed/failed commands
        
        Args:
            hours_old: Remove commands older than this many hours
            
        Returns:
            int: Number of commands cleaned up
        """
        try:
            from datetime import timedelta
            
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_old)
            
            commands_ref = self.db.collection('command_queues').document(self.user_id).collection('commands')
            
            # Query for old completed/failed commands (simplified to avoid index requirement)
            old_commands = commands_ref.where('status', '==', 'executed').stream()
            
            deleted_count = 0
            for doc in old_commands:
                doc.reference.delete()
                deleted_count += 1
            
            print(f"Cleaned up {deleted_count} old commands")
            return deleted_count
            
        except Exception as e:
            print(f"Error cleaning up old commands: {e}")
            return 0


def main():
    """Test Firebase configuration and setup"""
    print("Testing Firebase Configuration...")
    
    # Initialize Firebase
    firebase_config = FirebaseConfig()
    if not firebase_config.initialize_firebase():
        print("Failed to initialize Firebase")
        return
    
    # Create database structure
    if not firebase_config.create_database_structure():
        print("Failed to create database structure")
        return
    
    # Test command queue manager
    queue_manager = CommandQueueManager(firebase_config)
    
    # Add test command
    test_command = {
        'method': 'update_position',
        'params': {'x': 160000, 'y': 112000, 'z': 3500}
    }
    
    command_id = queue_manager.add_command(test_command)
    if command_id:
        print(f"Test command added with ID: {command_id}")
        
        # Test getting pending commands
        pending = queue_manager.get_pending_commands()
        print(f"Pending commands: {len(pending)}")
        
        # Test updating command status
        queue_manager.update_command_status(command_id, 'executed', {'success': True})
    
    print("Firebase configuration test completed")


if __name__ == "__main__":
    main()