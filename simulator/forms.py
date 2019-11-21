from django.conf import settings
from django import forms
from easy_select2 import apply_select2
import ipaddress

from .models import Recording


snmpsim_network = ipaddress.ip_network(settings.SNMPSIM_NETWORK)


class RecordingForm(forms.ModelForm):
    class Meta:
        model = Recording
        fields = ("name",
                  "ip_address",
                  "port",
                  "snmp_read_community",
                  "recording_file",
                  "autodiscover_sys_desc",
                  "sys_description",
                  "comment")
        widgets = {
            'ip_address': apply_select2(forms.Select),
        }

    def __init__(self, *args, **kwargs):
        """

        :param args:
        :param kwargs:
        """
        super().__init__(*args, **kwargs)
        free_ips, used_ips = self._get_recordings_ips()
        ip_adresses = (
            ('Free', [(ip_addr, ip_addr) for ip_addr in free_ips]),
            ('Used in other Recordings', [(ip_addr, ip_addr) for ip_addr in used_ips])
        )
        self.fields["ip_address"].widget.choices = ip_adresses
        self.fields["ip_address"].initial = ""
        self.fields["ip_address"].initial = free_ips[0] if free_ips else ""

    def _get_recordings_ips(self):
        """Find free IPs addresses for the new recording

        :return:
        """
        used_ips = Recording.objects.values_list("ip_address", flat=True)
        free_ips = [ip_addr for ip_addr in map(str, snmpsim_network.hosts()) if ip_addr not in used_ips]

        return free_ips, used_ips
