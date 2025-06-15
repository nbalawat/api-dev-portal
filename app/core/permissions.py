"""
API Key Permissions and Scoping System

Advanced permission system for API keys with hierarchical scopes,
resource-based permissions, and fine-grained access control.
"""
from typing import List, Dict, Set, Optional, Union
from enum import Enum
from dataclasses import dataclass
from functools import lru_cache

from ..models.api_key import APIKeyScope


class ResourceType(str, Enum):
    """Resource types that can be protected by API keys."""
    USER = "user"
    API_KEY = "api_key"
    ANALYTICS = "analytics"
    ADMIN = "admin"
    SYSTEM = "system"
    BILLING = "billing"
    WEBHOOK = "webhook"
    INTEGRATION = "integration"


class Permission(str, Enum):
    """Granular permissions for resources."""
    # Basic CRUD operations
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    
    # Special permissions
    LIST = "list"
    SEARCH = "search"
    EXPORT = "export"
    IMPORT = "import"
    
    # Admin permissions
    MANAGE = "manage"
    CONFIGURE = "configure"
    MONITOR = "monitor"
    
    # System permissions
    EXECUTE = "execute"
    DEPLOY = "deploy"
    DEBUG = "debug"


@dataclass
class ResourcePermission:
    """Represents a permission on a specific resource type."""
    resource: ResourceType
    permission: Permission
    
    def __str__(self) -> str:
        return f"{self.resource.value}:{self.permission.value}"
    
    @classmethod
    def from_string(cls, permission_str: str) -> 'ResourcePermission':
        """Create ResourcePermission from string like 'user:read'."""
        parts = permission_str.split(":", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid permission format: {permission_str}")
        
        resource = ResourceType(parts[0])
        permission = Permission(parts[1])
        return cls(resource=resource, permission=permission)


class ScopeDefinition:
    """Defines what permissions a scope grants."""
    
    def __init__(self, name: str, permissions: List[ResourcePermission], 
                 description: str = "", inherits: List[str] = None):
        self.name = name
        self.permissions = permissions
        self.description = description
        self.inherits = inherits or []
    
    def __str__(self) -> str:
        return f"Scope({self.name}): {len(self.permissions)} permissions"


class PermissionManager:
    """Manages API key permissions and scope definitions."""
    
    # Define comprehensive scope hierarchy
    SCOPE_DEFINITIONS = {
        # Basic read-only access
        APIKeyScope.read: ScopeDefinition(
            name="read",
            description="Read-only access to basic resources",
            permissions=[
                ResourcePermission(ResourceType.USER, Permission.READ),
                ResourcePermission(ResourceType.API_KEY, Permission.READ),
            ]
        ),
        
        # Write access (includes read)
        APIKeyScope.write: ScopeDefinition(
            name="write",
            description="Read and write access to basic resources",
            inherits=["read"],
            permissions=[
                ResourcePermission(ResourceType.USER, Permission.UPDATE),
                ResourcePermission(ResourceType.API_KEY, Permission.CREATE),
                ResourcePermission(ResourceType.API_KEY, Permission.UPDATE),
            ]
        ),
        
        # Analytics access
        APIKeyScope.analytics: ScopeDefinition(
            name="analytics",
            description="Access to usage analytics and reporting",
            inherits=["read"],
            permissions=[
                ResourcePermission(ResourceType.ANALYTICS, Permission.READ),
                ResourcePermission(ResourceType.ANALYTICS, Permission.LIST),
                ResourcePermission(ResourceType.ANALYTICS, Permission.EXPORT),
                ResourcePermission(ResourceType.API_KEY, Permission.MONITOR),
            ]
        ),
        
        # User management
        APIKeyScope.user_management: ScopeDefinition(
            name="user_management",
            description="Full user management capabilities",
            inherits=["read", "write"],
            permissions=[
                ResourcePermission(ResourceType.USER, Permission.CREATE),
                ResourcePermission(ResourceType.USER, Permission.DELETE),
                ResourcePermission(ResourceType.USER, Permission.LIST),
                ResourcePermission(ResourceType.USER, Permission.SEARCH),
                ResourcePermission(ResourceType.USER, Permission.MANAGE),
            ]
        ),
        
        # API key management
        APIKeyScope.api_management: ScopeDefinition(
            name="api_management",
            description="Full API key management capabilities",
            inherits=["read", "write"],
            permissions=[
                ResourcePermission(ResourceType.API_KEY, Permission.DELETE),
                ResourcePermission(ResourceType.API_KEY, Permission.LIST),
                ResourcePermission(ResourceType.API_KEY, Permission.SEARCH),
                ResourcePermission(ResourceType.API_KEY, Permission.MANAGE),
                ResourcePermission(ResourceType.API_KEY, Permission.CONFIGURE),
            ]
        ),
        
        # Full admin access
        APIKeyScope.admin: ScopeDefinition(
            name="admin",
            description="Complete administrative access",
            inherits=["read", "write", "analytics", "user_management", "api_management"],
            permissions=[
                ResourcePermission(ResourceType.ADMIN, Permission.MANAGE),
                ResourcePermission(ResourceType.SYSTEM, Permission.CONFIGURE),
                ResourcePermission(ResourceType.SYSTEM, Permission.MONITOR),
                ResourcePermission(ResourceType.SYSTEM, Permission.DEBUG),
                ResourcePermission(ResourceType.BILLING, Permission.READ),
                ResourcePermission(ResourceType.BILLING, Permission.MANAGE),
                ResourcePermission(ResourceType.WEBHOOK, Permission.MANAGE),
                ResourcePermission(ResourceType.INTEGRATION, Permission.MANAGE),
            ]
        ),
    }
    
    @classmethod
    @lru_cache(maxsize=128)
    def get_effective_permissions(cls, scopes: tuple) -> Set[str]:
        """
        Get all effective permissions for a list of scopes.
        
        Args:
            scopes: Tuple of scope names (tuple for caching)
            
        Returns:
            Set of permission strings
        """
        effective_permissions = set()
        processed_scopes = set()
        
        def _collect_permissions(scope_name: str):
            """Recursively collect permissions including inherited ones."""
            if scope_name in processed_scopes:
                return
            
            processed_scopes.add(scope_name)
            
            # Get scope definition
            scope_def = cls.SCOPE_DEFINITIONS.get(scope_name)
            if not scope_def:
                return
            
            # Add direct permissions
            for permission in scope_def.permissions:
                effective_permissions.add(str(permission))
            
            # Process inherited scopes
            for inherited_scope in scope_def.inherits:
                _collect_permissions(inherited_scope)
        
        # Process all provided scopes
        for scope in scopes:
            _collect_permissions(scope)
        
        return effective_permissions
    
    @classmethod
    def has_permission(cls, scopes: List[str], resource: ResourceType, 
                      permission: Permission) -> bool:
        """
        Check if the given scopes grant a specific permission on a resource.
        
        Args:
            scopes: List of scope names
            resource: Resource type
            permission: Required permission
            
        Returns:
            True if permission is granted
        """
        required_permission = str(ResourcePermission(resource, permission))
        effective_permissions = cls.get_effective_permissions(tuple(scopes))
        return required_permission in effective_permissions
    
    @classmethod
    def has_any_permission(cls, scopes: List[str], resource: ResourceType, 
                          permissions: List[Permission]) -> bool:
        """
        Check if the given scopes grant any of the specified permissions.
        
        Args:
            scopes: List of scope names
            resource: Resource type
            permissions: List of acceptable permissions
            
        Returns:
            True if any permission is granted
        """
        effective_permissions = cls.get_effective_permissions(tuple(scopes))
        
        for permission in permissions:
            required_permission = str(ResourcePermission(resource, permission))
            if required_permission in effective_permissions:
                return True
        
        return False
    
    @classmethod
    def get_resource_permissions(cls, scopes: List[str], 
                               resource: ResourceType) -> Set[Permission]:
        """
        Get all permissions granted for a specific resource.
        
        Args:
            scopes: List of scope names
            resource: Resource type
            
        Returns:
            Set of permissions for the resource
        """
        effective_permissions = cls.get_effective_permissions(tuple(scopes))
        resource_permissions = set()
        
        for perm_str in effective_permissions:
            try:
                resource_perm = ResourcePermission.from_string(perm_str)
                if resource_perm.resource == resource:
                    resource_permissions.add(resource_perm.permission)
            except ValueError:
                continue
        
        return resource_permissions
    
    @classmethod
    def validate_scopes(cls, scopes: List[str]) -> Dict[str, bool]:
        """
        Validate if all provided scopes are recognized.
        
        Args:
            scopes: List of scope names to validate
            
        Returns:
            Dictionary mapping scope names to validation results
        """
        results = {}
        for scope in scopes:
            results[scope] = scope in cls.SCOPE_DEFINITIONS
        return results
    
    @classmethod
    def get_scope_info(cls, scope: str) -> Optional[Dict]:
        """
        Get detailed information about a scope.
        
        Args:
            scope: Scope name
            
        Returns:
            Dictionary with scope information or None
        """
        scope_def = cls.SCOPE_DEFINITIONS.get(scope)
        if not scope_def:
            return None
        
        return {
            "name": scope_def.name,
            "description": scope_def.description,
            "inherits": scope_def.inherits,
            "direct_permissions": [str(p) for p in scope_def.permissions],
            "effective_permissions": list(cls.get_effective_permissions((scope,)))
        }
    
    @classmethod
    def get_all_scopes_info(cls) -> Dict[str, Dict]:
        """Get information about all available scopes."""
        return {
            scope: cls.get_scope_info(scope) 
            for scope in cls.SCOPE_DEFINITIONS.keys()
        }
    
    @classmethod
    def suggest_scopes_for_permissions(cls, required_permissions: List[str]) -> List[str]:
        """
        Suggest minimal scopes needed for given permissions.
        
        Args:
            required_permissions: List of required permission strings
            
        Returns:
            List of suggested scope names
        """
        required_set = set(required_permissions)
        suggestions = []
        
        # Check each scope to see if it covers all required permissions
        for scope_name in cls.SCOPE_DEFINITIONS.keys():
            scope_permissions = cls.get_effective_permissions((scope_name,))
            if required_set.issubset(scope_permissions):
                suggestions.append(scope_name)
        
        # Sort by number of permissions (prefer minimal scopes)
        suggestions.sort(key=lambda s: len(cls.get_effective_permissions((s,))))
        
        return suggestions
    
    @classmethod
    def check_scope_conflicts(cls, scopes: List[str]) -> List[str]:
        """
        Check for potential conflicts in scope combinations.
        
        Args:
            scopes: List of scope names
            
        Returns:
            List of conflict warnings
        """
        warnings = []
        
        # Check for redundant scopes (where one inherits from another)
        for i, scope1 in enumerate(scopes):
            scope1_def = cls.SCOPE_DEFINITIONS.get(scope1)
            if not scope1_def:
                continue
                
            for j, scope2 in enumerate(scopes):
                if i != j and scope2 in scope1_def.inherits:
                    warnings.append(
                        f"Scope '{scope1}' already includes '{scope2}' - "
                        f"'{scope2}' is redundant"
                    )
        
        return warnings


# Permission checking decorators and utilities
def require_resource_permission(resource: ResourceType, permission: Permission):
    """
    Decorator factory for requiring specific resource permissions.
    
    Args:
        resource: Resource type
        permission: Required permission
    """
    from functools import wraps
    from fastapi import HTTPException, status
    from ..middleware import require_api_key
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get API key from dependency injection
            api_key = None
            for arg in args:
                if hasattr(arg, 'scopes'):  # Assuming APIKey object has scopes
                    api_key = arg
                    break
            
            if not api_key:
                # Try to get from kwargs
                for value in kwargs.values():
                    if hasattr(value, 'scopes'):
                        api_key = value
                        break
            
            if not api_key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="API key required"
                )
            
            # Check permission
            if not PermissionManager.has_permission(
                api_key.scopes, resource, permission
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions: requires {resource.value}:{permission.value}"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_any_resource_permission(resource: ResourceType, permissions: List[Permission]):
    """
    Decorator factory for requiring any of multiple resource permissions.
    
    Args:
        resource: Resource type
        permissions: List of acceptable permissions
    """
    from functools import wraps
    from fastapi import HTTPException, status
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Similar implementation to require_resource_permission
            # but uses has_any_permission instead
            api_key = None
            for arg in args:
                if hasattr(arg, 'scopes'):
                    api_key = arg
                    break
            
            if not api_key:
                for value in kwargs.values():
                    if hasattr(value, 'scopes'):
                        api_key = value
                        break
            
            if not api_key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="API key required"
                )
            
            if not PermissionManager.has_any_permission(
                api_key.scopes, resource, permissions
            ):
                perm_strs = [f"{resource.value}:{p.value}" for p in permissions]
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions: requires one of {', '.join(perm_strs)}"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator