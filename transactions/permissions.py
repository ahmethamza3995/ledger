from rest_framework.permissions import BasePermission

class IsOwnerOrManager(BasePermission):
    """
    User: sadece kendi objeleri
    Manager/Admin: tüm objeler
    """
    def has_object_permission(self, request, view, obj):
        u = request.user
        if u.is_superuser:
            return True
        if u.groups.filter(name__in=['Admin', 'Manager']).exists():
            return True
        return obj.owner_id == u.id
