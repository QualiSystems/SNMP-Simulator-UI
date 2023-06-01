import logging
from rest_framework import serializers, viewsets, response, decorators, permissions, exceptions, status
from .models import Recording
from .snmpsim_runner import SNMPSimOSCommandRunner

logger = logging.getLogger(__name__)


# Serializers define the API representation.
class RecordingSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Recording
        fields = ['id', 'name', 'ip_address', 'port', 'snmp_read_community', 'recording_file', 'is_running']


# ViewSets define the view behavior.
class RecordingViewSet(viewsets.ModelViewSet):
    queryset = Recording.objects.all()
    serializer_class = RecordingSerializer

    @decorators.action(methods=['get'], detail=True, permission_classes=[permissions.IsAuthenticated])
    def start(self, request, pk=None):
        try:
            recording: Recording = Recording.objects.get(pk=pk)
        except Recording.DoesNotExist:
            return response.Response({'error': f'Recording with ID {pk}, does not exist'},
                                     status=status.HTTP_400_BAD_REQUEST)

        try:
            SNMPSimOSCommandRunner().start(recording_file=recording.recording_file.path,
                                           ip_address=recording.ip_address,
                                           port=recording.port,
                                           snmp_read_community=recording.snmp_read_community)
        except Exception:
            logger.exception(f"Failed to start recording '{recording}' due to:")
            return response.Response({'error': f'Failed to start recording {recording}'},
                                     status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            recording.is_running = True
            recording.save()
            return response.Response("", status=status.HTTP_204_NO_CONTENT)

    @decorators.action(methods=['get'], detail=True, permission_classes=[permissions.IsAuthenticated])
    def stop(self, request, pk=None):
        try:
            recording: Recording = Recording.objects.get(pk=pk)
        except Recording.DoesNotExist:
            return response.Response({'error': f'Recording with ID {pk}, does not exist'},
                                     status=status.HTTP_400_BAD_REQUEST)

        try:
            SNMPSimOSCommandRunner().stop(recording_file=recording.recording_file.path,
                                          ip_address=recording.ip_address,
                                          port=recording.port,
                                          snmp_read_community=recording.snmp_read_community,
                                          remove_sub_iface=Recording.objects.is_ip_address_unique(recording.ip_address))
        except Exception:
            logger.exception(f"Failed to stop recording '{recording}' due to:")
            return response.Response({'error': f'Failed to stop recording {recording}'},
                                     status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            recording.is_running = False
            recording.save()
            return response.Response("", status=status.HTTP_204_NO_CONTENT)
