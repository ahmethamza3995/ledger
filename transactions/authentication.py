from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend

User = get_user_model()

class EmailBackend(BaseBackend):
    
    def authenticate(self, request, email=None, username=None, password=None, **kwargs):
        identifier = email or username  
        if not identifier or not password:
            return None
        user = None
        # Önce email ile deneyelim
        try:
            user = User.objects.get(email__iexact=identifier)
        except User.DoesNotExist:
            # email alanı boş olabilir; username ile deneyelim
            try:
                user = User.objects.get(username__iexact=identifier)
            except User.DoesNotExist:
                return None
        if not user.is_active:
            return None
        return user if user.check_password(password) else None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
