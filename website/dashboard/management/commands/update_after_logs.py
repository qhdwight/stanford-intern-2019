from django.core.management.base import BaseCommand
from django.db import transaction

from dashboard.query import START_TIME, END_TIME, INTERVAL_DELTA, GET_REQUESTS
from dashboard.models import QueryCountAtTime


class Command(BaseCommand):
    help = 'Post-processes log data to find other information'

    def handle(self, *args, **options):
        print('Starting post-process')
        time = START_TIME
        with transaction.atomic():
            while time < END_TIME:
                count = GET_REQUESTS.filter(time__range=(time - INTERVAL_DELTA / 2, time + INTERVAL_DELTA / 2)).count()
                time += INTERVAL_DELTA
                at_time = QueryCountAtTime.objects.filter(time=time)
                if at_time.exists():
                    print(f'Updated query count reading at time {time} with count {count}')
                    at_time.update(count=count)
                else:
                    print(f'Created query count reading at time {time} with count {count}')
                    QueryCountAtTime.objects.create(time=time, count=count)
        print('Finished post-process')
