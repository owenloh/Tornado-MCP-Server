#!/usr/bin/env python3
"""
SQLite Database Manager for Tornado MCP System

This module provides SQLite database configuration and initialization
to replace Firebase functionality with local database storage.
"""

import sqlite3
import json
import os
import threading
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import uuid


class SQLiteManager:
    """SQLite database manager for local command queue and state management"""
    
    def __init__(self, db_path: str = None):
        """
        Initialize SQLite database manager
        
        Args:
            db_path: Path to SQLite database file
        """
        if db_path is None:
            # Default to database/tornado_mcp.db in project root
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            db_dir = project_root / "database"
            db_dir.mkdir(exist_ok=True)
            self.db_path = str(db_dir / "tornado_mcp.db")
        else:
            self.db_path = db_path
        
        self._lock = threading.Lock()
        self._connection_pool = []
        self._max_connections = 3  # Limit connections for network file systems
        self.initialize_database()
    
    def _check_database_accessible(self) -> bool:
        """Check if database file is accessible on network file system"""
        try:
            import os
            import time
            
            # Check if file exists and is readable
            if not os.path.exists(self.db_path):
                return False
            
            # Try to get file stats (this can fail on network file systems)
            stat_info = os.stat(self.db_path)
            
            # Check if file is not empty (0 size can indicate network issues)
            if stat_info.st_size == 0:
                return False
            
            # Try to open file in read mode to test network accessibility
            with open(self.db_path, 'rb') as f:
                f.read(1)  # Read just 1 byte to test access
            
            return True
            
        except Exception as e:
            print(f"Database accessibility check failed: {e}")
            return False
    
    def initialize_database(self) -> bool:
        """
        Initialize SQLite database and create tables
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            with self._lock:
                # Connect with improved settings for better reliability
                conn = sqlite3.connect(
                    self.db_path,
                    timeout=30.0,  # 30 second timeout
                    check_same_thread=False,  # Allow multi-threading
                    isolation_level=None  # Autocommit mode for better concurrency
                )
                
                # Use DELETE mode for network file systems (WAL mode causes corruption on NFS)
                conn.execute('PRAGMA journal_mode=DELETE')
                conn.execute('PRAGMA synchronous=FULL')  # Full sync for network file systems
                conn.execute('PRAGMA cache_size=1000')  # Smaller cache for network stability
                conn.execute('PRAGMA temp_store=MEMORY')  # Store temp tables in memory
                conn.execute('PRAGMA locking_mode=NORMAL')  # Normal locking for shared access
                conn.execute('PRAGMA busy_timeout=30000')  # 30 second timeout for network delays
                
                cursor = conn.cursor()
                
                # Create command_queue table with deduplication support
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS command_queue (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        method TEXT NOT NULL,
                        params TEXT,  -- JSON string
                        status TEXT DEFAULT 'queued',
                        timestamp TEXT NOT NULL,
                        result TEXT,  -- JSON string
                        error TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        processing_started_at DATETIME,  -- Track when processing started
                        UNIQUE(user_id, method, timestamp) ON CONFLICT IGNORE  -- Prevent duplicates
                    )
                ''')
                
                # Add migration for existing databases
                try:
                    cursor.execute('ALTER TABLE command_queue ADD COLUMN processing_started_at DATETIME')
                except Exception:
                    # Column already exists or other error, continue
                    pass
                
                # Create tornado_state table (replaces Firebase tornado_state collection)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS tornado_state (
                        user_id TEXT PRIMARY KEY,
                        state_data TEXT NOT NULL,  -- JSON string
                        timestamp TEXT NOT NULL,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create tornado_requests table (replaces Firebase tornado_requests collection)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS tornado_requests (
                        user_id TEXT PRIMARY KEY,
                        request_type TEXT NOT NULL,
                        request_data TEXT,  -- JSON string
                        timestamp TEXT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create system_status table (replaces Firebase system_status collection)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS system_status (
                        component TEXT PRIMARY KEY,
                        status TEXT NOT NULL,
                        last_update TEXT NOT NULL,
                        data TEXT,  -- JSON string
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create indexes for performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_command_queue_user_status ON command_queue(user_id, status)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_command_queue_timestamp ON command_queue(timestamp)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_tornado_state_user ON tornado_state(user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_tornado_requests_user ON tornado_requests(user_id)')
                
                conn.commit()
                conn.close()
                
                print(f"SQLite database initialized at {self.db_path}")
                return True
                
        except Exception as e:
            print(f"Error initializing SQLite database: {e}")
            return False
    
    def get_connection(self) -> sqlite3.Connection:
        """
        Get a new database connection with robust settings
        
        Returns:
            sqlite3.Connection: Database connection
        """
        conn = sqlite3.connect(
            self.db_path, 
            timeout=30.0,
            check_same_thread=False,
            isolation_level='DEFERRED'  # Use transactions for network safety
        )
        conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
        
        # Network-safe settings
        conn.execute('PRAGMA journal_mode=DELETE')
        conn.execute('PRAGMA synchronous=FULL')
        conn.execute('PRAGMA cache_size=1000')
        conn.execute('PRAGMA temp_store=MEMORY')
        conn.execute('PRAGMA locking_mode=NORMAL')
        conn.execute('PRAGMA busy_timeout=30000')
        
        return conn
    
    def execute_query(self, query: str, params: tuple = None, fetch: str = None) -> Any:
        """
        Execute a database query with network-safe error handling
        
        Args:
            query: SQL query to execute
            params: Query parameters
            fetch: 'one', 'all', or None for no fetch
            
        Returns:
            Query result or None
        """
        import time
        max_retries = 3
        retry_delay = 0.1
        
        for attempt in range(max_retries):
            try:
                with self._lock:
                    # Check database accessibility for network file systems
                    if not self._check_database_accessible():
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay * (2 ** attempt))
                            continue
                        else:
                            raise Exception("Database file not accessible after retries")
                    
                    conn = self.get_connection()
                    try:
                        cursor = conn.cursor()
                        if params:
                            cursor.execute(query, params)
                        else:
                            cursor.execute(query)
                        
                        if fetch == 'one':
                            result = cursor.fetchone()
                        elif fetch == 'all':
                            result = cursor.fetchall()
                        else:
                            result = None
                        
                        conn.commit()
                        return result
                        
                    except Exception as e:
                        conn.rollback()
                        raise e
                    finally:
                        conn.close()
                        
            except Exception as e:
                error_msg = str(e).lower()
                # Check for network/file system related errors
                if any(err in error_msg for err in ['disk i/o error', 'database is locked', 'unable to open database', 'database disk image is malformed']):
                    if attempt < max_retries - 1:
                        print(f"Network database error (attempt {attempt + 1}), retrying: {e}")
                        time.sleep(retry_delay * (2 ** attempt))
                        continue
                    else:
                        print(f"Network database error after {max_retries} attempts: {e}")
                        raise
                else:
                    # Non-network error, don't retry
                    raise
    
    def insert_command(self, command_id: str, user_id: str, method: str, 
                      params: Dict[str, Any] = None) -> bool:
        """
        Insert a new command into the queue
        
        Args:
            command_id: Unique command identifier
            user_id: User identifier
            method: Command method name
            params: Command parameters
            
        Returns:
            bool: True if successful
        """
        try:
            params_json = json.dumps(params) if params else None
            timestamp = datetime.now(timezone.utc).isoformat()
            
            query = '''
                INSERT INTO command_queue (id, user_id, method, params, status, timestamp)
                VALUES (?, ?, ?, ?, 'queued', ?)
            '''
            
            self.execute_query(query, (command_id, user_id, method, params_json, timestamp))
            return True
            
        except Exception as e:
            print(f"Error inserting command: {e}")
            return False
    
    def get_pending_commands(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get pending commands for a user with deduplication safety
        
        Args:
            user_id: User identifier
            
        Returns:
            List of pending commands
        """
        try:
            # Try with processing_started_at column first, fallback if column doesn't exist
            try:
                query = '''
                    SELECT * FROM command_queue 
                    WHERE user_id = ? AND status = 'queued'
                    AND (processing_started_at IS NULL OR 
                         datetime(processing_started_at, '+60 seconds') < datetime('now'))
                    ORDER BY timestamp ASC
                    LIMIT 10
                '''
                rows = self.execute_query(query, (user_id,), fetch='all')
            except Exception as e:
                if "no such column: processing_started_at" in str(e):
                    # Fallback for databases without the new column
                    query = '''
                        SELECT * FROM command_queue 
                        WHERE user_id = ? AND status = 'queued'
                        ORDER BY timestamp ASC
                        LIMIT 10
                    '''
                    rows = self.execute_query(query, (user_id,), fetch='all')
                else:
                    raise

            
            commands = []
            for row in rows:
                command = dict(row)
                # Parse JSON fields safely
                if command['params']:
                    try:
                        command['params'] = json.loads(command['params'])
                    except:
                        command['params'] = {}
                if command['result']:
                    try:
                        command['result'] = json.loads(command['result'])
                    except:
                        command['result'] = {}
                commands.append(command)
            
            return commands
            
        except Exception as e:
            print(f"Error getting pending commands: {e}")
            return []
    
    def update_command_status(self, command_id: str, status: str, 
                            result: Dict[str, Any] = None, error: str = None) -> bool:
        """
        Update command status and result
        
        Args:
            command_id: Command identifier
            status: New status ('processing', 'executed', 'failed')
            result: Command result data
            error: Error message if failed
            
        Returns:
            bool: True if successful
        """
        try:
            result_json = json.dumps(result) if result else None
            timestamp = datetime.now(timezone.utc).isoformat()
            
            query = '''
                UPDATE command_queue 
                SET status = ?, result = ?, error = ?, updated_at = ?
                WHERE id = ?
            '''
            
            self.execute_query(query, (status, result_json, error, timestamp, command_id))
            return True
            
        except Exception as e:
            print(f"Error updating command status: {e}")
            return False
    
    def mark_command_processing(self, command_id: str) -> bool:
        """
        Mark command as being processed to prevent duplicate processing
        
        Args:
            command_id: Command identifier
            
        Returns:
            bool: True if successful
        """
        try:
            query = '''
                UPDATE command_queue 
                SET processing_started_at = datetime('now')
                WHERE id = ? AND status = 'queued'
            '''
            
            self.execute_query(query, (command_id,))
            return True
            
        except Exception as e:
            if "no such column: processing_started_at" in str(e):
                # Column doesn't exist yet, skip this safety check
                print("Warning: processing_started_at column not available, skipping duplicate check")
                return True
            else:
                print(f"Error marking command as processing: {e}")
                return False
    
    def set_tornado_state(self, user_id: str, state_data: Dict[str, Any]) -> bool:
        """
        Set tornado state for a user
        
        Args:
            user_id: User identifier
            state_data: State data to store
            
        Returns:
            bool: True if successful
        """
        try:
            state_json = json.dumps(state_data)
            timestamp = datetime.now(timezone.utc).isoformat()
            
            query = '''
                INSERT OR REPLACE INTO tornado_state (user_id, state_data, timestamp)
                VALUES (?, ?, ?)
            '''
            
            self.execute_query(query, (user_id, state_json, timestamp))
            return True
            
        except Exception as e:
            print(f"Error setting tornado state: {e}")
            # Try to recover from database corruption with improved handling
            if "disk I/O error" in str(e) or "database is locked" in str(e) or "database disk image is malformed" in str(e):
                print("Attempting database recovery...")
                import time
                for attempt in range(3):  # Try up to 3 times with exponential backoff
                    try:
                        time.sleep(0.1 * (2 ** attempt))  # Exponential backoff: 0.1s, 0.2s, 0.4s
                        # Close existing connection first
                        if hasattr(self, 'connection') and self.connection:
                            self.connection.close()
                        # Reinitialize database connection
                        self.initialize_database()
                        # Retry the operation
                        self.execute_query(query, (user_id, state_json, timestamp))
                        print("Database recovery successful")
                        return True
                    except Exception as recovery_error:
                        if attempt == 2:  # Last attempt
                            print(f"Database recovery failed after 3 attempts: {recovery_error}")
                        else:
                            print(f"Recovery attempt {attempt + 1} failed, retrying...")
            return False
    
    def get_tornado_state(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get tornado state for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            State data with timestamp or None
        """
        try:
            query = 'SELECT state_data, timestamp FROM tornado_state WHERE user_id = ?'
            row = self.execute_query(query, (user_id,), fetch='one')
            
            if row:
                state_data = json.loads(row['state_data'])
                # Add the database timestamp to the state data for monitoring
                state_data['_db_timestamp'] = row['timestamp']
                return state_data
            else:
                return None
            
        except Exception as e:
            print(f"Error getting tornado state: {e}")
            return None
    
    def set_tornado_request(self, user_id: str, request_type: str, 
                          request_data: Dict[str, Any] = None) -> bool:
        """
        Set tornado request for a user
        
        Args:
            user_id: User identifier
            request_type: Type of request
            request_data: Request data
            
        Returns:
            bool: True if successful
        """
        try:
            data_json = json.dumps(request_data) if request_data else None
            timestamp = datetime.now(timezone.utc).isoformat()
            
            query = '''
                INSERT OR REPLACE INTO tornado_requests (user_id, request_type, request_data, timestamp)
                VALUES (?, ?, ?, ?)
            '''
            
            self.execute_query(query, (user_id, request_type, data_json, timestamp))
            return True
            
        except Exception as e:
            print(f"Error setting tornado request: {e}")
            return False
    
    def get_tornado_request(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get and remove tornado request for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            Request data or None
        """
        try:
            # Get the request
            query = 'SELECT * FROM tornado_requests WHERE user_id = ?'
            row = self.execute_query(query, (user_id,), fetch='one')
            
            if row:
                request = dict(row)
                if request['request_data']:
                    request['request_data'] = json.loads(request['request_data'])
                
                # Delete the request after reading
                delete_query = 'DELETE FROM tornado_requests WHERE user_id = ?'
                self.execute_query(delete_query, (user_id,))
                
                return request
            return None
            
        except Exception as e:
            print(f"Error getting tornado request: {e}")
            return None
    
    def cleanup_old_commands(self, hours: int = 24) -> int:
        """
        Clean up old completed/failed commands
        
        Args:
            hours: Age threshold in hours
            
        Returns:
            Number of commands cleaned up
        """
        try:
            cutoff_time = datetime.now(timezone.utc).timestamp() - (hours * 3600)
            cutoff_iso = datetime.fromtimestamp(cutoff_time, timezone.utc).isoformat()
            
            query = '''
                DELETE FROM command_queue 
                WHERE status IN ('executed', 'failed') AND timestamp < ?
            '''
            
            cursor = self.execute_query(query, (cutoff_iso,))
            return cursor.rowcount if cursor else 0
            
        except Exception as e:
            print(f"Error cleaning up old commands: {e}")
            return 0


# Global database instance
_db_instance = None

def get_database() -> SQLiteManager:
    """Get global database instance (singleton pattern)"""
    global _db_instance
    if _db_instance is None:
        _db_instance = SQLiteManager()
    return _db_instance    
def cleanup_old_commands(self, hours: int = 24) -> int:
        """
        Clean up old processed commands to prevent database bloat on network file systems
        
        Args:
            hours: Age in hours for commands to be considered old
            
        Returns:
            int: Number of commands cleaned up
        """
        try:
            query = '''
                DELETE FROM command_queue 
                WHERE status IN ('executed', 'failed') 
                AND datetime(updated_at, '+{} hours') < datetime('now')
            '''.format(hours)
            
            self.execute_query(query)
            
            # Also clean up stale processing commands (stuck for more than 1 hour)
            try:
                stale_query = '''
                    UPDATE command_queue 
                    SET status = 'failed', error = 'Processing timeout'
                    WHERE status = 'processing' 
                    AND datetime(processing_started_at, '+1 hour') < datetime('now')
                '''
                
                self.execute_query(stale_query)
            except Exception as e:
                if "no such column: processing_started_at" not in str(e):
                    # Only log if it's not the missing column error
                    print(f"Warning: Could not clean up stale commands: {e}")
            
            return 0  # Can't get exact count easily, but operation succeeded
            
        except Exception as e:
            print(f"Error cleaning up old commands: {e}")
            return 0