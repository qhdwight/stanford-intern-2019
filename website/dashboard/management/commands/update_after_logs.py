from django.core.management.base import BaseCommand
from django.db import transaction

from dashboard.models import QueryCountAtTime
from dashboard.query import START_TIME, END_TIME, INTERVAL_DELTA, GET_REQUESTS


class Command(BaseCommand):
    help = 'Post-processes log data to find other information'

    def handle(self, *args, **options):
        print('Starting post-process')
        time = START_TIME
        with transaction.atomic():
            # Iterate in chunks across database and sum up request count for evenly sized intervals
            while time < END_TIME:
                # Notice we filter data to left and right of the time
                count = GET_REQUESTS.filter(time__range=(time - INTERVAL_DELTA / 2, time + INTERVAL_DELTA / 2)).count()
                time += INTERVAL_DELTA
                at_time = QueryCountAtTime.objects.filter(time=time)
                # If the reading already exists for this time update it, or else create a new object
                if at_time.exists():
                    print(f'Updated query count reading at time {time} with count {count}')
                    at_time.update(count=count)
                else:
                    print(f'Created query count reading at time {time} with count {count}')
                    QueryCountAtTime.objects.create(time=time, count=count)
        print('Finished post-process')
