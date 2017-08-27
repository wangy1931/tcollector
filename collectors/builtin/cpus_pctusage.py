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
import os
import psutil

from collectors.lib.collectorbase import CollectorBase


class CpusPctusage(CollectorBase):
    def __init__(self, config, logger, readq):
        super(CpusPctusage, self).__init__(config, logger, readq)
        os.environ['LANG'] = "en_US.UTF-8"

    def __call__(self):
        try:
           cpus_count=psutil.cpu_count()
           for cpu_id in range(cpus_count):
               cpu_info_list=psutil.cpu_times_percent(interval=1,percpu=True)
               if(cpu_info_list is not None and len(cpu_info_list)>0):
                   timestamp = int(time.time())
                   cpu_info = cpu_info_list[0]
                   cpuid=str(cpu_id)
                   cpuuser = cpu_info.user
                   cpunice = cpu_info.nice
                   cpusystem = cpu_info.system
                   cpuinterrupt = cpu_info.irq
                   cpuidle = cpu_info.idle
                   self._readq.nput("cpu.usr %s %s cpu=%s" % (timestamp, cpuuser, cpuid))
                   self._readq.nput("cpu.nice %s %s cpu=%s" % (timestamp, cpunice, cpuid))
                   self._readq.nput("cpu.sys %s %s cpu=%s" % (timestamp, cpusystem, cpuid))
                   self._readq.nput("cpu.irq %s %s cpu=%s" % (timestamp, cpuinterrupt, cpuid))
                   self._readq.nput("cpu.idle %s %s cpu=%s" % (timestamp, cpuidle, cpuid))
                   self._readq.nput("cpu.state %s %s" % (int(time.time()), '0'))

        except Exception as e:
            self._readq.nput("cpu.state %s %s" % (int(time.time()), '1'))
            self.log_error("cpus_pctusage collector except exception when parse the filed, abort %s" % e)




if __name__ == "__main__":
    from Queue import Queue
    cpus_pctusage_inst = CpusPctusage(None, None, Queue())
    cpus_pctusage_inst()

