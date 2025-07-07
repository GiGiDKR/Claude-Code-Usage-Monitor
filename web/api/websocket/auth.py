"""
WebSocket authentication module.

This module provides authentication utilities for WebSocket connections.
"""

import jwt
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, Query, Depends
from fastapi.security import HTTPBearer

logger = logging.getLogger("api.websocket.auth")

# Simple JWT configuration (in production, use environment variables)
JWT_SECRET_KEY = "your-secret-key-change-in-production"
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24

security = HTTPBearer()


class WebSocketAuth:
    """WebSocket authentication handler."""
    
    def __init__(self):
        """Initialize WebSocket authentication."""
        self.authenticated_clients: Dict[str, Dict[str, Any]] = {}
    
    def create_access_token(
        self, 
        client_id: str, 
        user_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create JWT access token for WebSocket authentication.
        
        Args:
            client_id: Client identifier
            user_data: Optional user data to include in token
            
        Returns:
            JWT access token
        """
        payload = {
            "client_id": client_id,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS),
            "type": "websocket_access"
        }
        
        if user_data:
            payload["user"] = user_data
        
        return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify JWT token and extract payload.
        
        Args:
            token: JWT token to verify
            
        Returns:
            Token payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            
            # Check token type
            if payload.get("type") != "websocket_access":
                return None
            
            # Check expiration
            exp = payload.get("exp")
            if exp and datetime.utcnow().timestamp() > exp:
                return None
            
            return payload
            
        except jwt.InvalidTokenError:
            return None
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return None
    
    def authenticate_client(
        self, 
        client_id: str, 
        token: Optional[str] = None
    ) -> bool:
        """
        Authenticate WebSocket client.
        
        Args:
            client_id: Client identifier
            token: Optional JWT token
            
        Returns:
            True if authentication successful
        """
        if not token:
            # Allow unauthenticated connections for now
            # In production, you might want to require authentication
            self.authenticated_clients[client_id] = {
                "authenticated": False,
                "auth_time": datetime.now(),
                "permissions": ["read"]  # Limited permissions
            }
            return True
        
        payload = self.verify_token(token)
        if payload:
            self.authenticated_clients[client_id] = {
                "authenticated": True,
                "auth_time": datetime.now(),
                "token_payload": payload,
                "permissions": ["read", "write", "admin"]  # Full permissions
            }
            logger.info(f"Client {client_id} authenticated successfully")
            return True
        else:
            logger.warning(f"Authentication failed for client {client_id}")
            return False
    
    def is_authenticated(self, client_id: str) -> bool:
        """
        Check if client is authenticated.
        
        Args:
            client_id: Client identifier
            
        Returns:
            True if client is authenticated
        """
        return self.authenticated_clients.get(client_id, {}).get("authenticated", False)
    
    def has_permission(self, client_id: str, permission: str) -> bool:
        """
        Check if client has specific permission.
        
        Args:
            client_id: Client identifier
            permission: Permission to check
            
        Returns:
            True if client has permission
        """
        client_auth = self.authenticated_clients.get(client_id, {})
        permissions = client_auth.get("permissions", [])
        return permission in permissions
    
    def get_client_info(self, client_id: str) -> Optional[Dict[str, Any]]:
        """
        Get authentication info for client.
        
        Args:
            client_id: Client identifier
            
        Returns:
            Client authentication info
        """
        return self.authenticated_clients.get(client_id)
    
    def revoke_client_auth(self, client_id: str) -> None:
        """
        Revoke authentication for client.
        
        Args:
            client_id: Client identifier
        """
        if client_id in self.authenticated_clients:
            del self.authenticated_clients[client_id]
            logger.info(f"Authentication revoked for client {client_id}")


# Global authentication instance
websocket_auth = WebSocketAuth()


def get_websocket_token(token: Optional[str] = Query(None)) -> Optional[str]:
    """
    Dependency to extract WebSocket token from query parameters.
    
    Args:
        token: JWT token from query parameter
        
    Returns:
        Token if provided
    """
    return token


def authenticate_websocket_client(
    client_id: str,
    token: Optional[str] = Depends(get_websocket_token)
) -> bool:
    """
    Dependency to authenticate WebSocket client.
    
    Args:
        client_id: Client identifier
        token: JWT token
        
    Returns:
        True if authentication successful
        
    Raises:
        HTTPException: If authentication fails
    """
    if websocket_auth.authenticate_client(client_id, token):
        return True
    else:
        raise HTTPException(
            status_code=401,
            detail="WebSocket authentication failed"
        )


def require_websocket_permission(permission: str):
    """
    Decorator to require specific permission for WebSocket operations.
    
    Args:
        permission: Required permission
        
    Returns:
        Decorator function
    """
    def decorator(func):
        async def wrapper(client_id: str, *args, **kwargs):
            if not websocket_auth.has_permission(client_id, permission):
                logger.warning(
                    f"Permission denied for client {client_id}: {permission}"
                )
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission denied: {permission}"
                )
            return await func(client_id, *args, **kwargs)
        return wrapper
    return decorator


def create_client_token(client_id: str, user_data: Optional[Dict] = None) -> str:
    """
    Create authentication token for WebSocket client.
    
    Args:
        client_id: Client identifier
        user_data: Optional user data
        
    Returns:
        JWT token
    """
    return websocket_auth.create_access_token(client_id, user_data)


def get_auth_stats() -> Dict[str, Any]:
    """
    Get authentication statistics.
    
    Returns:
        Authentication statistics
    """
    total_clients = len(websocket_auth.authenticated_clients)
    authenticated_clients = sum(
        1 for client in websocket_auth.authenticated_clients.values()
        if client.get("authenticated", False)
    )
    
    return {
        "total_clients": total_clients,
        "authenticated_clients": authenticated_clients,
        "unauthenticated_clients": total_clients - authenticated_clients,
        "auth_enabled": True,
        "token_algorithm": JWT_ALGORITHM,
        "token_expires_hours": JWT_EXPIRE_HOURS
    }
