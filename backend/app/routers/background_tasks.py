"""
Background task management router for administrative control.
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..dependencies.auth import get_admin_user
from ..models.user import User
from ..services.background_scheduler import background_scheduler, get_scheduler_status


router = APIRouter(prefix="/background-tasks")


class TaskControlRequest(BaseModel):
    """Request model for task control operations."""
    task_name: str


class TaskControlResponse(BaseModel):
    """Response model for task control operations."""
    success: bool
    message: str
    task_status: Optional[Dict[str, Any]] = None


@router.get("/status")
async def get_background_scheduler_status(
    admin_user: User = Depends(get_admin_user)
) -> Dict[str, Any]:
    """
    Get the current status of the background scheduler and all tasks.
    
    Admin-only endpoint that provides comprehensive information about
    the background task system including task statuses, run counts, and errors.
    """
    return get_scheduler_status()


@router.post("/tasks/{task_name}/run", response_model=TaskControlResponse)
async def run_task_now(
    task_name: str,
    admin_user: User = Depends(get_admin_user)
) -> TaskControlResponse:
    """
    Run a specific background task immediately.
    
    This endpoint allows administrators to manually trigger background tasks
    without waiting for their scheduled execution time.
    """
    # Check if task exists
    task_status = background_scheduler.get_task_status(task_name)
    if not task_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Background task '{task_name}' not found"
        )
    
    # Run the task
    try:
        success = await background_scheduler.run_task_now(task_name)
        
        if success:
            return TaskControlResponse(
                success=True,
                message=f"Task '{task_name}' executed successfully",
                task_status=background_scheduler.get_task_status(task_name)
            )
        else:
            return TaskControlResponse(
                success=False,
                message=f"Task '{task_name}' execution failed",
                task_status=background_scheduler.get_task_status(task_name)
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute task '{task_name}': {str(e)}"
        )


@router.post("/tasks/{task_name}/enable", response_model=TaskControlResponse)
async def enable_task(
    task_name: str,
    admin_user: User = Depends(get_admin_user)
) -> TaskControlResponse:
    """
    Enable a background task.
    
    Enables the specified background task to run according to its schedule.
    """
    success = background_scheduler.enable_task(task_name)
    
    if success:
        return TaskControlResponse(
            success=True,
            message=f"Task '{task_name}' enabled successfully",
            task_status=background_scheduler.get_task_status(task_name)
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Background task '{task_name}' not found"
        )


@router.post("/tasks/{task_name}/disable", response_model=TaskControlResponse)
async def disable_task(
    task_name: str,
    admin_user: User = Depends(get_admin_user)
) -> TaskControlResponse:
    """
    Disable a background task.
    
    Disables the specified background task to prevent it from running
    according to its schedule.
    """
    success = background_scheduler.disable_task(task_name)
    
    if success:
        return TaskControlResponse(
            success=True,
            message=f"Task '{task_name}' disabled successfully",
            task_status=background_scheduler.get_task_status(task_name)
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Background task '{task_name}' not found"
        )


@router.get("/tasks/{task_name}/status")
async def get_task_status(
    task_name: str,
    admin_user: User = Depends(get_admin_user)
) -> Dict[str, Any]:
    """
    Get status information for a specific background task.
    
    Returns detailed information about the task including last run time,
    next scheduled run, error count, and current status.
    """
    task_status = background_scheduler.get_task_status(task_name)
    
    if not task_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Background task '{task_name}' not found"
        )
    
    return task_status


@router.get("/tasks")
async def list_all_tasks(
    admin_user: User = Depends(get_admin_user)
) -> Dict[str, Dict[str, Any]]:
    """
    List all registered background tasks and their statuses.
    
    Returns a comprehensive overview of all background tasks in the system.
    """
    return background_scheduler.get_all_task_status()