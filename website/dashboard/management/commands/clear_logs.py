from django.core.management.base import BaseCommand

from dashboard.models import Log


class Command(BaseCommand):
    help = 'Clear all logs in the database'

    def handle(self, *args, **options):
        Log.objects.all().delete()
