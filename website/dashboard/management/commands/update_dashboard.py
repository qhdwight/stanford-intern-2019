from datetime import datetime, timedelta

import requests
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from dashboard.models import Log, MostQueried, Item, get_item_name, get_encode_url, IntervalQueryCount

GET_JSON_HEADERS = {'accept': 'application/json'}


def get_or_create_item(s3_key):
    if Item.objects.filter(s3_key=s3_key).exists():
        return Item.objects.get(s3_key=s3_key)
    else:
        name = get_item_name(s3_key)
        url = f'{get_encode_url(name)}/?format=json'
        result = requests.get(url, headers=GET_JSON_HEADERS).json()
        experiment = result['dataset'].split('/')[2]
        experiment_url = f'{get_encode_url(experiment)}/?format=json'
        experiment_result = requests.get(experiment_url, headers=GET_JSON_HEADERS).json()
        assay_title = experiment_result['assay_title']
        print(
            f'Creating item object with key {s3_key}, name {name}, experiment {experiment}, and assay title {assay_title}')
        return Item.objects.create(
            s3_key=s3_key,
            experiment=experiment,
            assay_title=assay_title
        )


class Command(BaseCommand):
    help = 'Builds information for the dashboard page'

    def handle(self, *args, **options):
        print('Updating dashboard...')
        print('Finding most queried items via logs...')
        get_requests = Log.objects.filter(operation='REST.GET.OBJECT')
        # See which objects are queried the most
        most_queried_s3_keys = get_requests \
            .values('s3_key', 'ip_address') \
            .distinct() \
            .annotate(count=Count('s3_key')) \
            .order_by('-count')
        limited_most_queried = most_queried_s3_keys[:32]
        with transaction.atomic():
            for most_queried in limited_most_queried:
                item = get_or_create_item(most_queried['s3_key'])
                count = most_queried['count']
                item_query = MostQueried.objects.filter(item=item)
                if item_query.exists():
                    print(f'Updated queried item with name {item.s3_key} with count {count}')
                    item_query.update(count=count)
                else:
                    print(f'Created most queried with name {item.s3_key} with count {count}')
                    MostQueried.objects.create(item=item, count=count)
        print('Finished updating most queried items!')
        # See which experiments are most valuable

        # See how many requests we got at different times of the year
        start_time = datetime(2019, 3, 1, tzinfo=timezone.get_current_timezone())
        end_time = timezone.now()
        interval = timedelta(4)
        time = start_time
        with transaction.atomic():
            while time < end_time:
                count = Log.objects.filter(time__range=(time - interval / 2, time + interval / 2)).count()
                time += interval
                time_query = IntervalQueryCount.objects.filter(time=time)
                if time_query.exists():
                    print(f'Updated queried item with time {time} with count {count}')
                    time_query.update(count=count)
                else:
                    print(f'Created most queried with time {time} with count {count}')
                    IntervalQueryCount.objects.create(time=time, count=count)
        print('Finished updating interval query counts')
        print('Finished updating dashboard!')
