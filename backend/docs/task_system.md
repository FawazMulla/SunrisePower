# Background Task System

The Solar CRM Platform includes a simple background task processing system for Phase 1. This system can be easily upgraded to Celery or other task queues in the future.

## Features

- Simple Django-based task queue
- Task retry with exponential backoff
- Priority-based task processing
- Task status monitoring
- Management commands for task processing
- Admin interface for task monitoring
- API endpoints for task management

## Usage

### Registering Tasks

```python
from apps.integrations.tasks import TaskRegistry

@TaskRegistry.register('my_task')
def my_task_function(arg1, arg2, kwarg1=None):
    # Task implementation
    return {'result': 'success'}
```

### Enqueuing Tasks

```python
from apps.integrations.tasks import TaskManager

# Enqueue a task
task_id = TaskManager.enqueue_task(
    task_name='my_task',
    args=['value1', 'value2'],
    kwargs={'kwarg1': 'value'},
    priority=5,  # 1=highest, 10=lowest
    max_retries=3,
    retry_delay=60  # seconds
)
```

### Processing Tasks

```bash
# Process tasks once
python manage.py process_tasks --limit 10

# Run as daemon
python manage.py process_tasks --daemon --interval 10

# Clean up old tasks
python manage.py process_tasks --cleanup --cleanup-days 7
```

### API Endpoints

- `POST /api/tasks/enqueue/` - Enqueue a new task
- `GET /api/tasks/status/<task_id>/` - Get task status
- `GET /api/tasks/list/` - List available task types
- `GET /api/tasks/queue-status/` - Get queue statistics

### Webhook Integration

The system includes a webhook endpoint for EmailJS integration:

- `POST /api/webhooks/emailjs/` - Receive EmailJS form submissions

## Built-in Tasks

### EmailJS Processing
- `process_emailjs_submission` - Process form submissions from website

### Example Tasks
- `send_email` - Send email notifications
- `process_lead` - Process lead data
- `generate_report` - Generate reports

## Monitoring

Tasks can be monitored through:

1. **Django Admin** - View task status and details
2. **API Endpoints** - Programmatic access to task information
3. **Logs** - Task execution logs in Django logging system

## Future Upgrades

This simple system can be easily upgraded to:

- **Celery** - For distributed task processing
- **Redis/RabbitMQ** - For better message queuing
- **Monitoring Tools** - Flower, Celery Beat, etc.

The task registration and enqueueing API will remain the same, making the upgrade seamless.

## Configuration

Task system settings can be configured in Django settings:

```python
# Task processing settings
TASK_PROCESSING = {
    'DEFAULT_PRIORITY': 5,
    'DEFAULT_MAX_RETRIES': 3,
    'DEFAULT_RETRY_DELAY': 60,
    'CLEANUP_DAYS': 7,
}
```

## Production Deployment

For production, run the task processor as a separate service:

```bash
# Using systemd or supervisor
python manage.py process_tasks --daemon --interval 5
```

Or use a cron job for periodic processing:

```bash
# Process tasks every minute
* * * * * cd /path/to/project && python manage.py process_tasks --limit 50
```