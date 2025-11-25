from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from pathlib import Path
import hashlib
from django.utils import timezone
from .managers import ActiveOnlyManager, AllObjectsManager
from .utils import normalize_subcategory_name, validate_image_file, hashed_receipt_path, make_thumbnail, compute_content_hash, get_file_bytes


User = get_user_model()

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True

class PaymentMethod(TimeStampedModel):
    name = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)
    def __str__(self): return self.name

class Subcategory(TimeStampedModel):
    name = models.CharField(max_length=60)
    normalized_name = models.CharField(max_length=80, unique=True)
    is_active = models.BooleanField(default=True)

    def clean(self):
        self.normalized_name = normalize_subcategory_name(self.name or '')

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

    def __str__(self): return self.name

def _storage_move(storage, src: str, dst: str):
    """Storage üzerinde src -> dst taşı (kopyala+sil). dst yoksa oluşturur."""
    with storage.open(src, 'rb') as fh:
        content = fh.read()
    if not storage.exists(dst):
        storage.save(dst, ContentFile(content))
    # src'i sil (varsa)
    try:
        if storage.exists(src):
            storage.delete(src)
    except Exception:
        pass
    return dst

class Transaction(TimeStampedModel):
    class Types(models.TextChoices):
        INCOME = 'INCOME', 'Income'
        EXPENSE = 'EXPENSE', 'Expense'

    id = models.AutoField(primary_key=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    type = models.CharField(max_length=7, choices=Types.choices)

    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT, related_name='transactions')
    subcategory = models.ForeignKey(Subcategory, on_delete=models.PROTECT, related_name='transactions')

    description = models.CharField(max_length=60, blank=True)
    transaction_date = models.DateTimeField()

    # Receipt
    receipt_file = models.FileField(upload_to='receipts/tmp/', blank=True, null=True)
    receipt_original_name = models.CharField(max_length=255, blank=True)
    receipt_thumbnail = models.ImageField(upload_to='receipts/thumbnails/', blank=True, null=True)

    # Soft delete & audit
    is_active = models.BooleanField(default=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='deleted_transactions')

    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='created_transactions')
    updated_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='updated_transactions')

    objects = ActiveOnlyManager()
    all_objects = AllObjectsManager()

    class Meta:
        permissions = (
            ('can_restore_transaction', 'Can restore transaction'),
            ('can_export_transactions', 'Can export transactions'),
        )
        ordering = ['-transaction_date', '-id']

    def _normalize_receipt_paths(self):
            """
            Yanlış adlandırılmış yolları düzeltir; gerekiyorsa fiziksel taşıma yapar.
            """
            changed = False
            if self.receipt_file:
                storage = self.receipt_file.storage
                name = self.receipt_file.name.replace('\\', '/')

                # 1) receipts/tmp/receipts/... -> receipts/...
                if name.startswith('receipts/tmp/receipts/'):
                    fixed = name.replace('receipts/tmp/', '', 1)
                    if storage.exists(name):
                        _storage_move(storage, name, fixed)
                    self.receipt_file.name = fixed
                    name = fixed
                    changed = True

                # 2) halen /tmp/ içeriyorsa -> tmp dışına taşı (yeni bir klasöre)
                if '/tmp/' in name:
                    dst = f"receipts/{timezone.now():%Y/%m}/{Path(name).name}"
                    if storage.exists(name):
                        _storage_move(storage, name, dst)
                    self.receipt_file.name = dst
                    changed = True

            # Thumbnail yolu düzelt
            if self.receipt_thumbnail:
                tstorage = self.receipt_thumbnail.storage
                tname = self.receipt_thumbnail.name.replace('\\', '/')
                # receipts/thumbnails/receipts/... -> receipts/thumbnails/...
                if tname.startswith('receipts/thumbnails/receipts/'):
                    tfixed = tname.replace('receipts/thumbnails/receipts/', 'receipts/thumbnails/', 1)
                    if tstorage.exists(tname):
                        _storage_move(tstorage, tname, tfixed)
                    self.receipt_thumbnail.name = tfixed
                    changed = True

            return changed

    def clean(self):
        if self.amount is not None and self.amount <= 0:
            raise ValidationError({'amount': 'Amount must be positive.'})
        if self.transaction_date and self.transaction_date > timezone.now():
            raise ValidationError({'transaction_date': 'Future dates are not allowed.'})
        if self.receipt_file:
            try:
                validate_image_file(self.receipt_file)
            except ValueError as e:
                raise ValidationError({'receipt_file': str(e)})

    
    def save(self, *args, **kwargs):
        """
        - Yeni upload'ta: önce validasyon, sonra dosyayı final path'e (receipts/YYYY/MM/<hash>.<ext>)
        DOĞRUDAN storage.save ile yaz; upload_to'yu bypass et. Ardından .name ve _committed ayarla.
        - Güncellemelerde: dosyaya dokunma; varsa yol normalizasyonu (_normalize_receipt_paths) yap.
        - Thumbnail: yalnız dosya gerçekten varsa ve henüz yoksa oluştur (receipts/thumbnails/YYYY/MM/<base>.webp).
        """
        
        has_file = bool(self.receipt_file)

        # Orijinal adı set et
        if has_file and not self.receipt_original_name:
            self.receipt_original_name = Path(self.receipt_file.name or "").name

        # Yeni upload? (henüz storage'a yazılmamış)
        is_new_upload = bool(has_file and getattr(self.receipt_file, '_committed', True) is False)

        # Önce validasyon (utils.get_file_bytes güvenli okur)
        self.clean()

        # Dosya işlemleri
        if has_file:
            storage = self.receipt_file.storage
            current_name = (self.receipt_file.name or '').replace('\\', '/')

            if is_new_upload:
                # İçeriği oku ve hashle
                data = get_file_bytes(self.receipt_file)
                ext = Path(current_name).suffix.lower() or '.bin'
                file_hash = hashlib.sha256(data).hexdigest()
                final_path = f"receipts/{timezone.now():%Y/%m}/{file_hash}{ext}"

                # Final path'e DOĞRUDAN yaz (upload_to bypass)
                if not storage.exists(final_path):
                    storage.save(final_path, ContentFile(data))

                # (Varsa) tmp dosyasını temizle
                try:
                    if current_name and 'tmp/' in current_name and storage.exists(current_name):
                        storage.delete(current_name)
                except Exception:
                    pass

                # Alanları güncelle — tekrar yazmayı engelle
                self.receipt_file.name = final_path
                self.receipt_file._committed = True

            else:
                # Yeni upload değil -> sadece yol normalizasyonu (varsa)
                if hasattr(self, '_normalize_receipt_paths'):
                    self._normalize_receipt_paths()

        # DB'ye kaydet
        super().save(*args, **kwargs)

        # Thumbnail (yoksa üret)
        if has_file and not self.receipt_thumbnail:
            storage = self.receipt_file.storage
            if storage.exists(self.receipt_file.name):
                base = Path(self.receipt_file.name).stem
                # ImageField(upload_to='receipts/thumbnails/') → sadece alt yolu ver
                thumb_rel = f"{timezone.now():%Y/%m}/{base}.webp"
                thumb_content = make_thumbnail(self.receipt_file, width=320)
                self.receipt_thumbnail.save(thumb_rel, thumb_content, save=False)
                super().save(update_fields=['receipt_thumbnail'])


    def delete(self, using=None, keep_parents=False, by=None, hard=False):
        if hard:
            # isimleri normalize al
            rf_name = self.receipt_file.name.replace('\\','/') if self.receipt_file else None
            rf_storage = self.receipt_file.storage if self.receipt_file else None
            th_name = self.receipt_thumbnail.name.replace('\\','/') if self.receipt_thumbnail else None
            th_storage = self.receipt_thumbnail.storage if self.receipt_thumbnail else None

            # önce DB kaydını kaldır
            super().delete(using=using, keep_parents=keep_parents)

            def _del(storage, path):
                if storage and path:
                    try:
                        if storage.exists(path):
                            storage.delete(path)
                    except Exception:
                        pass

            # ana dosyalar
            _del(rf_storage, rf_name)
            _del(th_storage, th_name)

            # muhtemel DUP kopyalar (geçmişte oluşabilmiş)
            if rf_storage and rf_name:
                from pathlib import Path
                base = Path(rf_name).name
                # receipts/tmp/<base>
                _del(rf_storage, f"receipts/tmp/{base}")
                # receipts/tmp/<full rf_name>  (örn receipts/tmp/receipts/YYYY/MM/<hash>.png)
                _del(rf_storage, f"receipts/tmp/{rf_name}")

            if th_storage and th_name and th_name.startswith('receipts/thumbnails/receipts/'):
                # çifte receipts durumunu da sil
                _del(th_storage, th_name.replace('receipts/thumbnails/receipts/', 'receipts/thumbnails/', 1))
            return

        # Soft delete
        self.is_active = False
        self.deleted_at = timezone.now()
        if by:
            self.deleted_by = by
        self.save(update_fields=['is_active', 'deleted_at', 'deleted_by'])



    def restore(self, by=None):
        self.is_active = True
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=['is_active', 'deleted_at', 'deleted_by'])

    def __str__(self):
        return f"{self.transaction_date:%Y-%m-%d %H:%M} | {self.type} | {self.amount} | {self.owner}"

