import os
import shutil
import uuid

from django.conf import settings
from django.db import models
from django.dispatch import receiver


def upload_to(instance, filename):
    """

    :param instance:
    :param filename:
    :return:
    """
    return f"recordings/{uuid.uuid4().hex}/{filename}"


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


#todo: move start/stop script logic here??
@receiver(models.signals.post_delete, sender=Recording)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """Deletes file from filesystem when corresponding `Recording` object is deleted."""
    shutil.rmtree(os.path.dirname(instance.recording_file.path), ignore_errors=True)


@receiver(models.signals.pre_save, sender=Recording)
def auto_delete_old_file_on_change(sender, instance, **kwargs):
    """Deletes old file from filesystem when corresponding `Recording` object is updated with new file."""
    if not instance.pk:
        return False

    try:
        old_file = sender.objects.get(pk=instance.pk).recording_file
    except sender.DoesNotExist:
        return False

    if instance.recording_file != old_file:
        shutil.rmtree(os.path.dirname(old_file.path), ignore_errors=True)
