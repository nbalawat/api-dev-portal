"""
User management router for CRUD operations and profile management.
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from ..core.security import get_password_hash, validate_password_strength
from ..dependencies.database import get_database
from ..dependencies.auth import (
    get_current_active_user,
    get_admin_user,
    get_developer_user
)
from ..models.user import (
    User,
    UserCreate,
    UserUpdate,
    UserUpdateAdmin,
    UserResponse,
    UserResponseAdmin,
    UserListResponse,
    UserListResponseAdmin,
    PasswordChange,
    UserRole
)


router = APIRouter(prefix="/users", tags=["User Management"])


@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_active_user)
) -> UserResponse:
    """
    Get current user's profile.
    """
    return UserResponse.from_orm(current_user)


@router.put("/me", response_model=UserResponse)
async def update_my_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database)
) -> UserResponse:
    """
    Update current user's profile.
    """
    # Update user fields
    update_data = user_update.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    current_user.updated_at = func.now()
    
    await db.commit()
    await db.refresh(current_user)
    
    return UserResponse.from_orm(current_user)


@router.patch("/me/password")
async def change_my_password(
    password_change: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_database)
) -> dict:
    """
    Change current user's password.
    """
    from ..core.security import verify_password
    
    # Verify current password
    if not verify_password(password_change.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Validate new password strength
    try:
        validate_password_strength(password_change.new_password)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # Update password
    current_user.hashed_password = get_password_hash(password_change.new_password)
    current_user.updated_at = func.now()
    
    await db.commit()
    
    return {"message": "Password updated successfully"}


@router.get("/", response_model=UserListResponseAdmin)
async def list_users(
    skip: int = Query(0, ge=0, description="Number of users to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of users to return"),
    role: Optional[UserRole] = Query(None, description="Filter by user role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search in username, email, or full_name"),
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_database)
) -> UserListResponseAdmin:
    """
    List all users (admin only).
    
    Supports pagination, filtering, and search.
    """
    # Build query
    query = select(User)
    count_query = select(func.count(User.id))
    
    # Apply filters
    filters = []
    
    if role is not None:
        filters.append(User.role == role)
    
    if is_active is not None:
        filters.append(User.is_active == is_active)
    
    if search:
        search_term = f"%{search}%"
        filters.append(
            (User.username.ilike(search_term)) |
            (User.email.ilike(search_term)) |
            (User.full_name.ilike(search_term))
        )
    
    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination and execute
    query = query.offset(skip).limit(limit).order_by(User.created_at.desc())
    result = await db.execute(query)
    users = result.scalars().all()
    
    # Calculate pagination info
    pages = (total + limit - 1) // limit
    page = (skip // limit) + 1
    
    return UserListResponseAdmin(
        users=[UserResponseAdmin.from_orm(user) for user in users],
        total=total,
        page=page,
        size=len(users),
        pages=pages
    )


@router.post("/", response_model=UserResponseAdmin)
async def create_user(
    user_create: UserCreate,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_database)
) -> UserResponseAdmin:
    """
    Create a new user (admin only).
    """
    # Check if username already exists
    result = await db.execute(select(User).where(User.username == user_create.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == user_create.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )
    
    # Validate password strength
    try:
        validate_password_strength(user_create.password)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # Create user
    user_data = user_create.dict(exclude={"password"})
    user_data["hashed_password"] = get_password_hash(user_create.password)
    
    user = User(**user_data)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return UserResponseAdmin.from_orm(user)


@router.get("/{user_id}", response_model=UserResponseAdmin)
async def get_user(
    user_id: UUID,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_database)
) -> UserResponseAdmin:
    """
    Get user by ID (admin only).
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponseAdmin.from_orm(user)


@router.put("/{user_id}", response_model=UserResponseAdmin)
async def update_user(
    user_id: UUID,
    user_update: UserUpdateAdmin,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_database)
) -> UserResponseAdmin:
    """
    Update user by ID (admin only).
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update user fields
    update_data = user_update.dict(exclude_unset=True)
    
    # Check for unique constraints if email is being updated
    if "email" in update_data and update_data["email"] != user.email:
        result = await db.execute(
            select(User).where(
                and_(User.email == update_data["email"], User.id != user_id)
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )
    
    for field, value in update_data.items():
        setattr(user, field, value)
    
    user.updated_at = func.now()
    
    await db.commit()
    await db.refresh(user)
    
    return UserResponseAdmin.from_orm(user)


@router.delete("/{user_id}")
async def delete_user(
    user_id: UUID,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_database)
) -> dict:
    """
    Delete user by ID (admin only).
    
    This actually deactivates the user rather than hard deletion.
    """
    if user_id == admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Soft delete by deactivating user
    user.is_active = False
    user.updated_at = func.now()
    
    await db.commit()
    
    return {"message": f"User {user.username} has been deactivated"}


@router.post("/{user_id}/activate")
async def activate_user(
    user_id: UUID,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_database)
) -> dict:
    """
    Activate a deactivated user (admin only).
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = True
    user.updated_at = func.now()
    
    await db.commit()
    
    return {"message": f"User {user.username} has been activated"}


@router.patch("/{user_id}/role")
async def change_user_role(
    user_id: UUID,
    new_role: UserRole,
    admin_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_database)
) -> dict:
    """
    Change user's role (admin only).
    """
    if user_id == admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role"
        )
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    old_role = user.role
    user.role = new_role
    user.updated_at = func.now()
    
    await db.commit()
    
    return {
        "message": f"User {user.username} role changed from {old_role} to {new_role}"
    }