#!/usr/bin/env python
# This file is part of tcollector.
# Copyright (C) 2012  The tcollector Authors.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.  This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser
# General Public License for more details.  You should have received a copy
# of the GNU Lesser General Public License along with this program.  If not,
# see <http://www.gnu.org/licenses/>.
#

'''
CPU detailed statistics for TSDB

This plugin tracks, for all CPUs:

- user %
- nice %
- system %
- interrupt %
- idle %

Requirements :
- FreeBSD : top
- Linux : mpstat
'''

import time
import subprocess
import re
import platform
import os

from collectors.lib import utils
from collectors.lib.collectorbase import CollectorBase


class CpusPctusage(CollectorBase):
    def __init__(self, config, logger, readq):
        super(CpusPctusage, self).__init__(config, logger, readq)
        collection_interval = self.get_config('interval')
        os.environ['LANG'] = "en_US.UTF-8"
        self.is_new_top = False
        try:

            if utils.which_linux_command("mpstat"):
                self.p_top =  utils.get_linux_command(["mpstat", "-P", "ALL", str(collection_interval)])
            else:
                if platform.system() == "FreeBSD":
                    self.p_top = utils.get_linux_command(["top", "-t", "-I", "-P", "-n", "-s" + str(collection_interval),
                         "-d" + str((365 * 24 * 3600) / collection_interval)])
                else:
                    self.p_top = utils.get_linux_command(["top", "-b","-d "+str(collection_interval)])
                    self.is_new_top = True

        except OSError:
            self._readq.nput("cpu.state %s %s" % (int(time.time()), '1'))
            self.log_error("cpus_pctusage collector except error, abort %s" % OSError)
            return
        self.log_info('CpusPctusage created subprocess %d', self.p_top.pid)

    def __call__(self):
        try:

            while not self._exit:
                line = self.p_top.stdout.readline()
                if self.is_new_top:
                    if "Cpu" in line:
                        fields = ["", "1"]
                        l = re.findall(r"([0-9]{1,}\.[0-9]{1,})", line)
                        fields.append(l[1])
                        fields.append(l[3])
                        fields.append(l[2])
                        fields.append("")
                        fields.append(l[6])
                        fields.append(l[4])
                        self.send_data(fields)
                        continue
                else:
                    fields = re.sub(r"%( [uni][a-z]+,?)? | AM | PM ", "", line).split()
                    if len(fields) <= 0:
                        continue

                    if (((fields[0] == "CPU") or (re.match("[0-9][0-9]:[0-9][0-9]:[0-9][0-9]",fields[0]))) and (re.match("[0-9]+:?",fields[1]))):
                        self.send_data(fields)


        except Exception as e:
            self._readq.nput("cpu.state %s %s" % (int(time.time()), '1'))
            self.log_error("cpus_pctusage collector except exception when parse the filed, abort %s" % e)

    def cleanup(self):
        self.log_info('CpusPctusage stop subprocess %d', self.p_top.pid)
        self.stop_subprocess(self.p_top, __name__)

    def send_data(self,fields):
        timestamp = int(time.time())
        cpuid = fields[1].replace(":", "")
        cpuuser = fields[2]
        cpunice = fields[3]
        cpusystem = fields[4]
        cpuinterrupt = fields[6]
        cpuidle = fields[-1]
        self._readq.nput("cpu.usr %s %s cpu=%s" % (timestamp, cpuuser, cpuid))
        self._readq.nput("cpu.nice %s %s cpu=%s" % (timestamp, cpunice, cpuid))
        self._readq.nput("cpu.sys %s %s cpu=%s" % (timestamp, cpusystem, cpuid))
        self._readq.nput("cpu.irq %s %s cpu=%s" % (timestamp, cpuinterrupt, cpuid))
        self._readq.nput("cpu.idle %s %s cpu=%s" % (timestamp, cpuidle, cpuid))
        self._readq.nput("cpu.state %s %s" % (int(time.time()), '0'))

if __name__ == "__main__":
    from Queue import Queue
    cpus_pctusage_inst = CpusPctusage(None, None, Queue())
    cpus_pctusage_inst()

