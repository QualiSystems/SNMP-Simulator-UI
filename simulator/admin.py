import logging

from django.conf.urls import url
from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.template.loader import render_to_string
from django.urls import reverse

from .forms import RecordingForm
from .models import Recording
from .snmp_handler import SNMPHandler
from .snmpsim_runner import SNMPSimOSCommandRunner


admin.site.site_header = "Quali Simulator"
admin.site.site_title = "Quali Simulator"
admin.site.index_title = "Welcome to Quali Simulator"

logger = logging.getLogger(__name__)


@admin.register(Recording)
class RecordingAdmin(admin.ModelAdmin):
    form = RecordingForm
    change_form_template = "admin/recording_change_form.html"

    date_heirarchy = (
        "modified",
    )

    list_display = (
        "name",
        "ip_address",
        "port",
        "snmp_read_community",
        "is_running",
        "updated_at",
        "updated_by",
        "recording_actions",
    )

    search_fields = (
        "name",
        "sys_description",
        "comment",
        "ip_address",
    )

    readonly_fields = (
        "sys_description",
        "is_running",
    )

    list_filter = (
        "is_running",
        "updated_at",
        "updated_by",
    )

    def __init__(self, *args, **kwargs):
        """

        :param args:
        :param kwargs:
        """
        super().__init__(*args, **kwargs)
        self._snmpsim_runner = SNMPSimOSCommandRunner()

    def recording_actions(self, obj):
        """

        :param obj:
        :return:
        """
        return render_to_string('admin/recording_action_buttons.html', context={"recording": obj})

    recording_actions.short_description = 'Actions'
    recording_actions.allow_tags = True

    def get_urls(self):
        """

        :return:
        """
        urls = super().get_urls()
        custom_urls = [
            url(
                r'^(?P<recording_id>.+)/start/$',
                self.admin_site.admin_view(self.start_recording),
                name='recording-start',
            ),
            url(
                r'^(?P<recording_id>.+)/stop/$',
                self.admin_site.admin_view(self.stop_recording),
                name='recording-stop',
            ),
        ]
        return custom_urls + urls

    def get_fields(self, request, obj=None):
        """

        :param request:
        :param obj:
        :return:
        """
        fields = super().get_fields(request, obj)

        if obj is None:
            fields.remove("sys_description")

        return fields

    def save_model(self, request, obj, form, change):
        """

        :param request:
        :param obj:
        :param form:
        :param change:
        :return:
        """
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        """Given a model instance delete it from the database.

        :param request:
        :param obj:
        :return:
        """
        try:
            self._snmpsim_runner.stop(recording_file=obj.recording_file.path,
                                      ip_address=obj.ip_address,
                                      port=obj.port,
                                      snmp_read_community=obj.snmp_read_community,
                                      remove_sub_iface=Recording.objects.is_ip_address_unique(obj.ip_address))
        except Exception:
            logger.exception(f"Failed to stop recording '{obj}' due to:")
            self.message_user(request, f"Failed to stop recording: '{obj}'. Please check logs for the details",
                              level=messages.ERROR)

        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        """Given a queryset, delete it from the database.

        :param request:
        :param queryset:
        :return:
        """
        failed_recordings = []
        for recording in queryset:
            try:
                self._snmpsim_runner.stop(recording_file=recording.recording_file.path,
                                          ip_address=recording.ip_address,
                                          port=recording.port,
                                          snmp_read_community=recording.snmp_read_community,
                                          remove_sub_iface=Recording.objects.is_ip_address_unique(recording.ip_address))
            except Exception:
                logger.exception(f"Failed to stop recording {recording} due to:")
                failed_recordings.append(recording)
                continue

        if failed_recordings:
            self.message_user(request, f"Failed to stop next recordings: {failed_recordings}", level=messages.ERROR)

        return super().delete_queryset(request, queryset)

    def response_change(self, request, obj):
        """

        :param request:
        :param obj:
        :return:
        """
        if obj.is_running:
            old_recording = Recording.objects.get(pk=obj.pk)

            try:
                self._snmpsim_runner.stop(recording_file=old_recording.recording_file.path,
                                          ip_address=old_recording.ip_address,
                                          port=old_recording.port,
                                          snmp_read_community=old_recording.snmp_read_community,
                                          remove_sub_iface=Recording.objects.is_ip_address_unique(
                                              old_recording.ip_address))
            except Exception:
                logger.exception(f"Failed to stop old recording '{old_recording}' due to:")
            obj.is_running = False

        if "_start" in request.POST:
            try:
                self._snmpsim_runner.start(recording_file=obj.recording_file.path,
                                           ip_address=obj.ip_address,
                                           port=obj.port,
                                           snmp_read_community=obj.snmp_read_community)
            except Exception:
                logger.exception(f"Failed to start recording '{obj}' due to:")
                obj.is_running = False
                self.message_user(request,
                                  f"Failed to start recording: '{obj}'. Please check logs for the details",
                                  level=messages.ERROR)
            else:
                obj.is_running = True
                if obj.autodiscover_sys_desc:
                    try:
                        snmp_handler = SNMPHandler(ip_address=obj.ip_address,
                                                   snmp_read_community=obj.snmp_read_community,
                                                   port=obj.port,
                                                   logger=logger)

                        obj.sys_description = snmp_handler.get_sys_desc()

                    except Exception:
                        logger.exception(f"Failed to discover sysDescr of recording '{obj}' due to:")

                self.message_user(request, f"Recording '{obj}' updated and started")

            obj.save()

            return HttpResponseRedirect(
                reverse("admin:simulator_recording_changelist", current_app=self.admin_site.name))

        return super().response_change(request, obj)

    def response_add(self, request, obj, post_url_continue=None):
        """

        :param request:
        :param obj:
        :param post_url_continue:
        :return:
        """
        if "_start" in request.POST:
            try:
                self._snmpsim_runner.start(recording_file=obj.recording_file.path,
                                           ip_address=obj.ip_address,
                                           port=obj.port,
                                           snmp_read_community=obj.snmp_read_community)
            except Exception:
                logger.exception(f"Failed to start recording '{obj}' due to:")
                obj.is_running = False
                self.message_user(request,
                                  f"Failed to start recording: '{obj}'. Please check logs for the details",
                                  level=messages.ERROR)
            else:
                obj.is_running = True
                if obj.autodiscover_sys_desc:
                    try:
                        snmp_handler = SNMPHandler(ip_address=obj.ip_address,
                                                   snmp_read_community=obj.snmp_read_community,
                                                   port=obj.port,
                                                   logger=logger)

                        obj.sys_description = snmp_handler.get_sys_desc()

                    except Exception:
                        logger.exception(f"Failed to discover sysDescr of recording '{obj}' due to:")

                self.message_user(request, f"Recording '{obj}' created and started")

            obj.save()

            return HttpResponseRedirect(
                reverse("admin:simulator_recording_changelist", current_app=self.admin_site.name))

        return super().response_add(request, obj, post_url_continue)

    def start_recording(self, request, recording_id):
        """

        :param request:
        :param recording_id:
        :return:
        """
        recording = self.get_object(request, recording_id)
        try:
            self._snmpsim_runner.start(recording_file=recording.recording_file.path,
                                       ip_address=recording.ip_address,
                                       port=recording.port,
                                       snmp_read_community=recording.snmp_read_community)
        except Exception:
            logger.exception(f"Failed to start recording '{recording}' due to:")
            self.message_user(request, f"Failed to start recording: '{recording}'. Please check logs for the details",
                              level=messages.ERROR)
        else:
            recording.is_running = True
            recording.save()
            self.message_user(request, f"Recording '{recording}' started")

        return HttpResponseRedirect(reverse("admin:simulator_recording_changelist", current_app=self.admin_site.name))

    def stop_recording(self, request, recording_id):
        """

        :param request:
        :param recording_id:
        :return:
        """
        recording = self.get_object(request, recording_id)
        try:
            self._snmpsim_runner.stop(recording_file=recording.recording_file.path,
                                      ip_address=recording.ip_address,
                                      port=recording.port,
                                      snmp_read_community=recording.snmp_read_community,
                                      remove_sub_iface=Recording.objects.is_ip_address_unique(recording.ip_address))
        except Exception:
            logger.exception(f"Failed to stop recording '{recording}' due to:")
            self.message_user(request, f"Failed to stop recording: '{recording}'. Please check logs for the details",
                              level=messages.ERROR)
        else:
            recording.is_running = False
            recording.save()
            self.message_user(request, f"Recording '{recording}' stopped")

        return HttpResponseRedirect(reverse("admin:simulator_recording_changelist", current_app=self.admin_site.name))

    def start_recordings(self, request, queryset):
        """

        :param request:
        :param queryset:
        :return:
        """
        failed_recordings = []
        for recording in queryset:
            try:
                self._snmpsim_runner.start(recording_file=recording.recording_file.path,
                                           ip_address=recording.ip_address,
                                           port=recording.port,
                                           snmp_read_community=recording.snmp_read_community)
            except Exception:
                logger.exception(f"Failed to start recording {recording} due to:")
                failed_recordings.append(recording)
                continue

            recording.is_running = True
            recording.save()

        if failed_recordings:
            self.message_user(request, f"Failed to start next recordings: {failed_recordings}", level=messages.ERROR)
        else:
            self.message_user(request, f"Selected recordings successfully started")

    def stop_recordings(self, request, queryset):
        """

        :param request:
        :param queryset:
        :return:
        """
        failed_recordings = []
        for recording in queryset:
            try:
                self._snmpsim_runner.stop(recording_file=recording.recording_file.path,
                                          ip_address=recording.ip_address,
                                          port=recording.port,
                                          snmp_read_community=recording.snmp_read_community,
                                          remove_sub_iface=Recording.objects.is_ip_address_unique(recording.ip_address))
            except Exception:
                logger.exception(f"Failed to stop recording {recording} due to:")
                failed_recordings.append(recording)
                continue

            recording.is_running = False
            recording.save()

        if failed_recordings:
            self.message_user(request, f"Failed to stop next recordings: {failed_recordings}", level=messages.ERROR)
        else:
            self.message_user(request, f"Selected recordings successfully stopped")

    actions = [start_recordings, stop_recordings]
    start_recordings.short_description = "Start selected recordings"
    stop_recordings.short_description = "Stop selected recordings"
