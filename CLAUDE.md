# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Open WebUI is an extensible, self-hosted AI platform with a web interface for LLM runners like Ollama and OpenAI-compatible APIs. It's built with:
- **Frontend**: SvelteKit + TypeScript + Tailwind CSS
- **Backend**: Python FastAPI with SQLAlchemy
- **Database**: SQLite (default) or PostgreSQL
- **Containerization**: Docker with multiple deployment options

## Common Development Commands

### Frontend Development
```bash
# Install dependencies
npm install

# Run development server (default port 5173)
npm run dev

# Run on custom port 5050
npm run dev:5050

# Build frontend
npm run build

# Type checking
npm run check

# Linting
npm run lint:frontend  # ESLint for frontend
npm run lint:types    # TypeScript checking
npm run lint          # Run all lints

# Formatting
npm run format        # Prettier for frontend
npm run format:backend # Black for Python

# Internationalization
npm run i18n:parse    # Parse and extract i18n strings

# Tests
npm run test:frontend # Run Vitest tests
npm run cy:open      # Open Cypress E2E tests
```

### Backend Development
```bash
# Install with pip (requires Python 3.11)
pip install open-webui

# Run the server
open-webui serve

# Or run directly with uvicorn
python -m uvicorn open_webui.main:app --host 0.0.0.0 --port 8080

# Backend formatting
black . --exclude ".venv/|/venv/"

# Backend linting
pylint backend/
```

### Docker Commands
```bash
# Quick start (Ollama on same machine)
docker run -d -p 3000:8080 --add-host=host.docker.internal:host-gateway -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:main

# With external Ollama server
docker run -d -p 3000:8080 -e OLLAMA_BASE_URL=https://example.com -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:main

# With GPU support
docker run -d -p 3000:8080 --gpus all --add-host=host.docker.internal:host-gateway -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:cuda

# Docker Compose
docker-compose up -d
docker-compose down
```

### Testing Commands
```bash
# Frontend tests
npm run test:frontend

# E2E tests
npm run cy:open

# Backend tests
pytest backend/open_webui/test/
```

## Architecture & Code Organization

### Frontend Structure (`/src`)
- `/lib/apis/` - API client modules for backend communication
- `/lib/components/` - Reusable Svelte components
- `/lib/stores/` - Svelte stores for state management
- `/lib/i18n/` - Internationalization files and translations
- `/lib/utils/` - Utility functions and helpers
- `/routes/` - SvelteKit pages and routing
  - `/(app)/` - Main authenticated app routes
  - `/auth/` - Authentication pages
  - `/s/` - Shared content routes

### Backend Structure (`/backend/open_webui`)
- `/routers/` - FastAPI route handlers (audio, chats, models, etc.)
- `/models/` - SQLAlchemy database models
- `/retrieval/` - RAG (Retrieval-Augmented Generation) implementation
  - `/vector/` - Vector database implementations (Chroma, Pinecone, etc.)
  - `/web/` - Web search providers
  - `/loaders/` - Document loaders
- `/utils/` - Utility modules (auth, chat, embeddings, etc.)
- `/socket/` - WebSocket implementation for real-time features
- `/storage/` - File storage provider abstraction
- `/migrations/` - Database migrations (Alembic)
- `/internal/` - Internal modules and database setup

### Key Configuration Files
- `backend/open_webui/config.py` - Central configuration management
- `backend/open_webui/constants.py` - Application constants
- `.env.example` - Environment variable template

## Development Workflow

1. **Frontend Changes**: 
   - Work in `/src` directory
   - Use `npm run dev` for hot-reload development
   - Follow existing component patterns and Svelte conventions

2. **Backend Changes**:
   - Work in `/backend/open_webui` directory
   - API routes go in `/routers/`
   - Database models in `/models/`
   - Use FastAPI dependency injection patterns

3. **Adding New Features**:
   - Create API endpoint in appropriate router
   - Add database model if needed
   - Create/update frontend API client in `/lib/apis/`
   - Implement UI components following existing patterns

