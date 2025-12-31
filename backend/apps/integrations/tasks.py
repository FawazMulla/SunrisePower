"""
Background task processing for Solar CRM Platform.
Simple Django-based task system for Phase 1.
"""
import logging
import json
from datetime import datetime, timedelta
from django.db import models
from django.utils import timezone
from django.core.management.base import BaseCommand
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class TaskStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    RUNNING = 'running', 'Running'
    SUCCESS = 'success', 'Success'
    FAILED = 'failed', 'Failed'
    RETRY = 'retry', 'Retry'


class BackgroundTask(models.Model):
    """
    Simple background task model for Phase 1.
    Can be upgraded to Celery later.
    """
    
    # Task identification
    task_name = models.CharField(
        max_length=100,
        help_text='Name of the task function'
    )
    task_id = models.CharField(
        max_length=50,
        unique=True,
        help_text='Unique task identifier'
    )
    
    # Task data
    args = models.JSONField(
        default=list,
        help_text='Task arguments as JSON list'
    )
    kwargs = models.JSONField(
        default=dict,
        help_text='Task keyword arguments as JSON dict'
    )
    
    # Status and execution
    status = models.CharField(
        max_length=20,
        choices=TaskStatus.choices,
        default=TaskStatus.PENDING
    )
    result = models.JSONField(
        null=True,
        blank=True,
        help_text='Task result or error message'
    )
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Retry logic
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    retry_delay = models.IntegerField(
        default=60,
        help_text='Retry delay in seconds'
    )
    
    # Priority
    priority = models.IntegerField(
        default=5,
        help_text='Task priority (1=highest, 10=lowest)'
    )
    
    class Meta:
        db_table = 'background_tasks'
        ordering = ['priority', 'created_at']
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['created_at']),
            models.Index(fields=['task_name']),
        ]
    
    def __str__(self):
        return f"{self.task_name} ({self.status})"
    
    def mark_running(self):
        """Mark task as running."""
        self.status = TaskStatus.RUNNING
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at'])
    
    def mark_success(self, result: Any = None):
        """Mark task as successful."""
        self.status = TaskStatus.SUCCESS
        self.completed_at = timezone.now()
        if result is not None:
            self.result = result
        self.save(update_fields=['status', 'completed_at', 'result'])
    
    def mark_failed(self, error: str):
        """Mark task as failed."""
        self.status = TaskStatus.FAILED
        self.completed_at = timezone.now()
        self.result = {'error': str(error)}
        self.save(update_fields=['status', 'completed_at', 'result'])
    
    def should_retry(self) -> bool:
        """Check if task should be retried."""
        return (
            self.status == TaskStatus.FAILED and
            self.retry_count < self.max_retries
        )
    
    def schedule_retry(self):
        """Schedule task for retry."""
        if self.should_retry():
            self.status = TaskStatus.RETRY
            self.retry_count += 1
            # Calculate next retry time with exponential backoff
            delay = self.retry_delay * (2 ** (self.retry_count - 1))
            self.created_at = timezone.now() + timedelta(seconds=delay)
            self.save(update_fields=['status', 'retry_count', 'created_at'])


class TaskRegistry:
    """
    Registry for background tasks.
    """
    
    _tasks = {}
    
    @classmethod
    def register(cls, name: str):
        """Decorator to register a task function."""
        def decorator(func):
            cls._tasks[name] = func
            return func
        return decorator
    
    @classmethod
    def get_task(cls, name: str):
        """Get a registered task function."""
        return cls._tasks.get(name)
    
    @classmethod
    def list_tasks(cls):
        """List all registered tasks."""
        return list(cls._tasks.keys())


