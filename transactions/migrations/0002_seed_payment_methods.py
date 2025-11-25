from django.db import migrations

def seed_methods(apps, schema_editor):
    PaymentMethod = apps.get_model('transactions', 'PaymentMethod')
    for name in ['Nakit', 'IBAN', 'EFT', 'Havale', 'Kredi Kartı', 'POS', 'Çek', 'Senet']:
        PaymentMethod.objects.get_or_create(name=name)

class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_methods, migrations.RunPython.noop),
    ]

# Bu migration dosyası, PaymentMethod modeline başlangıç verileri ekler.
# 'Nakit', 'IBAN', 'EFT', 'Havale', 'Kredi Kartı', 'POS', 'Çek' ve 'Senet' gibi yaygın ödeme yöntemlerini içerir.
# Bu sayede, uygulama ilk kurulduğunda kullanıcıların ödeme yöntemlerini manuel olarak eklemesi gerekmez.