4. **Database Changes**:
   - Models are in `/backend/open_webui/models/`
   - Migrations use Alembic (see `/backend/open_webui/migrations/`)
   - Support both SQLite and PostgreSQL

## Important Considerations

- **Authentication**: Uses JWT tokens, managed through `/routers/auths.py`
- **WebSocket**: Real-time features use Socket.IO (see `/socket/main.py`)
- **File Storage**: Abstracted storage provider supports local and S3
- **RAG Integration**: Extensive document processing and vector search capabilities
- **Internationalization**: Add translations in `/src/lib/i18n/locales/`
- **Docker Volume**: Always mount `/app/backend/data` to persist data

## Environment Variables

Key environment variables (see `.env.example` for full list):
- `OLLAMA_BASE_URL` - Ollama server URL
- `OPENAI_API_KEY` - For OpenAI integration
- `DATABASE_URL` - PostgreSQL connection string (optional)
- `WEBUI_SECRET_KEY` - Session secret key
- `ENABLE_RAG_WEB_SEARCH` - Enable web search in RAG
- `DEFAULT_LOCALE` - Default UI language

## External Modifications & API Usage

### Authentication

Open WebUI uses JWT tokens for authentication. To interact with the API:

1. **Sign In**: `POST /api/v1/auths/signin`
   ```json
   {
     "email": "user@example.com",
     "password": "password"
   }
   ```
   Returns JWT token and user info.

2. **Include Token**: Add to all subsequent requests:
   ```
   Authorization: Bearer YOUR_JWT_TOKEN
   ```

### Chat API Endpoints

1. **Create New Chat**: `POST /api/v1/chats/new`
   ```json
   {
     "chat": {
       "name": "New Chat",
       "messages": [],
       "models": ["model-id"]
     }
   }
   ```

2. **Send Message (OpenAI-compatible)**: `POST /api/v1/openai/chat/completions`
   ```json
   {
     "model": "model-id",
     "messages": [
       {"role": "user", "content": "Hello!"}
     ],
     "stream": true
   }
   ```

3. **Update Chat**: `POST /api/v1/chats/{chat_id}`
4. **Search Chats**: `GET /api/v1/chats/search?text=query`
5. **Delete Chat**: `DELETE /api/v1/chats/{chat_id}`

### Pipelines System

Pipelines enable custom processing of requests/responses:

1. **Upload Pipeline**: `POST /api/v1/pipelines/upload`
   - Upload Python file with pipeline logic
   - Supports inlet/outlet filtering

2. **Pipeline Structure**:
   ```python
   class Pipeline:
       def __init__(self):
           self.type = "filter"  # or "pipe"
           self.priority = 0
           self.pipelines = ["*"]  # Models to apply to
       
       async def inlet(self, body, user):
           # Pre-process request
           return body
       
       async def outlet(self, body, user):
           # Post-process response
           return body
   ```

3. **Manage Pipelines**:
   - List: `GET /api/v1/pipelines/list`
   - Delete: `DELETE /api/v1/pipelines/delete`
   - Configure valves: `POST /api/v1/pipelines/{id}/valves/update`

### Tools System

Tools are Python modules that extend functionality:

1. **Create Tool**: `POST /api/v1/tools/create`
   ```json
   {
     "id": "my_tool",
     "name": "My Tool",
     "content": "# Python code here",
     "meta": {
       "description": "Tool description"
     }
   }
   ```

2. **Tool Structure**:
   ```python
   """
   title: My Tool
   description: Tool description
   """
   
   class Tools:
       def __init__(self):
           pass
       
       async def my_function(self, query: str) -> str:
           # Tool logic
           return result
   
   class Valves(BaseModel):
       # Configuration options
       api_key: str = ""
   ```

3. **Manage Tools**:
   - List: `GET /api/v1/tools/`
   - Update: `POST /api/v1/tools/id/{id}/update`
   - Delete: `DELETE /api/v1/tools/id/{id}/delete`
   - Configure valves: `POST /api/v1/tools/id/{id}/valves/update`

