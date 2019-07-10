from django.core.management.base import BaseCommand
from tqdm import tqdm

from dashboard.models import QueryCountAtTime
from dashboard.query import calculate_query_count_intervals, BERNSTEIN_EXPERIMENT_FILTER_KWARGS


class Command(BaseCommand):
    help = 'Post-processes log data to find other information'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dataset',
            nargs=1,
            type=str,
        )

    def handle(self, *args, **options):
        data_set = options['dataset'][0] or 'all'
        print(f'Starting post-process for {data_set}')
        filter_args = BERNSTEIN_EXPERIMENT_FILTER_KWARGS if data_set == 'bernstein' else {}
        readings = calculate_query_count_intervals(**filter_args)
        for time, count in readings:
            at_time = QueryCountAtTime.objects.filter(data_set=data_set, time=time)
            # If the reading already exists for this time update it, or else create a new object
            if at_time.exists():
                print(f'Updated query count reading at time {time} with count {count}')
                at_time.update(count=count)
            else:
                print(f'Created query count reading at time {time} with count {count}')
                QueryCountAtTime.objects.create(data_set=data_set, time=time, count=count)
        print('Finished post-process')
