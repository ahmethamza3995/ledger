from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from transactions.models import Transaction

class Command(BaseCommand):
    help = "(Admin, Manager, User) oluştur ve yetki ata."

    def handle(self, *args, **options):
        # ContentType -> Transaction model
        ct = ContentType.objects.get_for_model(Transaction)

        # Grubun var olduğundan emin ol
        admin_g, _ = Group.objects.get_or_create(name='Admin')
        manager_g, _ = Group.objects.get_or_create(name='Manager')
        user_g, _ = Group.objects.get_or_create(name='User')

        # Base codename -> Transaction model için
        codenames_all = Permission.objects.filter(content_type=ct).values_list('codename', flat=True)
        codenames_all = set(codenames_all)

        # Built-in model parametreleri
        add = Permission.objects.get(content_type=ct, codename='add_transaction')
        change = Permission.objects.get(content_type=ct, codename='change_transaction')
        delete = Permission.objects.get(content_type=ct, codename='delete_transaction')
        view = Permission.objects.get(content_type=ct, codename='view_transaction')

        # Custom parametreler (Transaction.Meta.permissions içinde tanımlı)
        can_restore = Permission.objects.get(content_type=ct, codename='can_restore_transaction')
        can_export = Permission.objects.get(content_type=ct, codename='can_export_transactions')

        # Admin: Bütün izinler (custom olanlar dahil)
        admin_perms = Permission.objects.filter(content_type=ct)
        admin_g.permissions.set(admin_perms)

        # Manager: CRUD + view + export
        manager_g.permissions.set([add, change, delete, view, can_export])

        # User: CRUD + view
        user_g.permissions.set([add, change, delete, view])

        self.stdout.write(self.style.SUCCESS('Roles and permissions bootstrapped:'))
        self.stdout.write(f'  Admin  -> {len(admin_perms)} perms')
        self.stdout.write(f'  Manager-> {len(manager_g.permissions.all())} perms (CRUD + export)')
        self.stdout.write(f'  User   -> {len(user_g.permissions.all())} perms (CRUD only)')

# Bu komut, Admin, Manager ve User olmak üzere üç rol oluşturur ve Transaction modeli üzerindeki izinleri atar.
# Admin rolü, tüm izinlere sahiptir (CRUD + view + custom).
# Manager rolü, CRUD işlemleri ve görüntüleme ile birlikte dışa aktarma iznine sahiptir (restore izni yok).
# User rolü ise sadece CRUD işlemleri ve görüntüleme iznine sahiptir (export ve restore izinleri yok).
# Bu sayede, farklı kullanıcı rollerine göre erişim kontrolü sağlanabilir ve güvenlik artırılabilir.
