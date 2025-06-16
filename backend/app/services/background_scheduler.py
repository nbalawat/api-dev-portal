"""
Background job scheduler for automated tasks.

This module handles scheduling and execution of background tasks such as
API key expiration checking, cleanup tasks, and other maintenance operations.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable
from enum import Enum

from .expiration_manager import run_expiration_check


class ScheduleFrequency(str, Enum):
    """Supported scheduling frequencies."""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class BackgroundTask:
    """Represents a background task that can be scheduled."""
    
    def __init__(
        self,
        name: str,
        func: Callable,
        frequency: ScheduleFrequency,
        enabled: bool = True,
        last_run: Optional[datetime] = None,
        next_run: Optional[datetime] = None
    ):
        self.name = name
        self.func = func
        self.frequency = frequency
        self.enabled = enabled
        self.last_run = last_run
        self.next_run = next_run or self._calculate_next_run()
        self.run_count = 0
        self.error_count = 0
        self.last_error: Optional[str] = None
    
    def _calculate_next_run(self) -> datetime:
        """Calculate the next run time based on frequency."""
        now = datetime.utcnow()
        
        if self.frequency == ScheduleFrequency.HOURLY:
            return now + timedelta(hours=1)
        elif self.frequency == ScheduleFrequency.DAILY:
            # Run daily at 2 AM UTC
            next_run = now.replace(hour=2, minute=0, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
            return next_run
        elif self.frequency == ScheduleFrequency.WEEKLY:
            # Run weekly on Sundays at 2 AM UTC
            days_ahead = 6 - now.weekday()  # Sunday is 6
            if days_ahead <= 0:  # Target day already happened this week
                days_ahead += 7
            next_run = now + timedelta(days=days_ahead)
            return next_run.replace(hour=2, minute=0, second=0, microsecond=0)
        elif self.frequency == ScheduleFrequency.MONTHLY:
            # Run monthly on the 1st at 2 AM UTC
            if now.day == 1 and now.hour < 2:
                next_run = now.replace(hour=2, minute=0, second=0, microsecond=0)
            else:
                # Next month
                if now.month == 12:
                    next_run = now.replace(year=now.year + 1, month=1, day=1, hour=2, minute=0, second=0, microsecond=0)
                else:
                    next_run = now.replace(month=now.month + 1, day=1, hour=2, minute=0, second=0, microsecond=0)
            return next_run
        else:
            return now + timedelta(hours=24)  # Default to daily
    
    def should_run(self) -> bool:
        """Check if the task should run now."""
        if not self.enabled:
            return False
        
        now = datetime.utcnow()
        return now >= self.next_run
    
    async def execute(self) -> bool:
        """Execute the background task."""
        if not self.enabled:
            return False
        
        try:
            print(f"Starting background task: {self.name}")
            start_time = datetime.utcnow()
            
            # Execute the task function
            if asyncio.iscoroutinefunction(self.func):
                await self.func()
            else:
                self.func()
            
            # Update task status
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            self.last_run = start_time
            self.next_run = self._calculate_next_run()
            self.run_count += 1
            self.last_error = None
            
            print(f"Completed background task: {self.name} (duration: {duration:.2f}s)")
            return True
            
        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            self.next_run = self._calculate_next_run()  # Still schedule next run
            
            print(f"Background task failed: {self.name} - {e}")
            logging.error(f"Background task '{self.name}' failed: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get task status information."""
        return {
            "name": self.name,
            "frequency": self.frequency.value,
            "enabled": self.enabled,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "run_count": self.run_count,
            "error_count": self.error_count,
            "last_error": self.last_error
        }


class BackgroundScheduler:
    """Manages and executes background tasks."""
    
    def __init__(self):
        self.tasks: Dict[str, BackgroundTask] = {}
        self.running = False
        self._task_handle: Optional[asyncio.Task] = None
        self.check_interval = 60  # Check every minute
    
    def register_task(
        self,
        name: str,
        func: Callable,
        frequency: ScheduleFrequency,
        enabled: bool = True
    ) -> BackgroundTask:
        """Register a new background task."""
        task = BackgroundTask(name, func, frequency, enabled)
        self.tasks[name] = task
        print(f"Registered background task: {name} (frequency: {frequency.value})")
        return task
    
    def enable_task(self, name: str) -> bool:
        """Enable a background task."""
        if name in self.tasks:
            self.tasks[name].enabled = True
            return True
        return False
    
    def disable_task(self, name: str) -> bool:
        """Disable a background task."""
        if name in self.tasks:
            self.tasks[name].enabled = False
            return True
        return False
    
    def get_task_status(self, name: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific task."""
        if name in self.tasks:
            return self.tasks[name].get_status()
        return None
    
    def get_all_task_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all tasks."""
        return {name: task.get_status() for name, task in self.tasks.items()}
    
    async def run_task_now(self, name: str) -> bool:
        """Run a specific task immediately."""
        if name in self.tasks:
            return await self.tasks[name].execute()
        return False
    
    async def _check_and_run_tasks(self):
        """Check for tasks that need to run and execute them."""
        tasks_to_run = []
        
        for task in self.tasks.values():
            if task.should_run():
                tasks_to_run.append(task)
        
        if tasks_to_run:
            print(f"Running {len(tasks_to_run)} scheduled background tasks")
            
            # Run tasks concurrently
            results = await asyncio.gather(
                *[task.execute() for task in tasks_to_run],
                return_exceptions=True
            )
            
            for task, result in zip(tasks_to_run, results):
                if isinstance(result, Exception):
                    print(f"Task {task.name} failed with exception: {result}")
    
    async def _scheduler_loop(self):
        """Main scheduler loop."""
        print(f"Background scheduler started (check interval: {self.check_interval}s)")
        
        while self.running:
            try:
                await self._check_and_run_tasks()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Scheduler loop error: {e}")
                logging.error(f"Background scheduler error: {e}")
                await asyncio.sleep(self.check_interval)
        
        print("Background scheduler stopped")
    
    def start(self):
        """Start the background scheduler."""
        if self.running:
            print("Background scheduler is already running")
            return
        
        self.running = True
        try:
            # Try to get current event loop
            loop = asyncio.get_running_loop()
            self._task_handle = loop.create_task(self._scheduler_loop())
        except RuntimeError:
            # No event loop running, set running to False
            self.running = False
            print("No event loop available for background scheduler")
            return
        
        print("Background scheduler starting...")
    
    async def stop(self):
        """Stop the background scheduler."""
        if not self.running:
            return
        
        self.running = False
        
        if self._task_handle:
            self._task_handle.cancel()
            try:
                await self._task_handle
            except asyncio.CancelledError:
                pass
        
        print("Background scheduler stopped")
    
    def is_running(self) -> bool:
        """Check if the scheduler is running."""
        return self.running


# Global scheduler instance
background_scheduler = BackgroundScheduler()


def initialize_default_tasks():
    """Initialize default background tasks."""
    
    # Register API key expiration checking task
    background_scheduler.register_task(
        name="api_key_expiration_check",
        func=run_expiration_check,
        frequency=ScheduleFrequency.DAILY,
        enabled=True
    )
    
    print("Default background tasks initialized")


def start_background_scheduler():
    """Start the background scheduler with default tasks."""
    initialize_default_tasks()
    background_scheduler.start()


async def stop_background_scheduler():
    """Stop the background scheduler."""
    await background_scheduler.stop()


def get_scheduler_status() -> Dict[str, Any]:
    """Get the current status of the background scheduler."""
    return {
        "running": background_scheduler.is_running(),
        "check_interval": background_scheduler.check_interval,
        "tasks": background_scheduler.get_all_task_status()
    }