from __future__ import print_function
from __future__ import absolute_import
from textwrap import dedent

from django.core.management.base import BaseCommand
from django.utils.timezone import now, timedelta
from figures.models import PipelineError

class Command(BaseCommand):
    '''Delete PipelineError records older than a specified number of days (default is 15 days).'''
    help = dedent(__doc__).strip()

    def add_arguments(self, parser):
        '''Add command arguments.'''
        parser.add_argument(
            '--days',
            type=int,
            default=15,
            help='Number of days to retain PipelineError records. Defaults to 15.',
        )

    def handle(self, *args, **options):
        '''Handle the deletion process.'''
        days = options['days']
        cutoff_date = now() - timedelta(days=days)

        print(f"Deleting PipelineError records older than {days} days in batches...")

        batch_size = 1000
        total_deleted = 0

        while True:
            old_records = PipelineError.objects.filter(created__lt=cutoff_date)[:batch_size]
            if not old_records.exists():
                break
            ids_to_delete = list(old_records.values_list('id', flat=True))
            PipelineError.objects.filter(id__in=ids_to_delete).delete()
            total_deleted += len(ids_to_delete)
            print(f"Deleted {len(ids_to_delete)} records in this batch. Total deleted: {total_deleted}.")

        print(f"Deletion complete. Total {total_deleted} PipelineError records older than {days} days deleted.")
        print('Done.')