### Functions System

Functions are similar to tools but designed for specific operations:

1. **Create Function**: `POST /api/v1/functions/create`
   ```json
   {
     "id": "my_function",
     "name": "My Function",
     "content": "# Python code",
     "meta": {
       "description": "Function description"
     }
   }
   ```

2. **Function Types**:
   - **Filter**: Modifies requests/responses
   - **Action**: Performs operations
   - **Pipe**: Transforms data

3. **Manage Functions**:
   - List: `GET /api/v1/functions/`
   - Toggle active: `POST /api/v1/functions/id/{id}/toggle`
   - Toggle global: `POST /api/v1/functions/id/{id}/toggle/global`

### WebSocket Events

For real-time updates, connect to WebSocket:

```javascript
import io from 'socket.io-client';

const socket = io('http://localhost:8080', {
  auth: { token: 'YOUR_JWT_TOKEN' }
});

socket.on('chat:message', (data) => {
  // Handle message updates
});
```

### Example: External Chat Client

```python
import requests
import json

# Configuration
BASE_URL = "http://localhost:8080/api/v1"
EMAIL = "user@example.com"
PASSWORD = "password"

# Sign in
auth_response = requests.post(
    f"{BASE_URL}/auths/signin",
    json={"email": EMAIL, "password": PASSWORD}
)
token = auth_response.json()["token"]
headers = {"Authorization": f"Bearer {token}"}

# Create new chat
chat_response = requests.post(
    f"{BASE_URL}/chats/new",
    headers=headers,
    json={
        "chat": {
            "name": "API Test Chat",
            "messages": [],
            "models": ["llama3.2:latest"]
        }
    }
)
chat_id = chat_response.json()["id"]

# Send message via OpenAI-compatible endpoint
message_response = requests.post(
    f"{BASE_URL}/openai/chat/completions",
    headers=headers,
    json={
        "model": "llama3.2:latest",
        "messages": [
            {"role": "user", "content": "Hello from API!"}
        ],
        "metadata": {"chat_id": chat_id}
    }
)
```

### Best Practices for Extensions

1. **Pipelines**: Use for request/response filtering and modification
2. **Tools**: Use for callable functions that can be invoked by models
3. **Functions**: Use for system-wide functionality and filters
4. **Authentication**: Always include JWT token in API requests
5. **Error Handling**: Check response status and handle errors appropriately
6. **Streaming**: Use SSE for streaming responses when needed

## Critical Development Knowledge

### Database Migrations

Open WebUI uses Alembic for database migrations. When modifying database schemas:

1. **Creating New Tables**: Add model in `/backend/open_webui/models/`
2. **Generate Migration**: 
   ```bash
   cd backend
   alembic revision --autogenerate -m "Description of changes"
   ```
3. **Apply Migration**: 
   ```bash
   alembic upgrade head
   ```
4. **Important**: Both SQLite and PostgreSQL must be supported

### Permission System

Open WebUI has a sophisticated permission system:

1. **Access Control Levels**:
   - `None`: Public access (all users)
   - `{}`: Private access (owner only)
   - Custom: Specific group/user permissions

2. **Permission Structure**:
   ```json
   {
     "read": {
       "group_ids": ["group1", "group2"],
       "user_ids": ["user1", "user2"]
     },
     "write": {
       "group_ids": ["group1"],
       "user_ids": ["user1"]
     }
   }
   ```

3. **Checking Permissions**:
   ```python
   from open_webui.utils.access_control import has_access, has_permission
   
   # Check resource access
   has_access(user_id, "read", access_control_dict)
   
   # Check hierarchical permissions
   has_permission(user_id, "workspace.tools", permissions)
   ```

### WebSocket/Real-time Features

1. **Socket.IO Integration**: Uses Socket.IO for real-time updates
2. **Redis Support**: Can use Redis for distributed WebSocket management
3. **Event Types**:
   - `chat:message`: Message updates
   - `usage`: Model usage tracking
   - `document:sync`: Collaborative editing

