"""Per-site failure isolation for 'backfill_figures_daily_metrics'"""
from unittest import mock

import pytest
from django.core.management import CommandError, call_command

CMD = 'figures.management.commands.backfill_figures_daily_metrics'


def test_failing_site_does_not_stop_next_site():
    sites = [mock.Mock(domain='bad.example.com'), mock.Mock(domain='good.example.com')]
    ok = dict(courses_processed=1, cdms_elapsed=0, sdm_elapsed=0)
    with mock.patch(CMD + '.get_active_tenant_lms_sites', return_value=sites), \
            mock.patch(CMD + '.backfill_daily_metrics_for_site_and_date',
                       side_effect=[AssertionError('Multiple orgs found'), ok]) as backfill:
        with pytest.raises(CommandError, match='bad.example.com'):
            call_command('backfill_figures_daily_metrics', date='2021-03-15')
    assert [c.args[0] for c in backfill.call_args_list] == sites
