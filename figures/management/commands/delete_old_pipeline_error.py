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

        print(f"Deleting PipelineError records older than {days} days...")

        deleted_count, _ = PipelineError.objects.filter(created__lt=cutoff_date).delete()

        print(f"Deleted {deleted_count} PipelineError records older than {days} days.")
        print('Done.')
