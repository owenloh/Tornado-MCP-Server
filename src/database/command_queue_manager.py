#!/usr/bin/env python3
"""
SQLite Command Queue Manager

Replaces Firebase CommandQueueManager with identical interface.
Maintains exact same functionality for seamless replacement.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import logging

from .sqlite_manager import get_database

class CommandQueueManager:
    """SQLite-based command queue manager (replaces Firebase version)"""
    
    def __init__(self):
        """Initialize command queue manager"""
        self.db = get_database()
        self.logger = logging.getLogger(__name__)
    
    def add_command(self, command_data: Dict[str, Any], user_id: str = "test_user_001") -> str:
        """
        Add command to queue (replaces Firebase add_command)
        
        Args:
            command_data: Dictionary containing command information
            user_id: User identifier (default for compatibility)
            
        Returns:
            Command ID
        """
        command_id = str(uuid.uuid4())
        
        try:
            # Extract method and params from command_data (Firebase compatibility)
            method = command_data.get('method')
            params = command_data.get('params', {})
            
            if not method:
                raise ValueError("Command method is required")
            
            # Use the sqlite_manager method directly
            success = self.db.insert_command(command_id, user_id, method, params)
            
            if success:
                self.logger.info(f"✅ Command added to queue: {command_id} - {method}")
                return command_id
            else:
                raise Exception("Failed to insert command")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to add command to queue: {e}")
            raise
    
    def add_command_direct(self, user_id: str, method: str, params: Dict[str, Any], 
                          command_id: Optional[str] = None) -> str:
        """
        Add command to queue with direct parameters (for tornado_listener compatibility)
        
        Args:
            user_id: User identifier
            method: Command method name
            params: Command parameters
            command_id: Optional command ID (generates if None)
            
        Returns:
            Command ID
        """
        if command_id is None:
            command_id = str(uuid.uuid4())
        
        try:
            # Use the sqlite_manager method directly
            success = self.db.insert_command(command_id, user_id, method, params)
            
            if success:
                self.logger.info(f"✅ Command added to queue: {command_id} - {method}")
                return command_id
            else:
                raise Exception("Failed to insert command")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to add command to queue: {e}")
            raise
    
    def get_pending_commands(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get pending commands for user (replaces Firebase get_pending_commands)
        
        Args:
            user_id: User identifier
            
        Returns:
            List of pending commands
        """
        try:
            # Use the sqlite_manager method directly
            commands = self.db.get_pending_commands(user_id)
            
            # Convert to expected format
            formatted_commands = []
            for cmd in commands:
                formatted_commands.append({
                    'command_id': cmd['id'],
                    'method': cmd['method'],
                    'params': cmd.get('params', {}),
                    'timestamp': cmd['timestamp'],
                    'status': cmd['status']
                })
            
            return formatted_commands
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get pending commands: {e}")
            return []
    
    def update_command_status(self, command_id: str, status: str, 
                            result: Optional[Dict[str, Any]] = None,
                            error: Optional[str] = None):
        """
        Update command status (replaces Firebase update_command_status)
        
        Args:
            command_id: Command identifier
            status: New status ('processing', 'executed', 'failed')
            result: Command result (for executed status)
            error: Error message (for failed status)
        """
        try:
            # Use the sqlite_manager method directly
            success = self.db.update_command_status(command_id, status, result, error)
            
            if success:
                self.logger.debug(f"Command {command_id} status updated to: {status}")
            else:
                # Don't raise exception for status update failures - log and continue
                self.logger.warning(f"⚠️ Command status update failed for {command_id}, but continuing execution")
            
        except Exception as e:
            # Don't raise exception for status update failures - log and continue
            self.logger.warning(f"⚠️ Failed to update command status for {command_id}: {e}, but continuing execution")
    
    def get_command_status(self, command_id: str) -> Optional[Dict[str, Any]]:
        """
        Get command status and result (replaces Firebase get_command_status)
        
        Args:
            command_id: Command identifier
            
        Returns:
            Command status information or None if not found
        """
        try:
            row = self.db.execute_query(
                """
                SELECT id, method, params, status, result, error, timestamp, updated_at
                FROM command_queue
                WHERE id = ?
                """,
                (command_id,),
                fetch='one'
            )
            
            if not row:
                return None
            
            try:
                params = json.loads(row['params']) if row['params'] else {}
            except json.JSONDecodeError:
                params = {}
            
            try:
                result = json.loads(row['result']) if row['result'] else None
            except json.JSONDecodeError:
                result = None
            
            return {
                'command_id': row['id'],
                'method': row['method'],
                'params': params,
                'status': row['status'],
                'result': result,
                'error': row['error'],
                'timestamp': row['timestamp'],
                'updated_at': row['updated_at']
            }
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get command status: {e}")
            return None
    
    def get_recent_commands(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent commands for user (for debugging/monitoring)
        
        Args:
            user_id: User identifier
            limit: Maximum number of commands to return
            
        Returns:
            List of recent commands
        """
        try:
            rows = self.db.execute_query(
                """
                SELECT id, method, params, status, result, error, timestamp, updated_at
                FROM command_queue
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (user_id, limit),
                fetch=True
            )
            
            commands = []
            for row in rows:
                try:
                    params = json.loads(row['params'])
                except json.JSONDecodeError:
                    params = {}
                
                try:
                    result = json.loads(row['result']) if row['result'] else None
                except json.JSONDecodeError:
                    result = None
                
                commands.append({
                    'command_id': row['id'],
                    'method': row['method'],
                    'params': params,
                    'status': row['status'],
                    'result': result,
                    'error': row['error'],
                    'timestamp': row['timestamp'],
                    'updated_at': row['updated_at']
                })
            
            return commands
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get recent commands: {e}")
            return []
    
    def clear_completed_commands(self, user_id: str, older_than_hours: int = 24):
        """
        Clear completed commands older than specified hours
        
        Args:
            user_id: User identifier
            older_than_hours: Clear commands older than this many hours
        """
        try:
            from datetime import timedelta
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
            cutoff_str = cutoff_time.isoformat()
            
            self.db.execute_query(
                """
                DELETE FROM command_queue
                WHERE user_id = ? AND status IN ('executed', 'failed') AND timestamp < ?
                """,
                (user_id, cutoff_str)
            )
            
            self.logger.info(f"✅ Cleared completed commands older than {older_than_hours} hours for user {user_id}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to clear completed commands: {e}")