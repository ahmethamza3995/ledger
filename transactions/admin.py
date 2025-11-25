from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from .models import PaymentMethod, Subcategory, Transaction, AuditLog

@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('name',)

@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'normalized_name', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'normalized_name')

class DeletedFilter(SimpleListFilter):
    title = 'Deleted'
    parameter_name = 'deleted'
    def lookups(self, request, model_admin):
        return [('only', 'Only deleted')]
    def queryset(self, request, queryset):
        if self.value() == 'only':
            return queryset.filter(is_active=False)
        return queryset

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_date', 'amount', 'type', 'payment_method', 'subcategory', 'owner', 'is_active')
    list_filter = ('type', 'payment_method', 'subcategory', 'is_active', 'transaction_date', DeletedFilter)
    search_fields = ('description', 'receipt_original_name')

    actions = ['restore_selected', 'hard_delete_selected']

    def get_queryset(self, request):
        return Transaction.all_objects.all()

    def restore_selected(self, request, queryset):
        for obj in queryset:
            obj.restore(by=request.user)
    restore_selected.short_description = "Restore selected transactions"

    def hard_delete_selected(self, request, queryset):
        if not (request.user.is_superuser or request.user.groups.filter(name='Admin').exists()):
            self.message_user(request, "Only Admin can hard delete.", level='error')
            return
        for obj in queryset:
            obj.delete(by=request.user, hard=True)
    hard_delete_selected.short_description = "Hard delete selected transactions"

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'actor', 'action', 'object_type', 'object_id')
    list_filter = ('action', ('timestamp', admin.DateFieldListFilter))
    search_fields = ('object_type', 'object_id', 'metadata')



