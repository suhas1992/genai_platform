# Session Service

Manages conversation sessions and user state.

## Structure

The service is organized with clear separation of concerns:

- **`store.py`**: Data layer - handles session persistence (currently in-memory)
- **`service.py`**: Business logic layer - implements gRPC interface
- **`main.py`**: Entry point - server setup and lifecycle

## Responsibilities

- Create and retrieve sessions
- Store session metadata (user_id, timestamps)
- Session persistence (currently in-memory, will add database in Chapter 6)

## Running

```bash
# Port is automatically assigned (50052) or override with:
export SESSIONS_PORT=50060

# Run service
python services/sessions/main.py
```

The service uses the shared infrastructure from `services/shared/` for:
- Port management (ensures unique ports across services)
- Server creation and lifecycle
- Common service patterns




