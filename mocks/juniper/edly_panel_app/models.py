from django.db import models
from django.contrib.auth.models import User

from openedx.features.edly.models import EdlySubOrganization


class EdlyUserActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    activity_date = models.DateField(auto_now_add=True, db_index=True)
    edly_sub_organization = models.ForeignKey(EdlySubOrganization, on_delete=models.CASCADE, null=True, blank=False)

    class Meta:
        unique_together = ('user', 'activity_date', 'edly_sub_organization')

    def __str__(self):
        return '{username} ({edly_sub_organization}) was active on {activity_date}.'.format(
            username=self.user.username,
            edly_sub_organization=self.edly_sub_organization,
            activity_date=self.activity_date
        )
