"""
Server Creation - Factory functions for creating HTTP and gRPC servers.
"""

from http.server import HTTPServer
from concurrent import futures
import grpc

from proto import sessions_pb2_grpc
from services.gateway.registry import ServiceRegistry
from services.gateway.grpc_proxy import GenericProxy, SessionServiceProxy
from services.gateway.http_handler import WorkflowHTTPHandler


def create_http_server(registry: ServiceRegistry, port: int = 8080):
    """Create HTTP server for external client requests."""
    def handler(*args, **kwargs):
        return WorkflowHTTPHandler(registry, *args, **kwargs)
    
    server = HTTPServer(('', port), handler)
    return server


def create_grpc_server(registry: ServiceRegistry, port: int = 50051):
    """Create and configure the gateway gRPC server for internal service communication."""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    
    # Create generic proxy
    proxy = GenericProxy(registry)
    
    # Register proxy handlers for each platform service interface
    # Each handler is minimal - just reads metadata and forwards
    sessions_pb2_grpc.add_SessionServiceServicer_to_server(
        SessionServiceProxy(proxy),
        server
    )
    
    listen_addr = f'[::]:{port}'
    server.add_insecure_port(listen_addr)
    
    return server

