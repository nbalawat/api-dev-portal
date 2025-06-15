"""
Enhanced Permission Middleware

Advanced permission checking middleware that integrates with the
resource-based permission system for fine-grained access control.
"""
from typing import List, Optional, Callable
from fastapi import Request, HTTPException, status, Depends

from ..core.permissions import PermissionManager, ResourceType, Permission
from ..models.api_key import APIKey
from .api_key_auth import require_api_key


def require_resource_permission(
    resource: ResourceType, 
    permission: Permission,
    allow_user_auth: bool = False
):
    """
    FastAPI dependency factory for requiring specific resource permissions.
    
    Args:
        resource: Resource type being accessed
        permission: Required permission level
        allow_user_auth: Whether to allow regular user authentication as fallback
        
    Returns:
        FastAPI dependency function
    """
    def _check_permission(
        request: Request,
        api_key: APIKey = Depends(require_api_key)
    ) -> APIKey:
        """Check if API key has required permission."""
        if not PermissionManager.has_permission(
            api_key.scopes, resource, permission
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "insufficient_permissions",
                    "message": f"Requires {resource.value}:{permission.value} permission",
                    "required_permission": f"{resource.value}:{permission.value}",
                    "current_scopes": api_key.scopes,
                    "available_permissions": list(
                        PermissionManager.get_effective_permissions(tuple(api_key.scopes))
                    )
                }
            )
        
        return api_key
    
    return _check_permission


def require_any_resource_permission(
    resource: ResourceType,
    permissions: List[Permission],
    allow_user_auth: bool = False
):
    """
    FastAPI dependency factory for requiring any of multiple permissions.
    
    Args:
        resource: Resource type being accessed
        permissions: List of acceptable permissions
        allow_user_auth: Whether to allow regular user authentication as fallback
        
    Returns:
        FastAPI dependency function
    """
    def _check_any_permission(
        request: Request,
        api_key: APIKey = Depends(require_api_key)
    ) -> APIKey:
        """Check if API key has any of the required permissions."""
        if not PermissionManager.has_any_permission(
            api_key.scopes, resource, permissions
        ):
            perm_strs = [f"{resource.value}:{p.value}" for p in permissions]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "insufficient_permissions",
                    "message": f"Requires one of: {', '.join(perm_strs)}",
                    "required_permissions": perm_strs,
                    "current_scopes": api_key.scopes,
                    "available_permissions": list(
                        PermissionManager.get_effective_permissions(tuple(api_key.scopes))
                    )
                }
            )
        
        return api_key
    
    return _check_any_permission


def require_resource_access(resource: ResourceType):
    """
    FastAPI dependency for basic resource access (read permission).
    
    Args:
        resource: Resource type being accessed
        
    Returns:
        FastAPI dependency function
    """
    return require_resource_permission(resource, Permission.READ)


def require_resource_write(resource: ResourceType):
    """
    FastAPI dependency for resource write access.
    
    Args:
        resource: Resource type being accessed
        
    Returns:
        FastAPI dependency function
    """
    return require_any_resource_permission(
        resource, 
        [Permission.CREATE, Permission.UPDATE, Permission.MANAGE]
    )


def require_resource_management(resource: ResourceType):
    """
    FastAPI dependency for full resource management access.
    
    Args:
        resource: Resource type being accessed
        
    Returns:
        FastAPI dependency function
    """
    return require_resource_permission(resource, Permission.MANAGE)


