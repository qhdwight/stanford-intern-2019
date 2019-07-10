import matplotlib.pyplot as plt
import pandas as pd
from django.core.management.base import BaseCommand
from tqdm import tqdm

from dashboard.models import ExperimentItem, Log


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
            nargs='+',
            type=str,
            help='Reads accessed and uploaded times to analyze from disk to save processing time'
        )

    def handle(self, *args, **options):
        if options['items']:
            ExperimentItem.objects.all().delete()
            for file_name in options['items']:
                item_index = 0
                with open(file_name, 'r') as file:
                    experiment_items = []
                    item_index += 1
                    # First line is a header so ignore. 6th index split item happens to be file name with extension.
                    item_names = [item_name.split('/')[6].replace('\n', '') for item_name in file.readlines()[1:]]
                    for item_name in tqdm(item_names):
                        experiment_items.append(ExperimentItem(name=item_name))
                    # Bulk create is key here, saves a lot of time by batching insertion into database.
                    ExperimentItem.objects.bulk_create(experiment_items, batch_size=500)
        # Logs that are from the specific experiment, people downloading files from that exact one.
        # Also only raw downloads no head requests. Also exclude any of developer downloaders.
        logs = (Log.objects
                .filter(operation='REST.GET.OBJECT')
                .filter(item_name__in=ExperimentItem.objects.values_list('name', flat=True))
                .exclude(requester='arn:aws:iam::265191883777:user/admin2'))
        # A distinct s3 key (file name in Amazon) and ip address represent a unique download.
        # The goal is to filter out when the same user downloads a file multiple times.
        distinct_logs = logs.values('s3_key', 'ip_address').distinct()
        if options['csv']:
            log_pd = pd.DataFrame()
            for file_name in options['csv']:
                read = pd.read_csv(file_name, parse_dates=['created', 'accessed'], date_parser=pd.to_datetime)
                log_pd = log_pd.append(read)
        else:
            rows = []
            for log in tqdm(distinct_logs.iterator(), total=distinct_logs.count()):
                # There will be multiple rows with the name key and ip address most of the time.
                # They will have different download times so just take the first one.
                # TODO maybe take average in future? sqlite does not support however
                duplicate_rows = logs.filter(s3_key=log['s3_key'], ip_address=log['ip_address'])
                first = duplicate_rows.order_by('time').first()
                # Pandas likes it when the the datetime is in their own type.
                # We are taking the date of creation to be that of what is in the s3 key so we do not have to do
                # additional querying to the encode server.
                created = pd.to_datetime('/'.join(first.s3_key.split('/')[:3]), format='%Y/%m/%d')
                accessed = pd.to_datetime(first.time.date())
                rows.append([created, accessed, accessed - created])
            log_pd = pd.DataFrame(rows, columns=['created', 'accessed', 'delta'])
        log_pd = log_pd.sort_values(by='accessed')
        log_pd.to_csv('access_creation_dates.csv', index=False)
        # Takes the created column
        created_pd = log_pd[['created']]
        # Create bar chart where how many times files of different years created are downloaded.
        ax = created_pd.groupby(created_pd['created'].dt.year).count().plot(kind='bar')
        ax.set(xlabel='Date File Uploaded', ylabel='Number of Total Downloads')
        plt.show()
