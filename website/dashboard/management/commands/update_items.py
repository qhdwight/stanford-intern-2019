from datetime import datetime

import requests
from django.core.management.base import BaseCommand
from tqdm import tqdm

from models import Item, Award, Experiment, Lab


class Command(BaseCommand):
    help = 'Post-processes log data to find other information'

    # def add_arguments(self, parser):
    #     parser.add_argument(
    #         '--dataset',
    #         nargs=1,
    #         type=str,
    #     )

    def handle(self, *args, **options):
        with open('analyze_files.txt', 'r') as file:
            item_names = [item_name.split('/')[6].replace('\n', '') for item_name in file.readlines()[1:]]
        db_items = []
        for item_name in tqdm(item_names):
            # File information
            file_url = f'https://www.encodeproject.org/{item_name}/?format=json'
            file_result = requests.get(file_url).json()
            s3_uri = file_result.get('s3_uri')
            s3_key = '/'.join(s3_uri.split('/')[4:]) if s3_uri else None
            file_format = file_result.get('file_format')
            file_type = file_result.get('file_format_type')
            raw_date_uploaded = file_result.gt('date_created')
            date_uploaded = datetime.strptime(raw_date_uploaded, '%Y-%m-%d') if raw_date_uploaded else None
            # Experiment information
            raw_experiment = file_result.get('dataset')
            experiment_name = raw_experiment.split('/')[2] if raw_experiment else None
            experiment_url = f'https://www.encodeproject.org/{experiment_name}/?format=json'
            experiment_result = requests.get(experiment_url).json()
            assay_title = experiment_result.get('assay_title')
            assay_term_name = experiment_result.get('assay_term_name')
            date_released = experiment_result.get('date_released')
            award = experiment_result.get('award')
            award_name = award.get('name') if award else None
            pi = award.get('pi') if award else None
            lab = pi.get('lab') if pi else None
            lab_name = lab.get('name') if lab else None
            project = award.get('project') if award else None
            rfa = award.get('rfa') if award else None
            award_status = award.get('status') if award else None
            # Award
            award = Award.objects.get_or_create(name=award_name, defaults={
                'name': award_name,
                'pi': pi,
                'project': project,
                'rfa': rfa,
                'status': award_status
            })
            # Experiment
            experiment = Experiment.objects.get_or_create(name=experiment_name, defaults={
                'name': experiment_name,
                'date_released': date_released,
                'assay_title': assay_title,
                'assay_term_name': assay_term_name
            })
            # Lab
            lab = Lab.objects.get_or_create(name=lab_name, defaults={
                'lab_name': lab_name
            })
            db_items.append(Item(
                s3_key=s3_key,
                name=item_name,
                experiment=experiment,
                file_Format=file_format,
                file_type=file_type,
                award=award,
                lab=lab,
                date_uploaded=date_uploaded
            ))
        Item.objects.bulk_create(db_items, batch_size=500)
