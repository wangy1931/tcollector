# -*- coding: utf-8 -*-
import time

from collectors.lib.inventory.linux_distribution import Distribution
from collectors.lib.inventory.linux_hardware import LinuxHardware
from collectors.lib.inventory.linux_platform import Platform
from collectors.lib.inventory.linux_network import LinuxNetwork

from collectors.lib import utils
from collectors.lib.collectorbase import CollectorBase
from collectors.lib.inventory.linux_virtual import LinuxVirtual


class LinuxHostScan(CollectorBase):
    def __init__(self, config, logger, readq):
        super(LinuxHostScan, self).__init__(config, logger, readq)

    def __call__(self):
        try:
            basic_hardware = LinuxHardware(self._logger).populate()
            platform = Platform().collect()
            network = LinuxNetwork(self._logger).populate(basic_hardware)
            virtual = LinuxVirtual(self._logger).get_virtual_facts()
            distribution = Distribution(self._logger).get_distribution_facts()

            host = HostParser(basic_hardware, platform, network, virtual, distribution)
            utils.alertd_post_sender('/cmdb/agent/host/scan', host.__dict__)
            self._readq.nput('scan.state %s %s' % (int(time.time()), '0'))
        except Exception as e:
            self.log_error('cannot send host scan result to alertd %s' % e)
            self._readq.nput('scan.state %s %s' % (int(time.time()), '1'))

class HostParser:
    def __init__(self, hardware, platform, network, virtual, distribution):

        ipv4 = self.get_ipv4(network)
        self.key = str(ipv4) + '_' + str(platform.get('hostname'))
        self.type = 'Host'

        self.architecture = None
        self.biosDate = None
        self.biosVersion = None
        self.totalMemory = None
        self.hostname = None
        self.domain = None
        self.fqdn = None
        self.defaultIp = None
        self.osFamily = None
        self.osName = None
        self.osVersion = None
        self.systemVendor = None
        self.productSerial = None
        self.productVersion = None
        self.productUuid = None
        self.productName = None
        self.cpu = []
        self.isVirtual = None

        self.interfaces = []
        self.devices = []

        self.parse(hardware, platform, network, virtual, distribution)

    def get_ipv4(self, network):
        default_v4 = network.get('default_ipv4')
        if default_v4.get('address') is not None:
            ipv4 = default_v4.get('address')
        else:
            import socket
            ipv4 = socket.gethostbyname(socket.gethostname())
        return ipv4

    def parse(self, hardware, platform, network, virtual, distribution):
        self.biosDate = hardware.get('bios_date')
        self.biosVersion = hardware.get('bios_version')
        self.totalMemory = hardware.get('memtotal_mb')
        self.productSerial = hardware.get('product_serial')
        self.productVersion = hardware.get('product_version')
        self.productUuid = hardware.get('product_uuid')
        self.productName = hardware.get('product_name')
        self.systemVendor = hardware.get('system_vendor')

        self.architecture = platform.get('architecture')
        self.hostname = platform.get('nodename')
        self.fqdn = platform.get('fqdn')
        self.domain = platform.get('domain')

        self.osFamily = distribution.get('os_family')
        self.osName = distribution.get('distribution')
        self.osVersion = distribution.get('distribution_version')

        self.defaultIp = self.get_ipv4(network)

        if virtual.get('virtualization_role') is None:
            vendor = hardware.get('system_vendor')
            if vendor is not None:
                if vendor == 'Xen' or vendor == 'VMWare' or 'Hyper' in vendor or 'VERSION' in vendor:
                    self.isVirtual = True
                else:
                    self.isVirtual = False
        else:
            self.isVirtual = virtual.get('virtualization_role') == 'guest'

        # processor looks like:
        # ['0', 'GenuineIntel', 'Intel(R) Core(TM) i7-5500U CPU @ 2.40GHz', ...]
        procs = hardware.get('processor')
        self.cpu = procs[2::3]

        for interface in network.get('interfaces'):
            interface_attr = {
                'key': self.key + '_interface_' + interface,
                'type': 'Interface'
            }
            intf = network.get(interface)
            ipv4 = intf.get('ipv4')
            if ipv4 is not None and ipv4['address'] != '127.0.0.1':
                interface_attr['name'] = interface
                interface_attr['ip'] = ipv4.get('address')

                if intf.get('speed') is not None:
                    interface_attr['speed'] = intf.get('speed')

                if intf.get('macaddress') is not None:
                    interface_attr['mac'] = intf.get('macaddress')

                self.interfaces.append(interface_attr)

        devices = hardware.get('devices')
        for i in devices:
            if 'loop' in i:
                continue

            device_attr = {
                'key': self.key + '_device_' + i,
                'type': 'Device',
                'model': devices[i].get('model'),
                'vendor': devices[i].get('vendor'),
                'size': devices[i].get('size')
            }

            self.devices.append(device_attr)
