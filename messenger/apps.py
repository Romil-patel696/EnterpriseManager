from django.apps import AppConfig


class MessengerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'messenger'
    
    def ready(self):
        import messenger.signals  # noqa