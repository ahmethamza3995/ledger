from rest_framework import serializers
from django.urls import reverse
from django.utils import timezone
from django.db import transaction as db_transaction
from .models import PaymentMethod, Subcategory, Transaction
from .utils import normalize_subcategory_name, validate_image_file

class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ['id', 'name', 'is_active']

class SubcategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Subcategory
        fields = ['id', 'name', 'normalized_name', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['normalized_name', 'created_at', 'updated_at']

class TransactionSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(read_only=True)

    # Görüntüde isim göstermek için (read-only)
    payment_method_name = serializers.CharField(source='payment_method.name', read_only=True)
    subcategory_label = serializers.CharField(source='subcategory.name', read_only=True)


    receipt_download_url = serializers.SerializerMethodField()
    receipt_thumbnail_url = serializers.SerializerMethodField()
    # Transaction oluştururken subcategory'yi isimle de kabul et (yoksa oluştur)
    subcategory_name = serializers.CharField(write_only=True, required=False, allow_blank=False)

    class Meta:
        model = Transaction
        fields = [
            'id','owner','amount','type',
            'payment_method','payment_method_name',
            'subcategory','subcategory_name','subcategory_label',
            'description','transaction_date',
            'receipt_file','receipt_original_name','receipt_thumbnail',
            'receipt_download_url','receipt_thumbnail_url',
            'created_at','updated_at','is_active'
        ]
        read_only_fields = ['owner','receipt_original_name','receipt_thumbnail','created_at','updated_at','is_active',
                            'payment_method_name','subcategory_label']

    def validate_transaction_date(self, value):
        if value > timezone.now():
            raise serializers.ValidationError("Future dates are not allowed.")
        return value

    def validate_receipt_file(self, value):
        if value:
            try:
                validate_image_file(value)
            except ValueError as e:
                raise serializers.ValidationError(str(e))
        return value

    def get_receipt_download_url(self, obj):
        if obj.receipt_file:
            return reverse('transactions-transaction-receipt', kwargs={'pk': obj.pk})
        return None

    def get_receipt_thumbnail_url(self, obj):
        if obj.receipt_thumbnail:
            request = self.context.get('request')
            url = obj.receipt_thumbnail.url
            return request.build_absolute_uri(url) if request else url
        return None

    def _resolve_subcategory(self, validated_data):
        # POST sırasında istenen "subcategory_name" varsa bul yoksa oluştur
        name = self.initial_data.get('subcategory_name') or validated_data.get('subcategory_name')
        if name:
            norm = normalize_subcategory_name(name)
            subcat, _ = Subcategory.objects.get_or_create(normalized_name=norm, defaults={'name': name})
            validated_data['subcategory'] = subcat
        return validated_data

    @db_transaction.atomic
    def create(self, validated_data):
        request = self.context['request']
        validated_data.pop('subcategory_name', None)
        validated_data = self._resolve_subcategory(validated_data)
        instance = Transaction(**validated_data)
        instance.owner = request.user
        instance.created_by = request.user
        instance.updated_by = request.user
        instance.save()
        return instance

    @db_transaction.atomic
    def update(self, instance, validated_data):
        request = self.context['request']
        validated_data.pop('subcategory_name', None)
        validated_data = self._resolve_subcategory(validated_data)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.updated_by = request.user
        instance.save()
        return instance

# Bu serializer seti, PaymentMethod, Subcategory ve Transaction modelleri için
# gerekli alanları ve doğrulamaları içerir. TransactionSerializer,
# işlem oluşturma ve güncelleme sırasında alt kategori adını işleyebilir.
# Ayrıca, makbuz dosyası ve küçük resim URL'lerini sağlar.
# İşlem oluşturulurken ve güncellenirken, işlemi yapan kullanıcı otomatik olarak atanır.
