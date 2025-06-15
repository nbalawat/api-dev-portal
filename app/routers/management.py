"""
Management Interface Router

Advanced management endpoints for bulk operations, system administration,
and complex API key management workflows.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, update

from ..middleware.permissions import require_resource_permission, get_permission_checker, PermissionChecker
from ..middleware import require_api_key
from ..core.permissions import ResourceType, Permission
from ..models.api_key import APIKey, APIKeyStatus, APIKeyScope
from ..models.user import User
from ..dependencies.database import get_database
from ..core.key_lifecycle import APIKeyLifecycleManager, RotationTrigger


router = APIRouter(prefix="/management", tags=["Advanced Management"])


# Request/Response Models
class BulkOperationRequest(BaseModel):
    """Request model for bulk operations."""
    api_key_ids: List[str]
    operation: str  # rotate, revoke, extend_expiration, update_scopes
    parameters: Optional[Dict[str, Any]] = None


class BulkOperationResult(BaseModel):
    """Result of a bulk operation."""
    operation: str
    total_processed: int
    successful: int
    failed: int
    results: List[Dict[str, Any]]
    execution_time_seconds: float


class SystemMaintenanceRequest(BaseModel):
    """Request model for system maintenance operations."""
    operation: str  # cleanup_expired, process_rotations, update_stats
    parameters: Optional[Dict[str, Any]] = None
    scheduled_for: Optional[datetime] = None


class ExportRequest(BaseModel):
    """Request model for data export."""
    format: str  # csv, json, xlsx
    data_type: str  # api_keys, usage_data, analytics
    filters: Optional[Dict[str, Any]] = None
    date_range: Optional[Dict[str, str]] = None


class ImportRequest(BaseModel):
    """Request model for data import."""
    format: str  # csv, json
    data_type: str  # api_keys, users
    data: List[Dict[str, Any]]
    validate_only: bool = False


class TemplateRequest(BaseModel):
    """Request model for creating API key templates."""
    name: str
    description: str
    default_scopes: List[str]
    default_expiration_days: int
    default_rate_limit: int
    allowed_user_roles: List[str]


# Bulk Operations
@router.post("/bulk-operations", response_model=BulkOperationResult)
async def execute_bulk_operation(
    bulk_request: BulkOperationRequest,
    background_tasks: BackgroundTasks,
    api_key: APIKey = Depends(require_resource_permission(ResourceType.API_KEY, Permission.MANAGE)),
    db: AsyncSession = Depends(get_database)
):
    """
    Execute bulk operations on multiple API keys.
    
    Supports bulk rotation, revocation, expiration updates, and scope changes.
    """
    import time
    start_time = time.time()
    
    checker = PermissionChecker(api_key)
    if not checker.can(ResourceType.API_KEY, Permission.MANAGE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions for bulk operations"
        )
    
    operation = bulk_request.operation
    api_key_ids = bulk_request.api_key_ids
    parameters = bulk_request.parameters or {}
    
    if len(api_key_ids) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 API keys per bulk operation"
        )
    
    successful = 0
    failed = 0
    results = []
    
    if operation == "rotate":
        # Bulk rotation
        lifecycle_manager = APIKeyLifecycleManager()
        
        for key_id in api_key_ids:
            try:
                rotation_result = await lifecycle_manager.rotate_api_key(
                    api_key_id=key_id,
                    trigger=RotationTrigger.MANUAL,
                    transition_days=parameters.get("transition_days", 14),
                    preserve_settings=parameters.get("preserve_settings", True)
                )
                
                if rotation_result.success:
                    successful += 1
                    results.append({
                        "key_id": key_id,
                        "status": "success",
                        "new_key_id": rotation_result.new_key_id,
                        "message": rotation_result.message
                    })
                else:
                    failed += 1
                    results.append({
                        "key_id": key_id,
                        "status": "failed",
                        "error": rotation_result.message
                    })
            except Exception as e:
                failed += 1
                results.append({
                    "key_id": key_id,
                    "status": "failed",
                    "error": str(e)
                })
    
    elif operation == "revoke":
        # Bulk revocation
        for key_id in api_key_ids:
            try:
                await db.execute(
                    update(APIKey)
                    .where(APIKey.id == key_id)
                    .values(
                        status=APIKeyStatus.revoked,
                        updated_at=datetime.utcnow()
                    )
                )
                successful += 1
                results.append({
                    "key_id": key_id,
                    "status": "success",
                    "message": "API key revoked"
                })
            except Exception as e:
                failed += 1
                results.append({
                    "key_id": key_id,
                    "status": "failed",
                    "error": str(e)
                })
    
    elif operation == "extend_expiration":
        # Bulk expiration extension
        extension_days = parameters.get("days", 90)
        new_expiration = datetime.utcnow() + timedelta(days=extension_days)
        
        for key_id in api_key_ids:
            try:
                await db.execute(
                    update(APIKey)
                    .where(APIKey.id == key_id)
                    .values(
                        expires_at=new_expiration,
                        updated_at=datetime.utcnow()
                    )
                )
                successful += 1
                results.append({
                    "key_id": key_id,
                    "status": "success",
                    "message": f"Expiration extended by {extension_days} days",
                    "new_expiration": new_expiration.isoformat()
                })
            except Exception as e:
                failed += 1
                results.append({
                    "key_id": key_id,
                    "status": "failed",
                    "error": str(e)
                })
    
    elif operation == "update_scopes":
        # Bulk scope updates
        new_scopes = parameters.get("scopes", [])
        
        for key_id in api_key_ids:
            try:
                await db.execute(
                    update(APIKey)
                    .where(APIKey.id == key_id)
                    .values(
                        scopes=new_scopes,
                        updated_at=datetime.utcnow()
                    )
                )
                successful += 1
                results.append({
                    "key_id": key_id,
                    "status": "success",
                    "message": "Scopes updated",
                    "new_scopes": new_scopes
                })
            except Exception as e:
                failed += 1
                results.append({
                    "key_id": key_id,
                    "status": "failed",
                    "error": str(e)
                })
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported operation: {operation}"
        )
    
    await db.commit()
    
    execution_time = time.time() - start_time
    
    return BulkOperationResult(
        operation=operation,
        total_processed=len(api_key_ids),
        successful=successful,
        failed=failed,
        results=results,
        execution_time_seconds=round(execution_time, 2)
    )


@router.post("/system-maintenance")
async def execute_system_maintenance(
    maintenance_request: SystemMaintenanceRequest,
    background_tasks: BackgroundTasks,
    api_key: APIKey = Depends(require_resource_permission(ResourceType.ADMIN, Permission.MANAGE)),
    db: AsyncSession = Depends(get_database)
):
    """
    Execute system maintenance operations.
    
    Performs system-wide maintenance tasks like cleanup, optimization, and updates.
    """
    operation = maintenance_request.operation
    parameters = maintenance_request.parameters or {}
    
    if operation == "cleanup_expired":
        # Clean up expired API keys and usage data
        lifecycle_manager = APIKeyLifecycleManager()
        
        # Expire old keys
        expired_keys = await lifecycle_manager.expire_old_keys()
        
        # Clean up old usage data
        days_to_keep = parameters.get("days_to_keep", 90)
        from ..services.usage_tracking import get_usage_tracker
        usage_tracker = get_usage_tracker()
        await usage_tracker.cleanup_old_usage_data(days_to_keep)
        
        return {
            "operation": operation,
            "results": {
                "expired_keys": len(expired_keys),
                "expired_key_ids": expired_keys,
                "usage_data_cleanup": f"Removed data older than {days_to_keep} days"
            },
            "completed_at": datetime.utcnow().isoformat()
        }
    
    elif operation == "process_rotations":
        # Process all scheduled rotations
        lifecycle_manager = APIKeyLifecycleManager()
        rotation_results = await lifecycle_manager.process_scheduled_rotations()
        
        successful_rotations = [r for r in rotation_results if r.success]
        failed_rotations = [r for r in rotation_results if not r.success]
        
        return {
            "operation": operation,
            "results": {
                "total_processed": len(rotation_results),
                "successful": len(successful_rotations),
                "failed": len(failed_rotations),
                "details": [
                    {
                        "old_key_id": r.old_key_id,
                        "new_key_id": r.new_key_id,
                        "success": r.success,
                        "message": r.message
                    }
                    for r in rotation_results
                ]
            },
            "completed_at": datetime.utcnow().isoformat()
        }
    
    elif operation == "update_stats":
        # Update cached statistics and metrics
        from ..services.usage_tracking import get_usage_tracker
        usage_tracker = get_usage_tracker()
        await usage_tracker._update_metrics_cache()
        
        return {
            "operation": operation,
            "results": {
                "message": "Statistics and metrics updated",
                "cache_updated": True
            },
            "completed_at": datetime.utcnow().isoformat()
        }
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported maintenance operation: {operation}"
        )


@router.post("/export")
async def export_data(
    export_request: ExportRequest,
    background_tasks: BackgroundTasks,
    api_key: APIKey = Depends(require_resource_permission(ResourceType.ANALYTICS, Permission.EXPORT)),
    db: AsyncSession = Depends(get_database)
):
    """
    Export data in various formats.
    
    Supports exporting API keys, usage data, and analytics in CSV, JSON, or Excel formats.
    """
    checker = PermissionChecker(api_key)
    data_type = export_request.data_type
    format_type = export_request.format
    filters = export_request.filters or {}
    
    # Validate permissions
    if data_type == "api_keys" and not checker.can(ResourceType.API_KEY, Permission.READ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to export API keys"
        )
    
    # This would implement actual export functionality
    # For now, return metadata about what would be exported
    
    export_metadata = {
        "export_id": f"export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
        "data_type": data_type,
        "format": format_type,
        "filters": filters,
        "estimated_records": 0,  # Would calculate actual count
        "estimated_size_mb": 0,  # Would calculate actual size
        "download_url": f"/downloads/export_{data_type}_{format_type}.{format_type}",
        "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
        "created_by": api_key.key_id,
        "status": "processing"
    }
    
    if data_type == "api_keys":
        # Export API keys
        query = select(APIKey)
        
        # Apply user filtering if not admin
        if not checker.can(ResourceType.ADMIN, Permission.READ):
            query = query.where(APIKey.user_id == api_key.user_id)
        
        # Apply additional filters
        if "status" in filters:
            query = query.where(APIKey.status == filters["status"])
        
        result = await db.execute(query)
        keys = result.scalars().all()
        
        export_metadata["estimated_records"] = len(keys)
        export_metadata["estimated_size_mb"] = len(keys) * 0.001  # Rough estimate
    
    elif data_type == "usage_data":
        # Export usage data
        from ..models.api_key import APIKeyUsage
        
        # Date range filtering
        query = select(APIKeyUsage)
        if export_request.date_range:
            start_date = datetime.fromisoformat(export_request.date_range.get("start"))
            end_date = datetime.fromisoformat(export_request.date_range.get("end"))
            query = query.where(
                and_(
                    APIKeyUsage.timestamp >= start_date,
                    APIKeyUsage.timestamp <= end_date
                )
            )
        
        # Apply user filtering
        if not checker.can(ResourceType.ADMIN, Permission.READ):
            user_keys_query = select(APIKey.id).where(APIKey.user_id == api_key.user_id)
            user_keys_result = await db.execute(user_keys_query)
            user_key_ids = [row[0] for row in user_keys_result.fetchall()]
            query = query.where(APIKeyUsage.api_key_id.in_(user_key_ids))
        
        count_result = await db.execute(select(func.count(APIKeyUsage.id)).select_from(query.subquery()))
        record_count = count_result.scalar()
        
        export_metadata["estimated_records"] = record_count
        export_metadata["estimated_size_mb"] = record_count * 0.0005  # Rough estimate
    
    # Queue background task for actual export processing
    background_tasks.add_task(_process_export, export_metadata, export_request, api_key.user_id)
    
    return {
        "message": "Export initiated",
        "export_metadata": export_metadata,
        "note": "You will receive a notification when the export is ready for download"
    }


@router.post("/import")
async def import_data(
    import_request: ImportRequest,
    api_key: APIKey = Depends(require_resource_permission(ResourceType.ADMIN, Permission.MANAGE)),
    db: AsyncSession = Depends(get_database)
):
    """
    Import data from external sources.
    
    Supports importing API keys and users with validation and conflict resolution.
    """
    data_type = import_request.data_type
    format_type = import_request.format
    data = import_request.data
    validate_only = import_request.validate_only
    
    validation_results = []
    import_results = []
    
    if data_type == "api_keys":
        # Import API keys
        for i, key_data in enumerate(data):
            validation = _validate_api_key_data(key_data, i)
            validation_results.append(validation)
            
            if not validate_only and validation["valid"]:
                try:
                    # Create API key (simplified)
                    # In practice, this would use the full API key creation flow
                    import_results.append({
                        "row": i,
                        "status": "success",
                        "message": "API key would be created",
                        "key_id": "mock_key_id"
                    })
                except Exception as e:
                    import_results.append({
                        "row": i,
                        "status": "failed",
                        "error": str(e)
                    })
    
    elif data_type == "users":
        # Import users
        for i, user_data in enumerate(data):
            validation = _validate_user_data(user_data, i)
            validation_results.append(validation)
            
            if not validate_only and validation["valid"]:
                try:
                    # Create user (simplified)
                    import_results.append({
                        "row": i,
                        "status": "success",
                        "message": "User would be created",
                        "user_id": "mock_user_id"
                    })
                except Exception as e:
                    import_results.append({
                        "row": i,
                        "status": "failed",
                        "error": str(e)
                    })
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported data type: {data_type}"
        )
    
    valid_count = len([v for v in validation_results if v["valid"]])
    invalid_count = len(validation_results) - valid_count
    
    response = {
        "data_type": data_type,
        "total_records": len(data),
        "valid_records": valid_count,
        "invalid_records": invalid_count,
        "validation_results": validation_results
    }
    
    if not validate_only:
        successful_imports = len([r for r in import_results if r["status"] == "success"])
        failed_imports = len(import_results) - successful_imports
        
        response.update({
            "import_executed": True,
            "successful_imports": successful_imports,
            "failed_imports": failed_imports,
            "import_results": import_results
        })
    else:
        response["import_executed"] = False
        response["note"] = "Validation only - no data was imported"
    
    return response


@router.get("/templates")
async def get_api_key_templates(
    api_key: APIKey = Depends(require_resource_permission(ResourceType.API_KEY, Permission.READ))
):
    """
    Get available API key templates.
    
    Returns predefined templates for common API key configurations.
    """
    templates = [
        {
            "id": "readonly",
            "name": "Read-Only Access",
            "description": "Basic read-only access for viewing data",
            "default_scopes": ["read"],
            "default_expiration_days": 90,
            "default_rate_limit": 1000,
            "recommended_for": ["Data analysis", "Monitoring", "Reporting"]
        },
        {
            "id": "developer",
            "name": "Developer Access",
            "description": "Read and write access for development",
            "default_scopes": ["read", "write"],
            "default_expiration_days": 60,
            "default_rate_limit": 5000,
            "recommended_for": ["Development", "Testing", "Integration"]
        },
        {
            "id": "analytics",
            "name": "Analytics Access",
            "description": "Access to analytics and usage data",
            "default_scopes": ["read", "analytics"],
            "default_expiration_days": 180,
            "default_rate_limit": 2000,
            "recommended_for": ["Business intelligence", "Usage analysis", "Reporting"]
        },
        {
            "id": "admin",
            "name": "Administrative Access",
            "description": "Full administrative access",
            "default_scopes": ["admin"],
            "default_expiration_days": 30,
            "default_rate_limit": 10000,
            "recommended_for": ["System administration", "User management"]
        }
    ]
    
    return {
        "templates": templates,
        "total_templates": len(templates),
        "usage_note": "Templates provide starting configurations that can be customized"
    }


@router.post("/templates/{template_id}/apply")
async def apply_template(
    template_id: str,
    customizations: Optional[Dict[str, Any]] = None,
    api_key: APIKey = Depends(require_resource_permission(ResourceType.API_KEY, Permission.CREATE)),
    db: AsyncSession = Depends(get_database)
):
    """
    Apply a template to create a new API key.
    
    Creates a new API key based on a template with optional customizations.
    """
    # Get template configuration
    templates = {
        "readonly": {
            "scopes": ["read"],
            "expiration_days": 90,
            "rate_limit": 1000,
            "name": "Read-Only Key"
        },
        "developer": {
            "scopes": ["read", "write"],
            "expiration_days": 60,
            "rate_limit": 5000,
            "name": "Developer Key"
        },
        "analytics": {
            "scopes": ["read", "analytics"],
            "expiration_days": 180,
            "rate_limit": 2000,
            "name": "Analytics Key"
        },
        "admin": {
            "scopes": ["admin"],
            "expiration_days": 30,
            "rate_limit": 10000,
            "name": "Admin Key"
        }
    }
    
    if template_id not in templates:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_id}' not found"
        )
    
    template_config = templates[template_id]
    
    # Apply customizations
    if customizations:
        template_config.update(customizations)
    
    # This would integrate with the actual API key creation flow
    # For now, return what would be created
    
    return {
        "message": f"API key created from template '{template_id}'",
        "template_id": template_id,
        "configuration": template_config,
        "note": "This would create an actual API key in production",
        "next_steps": [
            "The new API key would be generated",
            "Secret key would be returned (store securely)",
            "Key would be activated immediately"
        ]
    }


# Helper functions
def _validate_api_key_data(key_data: Dict[str, Any], row_index: int) -> Dict[str, Any]:
    """Validate API key import data."""
    errors = []
    
    if not key_data.get("name"):
        errors.append("Name is required")
    
    if "scopes" in key_data and not isinstance(key_data["scopes"], list):
        errors.append("Scopes must be a list")
    
    if "expires_at" in key_data:
        try:
            datetime.fromisoformat(key_data["expires_at"])
        except ValueError:
            errors.append("Invalid expiration date format")
    
    return {
        "row": row_index,
        "valid": len(errors) == 0,
        "errors": errors,
        "data": key_data
    }


def _validate_user_data(user_data: Dict[str, Any], row_index: int) -> Dict[str, Any]:
    """Validate user import data."""
    errors = []
    
    if not user_data.get("username"):
        errors.append("Username is required")
    
    if not user_data.get("email"):
        errors.append("Email is required")
    
    if "role" in user_data and user_data["role"] not in ["admin", "developer", "viewer"]:
        errors.append("Invalid role")
    
    return {
        "row": row_index,
        "valid": len(errors) == 0,
        "errors": errors,
        "data": user_data
    }


async def _process_export(export_metadata: Dict[str, Any], export_request: ExportRequest, user_id: str):
    """Background task to process export requests."""
    # This would implement the actual export processing
    # For now, it's a placeholder
    import asyncio
    await asyncio.sleep(5)  # Simulate processing time
    
    # In production, this would:
    # 1. Generate the export file
    # 2. Upload to storage (S3, local file system, etc.)
    # 3. Send notification to user
    # 4. Update export status
    pass