4. **Connection Example**:
   ```python
   # Backend emitting event
   event_emitter = get_event_emitter({"user_id": user.id, "chat_id": chat_id})
   await event_emitter({"type": "chat:message", "data": {...}})
   ```

### Model Management

1. **Model Structure**:
   - `id`: API identifier
   - `base_model_id`: Actual model to proxy to
   - `params`: Model-specific parameters
   - `meta`: Display information
   - `access_control`: Permission settings

2. **Model Override**: Can override existing models by using same ID
3. **Pipeline Integration**: Models can be pipelines with custom logic

### RAG (Retrieval-Augmented Generation)

1. **Vector Databases**: Supports multiple backends (Chroma, Pinecone, Qdrant, etc.)
2. **Document Processing**:
   ```python
   # Files are chunked and embedded
   # Stored in collections by file_id
   # Supports hybrid search (vector + BM25)
   ```

3. **File Storage**: Abstracted storage (local, S3, GCS, Azure)
4. **Knowledge Base**: Can create collections from multiple documents

### File Handling Best Practices

1. **Storage Provider Pattern**:
   ```python
   from open_webui.storage.provider import Storage
   
   # Upload file
   contents, file_path = Storage.upload_file(file, filename, tags)
   
   # Get file
   file_path = Storage.get_file(file_path)
   ```

2. **File Processing**:
   - PDFs, DOCX, TXT supported
   - Images processed with OCR
   - Web pages can be scraped

### Frontend-Backend Communication

1. **API Client Pattern**: Frontend uses `/lib/apis/` modules
2. **State Management**: Svelte stores for global state
3. **Error Handling**: Consistent error response format
4. **Loading States**: Use skeleton loaders for better UX

### Security Considerations

1. **JWT Token Handling**: Tokens stored in cookies (httpOnly)
2. **CORS**: Configured in FastAPI middleware
3. **Input Validation**: Use Pydantic models
4. **SQL Injection**: Use SQLAlchemy ORM, avoid raw SQL
5. **File Upload**: Validate file types and sizes

### Testing Approach

1. **Backend Tests**: Use pytest with fixtures
2. **Frontend Tests**: Vitest for unit tests
3. **E2E Tests**: Cypress for integration testing
4. **Database Tests**: Use test database, rollback transactions

### Common Pitfalls to Avoid

1. **Direct Database Access**: Always use ORM models
2. **Synchronous Operations**: Use async/await for I/O operations
3. **Missing Permissions**: Always check user permissions
4. **Memory Leaks**: Clean up WebSocket connections
5. **Large File Handling**: Stream large files, don't load in memory
6. **Migration Conflicts**: Always pull latest before creating migrations

### Debugging Tips

1. **Enable Debug Logging**:
   ```python
   export GLOBAL_LOG_LEVEL=DEBUG
   ```

2. **Database Queries**: SQLAlchemy echo mode shows SQL
3. **WebSocket Events**: Use browser dev tools
4. **API Requests**: Check network tab for full request/response

### Performance Optimization

1. **Database Queries**: Use eager loading for relationships
2. **Caching**: Redis for session management and caching
3. **Batch Operations**: Process multiple items together
4. **Async Operations**: Use asyncio for concurrent tasks
5. **Vector Search**: Limit search scope with metadata filters

## Adding Custom Variables to System Prompts

Open WebUI supports custom variables in system prompts that are dynamically replaced at runtime. Here's how to add a new custom variable like `{{SOREN_MEMORIES}}`:

### 1. Create Your Data Source

First, create a module to retrieve your data. For example, for memories stored in an external database:

```python
# backend/open_webui/models/custom_data_source.py
import sqlite3
from typing import List

class CustomDataSource:
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def get_all_data(self) -> List[dict]:
        conn = sqlite3.connect(self.db_path)
        # Your query logic here
        conn.close()
        return data

# Create global instance
custom_source = CustomDataSource("/path/to/your/db.db")
```

