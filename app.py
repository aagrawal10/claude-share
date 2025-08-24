import os
import json
import tarfile
import shutil
import fcntl
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_file
import io
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

app = Flask(__name__)

# Configuration
STATE_FILE_PATH = os.getenv("STATE_FILE_PATH", "./claude_sessions/state.json")
SESSIONS_BASE_DIR = os.getenv("SESSIONS_BASE_DIR", "./claude_sessions")
LEASE_TTL_MINUTES = int(os.getenv("LEASE_TTL_MINUTES", "30"))

# Production settings
app.config['MAX_CONTENT_LENGTH'] = int(
    os.getenv('MAX_CONTENT_LENGTH', '104857600')  # 100MB default
)


class SessionManager:
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

    def cleanup_expired_sessions(self, state):
        """Clean up expired locked sessions"""
        current_time = datetime.now()
        ttl_delta = timedelta(minutes=LEASE_TTL_MINUTES)

        for session_id, session_data in state.items():
            if (session_data.get('status') == 'locked' and
                    session_data.get('lease_acquired_at')):
                lease_time = datetime.fromisoformat(
                    session_data['lease_acquired_at'])
                if current_time - lease_time > ttl_delta:
                    session_data['status'] = 'available'
                    session_data['lease_acquired_at'] = None

    def get_session_directory(self, session_id):
        """Get the directory path for a session"""
        return os.path.join(SESSIONS_BASE_DIR, session_id)


session_manager = SessionManager()


@app.route('/claude/sessions/acquire', methods=['POST'])
def acquire_session():
    """Acquire an available session"""
    state = session_manager.load_state()

    # Clean up expired sessions
    session_manager.cleanup_expired_sessions(state)

    # Find first available session
    available_session = None
    for session_id, session_data in state.items():
        if session_data.get('status') == 'available':
            available_session = session_id
            break

    if not available_session:
        return jsonify({"error": "No sessions available"}), 429

    # Lock the session
    state[available_session]['status'] = 'locked'
    state[available_session]['lease_acquired_at'] = (
        datetime.now().isoformat())

    session_manager.save_state(state)

    return jsonify({"session_id": available_session}), 200


@app.route('/claude/sessions/<session_id>', methods=['GET'])
def download_session(session_id):
    """Download session directory as tar.gz"""
    session_dir = session_manager.get_session_directory(session_id)

    if not os.path.exists(session_dir):
        return jsonify({"error": "Session not found"}), 404

    # Create tar.gz in memory
    memory_file = io.BytesIO()

    with tarfile.open(fileobj=memory_file, mode='w:gz') as tar:
        # Add all files from session directory
        for root, dirs, files in os.walk(session_dir):
            for file in files:
                file_path = os.path.join(root, file)
                # Calculate archive name (relative to session directory)
                arcname = os.path.relpath(file_path, session_dir)
                tar.add(file_path, arcname=arcname)

    memory_file.seek(0)

    return send_file(
        memory_file,
        mimetype='application/gzip',
        as_attachment=True,
        download_name=f'session_{session_id}.tar.gz'
    )


@app.route('/claude/sessions/<session_id>/release', methods=['POST'])
def release_session(session_id):
    """Release a session and update its contents"""
    state = session_manager.load_state()

    if session_id not in state:
        return jsonify({"error": "Session not found"}), 404

    if state[session_id].get('status') != 'locked':
        return jsonify({"error": "Session is not locked"}), 400

    # Get the uploaded tar.gz file
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    uploaded_file = request.files['file']
    if uploaded_file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    session_dir = session_manager.get_session_directory(session_id)

    try:
        # Clear existing session directory
        if os.path.exists(session_dir):
            shutil.rmtree(session_dir)
        os.makedirs(session_dir)

        # Extract uploaded tar.gz to session directory
        with tarfile.open(fileobj=uploaded_file.stream, mode='r:gz') as tar:
            tar.extractall(path=session_dir)

        # Update session state
        state[session_id]['status'] = 'available'
        state[session_id]['lease_acquired_at'] = None

        session_manager.save_state(state)

        return jsonify({"message": "Session released successfully"}), 200

    except Exception as e:
        return jsonify(
            {"error": f"Failed to process session: {str(e)}"}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }), 200


@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "File too large"}), 413


@app.errorhandler(500)
def internal_server_error(e):
    app.logger.error(f"Internal server error: {str(e)}")
    return jsonify({"error": "Internal server error"}), 500


@app.errorhandler(Exception)
def handle_exception(e):
    app.logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
    return jsonify({"error": "An unexpected error occurred"}), 500


# For development only
if __name__ == '__main__':
    # This will only run when called directly, not when imported by gunicorn
    app.run(host='0.0.0.0', port=5000, debug=False)
