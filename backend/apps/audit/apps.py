from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.audit"
    verbose_name = 'Audit Logging'
    
    def ready(self):
        """Import signal handlers when the app is ready."""
        from . import signals
