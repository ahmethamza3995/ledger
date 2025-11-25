from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentMethod',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=50, unique=True)),
                ('is_active', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='Subcategory',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=60)),
                ('normalized_name', models.CharField(max_length=80, unique=True)),
                ('is_active', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('type', models.CharField(choices=[('INCOME', 'Income'), ('EXPENSE', 'Expense')], max_length=7)),
                ('description', models.CharField(blank=True, max_length=60)),
                ('transaction_date', models.DateTimeField()),
                ('receipt_file', models.FileField(blank=True, null=True, upload_to='receipts/tmp/')),
                ('receipt_original_name', models.CharField(blank=True, max_length=255)),
                ('receipt_thumbnail', models.ImageField(blank=True, null=True, upload_to='receipts/thumbnails/')),
                ('is_active', models.BooleanField(default=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='auth.user')),
                ('deleted_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='deleted_transactions', to='auth.user')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_transactions', to='auth.user')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='updated_transactions', to='auth.user')),
                ('payment_method', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='transactions', to='transactions.paymentmethod')),
                ('subcategory', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='transactions', to='transactions.subcategory')),
            ],
            options={
                'ordering': ['-transaction_date', '-id'],
                'permissions': (('can_restore_transaction', 'Can restore transaction'), ('can_export_transactions', 'Can export transactions')),
            },
        ),
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='audit_logs', to='auth.user')),
                ('action', models.CharField(choices=[('LOGIN', 'Login'), ('CREATE', 'Create'), ('UPDATE', 'Update'), ('SOFT_DELETE', 'Soft delete'), ('RESTORE', 'Restore'), ('HARD_DELETE', 'Hard delete'), ('EXPORT', 'Export')], max_length=20)),
                ('object_type', models.CharField(max_length=60)),
                ('object_id', models.CharField(max_length=64)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('metadata', models.JSONField(blank=True, default=dict)),
            ],
        ),
    ]

# Bu migration dosyası, transactions uygulamasının ilk migration dosyasıdır.
# PaymentMethod, Subcategory, Transaction ve AuditLog modellerini oluşturur.
# Her modelin alanları ve ilişkileri belirtilmiştir.
# Transaction modeli, kullanıcı işlemlerini (gelir/gider) saklar ve soft delete özelliğine sahiptir.
# AuditLog modeli, kullanıcı aktivitelerini izlemek için kullanılır.
# Bu sayede, sistemdeki kullanıcı aktiviteleri izlenebilir ve gerektiğinde denetlenebilir.
# İleride başka migration dosyaları eklenerek, modellerde değişiklikler yapılabilir veya yeni modeller eklenebilir.
