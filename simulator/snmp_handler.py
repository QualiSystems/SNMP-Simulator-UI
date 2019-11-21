from cloudshell.snmp.cloudshell_snmp import Snmp
from cloudshell.snmp.core.domain.snmp_oid import SnmpMibObject
from cloudshell.snmp.snmp_parameters import SNMPReadParameters


class SNMPHandler:
    def __init__(self, ip_address, snmp_read_community, port, logger):
        """

        :param ip_address:
        :param snmp_read_community:
        :param port:
        """
        self._snmp_params = SNMPReadParameters(ip=ip_address, snmp_community=snmp_read_community, port=port)
        self._logger = logger

    def get_sys_desc(self):
        """

        :return:
        """
        with Snmp().get_snmp_service(snmp_parameters=self._snmp_params, logger=self._logger) as snmp_service:
            return snmp_service.get_property(SnmpMibObject("SNMPv2-MIB", "sysDescr", "0")).safe_value
