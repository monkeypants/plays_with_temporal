# Julee Example - Docker Setup Guide

This guide explains how to set up and run the Julee Example application using Docker Compose.

## Prerequisites

- Docker and Docker Compose installed
- API keys for external services

## Quick Start

**Note**: All commands should be run from the top-level `plays_with_temporal` directory.

1. **Set up environment variables**:
   ```bash
   cp julee_example/.env.example .env
   ```
   Edit `.env` and add your API keys:
   ```bash
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

2. **Run the application**:
   ```bash
   docker-compose --profile julee up --build -d
   ```

3. **Access the services**:
   - **Web UI**: http://localhost:3000
   - **API**: http://localhost:8000
   - **API Docs**: http://localhost:8000/docs
   - **Temporal UI**: http://localhost:8001 (linked in the UI)
   - **MinIO Console**: http://localhost:9001

### Building and Running

```bash
# Start in background
docker-compose --profile julee up -d --build

# View logs
docker-compose --profile julee logs -f

# Stop all services
docker-compose --profile julee down
```

## Demo Features

The application includes pre-loaded demo data:

- **Knowledge Services**: Anthropic Claude configurations
- **Queries**: Meeting extraction queries (info, agenda, actions)
- **Assembly Specs**: Meeting minutes specification
- **Documents**: Sample meeting transcripts

### Using the Demo

1. Navigate to **Specifications** in the UI
2. Click **"Run Assembly"** on the Meeting Minutes specification
3. Select a document from the dropdown
4. Click **"Start Assembly"** to trigger the workflow
5. Monitor progress in the Temporal UI (Click on the Workflows option)

## Current Limitations

### Cannot view assembled document output in UI

The current interface doesn't provide a way to view the final assembled document that results from running the workflow. To view the assembled content, you need to use the API directly with the document ID that's returned when the workflow completes successfully.

**API commands to view assembled document:**

```bash
# curl command
curl -X GET "http://localhost:8000/documents/doc-68f2047f-6796-4830-91ad-104da83f6f24/content"

# HTTPie command
http GET http://localhost:8000/documents/doc-68f2047f-6796-4830-91ad-104da83f6f24/content

# With JSON formatting
curl -X GET "http://localhost:8000/documents/doc-68f2047f-6796-4830-91ad-104da83f6f24/content" \
  -H "Accept: application/json" | jq .
```

Replace the document ID with the one returned from your workflow execution.

## Troubleshooting

### Common Issues

**Services fail to start:**
- Check Docker daemon is running
- Verify port availability (3000, 8000, 8001, 9000, 9001)
- Ensure API keys are set correctly

**API key errors:**
- Verify keys are valid and active
- Check .env file is in the correct location
- Restart services after updating environment variables

**Build failures:**
- Clear Docker cache: `docker system prune -f`
- Rebuild without cache: `docker-compose build --no-cache`

### Database and Storage

**Reset data:**
```bash
# Stop services and remove volumes
docker-compose --profile julee down -v

# Restart with fresh data
docker-compose --profile julee up --build
```

**Access MinIO Console:**
- URL: http://localhost:9001
- Username: `minioadmin`
- Password: `minioadmin`

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React UI      │────│   FastAPI       │────│   Temporal      │
│   (vite:3000)   │    │   (uvicorn:8000)│    │   Worker        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                │                        │
                       ┌─────────────────┐    ┌─────────────────┐
                       │     MinIO       │    │   PostgreSQL    │
                       │   (storage)     │    │   (temporal)    │
                       └─────────────────┘    └─────────────────┘
```