class AuditLog(models.Model):
    class Actions(models.TextChoices):
        LOGIN = 'LOGIN', 'Login'
        CREATE = 'CREATE', 'Create'
        UPDATE = 'UPDATE', 'Update'
        SOFT_DELETE = 'SOFT_DELETE', 'Soft delete'
        RESTORE = 'RESTORE', 'Restore'
        HARD_DELETE = 'HARD_DELETE', 'Hard delete'
        EXPORT = 'EXPORT', 'Export'

    actor = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='audit_logs')
    action = models.CharField(max_length=20, choices=Actions.choices)
    object_type = models.CharField(max_length=60)
    object_id = models.CharField(max_length=64)
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.timestamp:%Y-%m-%d %H:%M:%S} {self.action} {self.object_type}#{self.object_id}"

# Bu dosya için ek açıklamalar:
# - Transaction modeli, finansal işlemleri temsil eder ve soft delete, dosya yönetimi gibi özelliklere sahiptir.
# - ActiveOnlyManager ve AllObjectsManager, aktif ve tüm nesneleri sorgulamak için özel yöneticilerdir.
# - AuditLog modeli, kullanıcı eylemlerini izlemek için kullanılır.
# - validate_image_file, hashed_receipt_path ve make_thumbnail gibi yardımcı işlevler utils.py dosyasında tanımlanmıştır.
# - created_by ve updated_by alanları, işlemi oluşturan ve güncelleyen kullanıcıları izlemek için opsiyoneldir.
# - Transaction modelindeki delete ve restore yöntemleri, yumuşak silme ve geri yükleme işlevselliğini sağlar.
# 