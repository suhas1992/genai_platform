# API Gateway Service

The API Gateway is the single entry point for all platform traffic, serving two purposes:

1. **External HTTP traffic** → Routes HTTP requests from external clients to workflow containers based on API paths
2. **Internal gRPC traffic** → Routes gRPC calls from workflows to platform services (sessions, models, etc.) based on `x-target-service` metadata

## Architecture

The gateway is a single component that handles both types of traffic. Internally, it runs two servers:
- **HTTP server** (port 8080): Handles external client requests → workflow routing
- **gRPC server** (port 50051): Handles internal service-to-service communication

Both servers share a unified `ServiceRegistry` that tracks:
- Platform services (sessions, models, data, etc.) for gRPC routing
- Workflow services (user-defined workflows) for HTTP routing

## Responsibilities

- Routes HTTP requests to workflow containers based on API path
- Routes gRPC calls to platform services based on `x-target-service` metadata
- Service discovery and load balancing
- Health checking (to be implemented)
- Authentication and rate limiting (to be implemented)

## Running

```bash
# Set backend service addresses
export SESSIONS_SERVICE_ADDR=localhost:50052
export GATEWAY_PORT=50051          # gRPC server port
export GATEWAY_HTTP_PORT=8080      # HTTP server port (optional, defaults to 8080)

# Run gateway
python services/gateway/main.py
```

The gateway will start both servers and serve as the unified entry point for all platform traffic.