class PermissionChecker:
    """Helper class for checking permissions programmatically."""
    
    def __init__(self, api_key: APIKey):
        self.api_key = api_key
        self.permissions = PermissionManager.get_effective_permissions(
            tuple(api_key.scopes)
        )
    
    def can(self, resource: ResourceType, permission: Permission) -> bool:
        """Check if API key can perform permission on resource."""
        return PermissionManager.has_permission(
            self.api_key.scopes, resource, permission
        )
    
    def can_any(self, resource: ResourceType, permissions: List[Permission]) -> bool:
        """Check if API key can perform any of the permissions on resource."""
        return PermissionManager.has_any_permission(
            self.api_key.scopes, resource, permissions
        )
    
    def get_resource_permissions(self, resource: ResourceType) -> List[str]:
        """Get all permissions for a specific resource."""
        perms = PermissionManager.get_resource_permissions(
            self.api_key.scopes, resource
        )
        return [perm.value for perm in perms]
    
    def get_all_permissions(self) -> List[str]:
        """Get all effective permissions."""
        return list(self.permissions)
    
    def can_access_user_data(self, target_user_id: str = None) -> bool:
        """Check if can access user data (with optional user-specific check)."""
        if self.can(ResourceType.USER, Permission.MANAGE):
            return True
        
        if target_user_id and str(self.api_key.user_id) == target_user_id:
            return self.can(ResourceType.USER, Permission.READ)
        
        return self.can(ResourceType.USER, Permission.LIST)
    
    def can_manage_api_keys(self, target_user_id: str = None) -> bool:
        """Check if can manage API keys (with optional user-specific check)."""
        if self.can(ResourceType.API_KEY, Permission.MANAGE):
            return True
        
        if target_user_id and str(self.api_key.user_id) == target_user_id:
            return self.can(ResourceType.API_KEY, Permission.UPDATE)
        
        return False
    
    def is_admin(self) -> bool:
        """Check if has admin permissions."""
        return self.can(ResourceType.ADMIN, Permission.MANAGE)
    
    def can_view_analytics(self) -> bool:
        """Check if can view analytics."""
        return self.can(ResourceType.ANALYTICS, Permission.READ)
    
    def can_export_data(self) -> bool:
        """Check if can export data."""
        return self.can_any(
            ResourceType.ANALYTICS, 
            [Permission.EXPORT, Permission.MANAGE]
        )


def get_permission_checker(api_key: APIKey = Depends(require_api_key)) -> PermissionChecker:
    """FastAPI dependency to get a PermissionChecker instance."""
    return PermissionChecker(api_key)


# Utility functions for common permission patterns
def check_user_access_permission(
    api_key: APIKey, 
    target_user_id: Optional[str] = None
) -> bool:
    """
    Check if API key can access user data.
    
    Args:
        api_key: API key object
        target_user_id: Optional specific user ID being accessed
        
    Returns:
        True if access is allowed
    """
    checker = PermissionChecker(api_key)
    return checker.can_access_user_data(target_user_id)


def check_api_key_access_permission(
    api_key: APIKey,
    target_user_id: Optional[str] = None
) -> bool:
    """
    Check if API key can manage API keys.
    
    Args:
        api_key: API key object  
        target_user_id: Optional specific user ID whose keys are being accessed
        
    Returns:
        True if access is allowed
    """
    checker = PermissionChecker(api_key)
    return checker.can_manage_api_keys(target_user_id)


def get_filtered_permissions_info(api_key: APIKey) -> dict:
    """
    Get comprehensive permission information for an API key.
    
    Args:
        api_key: API key object
        
    Returns:
        Dictionary with permission information
    """
    checker = PermissionChecker(api_key)
    
    return {
        "scopes": api_key.scopes,
        "effective_permissions": checker.get_all_permissions(),
        "resource_permissions": {
            "user": checker.get_resource_permissions(ResourceType.USER),
            "api_key": checker.get_resource_permissions(ResourceType.API_KEY),
            "analytics": checker.get_resource_permissions(ResourceType.ANALYTICS),
            "admin": checker.get_resource_permissions(ResourceType.ADMIN),
            "system": checker.get_resource_permissions(ResourceType.SYSTEM),
        },
        "capabilities": {
            "is_admin": checker.is_admin(),
            "can_view_analytics": checker.can_view_analytics(),
            "can_export_data": checker.can_export_data(),
            "can_manage_users": checker.can(ResourceType.USER, Permission.MANAGE),
            "can_manage_api_keys": checker.can(ResourceType.API_KEY, Permission.MANAGE),
        }
    }