### 2. Create a Formatter Utility

Create a utility to format your data for the prompt:

```python
# backend/open_webui/utils/custom_formatter.py
from open_webui.models.custom_data_source import custom_source

def format_custom_data() -> str:
    """Format data for inclusion in prompts"""
    data = custom_source.get_all_data()
    
    formatted = "=== CUSTOM DATA ===\n\n"
    # Format your data as needed
    for item in data:
        formatted += f"- {item['content']}\n"
    formatted += "\n=== END CUSTOM DATA ==="
    
    return formatted

# Optional: Add caching
_cached_data = None
_cache_timestamp = 0

def get_custom_data_cached(cache_duration: int = 300) -> str:
    global _cached_data, _cache_timestamp
    import time
    
    current_time = time.time()
    if _cached_data is None or (current_time - _cache_timestamp) > cache_duration:
        _cached_data = format_custom_data()
        _cache_timestamp = current_time
    
    return _cached_data
```

### 3. Register the Variable in prompt_template

Edit `backend/open_webui/utils/task.py` to add your variable:

```python
def prompt_template(
    template: str, user_name: Optional[str] = None, user_location: Optional[str] = None, user=None
) -> str:
    # ... existing code ...
    
    # Add support for {{YOUR_VARIABLE}}
    if "{{YOUR_VARIABLE}}" in template:
        try:
            from open_webui.utils.custom_formatter import get_custom_data_cached
            # Get user_id if available
            user_id = None
            if user and hasattr(user, 'id'):
                user_id = user.id
            
            custom_data = get_custom_data_cached()
            template = template.replace("{{YOUR_VARIABLE}}", custom_data)
            log.info(f"YOUR_VARIABLE replaced successfully")
        except Exception as e:
            log.warning(f"Error loading YOUR_VARIABLE: {e}")
            template = template.replace("{{YOUR_VARIABLE}}", "No data available.")
    
    return template
```

### 4. Update payload.py to Pass User Context

Ensure the user object is passed to prompt_template in `backend/open_webui/utils/payload.py`:

```python
def apply_model_system_prompt_to_body(
    system: Optional[str], form_data: dict, metadata: Optional[dict] = None, user=None
) -> dict:
    # ... existing code ...
    
    system = prompt_template(system, user=user, **template_params)
    
    # ... rest of the function
```

### 5. Optional: Create API Endpoints

If you need to manage the data via API:

```python
# backend/open_webui/routers/custom_data.py
from fastapi import APIRouter, Depends
from open_webui.utils.auth import get_verified_user

router = APIRouter()

@router.get("/custom-data")
async def get_custom_data(user=Depends(get_verified_user)):
    from open_webui.utils.custom_formatter import format_custom_data
    return {"data": format_custom_data()}
```

Don't forget to register the router in `main.py`:
1. Import: `from open_webui.routers import custom_data`
2. Register: `app.include_router(custom_data.router, prefix="/api/v1", tags=["custom_data"])`

### 6. Usage in System Prompts

Once implemented, you can use your variable in any model's system prompt:

```
You are a helpful assistant.

{{YOUR_VARIABLE}}

Use the above information to provide personalized responses.
```

### Important Notes:

1. **Always restart the backend** after making these changes
2. **Check logs** for debugging - the variable replacement logs success/failure
3. **Cache appropriately** to avoid performance issues
4. **Handle errors gracefully** - always provide fallback text
5. **Consider security** - ensure sensitive data is properly filtered

### Example Variables Already Available:

- `{{CURRENT_DATE}}` - Current date in YYYY-MM-DD format
- `{{CURRENT_TIME}}` - Current time
- `{{CURRENT_DATETIME}}` - Combined date and time
- `{{CURRENT_WEEKDAY}}` - Day of the week
- `{{USER_NAME}}` - User's name
- `{{USER_LOCATION}}` - User's location
- `{{SOREN_MEMORIES}}` - Custom memories from external DB (custom implementation)