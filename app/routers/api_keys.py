"""
API Key management router for CRUD operations and key management.
"""
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, asc

from ..core.api_keys import APIKeyManager
from ..dependencies.database import get_database
from ..dependencies.auth import get_current_active_user, get_admin_user, get_developer_user
from ..services.activity_logging import log_api_key_created, log_admin_action
from ..models.user import User
from ..models.api_key import (
    APIKey,
    APIKeyCreate,
    APIKeyUpdate,
    APIKeyResponse,
    APIKeyCreateResponse,
    APIKeyListResponse,
    APIKeyUsageResponse,
    APIKeyRevoke,
    APIKeyRotate,
    APIKeyRotateResponse,
    BulkAPIKeyOperation,
    BulkAPIKeyOperationResponse,
    APIKeyStatus,
    APIKeyScope,
    APIKeyUsage
)


router = APIRouter(prefix="/api-keys", tags=["API Key Management"])


@router.post("/", response_model=APIKeyCreateResponse)
async def create_api_key(
    api_key_data: APIKeyCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database)
) -> APIKeyCreateResponse:
    """
    Create a new API key for the current user.
    
    Creates a new API key with the specified permissions and settings.
    The secret key is only returned once and cannot be retrieved again.
    """
    # Generate key pair
    key_id, secret_key, key_hash = APIKeyManager.generate_key_pair()
    
    # Create API key object
    api_key = APIKey(
        key_id=key_id,
        key_hash=key_hash,
        name=api_key_data.name,
        description=api_key_data.description,
        user_id=current_user.id,
        scopes=[scope.value for scope in api_key_data.scopes],
        expires_at=api_key_data.expires_at,
        allowed_ips=api_key_data.allowed_ips,
        allowed_domains=api_key_data.allowed_domains,
        rate_limit=api_key_data.rate_limit,
        rate_limit_period=api_key_data.rate_limit_period,
        extra_data=api_key_data.extra_data or {}
    )
    
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    
    # Log API key creation
    try:
        await log_api_key_created(
            api_key_id=str(api_key.id),
            user_id=str(current_user.id),
            key_name=api_key.name,
            scopes=api_key.scopes or []
        )
    except Exception as e:
        print(f"Failed to log API key creation: {e}")
    
    return APIKeyCreateResponse(
        api_key=APIKeyResponse.from_orm(api_key),
        secret_key=secret_key
    )


@router.get("/", response_model=APIKeyListResponse)
async def list_api_keys(
    skip: int = Query(0, ge=0, description="Number of keys to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of keys to return"),
    status_filter: Optional[APIKeyStatus] = Query(None, description="Filter by status"),
    scope_filter: Optional[APIKeyScope] = Query(None, description="Filter by scope"),
    search: Optional[str] = Query(None, description="Search in name or description"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database)
) -> APIKeyListResponse:
    """
    List API keys for the current user.
    
    Supports pagination, filtering by status/scope, and search functionality.
    """
    # Build query
    query = select(APIKey).where(APIKey.user_id == current_user.id)
    count_query = select(func.count(APIKey.id)).where(APIKey.user_id == current_user.id)
    
    # Apply filters
    filters = []
    
    if status_filter:
        filters.append(APIKey.status == status_filter)
    
    if scope_filter:
        filters.append(APIKey.scopes.contains([scope_filter.value]))
    
    if search:
        search_term = f"%{search}%"
        filters.append(
            (APIKey.name.ilike(search_term)) |
            (APIKey.description.ilike(search_term))
        )
    
    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination and execute
    query = query.offset(skip).limit(limit).order_by(desc(APIKey.created_at))
    result = await db.execute(query)
    api_keys = result.scalars().all()
    
    # Calculate pagination info
    pages = (total + limit - 1) // limit
    page = (skip // limit) + 1
    
    return APIKeyListResponse(
        api_keys=[APIKeyResponse.from_orm(key) for key in api_keys],
        total=total,
        page=page,
        size=len(api_keys),
        pages=pages
    )


@router.get("/{api_key_id}", response_model=APIKeyResponse)
async def get_api_key(
    api_key_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database)
) -> APIKeyResponse:
    """
    Get a specific API key by ID.
    
    Users can only access their own API keys unless they have admin privileges.
    """
    # Check if user is admin
    is_admin = current_user.role.value == "admin"
    
    # Build query with ownership check
    query = select(APIKey).where(APIKey.id == api_key_id)
    if not is_admin:
        query = query.where(APIKey.user_id == current_user.id)
    
    result = await db.execute(query)
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    return APIKeyResponse.from_orm(api_key)


