from django.db import migrations

SQL = "CREATE UNIQUE INDEX IF NOT EXISTS auth_user_email_ci_uniq ON auth_user (LOWER(email));"
REVERSE_SQL = "DROP INDEX IF EXISTS auth_user_email_ci_uniq;"

class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0002_seed_payment_methods'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunSQL(SQL, REVERSE_SQL),
    ]

# Bu migration dosyası, auth_user tablosundaki email alanı için büyük/küçük harf duyarsız (case-insensitive) benzersiz bir indeks oluşturur.
# Bu sayede, kullanıcıların aynı email adresini farklı büyük/küçük harf kombinasyonlarıyla kaydetmeleri engellenir.