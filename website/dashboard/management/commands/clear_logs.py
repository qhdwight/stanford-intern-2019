from django.core.management.base import BaseCommand, CommandError

from dashboard.management.extractor import extract_from_local_into_database

from dashboard.models import Log


class Command(BaseCommand):
    help = 'Clear all logs in the database'
    
    def handle(self, *args, **options):
        Log.objects.all().delete()
