from django.core.management.base import BaseCommand
from django.utils import timezone

from plataforma_de_servicos.cart.models import ReservaEstoque


class Command(BaseCommand):
    help = 'Remove reservas de estoque expiradas'

    def handle(self, *args, **options):
        count, _ = ReservaEstoque.objects.filter(
            expires_at__lt=timezone.now()
        ).delete()
        
        self.stdout.write(
            self.style.SUCCESS(f'Removidas {count} reservas expiradas')
        )