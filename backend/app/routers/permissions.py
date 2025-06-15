"""
Permissions Management Router

API endpoints for managing and inspecting API key permissions,
scopes, and access control policies.
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel

from ..core.permissions import (
    PermissionManager, ResourceType, Permission, 
    ResourcePermission, ScopeDefinition
)
from ..middleware.permissions import (
    require_resource_permission, get_permission_checker, 
    PermissionChecker, get_filtered_permissions_info
)
from ..middleware import require_api_key
from ..models.api_key import APIKey, APIKeyScope


router = APIRouter(prefix="/permissions")


# Response models
class PermissionInfo(BaseModel):
    """Information about a specific permission."""
    resource: str
    permission: str
    description: str


class ScopeInfo(BaseModel):
    """Detailed information about a scope."""
    name: str
    description: str
    inherits: List[str]
    direct_permissions: List[str]
    effective_permissions: List[str]


class PermissionCheckRequest(BaseModel):
    """Request model for permission checking."""
    resource: ResourceType
    permission: Permission


class PermissionCheckResponse(BaseModel):
    """Response model for permission checking."""
    allowed: bool
    message: str
    required_permission: str
    current_scopes: List[str]


class ScopeValidationResponse(BaseModel):
    """Response model for scope validation."""
    valid_scopes: List[str]
    invalid_scopes: List[str]
    warnings: List[str]
    suggestions: List[str]


class APIKeyPermissionInfo(BaseModel):
    """Comprehensive permission information for an API key."""
    api_key_id: str
    scopes: List[str]
    effective_permissions: List[str]
    resource_permissions: Dict[str, List[str]]
    capabilities: Dict[str, bool]


# Public endpoints (require basic API key)
@router.get("/scopes", response_model=Dict[str, ScopeInfo])
async def list_available_scopes(
    api_key: APIKey = Depends(require_api_key)
):
    """
    Get information about all available scopes.
    
    Returns detailed information about each scope including
    permissions, inheritance, and descriptions.
    """
    scopes_info = {}
    
    for scope_name in PermissionManager.SCOPE_DEFINITIONS:
        scope_info = PermissionManager.get_scope_info(scope_name)
        if scope_info:
            scopes_info[scope_name] = ScopeInfo(**scope_info)
    
    return scopes_info


@router.get("/scope/{scope_name}", response_model=ScopeInfo)
async def get_scope_info(
    scope_name: str,
    api_key: APIKey = Depends(require_api_key)
):
    """
    Get detailed information about a specific scope.
    
    Args:
        scope_name: Name of the scope to inspect
    """
    scope_info = PermissionManager.get_scope_info(scope_name)
    
    if not scope_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scope '{scope_name}' not found"
        )
    
    return ScopeInfo(**scope_info)


@router.post("/validate-scopes", response_model=ScopeValidationResponse)
async def validate_scopes(
    scopes: List[str],
    api_key: APIKey = Depends(require_api_key)
):
    """
    Validate a list of scopes and get suggestions.
    
    Args:
        scopes: List of scope names to validate
    """
    validation_results = PermissionManager.validate_scopes(scopes)
    warnings = PermissionManager.check_scope_conflicts(scopes)
    
    valid_scopes = [scope for scope, valid in validation_results.items() if valid]
    invalid_scopes = [scope for scope, valid in validation_results.items() if not valid]
    
    # Get suggestions for invalid scopes
    suggestions = []
    if invalid_scopes:
        all_scopes = list(PermissionManager.SCOPE_DEFINITIONS.keys())
        suggestions = [scope for scope in all_scopes if scope not in scopes][:5]
    
    return ScopeValidationResponse(
        valid_scopes=valid_scopes,
        invalid_scopes=invalid_scopes,
        warnings=warnings,
        suggestions=suggestions
    )


@router.post("/check-permission", response_model=PermissionCheckResponse)
async def check_permission(
    permission_check: PermissionCheckRequest,
    api_key: APIKey = Depends(require_api_key)
):
    """
    Check if current API key has a specific permission.
    
    Args:
        permission_check: Resource and permission to check
    """
    has_permission = PermissionManager.has_permission(
        api_key.scopes,
        permission_check.resource,
        permission_check.permission
    )
    
    required_permission = f"{permission_check.resource.value}:{permission_check.permission.value}"
    
    return PermissionCheckResponse(
        allowed=has_permission,
        message="Permission granted" if has_permission else "Permission denied",
        required_permission=required_permission,
        current_scopes=api_key.scopes
    )


@router.get("/my-permissions", response_model=APIKeyPermissionInfo)
async def get_my_permissions(
    api_key: APIKey = Depends(require_api_key)
):
    """
    Get comprehensive permission information for the current API key.
    
    Returns all effective permissions, resource-specific permissions,
    and capability flags.
    """
    permission_info = get_filtered_permissions_info(api_key)
    
    return APIKeyPermissionInfo(
        api_key_id=api_key.key_id,
        scopes=permission_info["scopes"],
        effective_permissions=permission_info["effective_permissions"],
        resource_permissions=permission_info["resource_permissions"],
        capabilities=permission_info["capabilities"]
    )


@router.get("/suggest-scopes")
async def suggest_scopes_for_permissions(
    permissions: List[str] = Query(..., description="Required permissions"),
    api_key: APIKey = Depends(require_api_key)
):
    """
    Get scope suggestions for required permissions.
    
    Args:
        permissions: List of required permission strings (e.g., "user:read")
    """
    try:
        # Validate permission format
        for perm in permissions:
            ResourcePermission.from_string(perm)
        
        suggestions = PermissionManager.suggest_scopes_for_permissions(permissions)
        
        return {
            "required_permissions": permissions,
            "suggested_scopes": suggestions,
            "scope_details": {
                scope: PermissionManager.get_scope_info(scope)
                for scope in suggestions
            }
        }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid permission format: {str(e)}"
        )


# Admin endpoints (require admin permissions)
@router.get("/admin/all-permissions")
async def list_all_permissions(
    api_key: APIKey = Depends(
        require_resource_permission(ResourceType.ADMIN, Permission.READ)
    )
):
    """
    Get comprehensive list of all available permissions (admin only).
    
    Returns all resources, permissions, and their combinations.
    """
    resources = list(ResourceType)
    permissions = list(Permission)
    
    all_permissions = []
    for resource in resources:
        for permission in permissions:
            all_permissions.append({
                "resource": resource.value,
                "permission": permission.value,
                "full_permission": f"{resource.value}:{permission.value}"
            })
    
    return {
        "resources": [r.value for r in resources],
        "permissions": [p.value for p in permissions],
        "all_combinations": all_permissions,
        "total_combinations": len(all_permissions)
    }


@router.get("/admin/scope-usage")
async def get_scope_usage_statistics(
    api_key: APIKey = Depends(
        require_resource_permission(ResourceType.ADMIN, Permission.READ)
    )
):
    """
    Get statistics about scope usage across API keys (admin only).
    
    Returns usage analytics for different scopes.
    """
    # This would typically query the database for actual usage statistics
    # For now, return mock data structure
    return {
        "message": "Scope usage statistics",
        "note": "This endpoint would return actual usage statistics from the database",
        "available_scopes": list(PermissionManager.SCOPE_DEFINITIONS.keys()),
        "statistics": {
            "total_api_keys": 0,
            "scope_distribution": {},
            "most_common_combinations": [],
            "least_used_scopes": []
        }
    }


@router.post("/admin/create-custom-scope")
async def create_custom_scope(
    scope_data: dict,
    api_key: APIKey = Depends(
        require_resource_permission(ResourceType.ADMIN, Permission.MANAGE)
    )
):
    """
    Create a custom scope definition (admin only).
    
    This endpoint allows admins to define new scopes with
    custom permission combinations.
    """
    # This would implement custom scope creation
    # For now, return a placeholder response
    return {
        "message": "Custom scope creation",
        "note": "This endpoint would allow creating custom scopes",
        "received_data": scope_data,
        "status": "not_implemented"
    }


# Utility endpoints
@router.get("/resources")
async def list_resource_types(
    api_key: APIKey = Depends(require_api_key)
):
    """
    Get list of all available resource types.
    """
    return {
        "resources": [
            {
                "name": resource.value,
                "description": f"Resource type: {resource.value}"
            }
            for resource in ResourceType
        ]
    }


@router.get("/permission-types")
async def list_permission_types(
    api_key: APIKey = Depends(require_api_key)
):
    """
    Get list of all available permission types.
    """
    return {
        "permissions": [
            {
                "name": permission.value,
                "description": f"Permission: {permission.value}"
            }
            for permission in Permission
        ]
    }


@router.get("/permission-matrix")
async def get_permission_matrix(
    api_key: APIKey = Depends(require_api_key)
):
    """
    Get a matrix showing which scopes grant which permissions.
    
    Useful for understanding scope relationships and permissions.
    """
    matrix = {}
    
    for scope_name in PermissionManager.SCOPE_DEFINITIONS:
        effective_perms = PermissionManager.get_effective_permissions((scope_name,))
        matrix[scope_name] = list(effective_perms)
    
    return {
        "permission_matrix": matrix,
        "scope_count": len(matrix),
        "unique_permissions": list(set().union(*matrix.values()))
    }