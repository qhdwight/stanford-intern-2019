import json
from datetime import datetime

import requests
from django.core.management.base import BaseCommand
from tqdm import tqdm

from dashboard.models import Item, Award, Experiment, Lab


class Command(BaseCommand):
    help = 'Post-processes log data to find other information'

    def add_arguments(self, parser):
        parser.add_argument(
            '--items',
            nargs='?',
            const='items.json',
            type=str,
        )
        parser.add_argument(
            '--experiments',
            nargs='?',
            const='experiments.json',
            type=str,
        )

    def handle(self, *args, **options):
        item_fields = [
            'assay_title',
            's3_uri',
            'file_format',
            'file_format_type',
            'date_created',
            'dataset',
            'award.project',
            'award.name',
            'award.rfa',
            'award.status',
            'award.pi.title',
            'award.pi.lab.name',
        ]
        experiment_fields = [
            'assay_title',
            'assay_term_name',
            'date_released',
        ]

        def add_fields(base_url, fields):
            for field in fields:
                base_url += f'&field={field}'
            return base_url

        # Load items JSON
        if options['items']:
            item_json_file_name = options['items']
            print(f'Loading items from file {item_json_file_name}')
            with open(item_json_file_name, 'r') as items_json_file:
                items_results = json.load(items_json_file)['@graph']
        else:
            items_url = add_fields('https://www.encodeproject.org/search/?type=File&format=json&limit=all', item_fields)
            print(f'Using item url: {items_url}')
            items_results = requests.get(items_url).json()['@graph']

        # Load experiments JSON
        if options['experiments']:
            experiments_json_file_name = options['experiments']
            print(f'Loading experiments from file {experiments_json_file_name}')
            with open(experiments_json_file_name, 'r') as experiments_json_file:
                experiment_results = json.load(experiments_json_file)['@graph']
        else:
            experiment_url = add_fields('https://www.encodeproject.org/search/?type=Experiment&format=json&limit=all',
                                        experiment_fields)
            print(f'Using experiment url: {experiment_url}')
            experiment_results = requests.get(experiment_url).json()['@graph']
        experiment_result_dict = {}
        for result in tqdm(experiment_results):
            experiment_result_dict[result['@id'].split('/')[2]] = result

        db_items = []
        for item_json in tqdm(items_results):
            if 's3_uri' not in item_json:
                tqdm.write(f'[Warning] No S3 key for {item_json["@id"].split("/")[2]}')
                continue
            s3_uri_split = item_json['s3_uri'].split('/')
            item_name = s3_uri_split[-1]
            s3_key = '/'.join(s3_uri_split[3:])
            file_format = item_json.get('file_format')
            file_type = item_json.get('file_format_type')
            date_uploaded = datetime.strptime(item_json['date_created'].split('T')[0], '%Y-%m-%d')
            # Experiment information
            data_set_type = item_json['dataset'].split('/')[1]
            data_set_name = item_json['dataset'].split('/')[2]
            if data_set_type == 'experiments':
                experiment_json = experiment_result_dict.get(data_set_name)
                assay_title = experiment_json.get('assay_title') if experiment_json else None
                assay_term_name = experiment_json.get('assay_term_name') if experiment_json else None
                date_released = experiment_json.get('date_released') if experiment_json else None
                experiment, _ = Experiment.objects.get_or_create(name=data_set_name, defaults={
                    'name': data_set_name,
                    'date_released': date_released,
                    'assay_title': assay_title,
                    'assay_term_name': assay_term_name,
                })
            else:
                experiment = None
            # Getting award, lab, and PI information from JSON
            award = item_json.get('award')
            award_name = award.get('name') if award else None
            pi = award.get('pi') if award else None
            lab = pi.get('lab') if pi else None
            lab_name = lab.get('name') if lab else None
            project = award.get('project') if award else None
            rfa = award.get('rfa') if award else None
            award_status = award.get('status') if award else None
            pi_name = pi.get('title') if pi else None
            # Award
            if award_name:
                db_award, _ = Award.objects.get_or_create(name=award_name, defaults={
                    'name': award_name,
                    'pi': pi_name,
                    'project': project,
                    'rfa': rfa,
                    'status': award_status
                })
            else:
                db_award = None
            if lab_name:
                # Lab
                db_lab, _ = Lab.objects.get_or_create(name=lab_name, defaults={
                    'name': lab_name
                })
            else:
                db_lab = None
            # Item
            db_item = Item.objects.get(s3_key=s3_key)
            db_item.lab = db_lab
            db_item.award = db_award
            db_items.append(db_item)
            # Item.objects.get(s3_key=s3_key).update(
            #     name=item_name,
            #     dataset=data_set_name,
            #     dataset_type=data_set_type,
            #     experiment=experiment,
            #     file_format=file_format,
            #     file_type=file_type,
            #     award=db_award,
            #     lab=db_lab,
            #     date_uploaded=date_uploaded
            # ))

        Item.objects.bulk_update(db_items, ['lab', 'award'], batch_size=400)
        print('Done! Hopefully...')
