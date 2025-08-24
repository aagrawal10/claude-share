# Production Setup Guide

This guide explains how to run the Claude Share application in production using Gunicorn and Docker.

## Quick Start

### Using Docker (Recommended)

1. **Build the Docker image:**
   ```bash
   docker build -t claude-share .
   ```

2. **Run the container:**
   ```bash
   docker run -d \
     --name claude-share \
     -p 5000:5000 \
     -v $(pwd)/claude_sessions:/app/claude_sessions \
     claude-share
   ```

3. **Using Docker Compose:**
   ```bash
   # For production
   docker-compose up -d

   # For development with hot reload
   docker-compose --profile dev up -d claude-share-dev
   ```

### Manual Setup (Advanced)

1. **Install dependencies:**
   ```bash
   pipenv install --deploy
   ```

2. **Run with Gunicorn:**
   ```bash
   pipenv run gunicorn --config gunicorn.conf.py app:app
   ```

## Configuration

### Environment Variables

The application supports the following environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `5000` | Port to bind the server |
| `WORKERS` | `2` | Number of Gunicorn worker processes |
| `LOG_LEVEL` | `info` | Logging level (debug, info, warning, error) |
| `STATE_FILE_PATH` | `./claude_sessions/state.json` | Path to state file |
| `SESSIONS_BASE_DIR` | `./claude_sessions` | Base directory for session storage |
| `LEASE_TTL_MINUTES` | `30` | Session lease TTL in minutes |
| `MAX_CONTENT_LENGTH` | `104857600` | Max upload size in bytes (100MB) |

### Example with custom configuration:
```bash
docker run -d \
  --name claude-share \
  -p 8080:8080 \
  -e PORT=8080 \
  -e WORKERS=4 \
  -e LOG_LEVEL=debug \
  -v $(pwd)/claude_sessions:/app/claude_sessions \
  claude-share
```

## Production Features

### Security
- Runs as non-root user inside container
- File upload size limits
- Comprehensive error handling
- Request timeout configuration

### Performance
- Multi-worker Gunicorn setup
- Optimized Docker image with multi-stage build
- Proper logging and monitoring
- Health check endpoint at `/health`

### Reliability
- Graceful shutdown handling
- Worker process recycling
- Automatic session cleanup
- Persistent session storage with Docker volumes

## Monitoring

### Health Checks
The application provides a health endpoint:
```bash
curl http://localhost:5000/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00",
  "version": "1.0.0"
}
```

### Logs
Application logs are written to stdout and can be viewed with:
```bash
# Docker
docker logs claude-share

# Docker Compose
docker-compose logs claude-share
```

## Scaling

### Horizontal Scaling
To run multiple instances behind a load balancer:

1. **Use shared storage for sessions:**
   ```bash
   # Mount shared volume across instances
   -v /shared/claude_sessions:/app/claude_sessions
   ```

2. **Configure load balancer** to distribute traffic across instances

### Vertical Scaling
Increase worker processes:
```bash
docker run -e WORKERS=8 claude-share
```

## Troubleshooting

### Common Issues

1. **Permission denied errors:**
   - Ensure the mounted volume has proper permissions
   - The container runs as user `appuser` (non-root)

2. **Out of memory:**
   - Reduce the number of workers
   - Increase container memory limits

3. **Session files not persisting:**
   - Verify volume mount is correct
   - Check directory permissions

### Debug Mode
For development/debugging, you can override the command:
```bash
docker run -it --rm \
  -p 5000:5000 \
  -v $(pwd):/app \
  claude-share \
  gunicorn --config gunicorn.conf.py --reload app:app
```

## Production Deployment

### With Nginx (Recommended)
Configure Nginx as a reverse proxy:
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Handle large file uploads
        client_max_body_size 100M;
        proxy_request_buffering off;
    }
}
```

### With Docker Compose + Nginx
See the provided `docker-compose.yml` for a complete setup example.
