from django.db import models
from django.utils import timezone

class ActiveOnlyQuerySet(models.QuerySet):
    def delete(self, by=None, hard=False):
        if hard:
            return super().delete()
        now = timezone.now()
        count = 0
        for obj in self:
            if obj.is_active:
                obj.is_active = False
                obj.deleted_at = now
                if by is not None:
                    obj.deleted_by = by
                obj.save(update_fields=['is_active', 'deleted_at', 'deleted_by'])
                count += 1
        return (count, {})

class ActiveOnlyManager(models.Manager):
    def get_queryset(self):
        return ActiveOnlyQuerySet(self.model, using=self._db).filter(is_active=True)

class AllObjectsManager(models.Manager):
    def get_queryset(self):
        return ActiveOnlyQuerySet(self.model, using=self._db)