class TaskManager:
    """
    Simple task manager for Phase 1.
    """
    
    @staticmethod
    def enqueue_task(
        task_name: str,
        args: list = None,
        kwargs: dict = None,
        priority: int = 5,
        max_retries: int = 3,
        retry_delay: int = 60
    ) -> str:
        """
        Enqueue a background task.
        
        Args:
            task_name: Name of the registered task function
            args: Task arguments
            kwargs: Task keyword arguments
            priority: Task priority (1=highest, 10=lowest)
            max_retries: Maximum retry attempts
            retry_delay: Delay between retries in seconds
            
        Returns:
            Task ID
        """
        import uuid
        
        task_id = str(uuid.uuid4())
        
        task = BackgroundTask.objects.create(
            task_name=task_name,
            task_id=task_id,
            args=args or [],
            kwargs=kwargs or {},
            priority=priority,
            max_retries=max_retries,
            retry_delay=retry_delay
        )
        
        logger.info(f"Enqueued task {task_name} with ID {task_id}")
        return task_id
    
    @staticmethod
    def process_pending_tasks(limit: int = 10):
        """
        Process pending tasks.
        
        Args:
            limit: Maximum number of tasks to process
        """
        # Get pending tasks ordered by priority and creation time
        tasks = BackgroundTask.objects.filter(
            status__in=[TaskStatus.PENDING, TaskStatus.RETRY],
            created_at__lte=timezone.now()
        ).order_by('priority', 'created_at')[:limit]
        
        for task in tasks:
            TaskManager._execute_task(task)
    
    @staticmethod
    def _execute_task(task: BackgroundTask):
        """
        Execute a single task.
        
        Args:
            task: BackgroundTask instance
        """
        try:
            # Mark task as running
            task.mark_running()
            
            # Get the task function
            task_func = TaskRegistry.get_task(task.task_name)
            if not task_func:
                raise ValueError(f"Task function '{task.task_name}' not found")
            
            # Execute the task
            logger.info(f"Executing task {task.task_name} (ID: {task.task_id})")
            result = task_func(*task.args, **task.kwargs)
            
            # Mark as successful
            task.mark_success(result)
            logger.info(f"Task {task.task_name} completed successfully")
            
        except Exception as e:
            logger.error(f"Task {task.task_name} failed: {str(e)}")
            task.mark_failed(str(e))
            
            # Schedule retry if applicable
            if task.should_retry():
                task.schedule_retry()
                logger.info(f"Task {task.task_name} scheduled for retry ({task.retry_count}/{task.max_retries})")
    
    @staticmethod
    def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task status.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task status dict or None if not found
        """
        try:
            task = BackgroundTask.objects.get(task_id=task_id)
            return {
                'task_id': task.task_id,
                'task_name': task.task_name,
                'status': task.status,
                'result': task.result,
                'created_at': task.created_at,
                'started_at': task.started_at,
                'completed_at': task.completed_at,
                'retry_count': task.retry_count,
                'max_retries': task.max_retries
            }
        except BackgroundTask.DoesNotExist:
            return None
    
    @staticmethod
    def cleanup_old_tasks(days: int = 7):
        """
        Clean up old completed tasks.
        
        Args:
            days: Number of days to keep completed tasks
        """
        cutoff_date = timezone.now() - timedelta(days=days)
        deleted_count = BackgroundTask.objects.filter(
            status__in=[TaskStatus.SUCCESS, TaskStatus.FAILED],
            completed_at__lt=cutoff_date
        ).delete()[0]
        
        logger.info(f"Cleaned up {deleted_count} old tasks")
        return deleted_count


# Example task functions
@TaskRegistry.register('send_email')
def send_email_task(to_email: str, subject: str, message: str):
    """
    Example task: Send email.
    """
    # This would integrate with actual email service
    logger.info(f"Sending email to {to_email}: {subject}")
    # Simulate email sending
    import time
    time.sleep(1)  # Simulate processing time
    return {'status': 'sent', 'to': to_email}


@TaskRegistry.register('process_lead')
def process_lead_task(lead_id: int, action: str):
    """
    Example task: Process lead.
    """
    logger.info(f"Processing lead {lead_id} with action {action}")
    # This would integrate with lead processing logic
    return {'lead_id': lead_id, 'action': action, 'processed': True}


@TaskRegistry.register('generate_report')
def generate_report_task(report_type: str, date_range: dict):
    """
    Example task: Generate report.
    """
    logger.info(f"Generating {report_type} report for {date_range}")
    # This would integrate with report generation logic
    return {'report_type': report_type, 'generated': True}