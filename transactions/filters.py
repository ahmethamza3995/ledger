import django_filters
from django.db.models import Q
from .models import Transaction

class TransactionFilter(django_filters.FilterSet):
    date_from = django_filters.IsoDateTimeFilter(field_name='transaction_date', lookup_expr='gte')
    date_to = django_filters.IsoDateTimeFilter(field_name='transaction_date', lookup_expr='lte')
    type = django_filters.CharFilter(field_name='type', lookup_expr='iexact')
    payment_method = django_filters.NumberFilter(field_name='payment_method_id')
    subcategory = django_filters.NumberFilter(field_name='subcategory_id')
    min_amount = django_filters.NumberFilter(field_name='amount', lookup_expr='gte')
    max_amount = django_filters.NumberFilter(field_name='amount', lookup_expr='lte')
    search = django_filters.CharFilter(method='filter_search')

    class Meta:
        model = Transaction
        fields = []

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(description__icontains=value) | Q(subcategory__name__icontains=value)
        )

# Bu filtre seti, Transaction modeline çeşitli filtreleme seçenekleri ekler.
# Kullanıcılar, tarih aralığı, tür, ödeme yöntemi, alt kategori,
# miktar aralığı ve açıklama veya alt kategori adına göre arama yapabilirler.
