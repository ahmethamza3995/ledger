from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PaymentMethodViewSet, SubcategoryViewSet, TransactionViewSet,
    ExportLogView, api_login
)

router = DefaultRouter()
router.register(r'transactions', TransactionViewSet, basename='transactions-transaction')
router.register(r'payment-methods', PaymentMethodViewSet, basename='payment-methods')
router.register(r'subcategories', SubcategoryViewSet, basename='subcategories')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/login/', api_login, name='api-login'),        # /api/v1/auth/login/
    path('export-log/', ExportLogView.as_view(), name='export-log'),
]
# API uç noktaları:
# - /api/v1/transactions/ : İşlemler için CRUD işlemleri
# - /api/v1/payment-methods/ : Ödeme yöntemleri için CRUD işlemleri
# - /api/v1/subcategories/ : Alt kategoriler için CRUD işlemleri
# - /api/v1/auth/login/ : Kullanıcı girişi