from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.http import FileResponse
from django.shortcuts import render, redirect

from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, DjangoModelPermissions, AllowAny
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, NotFound

from .models import PaymentMethod, Subcategory, Transaction, AuditLog
from .serializers import PaymentMethodSerializer, SubcategorySerializer, TransactionSerializer
from .permissions import IsOwnerOrManager
from .filters import TransactionFilter

# --- mevcut template görünümü ---
def home_redirect(request):
    if request.user.is_authenticated:
        return redirect('transactions_page')
    return redirect('login')

def login_view(request):
    if request.method == 'GET':
        if request.user.is_authenticated:
            return redirect('transactions_page')
        return render(request, 'registration/login.html')
    email = request.POST.get('email')
    password = request.POST.get('password')
    user = authenticate(request, email=email, password=password)
    if user:
        login(request, user)
        return redirect('transactions_page')
    return render(request, 'registration/login.html', {'error': 'E-posta veya şifre hatalı.'}, status=401)

@login_required
def transactions_page(request):
    is_admin_group = request.user.groups.filter(name='Admin').exists() or request.user.is_superuser
    is_manager = request.user.groups.filter(name='Manager').exists()
    can_export = request.user.has_perm('transactions.can_export_transactions')
    can_restore = request.user.has_perm('transactions.can_restore_transaction')  #
    ctx = {
        'user_role': 'Admin' if is_admin_group else ('Manager' if is_manager else 'User'),
        'can_export': can_export,
        'can_restore': can_restore, # 
    }
    return render(request, 'transactions/list.html', ctx)

@login_required
def transaction_create_page(request):
    # Basit bir sayfa; JS API'den pm & subcategory listesini çekecek
    return render(request, 'transactions/create.html')

# --- API: Session login (CSRF korumalı) ---
@api_view(['POST'])
@permission_classes([AllowAny])
def api_login(request):
    email = request.data.get('email')
    password = request.data.get('password')
    user = authenticate(request, email=email, password=password)
    if not user:
        return Response({'detail': 'Invalid credentials'}, status=401)
    login(request, user)
    return Response({'detail': 'ok'})

# --- API: PaymentMethod (sadece list/retrieve) ---
class PaymentMethodViewSet(mixins.ListModelMixin,
                           mixins.RetrieveModelMixin,
                           viewsets.GenericViewSet):
    queryset = PaymentMethod.objects.filter(is_active=True).order_by('name')
    serializer_class = PaymentMethodSerializer
    permission_classes = [IsAuthenticated]

# --- API: Subcategory (admin/permissions ile create/update) ---
class SubcategoryViewSet(viewsets.ModelViewSet):
    queryset = Subcategory.objects.filter(is_active=True).order_by('name')
    serializer_class = SubcategorySerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

# --- API: Transaction ---
class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions, IsOwnerOrManager]
    filterset_class = TransactionFilter
    search_fields = ['description', 'subcategory__name']
    ordering_fields = ['transaction_date', 'amount']

    def get_queryset(self):
        user = self.request.user
        only_deleted = self.request.query_params.get('only_deleted') in ('1', 'true', 'True')

        # Yalnız Admin (restore izni) silinmişleri görebilir
        if only_deleted and not user.has_perm('transactions.can_restore_transaction'):
            raise PermissionDenied('Only Admin can view deleted transactions.')

        base = Transaction.all_objects.all() if only_deleted else Transaction.objects.all()

        if user.is_superuser or user.groups.filter(name__in=['Admin', 'Manager']).exists():
            qs = base
        else:
            qs = base.filter(owner=user)

        if only_deleted:
            qs = qs.filter(is_active=False)
        return qs
    
    def _get_object_any(self, pk):
        """
        Aktif/soft-deleted ayrımı yapmadan nesneyi getirir.
        Obje-seviyesi izinleri ayrıca kontrol edeceğiz.
        """
        try:
            return Transaction.all_objects.select_related('owner').get(pk=pk)
        except Transaction.DoesNotExist:
            raise NotFound('Transaction not found.')

    def perform_create(self, serializer):
        obj = serializer.save()
        AuditLog.objects.create(actor=self.request.user, action=AuditLog.Actions.CREATE,
                                object_type='Transaction', object_id=str(obj.id),
                                metadata={'id': obj.id})

    def perform_update(self, serializer):
        obj = serializer.save()
        AuditLog.objects.create(actor=self.request.user, action=AuditLog.Actions.UPDATE,
                                object_type='Transaction', object_id=str(obj.id),
                                metadata={'id': obj.id})

    def perform_destroy(self, instance):
        instance.delete(by=self.request.user)
        AuditLog.objects.create(actor=self.request.user, action=AuditLog.Actions.SOFT_DELETE,
                                object_type='Transaction', object_id=str(instance.id))

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        # Sadece can_restore izni olan (Admin)
        if not request.user.has_perm('transactions.can_restore_transaction'):
            raise PermissionDenied('Permission denied.')

        obj = self._get_object_any(pk)
        # Obje-seviyesi izin (Admin/Manager geçer; diğerleri sahibiyse geçer)
        self.check_object_permissions(request, obj)

        if obj.is_active:
            return Response({'status': 'already_active'}, status=200)

        obj.restore(by=request.user)
        AuditLog.objects.create(actor=request.user, action=AuditLog.Actions.RESTORE,
                                object_type='Transaction', object_id=str(obj.id))
        return Response({'status': 'restored'}, status=200)

    @action(detail=True, methods=['delete'], url_path='hard-delete')
    def hard_delete(self, request, pk=None):
        if not (request.user.is_superuser or request.user.groups.filter(name='Admin').exists()):
            raise PermissionDenied('Only Admin can hard delete.')

        obj = self._get_object_any(pk)
        self.check_object_permissions(request, obj)

        obj.delete(by=request.user, hard=True)
        AuditLog.objects.create(actor=request.user, action=AuditLog.Actions.HARD_DELETE,
                                object_type='Transaction', object_id=str(pk))
        return Response(status=204)

    @action(detail=True, methods=['get'], url_path='receipt')
    def receipt(self, request, pk=None):
        obj = self.get_object()
        # obje-seviyesi erişim
        u = request.user
        if not (u.is_superuser or u.groups.filter(name__in=['Admin', 'Manager']).exists() or obj.owner_id == u.id):
            return Response({'detail': 'Forbidden.'}, status=403)
        if not obj.receipt_file:
            return Response({'detail': 'No receipt.'}, status=404)
        return FileResponse(obj.receipt_file.open('rb'), as_attachment=True,
                            filename=(obj.receipt_original_name or 'receipt'))
                            
# --- API: Export log (ayrıntısız) ---
from rest_framework.views import APIView
class ExportLogView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        AuditLog.objects.create(actor=request.user, action=AuditLog.Actions.EXPORT,
                                object_type='Transaction', object_id='*',
                                metadata={'params': request.data})
        return Response({'status': 'ok'})

# Bu görünüm seti, ödeme yöntemleri, alt kategoriler ve işlemler için API uç noktaları sağlar.
# İşlemler için, kullanıcıların yalnızca kendi işlemlerini görmelerini ve yönetmelerini sağlar,
# ancak Admin ve Manager gruplarındaki kullanıcılar tüm işlemleri görebilir ve yönetebilir.
# Ayrıca, işlem makbuz dosyalarını indirme, işlemleri geri yükleme ve kalıcı silme gibi ek işlevler de içerir.
# AuditLog modeli, kullanıcı eylemlerini izlemek için kullanılır.
# ExportLogView, kullanıcıların işlem verilerini dışa aktardıklarında bir kayıt oluşturur.
