from django.conf import settings
from django.db import models


class Recording(models.Model):
    name = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField()
    port = models.PositiveIntegerField(default=161)
    snmp_read_community = models.CharField(default="public", max_length=255)
    is_running = models.BooleanField(default=False)
    recording_file = models.FileField(upload_to="recordings")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.name} IP: {self.ip_address}"
