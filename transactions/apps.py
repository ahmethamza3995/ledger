from django.apps import AppConfig

class TransactionsConfig(AppConfig):
    default_auto_field = 'django.db.models.AutoField' #default_auto_field = 'django.db.models.BigAutoField'
    name = 'transactions'
    def ready(self):
        from . import signals  # Sinyalleri kaydetmek için import ediyoruz