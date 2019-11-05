import logging
import os
import shutil
import subprocess

from django.conf import settings


logger = logging.getLogger(__name__)


class SNMPSimOSCommandRunner:
    def __init__(self):
        logger.info(f"Creating directory '{settings.SNMPSIM_DAEMON_FOLDER}' for the snmpsim daemon...")
        os.makedirs(settings.SNMPSIM_DAEMON_FOLDER, exist_ok=True)
        shutil.chown(path=settings.SNMPSIM_DAEMON_FOLDER, user=settings.SNMPSIM_USER, group=settings.SNMPSIM_GROUP)

    def _prepare_start_command(self, recording_file, ip_address, port, snmp_read_community):
        """

        :param recording_file:
        :param ip_address:
        :param port:
        :param snmp_read_community:
        :return:
        """
        return [settings.SNMPSIM_SCRIPT_PATH,
                f"--process-user={settings.SNMPSIM_USER}",
                f"--process-group={settings.SNMPSIM_GROUP}",
                f"--data-dir={os.path.dirname(recording_file)}",
                f"--agent-udpv4-endpoint={ip_address}:{port}",
                f"--v2c-arch",
                f"--v2c-community={snmp_read_community}",
                f"--daemonize"]

    def _generate_sub_interface_name(self, ip_address):
        """

        :param ip_address:
        :return:
        """
        return f"{settings.SNMPSIM_IFACE_NAME}:{ip_address.split('.')[-1]}"

    def _create_sub_interface(self, ip_address):
        """

        :param ip_address:
        :return:
        """
        logger.info(f"Creating interface for the IP '{ip_address}' ...")
        output = subprocess.check_output(["ifconfig",
                                          self._generate_sub_interface_name(ip_address),
                                          f"{ip_address}/24"])

        logger.info(f"Command output: {output}")

    def _remove_sub_interface(self, ip_address):
        """

        :param ip_address:
        :return:
        """
        logger.info(f"Removing interface for the IP '{ip_address}' ...")
        try:
            output = subprocess.check_output(["ifconfig",
                                              self._generate_sub_interface_name(ip_address),
                                              "down"],
                                             stderr=subprocess.STDOUT)
            logger.info(f"Command output: {output}")
        except subprocess.CalledProcessError:
            logger.info(f"Failed to remove interface for IP '{ip_address}'", exc_info=True)

    def start(self, recording_file, ip_address, port, snmp_read_community):
        """

        :param recording_file:
        :param ip_address:
        :param port:
        :param snmp_read_community:
        :return:
        """
        self._create_sub_interface(ip_address)

        logger.info(f"Starting snmpsim recording '{recording_file}' on {ip_address}:{port} ...")
        output = subprocess.check_output(self._prepare_start_command(recording_file=recording_file,
                                                                     ip_address=ip_address,
                                                                     port=port,
                                                                     snmp_read_community=snmp_read_community))

        logger.info(f"Command output: {output}")

    def stop(self, recording_file, ip_address, port, snmp_read_community, remove_sub_iface=False):
        """

        :param recording_file:
        :param ip_address:
        :param port:
        :param snmp_read_community:
        :param remove_sub_iface:
        :return:
        """
        logger.info(f"Stopping snmpsim recording '{recording_file}' on {ip_address}:{port} ...")
        start_command = self._prepare_start_command(recording_file=recording_file,
                                                    ip_address=ip_address,
                                                    port=port,
                                                    snmp_read_community=snmp_read_community)
        start_command = " ".join(start_command)
        os.system(f"pkill -f '{start_command}'")

        if remove_sub_iface:
            self._remove_sub_interface(ip_address)

    def stop_all(self):
        """

        :return:
        """
        logger.info(f"Stopping all snmpsim recordings ...")
        os.system(f"pkill -f '{settings.SNMPSIM_SCRIPT_PATH}'")
