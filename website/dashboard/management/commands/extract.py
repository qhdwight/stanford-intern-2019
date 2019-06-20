from django.core.management.base import BaseCommand

from dashboard.management.extractor import extract_from_local_into_database


class Command(BaseCommand):
    help = 'Grabs local logging data and puts it into the database'

    def handle(self, *args, **options):
        extract_from_local_into_database()
