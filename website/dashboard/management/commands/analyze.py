import os

import matplotlib.pyplot as plt
import pandas as pd
from django.core.management.base import BaseCommand
from tqdm import tqdm

from dashboard.models import AnalysisLabItem, Log

DEFAULT_FILE = 'access_creation_dates.csv'


class Command(BaseCommand):
    help = 'Analyzes a specific experiment'

    def add_arguments(self, parser):
        parser.add_argument(
            '--items',
            nargs='+',
            type=str,
            help='Resets all of the models in the database and re-adds them from the file'
        )
        parser.add_argument(
            '--csv',
            nargs='?',
            const=DEFAULT_FILE,
            type=str,
            help='Reads accessed and uploaded times to analyze from disk to save processing time'
        )
        parser.add_argument(
            '--save',
            nargs='?',
            const=DEFAULT_FILE,
            type=str,
            help='Read from database and save to given CSV file'
        )
        parser.add_argument(
            '--noplot',
            action='store_true'
        )

    @staticmethod
    def get_df_from_db():
        # Logs that are from the specific experiment, people downloading files from that exact one.
        # Also only raw downloads no head requests. Also exclude any of developer downloaders.
        logs = (Log.objects
                .filter(operation='REST.GET.OBJECT')
                .filter(item_name__in=AnalysisLabItem.objects.values_list('name', flat=True))
                .exclude(requester='arn:aws:iam::265191883777:user/admin2'))
        # A distinct s3 key (file name in Amazon) and ip address represent a unique download.
        # The goal is to filter out when the same user downloads a file multiple times.
        rows = []
        for log in tqdm(logs.iterator(), total=logs.count()):
            created = pd.to_datetime('/'.join(log.s3_key.split('/')[:3]), format='%Y/%m/%d')
            accessed = pd.to_datetime(log.time.date())
            rows.append([log.s3_key, created, accessed, accessed - created])
        # distinct_logs = logs.values_list('s3_key', 'ip_address').distinct()
        # rows = []
        # for s3_key, ip_address in tqdm(distinct_logs.iterator(), total=distinct_logs.count()):
        #     # There will be multiple rows with the name key and ip address most of the time.
        #     # They will have different download times so just take the first one.
        #     # TODO maybe take average in future? sqlite does not support however
        #     duplicate_rows = logs.filter(s3_key=s3_key, ip_address=ip_address)
        #     first = duplicate_rows.order_by('time').first()
        #     # Pandas likes it when the the datetime is in their own type.
        #     # We are taking the date of creation to be that of what is in the s3 key so we do not have to do
        #     # additional querying to the encode server.
        #     created = pd.to_datetime('/'.join(first.s3_key.split('/')[:3]), format='%Y/%m/%d')
        #     accessed = pd.to_datetime(first.time.date())
        #     rows.append([s3_key, created, accessed, accessed - created])
        return pd.DataFrame(rows, columns=['s3_key', 'created', 'accessed', 'delta'])

    def handle(self, *args, **options):
        if options['items']:
            AnalysisLabItem.objects.all().delete()
            for file_name in options['items']:
                item_index = 0
                with open(file_name, 'r') as file:
                    print(f'Reading from file {file_name}')
                    experiment_items = []
                    item_index += 1
                    # First line is a header so ignore. 6th index split item happens to be file name with extension.
                    item_names = [item_name.split('/')[6].replace('\n', '') for item_name in file.readlines()[1:]]
                    for item_name in tqdm(item_names):
                        experiment_items.append(AnalysisLabItem(name=item_name))
                    # Bulk create is key here, saves a lot of time by batching insertion into database.
                    AnalysisLabItem.objects.bulk_create(experiment_items, batch_size=500)
        if options['csv']:
            log_df = pd.DataFrame()
            file_name = options['csv']
            if os.path.exists(file_name):
                print(f'Reading from CSV file {file_name}')
                read = pd.read_csv(file_name, parse_dates=['created', 'accessed'], date_parser=pd.to_datetime)
                log_df = log_df.append(read)
            else:
                print(f'[Warning] File not found: {file_name}')
        else:
            log_df = self.get_df_from_db()
        if options['save']:
            file_name = options['save']
            print(f'Saving to {file_name}')
            log_df.to_csv(file_name, index=False)
        # still_used = log_df.loc[log_df['created'].dt.year == 2010]
        log_df = log_df.sort_values(by='accessed')
        # Takes the created column
        created_df = log_df[['created']]
        # Create bar chart where how many times files of different years created are downloaded.
        if options['noplot']:
            return
        ax = created_df.groupby(created_df['created'].dt.year).count().plot(kind='bar')
        ax.set(xlabel='Date File Uploaded', ylabel='Number of Total Downloads',
               title='Downloads Since April based on File Upload Time')
        plt.show()
