#!/usr/bin/env python3
"""
Admin script for managing Claude sessions in the session leasing service.

Usage:
    python admin.py create <session_id>
    python admin.py list
    python admin.py status <session_id>
"""

import os
import json
import argparse
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

    def create_session(self, session_id):
        """Create a new session entry in state file"""
        state = self.load_state()

        if session_id in state:
            raise ValueError(f"Session ID {session_id} already exists")

        session_dir = self.get_session_directory(session_id)

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
            created_raw = session_data.get('created_at')
            created = (created_raw[:19] if created_raw
                       else 'unknown')
            updated_raw = session_data.get('updated_at')
            updated = (updated_raw[:19] if updated_raw
                       else 'unknown')

            print(f"{session_id:<8} {status:<12} "
                  f"{created:<20} {updated:<20}")

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
        print(f"Lease acquired: "
              f"{session_data.get('lease_acquired_at', 'None')}")

        if os.path.exists(session_dir):
            files = list(Path(session_dir).rglob('*'))
            file_count = len([f for f in files if f.is_file()])
            dir_count = len([f for f in files if f.is_dir()])
            print(f"Files in directory: {file_count}")
            print(f"Subdirectories: {dir_count}")


def main():
    parser = argparse.ArgumentParser(
        description="Admin tool for Claude session management")
    subparsers = parser.add_subparsers(
        dest='command', help='Available commands')

    # Create command
    create_parser = subparsers.add_parser('create',
                                          help='Create a new session')
    create_parser.add_argument(
        'session_id', help='Session ID to create')

    # List command
    subparsers.add_parser('list', help='List all sessions')

    # Status command
    status_parser = subparsers.add_parser(
        'status', help='Get detailed status of a session')
    status_parser.add_argument('session_id', help='Session ID to check')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    admin = AdminManager()

    try:
        if args.command == 'create':
            admin.create_session(args.session_id)
        elif args.command == 'list':
            admin.list_sessions()
        elif args.command == 'status':
            admin.get_session_status(args.session_id)
    except Exception as e:
        print(f"Error: {e}")
        exit(1)


if __name__ == '__main__':
    main()