@router.put("/{api_key_id}", response_model=APIKeyResponse)
async def update_api_key(
    api_key_id: UUID,
    api_key_update: APIKeyUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database)
) -> APIKeyResponse:
    """
    Update an API key's settings.
    
    Users can only update their own API keys. The secret key cannot be changed.
    """
    # Get the API key with ownership check
    result = await db.execute(
        select(APIKey).where(
            and_(
                APIKey.id == api_key_id,
                APIKey.user_id == current_user.id
            )
        )
    )
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    # Update fields
    update_data = api_key_update.dict(exclude_unset=True)
    
    # Convert scopes to string values if provided
    if "scopes" in update_data and update_data["scopes"]:
        update_data["scopes"] = [scope.value for scope in update_data["scopes"]]
    
    for field, value in update_data.items():
        setattr(api_key, field, value)
    
    api_key.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(api_key)
    
    return APIKeyResponse.from_orm(api_key)


@router.post("/{api_key_id}/revoke")
async def revoke_api_key(
    api_key_id: UUID,
    revoke_data: APIKeyRevoke = APIKeyRevoke(),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database)
) -> dict:
    """
    Revoke an API key.
    
    Once revoked, the API key cannot be used and cannot be reactivated.
    """
    success = await APIKeyManager.revoke_api_key(
        db=db,
        api_key_id=api_key_id,
        user_id=current_user.id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    await db.commit()
    
    return {
        "message": "API key revoked successfully",
        "api_key_id": str(api_key_id),
        "reason": revoke_data.reason
    }


@router.post("/{api_key_id}/rotate", response_model=APIKeyRotateResponse)
async def rotate_api_key(
    api_key_id: UUID,
    rotate_data: APIKeyRotate = APIKeyRotate(),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database)
) -> APIKeyRotateResponse:
    """
    Rotate an API key (legacy endpoint).
    
    Creates a new API key with the same settings and revokes the old one.
    Note: Consider using the new /lifecycle/rotate/{api_key_id} endpoint for advanced features.
    """
    result = await APIKeyManager.rotate_api_key(
        db=db,
        api_key_id=api_key_id,
        user_id=current_user.id,
        new_name=rotate_data.new_name
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    new_api_key, secret_key = result
    
    return APIKeyRotateResponse(
        old_key_id=str(api_key_id),
        new_api_key=APIKeyResponse.from_orm(new_api_key),
        new_secret_key=secret_key
    )


@router.get("/{api_key_id}/usage", response_model=APIKeyUsageResponse)
async def get_api_key_usage(
    api_key_id: UUID,
    days: int = Query(30, ge=1, le=90, description="Number of days to analyze"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database)
) -> APIKeyUsageResponse:
    """
    Get usage analytics for an API key.
    
    Returns detailed usage statistics including request counts, response times, and error rates.
    """
    # Verify ownership
    result = await db.execute(
        select(APIKey).where(
            and_(
                APIKey.id == api_key_id,
                APIKey.user_id == current_user.id
            )
        )
    )
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    # Calculate time windows
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)
    month_start = now - timedelta(days=30)
    
    # Get usage statistics
    usage_query = select(APIKeyUsage).where(
        and_(
            APIKeyUsage.api_key_id == api_key_id,
            APIKeyUsage.timestamp >= start_date
        )
    )
    usage_result = await db.execute(usage_query)
    usage_records = usage_result.scalars().all()
    
    # Calculate metrics
    total_requests = len(usage_records)
    requests_today = len([r for r in usage_records if r.timestamp >= today_start])
    requests_this_week = len([r for r in usage_records if r.timestamp >= week_start])
    requests_this_month = len([r for r in usage_records if r.timestamp >= month_start])
    
    # Response time analysis
    response_times = [r.response_time_ms for r in usage_records if r.response_time_ms]
    avg_response_time = sum(response_times) / len(response_times) if response_times else None
    
    # Error rate analysis
    error_count = len([r for r in usage_records if r.status_code >= 400])
    error_rate = (error_count / total_requests * 100) if total_requests > 0 else 0
    
    # Top endpoints analysis
    endpoint_counts = {}
    for record in usage_records:
        endpoint = record.endpoint
        endpoint_counts[endpoint] = endpoint_counts.get(endpoint, 0) + 1
    
    top_endpoints = [
        {"endpoint": endpoint, "requests": count}
        for endpoint, count in sorted(endpoint_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    ]
    
    # Usage by day
    usage_by_day = {}
    for record in usage_records:
        day = record.timestamp.date().isoformat()
        usage_by_day[day] = usage_by_day.get(day, 0) + 1
    
    usage_by_day_list = [
        {"date": day, "requests": count}
        for day, count in sorted(usage_by_day.items())
    ]
    
    return APIKeyUsageResponse(
        api_key_id=api_key_id,
        total_requests=total_requests,
        requests_today=requests_today,
        requests_this_week=requests_this_week,
        requests_this_month=requests_this_month,
        average_response_time_ms=avg_response_time,
        error_rate_percent=error_rate,
        top_endpoints=top_endpoints,
        usage_by_day=usage_by_day_list
    )


# Admin-only endpoints
@router.get("/admin/all", response_model=APIKeyListResponse)
async def list_all_api_keys(
    skip: int = Query(0, ge=0, description="Number of keys to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of keys to return"),
    user_id: Optional[UUID] = Query(None, description="Filter by user ID"),
    status_filter: Optional[APIKeyStatus] = Query(None, description="Filter by status"),
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_database)
) -> APIKeyListResponse:
    """
    List all API keys in the system (admin only).
    
    Provides system-wide API key management capabilities.
    """
    # Build query
    query = select(APIKey)
    count_query = select(func.count(APIKey.id))
    
    # Apply filters
    filters = []
    
    if user_id:
        filters.append(APIKey.user_id == user_id)
    
    if status_filter:
        filters.append(APIKey.status == status_filter)
    
    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination and execute
    query = query.offset(skip).limit(limit).order_by(desc(APIKey.created_at))
    result = await db.execute(query)
    api_keys = result.scalars().all()
    
    # Calculate pagination info
    pages = (total + limit - 1) // limit
    page = (skip // limit) + 1
    
    return APIKeyListResponse(
        api_keys=[APIKeyResponse.from_orm(key) for key in api_keys],
        total=total,
        page=page,
        size=len(api_keys),
        pages=pages
    )


@router.post("/admin/bulk-operation", response_model=BulkAPIKeyOperationResponse)
async def bulk_api_key_operation(
    bulk_operation: BulkAPIKeyOperation,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_database)
) -> BulkAPIKeyOperationResponse:
    """
    Perform bulk operations on API keys (admin only).
    
    Supports bulk revoke, suspend, or activate operations.
    """
    successful = []
    failed = []
    
    for api_key_id in bulk_operation.api_key_ids:
        try:
            # Get the API key
            result = await db.execute(
                select(APIKey).where(APIKey.id == api_key_id)
            )
            api_key = result.scalar_one_or_none()
            
            if not api_key:
                failed.append({
                    "api_key_id": api_key_id,
                    "error": "API key not found"
                })
                continue
            
            # Perform operation
            if bulk_operation.operation == "revoke":
                api_key.status = APIKeyStatus.revoked
            elif bulk_operation.operation == "suspend":
                api_key.status = APIKeyStatus.suspended
            elif bulk_operation.operation == "activate":
                api_key.status = APIKeyStatus.active
            
            api_key.updated_at = datetime.utcnow()
            successful.append(api_key_id)
            
        except Exception as e:
            failed.append({
                "api_key_id": api_key_id,
                "error": str(e)
            })
    
    await db.commit()
    
    return BulkAPIKeyOperationResponse(
        successful=successful,
        failed=failed,
        total_processed=len(bulk_operation.api_key_ids)
    )


@router.delete("/admin/{api_key_id}")
async def force_delete_api_key(
    api_key_id: UUID,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_database)
) -> dict:
    """
    Force delete an API key (admin only).
    
    Permanently removes the API key and all associated usage data.
    """
    # Delete usage records first (they will be cascade deleted)
    
    # Delete the API key
    result = await db.execute(
        select(APIKey).where(APIKey.id == api_key_id)
    )
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    await db.delete(api_key)
    await db.commit()
    
    return {
        "message": "API key permanently deleted",
        "api_key_id": str(api_key_id)
    }