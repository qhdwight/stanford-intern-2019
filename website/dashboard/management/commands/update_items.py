import requests
from django.core.management.base import BaseCommand
from django.db import transaction

from dashboard.models import Item
from query import get_most_queried_s3_keys
from views import get_item_name, get_encode_url

MOST_QUERIED_COUNT = 32

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
        print(f'Creating item {name}, key {s3_key}, experiment {experiment}, and assay {assay_title}')
        return Item.objects.create(
            name=name,
            s3_key=s3_key,
            experiment=experiment,
            assay_title=assay_title
        )


class Command(BaseCommand):
    help = 'Updates the most queried items'

    def handle(self, *args, **options):
        print('Updating dashboard...')
        print('Finding most queried items via logs...')
        limited_most_queried = get_most_queried_s3_keys()[:MOST_QUERIED_COUNT]
        with transaction.atomic():
            for most_queried in limited_most_queried:
                get_or_create_item(most_queried['s3_key'])
        print('Finished updating most queried items!')
