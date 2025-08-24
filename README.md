# claude-share
A simple server to share claude code sessions

## Features

**Session Creation:**
- `python admin.py create <directory_or_tar>` - Creates new session with auto-generated ID
- `python admin.py create <directory_or_tar> --session-id <id>` - Creates session with specific ID

**Session Updates:**
- `python admin.py update <session_id> <directory_or_tar>` - Updates existing session content

**Session Management:**
- `python admin.py list` - Lists all sessions with status
- `python admin.py status <session_id>` - Detailed status of specific session

## Key Capabilities

1. **Flexible Input:** Accepts both directories and tar files (.tar, .tar.gz, .gz)
2. **Auto ID Generation:** Creates sequential session IDs automatically
3. **Safe Operations:** Uses file locking and atomic operations like the main service
4. **Error Handling:** Comprehensive error handling with cleanup on failure
5. **Status Tracking:** Maintains creation/update timestamps and session metadata

The script integrates seamlessly with your existing Flask service by using the same state file format and directory structure.
