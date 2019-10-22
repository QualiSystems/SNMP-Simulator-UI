from django.conf import settings
from django.db import models


def upload_to(instance, filename):
    """

    :param instance:
    :param filename:
    :return:
    """
    return f"recordings/{instance.ip_address}_{instance.port}/{filename}"


class Recording(models.Model):
    name = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField()
    port = models.PositiveIntegerField(default=161)
    snmp_read_community = models.CharField(default="public", max_length=255)
    is_running = models.BooleanField(default=False)
    recording_file = models.FileField(upload_to=upload_to)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        unique_together = ('ip_address', 'port')

    def __str__(self):
        return f"{self.name} IP: {self.ip_address}"
