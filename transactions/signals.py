from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from .models import AuditLog

@receiver(user_logged_in)
def log_user_login(sender, user, request, **kwargs):
    AuditLog.objects.create(actor=user, action=AuditLog.Actions.LOGIN,
                            object_type='User', object_id=str(user.id))

# Bu sinyal, kullanıcı giriş yaptığında AuditLog tablosuna bir giriş ekler.
# 'actor' alanı giriş yapan kullanıcıyı, 'action' alanı ise yapılan işlemi belirtir.
# 'object_type' ve 'object_id' alanları, işlemle ilgili nesne türünü ve kimliğini saklar.
# Bu sayede, sistemdeki kullanıcı aktiviteleri izlenebilir ve gerektiğinde denetlenebilir.
# İleride başka sinyaller de eklenerek, örneğin kullanıcı çıkış yaptığında veya şifre değiştirdiğinde de log tutulabilir.