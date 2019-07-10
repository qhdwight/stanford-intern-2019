import matplotlib.pyplot as plt
import pandas as pd
from django.core.management.base import BaseCommand
from tqdm import tqdm

from dashboard.models import ExperimentItem


class Command(BaseCommand):
    help = 'FIll in later'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dbreset',
            action='store_true',
            help='Resets all of the models in the database and re-adds them from the file'
        )

    def handle(self, *args, **options):
        if options['dbreset']:
            item_index = 0
            with open('analyze_files.txt', 'r') as file:
                experiment_items = []
                item_index += 1
                ExperimentItem.objects.all().delete()
                item_names = [item_name.split('/')[6].replace('\n', '') for item_name in file.readlines()[1:]]
                for item_name in tqdm(item_names):
                    experiment_items.append(ExperimentItem(name=item_name))
                ExperimentItem.objects.bulk_create(experiment_items, batch_size=500)

        # logs = (Log.objects
        #         .filter(operation='REST.GET.OBJECT')
        #         .filter(item_name__in=ExperimentItem.objects.values_list('name', flat=True))
        #         .exclude(requester='arn:aws:iam::265191883777:user/admin2')
        #         )
        # distinct_logs = logs.values('s3_key', 'ip_address').distinct()
        # rows = []
        # for log in tqdm(distinct_logs.iterator(), total=distinct_logs.count()):
        #     duplicate_rows = logs.filter(s3_key=log['s3_key'], ip_address=log['ip_address'])
        #     first = duplicate_rows.order_by('time').first()
        #     created = pd.to_datetime('/'.join(first.s3_key.split('/')[:3]), format='%Y/%m/%d')
        #     accessed = pd.to_datetime(first.time.date())
        #     rows.append([created, accessed, accessed - created])
        # log_pd = pd.DataFrame(rows, columns=['created', 'accessed', 'delta'])
        log_pd = pd.read_csv('access_creation_dates.csv', parse_dates=['created', 'accessed'], date_parser=pd.to_datetime)
        log_pd = log_pd.sort_values(by='accessed')
        log_pd.to_csv('access_creation_dates.csv', index=False)
        created_pd = log_pd[['created']]
        created_pd.groupby(created_pd['created'].dt.year).count().plot(kind='bar')
        plt.show()
