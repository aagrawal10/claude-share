#!/usr/bin/env python3
"""
Admin script for managing Claude sessions in the session leasing service.

Usage:
    python admin.py create <directory_or_tar> [--session-id <id>]
    python admin.py update <session_id> <directory_or_tar>
    python admin.py list
    python admin.py status <session_id>
"""

import os
import json
import argparse
import tarfile
import shutil
import fcntl
from pathlib import Path
from datetime import datetime

# Configuration (should match app.py)
STATE_FILE_PATH = "./claude_sessions/state.json"
SESSIONS_BASE_DIR = "./claude_sessions"

class AdminManager:
    def __init__(self):
        self.ensure_directories()
    
    def ensure_directories(self):
        """Ensure the sessions directory exists"""
        os.makedirs(SESSIONS_BASE_DIR, exist_ok=True)
    
    def load_state(self):
        """Load state from JSON file with file locking"""
        try:
            with open(STATE_FILE_PATH, 'r') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def save_state(self, state):
        """Save state to JSON file atomically with file locking"""
        temp_file = STATE_FILE_PATH + '.tmp'
        with open(temp_file, 'w') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            json.dump(state, f, indent=2)
        os.rename(temp_file, STATE_FILE_PATH)
    
    def get_next_session_id(self, state):
        """Generate the next available session ID"""
        existing_ids = [int(sid) for sid in state.keys() if sid.isdigit()]
        return str(max(existing_ids, default=0) + 1)
    
    def get_session_directory(self, session_id):
        """Get the directory path for a session"""
        return os.path.join(SESSIONS_BASE_DIR, session_id)
    
    def extract_source(self, source_path, target_dir):
        """Extract directory or tar file to target directory"""
        source_path = Path(source_path)
        
        if not source_path.exists():
            raise FileNotFoundError(f"Source path does not exist: {source_path}")
        
        # Clean target directory
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
        os.makedirs(target_dir)
        
        if source_path.is_dir():
            # Copy directory contents
            for item in source_path.iterdir():
                if item.is_dir():
                    shutil.copytree(item, os.path.join(target_dir, item.name))
                else:
                    shutil.copy2(item, target_dir)
        elif source_path.suffix in ['.tar', '.gz'] or source_path.name.endswith('.tar.gz'):
            # Extract tar file
            with tarfile.open(source_path, 'r:*') as tar:
                tar.extractall(path=target_dir)
        else:
            raise ValueError(f"Unsupported source type. Expected directory or tar file, got: {source_path}")
    
    def create_session(self, source_path, session_id=None):
        """Create a new session from directory or tar file"""
        state = self.load_state()
        
        if session_id is None:
            session_id = self.get_next_session_id(state)
        elif session_id in state:
            raise ValueError(f"Session ID {session_id} already exists")
        
        session_dir = self.get_session_directory(session_id)
        
        try:
            # Extract source to session directory
            self.extract_source(source_path, session_dir)
            
            # Add session to state
            state[session_id] = {
                'status': 'available',
                'lease_acquired_at': None,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            self.save_state(state)
            
            print(f"Session {session_id} created successfully")
            print(f"Session directory: {session_dir}")
            return session_id
            
        except Exception as e:
            # Cleanup on failure
            if os.path.exists(session_dir):
                shutil.rmtree(session_dir)
            raise e
    
    def update_session(self, session_id, source_path):
        """Update an existing session with new directory or tar file"""
        state = self.load_state()
        
        if session_id not in state:
            raise ValueError(f"Session ID {session_id} does not exist")
        
        if state[session_id].get('status') == 'locked':
            print(f"Warning: Session {session_id} is currently locked. Updating anyway.")
        
        session_dir = self.get_session_directory(session_id)
        
        # Extract source to session directory
        self.extract_source(source_path, session_dir)
        
        # Update session metadata
        state[session_id]['updated_at'] = datetime.now().isoformat()
        
        self.save_state(state)
        
        print(f"Session {session_id} updated successfully")
        print(f"Session directory: {session_dir}")
    
    def list_sessions(self):
        """List all sessions with their status"""
        state = self.load_state()
        
        if not state:
            print("No sessions found")
            return
        
        print(f"{'ID':<8} {'Status':<12} {'Created':<20} {'Updated':<20}")
        print("-" * 64)
        
        for session_id, session_data in sorted(state.items()):
            status = session_data.get('status', 'unknown')
            created = session_data.get('created_at', 'unknown')[:19] if session_data.get('created_at') else 'unknown'
            updated = session_data.get('updated_at', 'unknown')[:19] if session_data.get('updated_at') else 'unknown'
            
            print(f"{session_id:<8} {status:<12} {created:<20} {updated:<20}")
    
    def get_session_status(self, session_id):
        """Get detailed status of a specific session"""
        state = self.load_state()
        
        if session_id not in state:
            print(f"Session {session_id} does not exist")
            return
        
        session_data = state[session_id]
        session_dir = self.get_session_directory(session_id)
        
        print(f"Session ID: {session_id}")
        print(f"Status: {session_data.get('status', 'unknown')}")
        print(f"Directory: {session_dir}")
        print(f"Directory exists: {os.path.exists(session_dir)}")
        print(f"Created: {session_data.get('created_at', 'unknown')}")
        print(f"Updated: {session_data.get('updated_at', 'unknown')}")
        print(f"Lease acquired: {session_data.get('lease_acquired_at', 'None')}")
        
        if os.path.exists(session_dir):
            files = list(Path(session_dir).rglob('*'))
            print(f"Files in directory: {len([f for f in files if f.is_file()])}")
            print(f"Subdirectories: {len([f for f in files if f.is_dir()])}")

def main():
    parser = argparse.ArgumentParser(description="Admin tool for Claude session management")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create a new session')
    create_parser.add_argument('source', help='Directory or tar file to use as session source')
    create_parser.add_argument('--session-id', help='Specific session ID to use (optional)')
    
    # Update command
    update_parser = subparsers.add_parser('update', help='Update an existing session')
    update_parser.add_argument('session_id', help='Session ID to update')
    update_parser.add_argument('source', help='Directory or tar file to use as new session content')
    
    # List command
    subparsers.add_parser('list', help='List all sessions')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Get detailed status of a session')
    status_parser.add_argument('session_id', help='Session ID to check')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    admin = AdminManager()
    
    try:
        if args.command == 'create':
            admin.create_session(args.source, args.session_id)
        elif args.command == 'update':
            admin.update_session(args.session_id, args.source)
        elif args.command == 'list':
            admin.list_sessions()
        elif args.command == 'status':
            admin.get_session_status(args.session_id)
    except Exception as e:
        print(f"Error: {e}")
        exit(1)

if __name__ == '__main__':
    main()