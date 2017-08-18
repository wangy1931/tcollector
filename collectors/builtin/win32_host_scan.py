# -*- coding: utf-8 -*-
import copy
import subprocess
import sys
import time

import wmi

from collectors.lib import utils
from collectors.lib.collectorbase import CollectorBase


class WindowsHostScan(CollectorBase):
    def __init__(self, config, logger, readq):
        super(WindowsHostScan, self).__init__(config, logger, readq)

    def __call__(self):
        try:
            host = HostParser(self._logger)
            host.collect_all()

            utils.alertd_post_sender('/cmdb/agent/host/scan', host.to_CI())
            self._readq.nput('scan.state %s %s' % (int(time.time()), '0'))
        except Exception as e:
            self.log_error('cannot send host scan result to alertd %s' % e)
            self._readq.nput('scan.state %s %s' % (int(time.time()), '1'))


class HostParser:
    def __init__(self, logger):
        self.logger = logger

        self.key = None
        self.type = 'Host'

        self.biosDate = None
        self.biosVersion = None
        self.totalMemory = None

        self.productSerial = None
        self.productVersion = None
        self.productUuid = None
        self.productName = None
        self.systemVendor = None

        self.architecture = None
        self.hostname = None
        self.domain = None
        self.fqdn = None

        self.osFamily = None
        self.osName = None
        self.osVersion = None

        self.defaultIp = None

        self.isVirtual = None

        self.cpu = None

        self.interfaces = None
        self.devices = None
        self.memory = None

    def collect_all(self):
        c = wmi.WMI()

        self.collect_default_ip()
        self.collect_computer_system(c)
        self.key = str(self.defaultIp) + '_' + str(self.hostname)

        self.populate_bios(c)
        self.populate_os(c)
        self.collect_product(c)
        self.collect_cpu(c)
        self.collect_network_adapter(c)
        self.collect_device(c)
        self.collect_memory(c)

    def populate_bios(self, wmi_obj):
        try:
            for i in wmi_obj.Win32_Bios():
                # for bios, it has just 1 element
                self.biosDate = self.to_date(i.ReleaseDate)
                self.biosVersion = i.Version

                return
        except Exception as ae:
            self.log_error('cannot collect bios info %s' % ae)

    def populate_os(self, wmi_obj):
        try:
            for i in wmi_obj.Win32_OperatingSystem():
                # for os, it has just 1 element
                self.architecture = i.OSArchitecture
                self.osFamily = 'Windows'
                self.osName = i.Caption
                self.osVersion = i.Version

                return
        except Exception as ae:
            self.log_error('cannot collect os info %s' % ae)

    def collect_computer_system(self, wmi_obj):
        try:
            for i in wmi_obj.Win32_ComputerSystem():
                # for os, it has just 1 element
                self.totalMemory = int(i.TotalPhysicalMemory) / (1024 * 1024)
                self.hostname = i.DNSHostName
                self.domain = i.Domain
                self.fqdn = self.hostname + '.' + self.domain

                self.productName = i.Model

                return
        except Exception as ae:
            self.log_error('cannot collect cs info %s' % ae)

    def collect_product(self, wmi_obj):
        try:
            for i in wmi_obj.Win32_ComputerSystemProduct():
                # for product, it has just 1 element
                self.systemVendor = i.Vendor
                self.productSerial = i.IdentifyingNumber
                self.productVersion = i.Version
                self.productUuid = i.UUID

                if i.Vendor == 'Xen' or i.Vendor == 'VMWare' or 'Hyper' in i.Vendor or 'VERSION' in i.Vendor:
                    self.isVirtual = True
                else:
                    self.isVirtual = False

                return
        except Exception as ae:
            self.log_error('cannot collect product info %s' % ae)

    def collect_cpu(self, wmi_obj):
        try:
            self.cpu = []
            for i in wmi_obj.Win32_Processor():
                self.cpu.append(i.Name)
        except Exception as ae:
            self.log_error('cannot collect cpu info %s' % ae)

    def collect_network_adapter(self, wmi_obj):
        try:
            adapter = {}
            for i in wmi_obj.Win32_NetworkAdapterConfiguration(IPEnabled=True):
                if i.MACAddress:
                    ip = i.IPAddress
                    if ip and len(ip) > 0 and ip[0] != '127.0.0.1':
                        adapter[i.MACAddress] = {'key': self.key + '_interface_' + i.Index, 'mac': i.MACAddress,
                                                 'ip': ip[0]}

            for i in wmi_obj.Win32_NetworkAdapter():
                if i.MACAddress and adapter.get(i.MACAddress) is not None and i.Speed and i.Speed < sys.maxsize:
                    adapter[i.MACAddress]['speed'] = round(int(i.Speed) / (1000 * 1000))  # 1000进制, 而非 1024

            self.interfaces = adapter.values()

        except Exception as ae:
            self.log_error('cannot collect network info %s' % ae)

    # use route print to print ip table and parse the output
    def collect_default_ip(self):
        try:
            ip_table = subprocess.check_output('route print -4')
            for i in ip_table.splitlines():
                parts = i.split()
                # 网络目标 网络掩码 网关 接口 跃点数
                if len(parts) == 5 and parts[0] == '0.0.0.0':
                    self.defaultIp = parts[3]
        except Exception as e:
            self.log_error('cannot collect default ip info %s' % e)

    def collect_device(self, wmi_obj):
        try:
            self.devices = []
            for i in wmi_obj.Win32_DiskDrive():
                d = {'key': self.key + '_device_' + i.DeviceID, 'vendor': i.Manufacturer, 'model': i.Model}
                if i.Size:
                    d['size'] = str(round(int(i.Size) / (1024 * 1024 * 1024), 2)) + ' GB'
                self.devices.append(d)
        except Exception as ae:
            self.log_error('cannot collect device info %s' % ae)

    def collect_memory(self, wmi_obj):
        try:
            self.memory = []
            for i in wmi_obj.Win32_PhysicalMemory():
                m = {'key': self.key + '_memory_' + i.DeviceLocator, 'vendor': i.Manufacturer,
                     'locator': i.DeviceLocator, 'model': i.Model, 'serialNumber': i.SerialNumber}
                if i.Capacity:
                    m['size'] = round(int(i.Capacity) / (1024 * 1024))
                self.memory.append(m)
        except Exception as ae:
            self.log_error('cannot collect memory info %s' % ae)

    def to_CI(self):
        p = copy.deepcopy(self.__dict__)
        del p['logger']

        return p

    def to_date(self, wmi_time):
        time_tuple = wmi.to_time(wmi_time)
        if len(time_tuple) == 8:
            # fix time tuple by add 0 to the end
            l = list(time_tuple)
            l.insert(7, 0)
            if l[8] is None:
                l[8] = 0
            else:
                l[8] = int(l[8])
            time_tuple = tuple(l)

        return time.strftime("%Y-%m-%d", time_tuple)

    def log_error(self, msg, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)
