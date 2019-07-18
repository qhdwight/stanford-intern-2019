import json
import multiprocessing as mp
import os
from datetime import datetime

import gc
import numpy as np
import pandas as pd
import requests
from django.core.management.base import BaseCommand
from s3logparse import s3logparse
from tqdm import tqdm

from dashboard.models import Log, Experiment, Award, Lab, Item

ITEM_FIELDS = [
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
EXPERIMENT_FIELDS = [
    'assay_title',
    'assay_term_name',
    'date_released',
]
LOGS_DIR = 's3_logs'


def get_db_log_from_log_line(log_file_name, log):
    # TODO compress somehow?
    return Log(
        key_name=log_file_name,
        bucket=log.bucket,
        time=log.timestamp,
        ip_address=log.remote_ip,
        requester=log.requester,
        request_id=log.request_id,
        operation=log.operation,
        s3_key=log.s3_key,
        request_uri=log.request_uri,
        http_status=log.status_code,
        error_code=log.error_code,
        bytes_sent=log.bytes_sent,
        object_size=log.object_size,
        total_time=log.total_time,
        turn_around_time=log.turn_around_time,
        referrer=log.referrer,
        user_agent=log.user_agent,
        version_id=log.version_id
    )


def process_chunk(log_file_names, existing_request_ids, items_df):
    db_logs = []
    for log_file_name in log_file_names:
        with open(f'{LOGS_DIR}/{log_file_name}', 'r') as log_file:
            for log in s3logparse.parse_log_lines(log_file.readlines()):
                # Skip if we have already pulled this log file. Note this cancels out of the entire file.
                # Request IDs are unique.
                if log.operation == 'REST.COPY.PART' or (existing_request_ids == log.request_id).any():
                    break
                if log.operation != 'REST.GET.OBJECT':
                    continue
                # Converting S3 log parse object to django object.
                # TODO there are two conversions when one could do.
                #  Maybe the log parse library should be ditched.
                db_log = get_db_log_from_log_line(log_file_name, log)
                try:
                    db_log.item_id = items_df.loc[db_log.s3_key].pk
                except KeyError:
                    pass
                db_logs.append(db_log)
    return db_logs


class Command(BaseCommand):
    help = 'Syncs the database with the latest logs'

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
        parser.add_argument(
            '--skip',
            action='store_true'
        )

    @staticmethod
    def add_fields_to_search(base_url, fields):
        for field in fields:
            base_url += f'&field={field}'
        return base_url

    @staticmethod
    def get_json_from_url(option, object_type, fields):
        file_name = option
        if file_name and os.path.exists(file_name):
            print(f'Loading from file {file_name}')
            with open(file_name, 'r') as file:
                json_result = json.load(file)
        else:
            url = Command.add_fields_to_search(
                f'https://www.encodeproject.org/search/?type={object_type}&format=json&limit=all', fields)
            print(f'Using url: {url}')
            json_result = requests.get(url).json()
            if file_name:
                print(f'Saving to file {file_name}')
                with open(file_name, 'w') as file:
                    json.dump(json_result, file)
        return json_result['@graph']

    @staticmethod
    def add_items_and_experiments(items_result, experiment_result_dict):
        for item_json in tqdm(items_result):
            if 's3_uri' not in item_json:
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
            Item.objects.get_or_create({
                's3_key': s3_key,
                'name': item_name,
                'dataset': data_set_name,
                'dataset_type': data_set_type,
                'experiment': experiment,
                'file_format': file_format,
                'file_type': file_type,
                'award': db_award,
                'lab': db_lab,
                'date_uploaded': date_uploaded
            }, s3_key=s3_key)

    def on_processed_chunk(self, db_logs):
        Log.objects.bulk_create(db_logs)
        self.progress_bar.update()
        gc.collect()

    def handle(self, *args, **options):
        if options['skip']:
            print('Skipping synchronization of items and experiments...')
        else:
            print('Getting items and experiments...')
            # Add items and experiments into the database so we can link logs to them
            item_results = self.get_json_from_url(options['items'], 'File', ITEM_FIELDS)
            experiment_json = self.get_json_from_url(options['experiments'], 'Experiment', EXPERIMENT_FIELDS)
            experiment_result_dict = {}
            for result in experiment_json:
                experiment_result_dict[result['@id'].split('/')[2]] = result
            print('Adding items and experiments...')
            self.add_items_and_experiments(item_results, experiment_result_dict)

        print('Updating log files from locals...')
        existing_request_ids = pd.Series(Log.objects.values_list('request_id', flat=True))
        items_df = pd.DataFrame(Item.objects.values_list('pk', flat=True),
                                Item.objects.values_list('s3_key', flat=True),
                                columns=['pk'])

        # Looping through each actual log file on disk. They correspond to the time at which they were generated.
        all_file_names = os.listdir(LOGS_DIR)
        file_count = len(all_file_names)

        chunk_count = max(file_count / 5000, 1)
        self.progress_bar = tqdm(total=chunk_count, unit='file', desc='Files Processed')
        log_file_name_chunks = np.array_split(all_file_names, chunk_count)
        pool = mp.Pool(processes=mp.cpu_count())
        start = datetime.now()
        for log_file_name_chunk in log_file_name_chunks:
            pool.apply_async(
                process_chunk,
                args=(log_file_name_chunk, existing_request_ids, items_df),
                callback=self.on_processed_chunk
            )
        pool.close()
        pool.join()

        print(f'Done in {datetime.now() - start}!')
