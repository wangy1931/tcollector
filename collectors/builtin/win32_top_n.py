#!/usr/bin/env python

# This file is part of tcollector.
# Copyright (C) 2010  The tcollector Authors.

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

"""import cpu and memory stats of all processes from wmi into TSDB"""


import os
import re
import sys
import time
import glob
from Queue import Queue
from checks.libs.wmi.sampler import WMISampler
from functools import partial
import logging
import numbers

from collectors.lib import utils
from collectors.lib.collectorbase import CollectorBase

#WMISampler = None

class Win32TopN(CollectorBase):

    def __init__(self, config, logger, readq):
        super(Win32TopN, self).__init__(config, logger, readq)
        # log = logging.getLogger("C:\\logs\\test.log")
        self.WMISampler = partial(WMISampler, logger)

    def __call__(self):
        metrics = self.WMISampler("Win32_PerfFormattedData_PerfProc_Process", \
            ["IDProcess", "Name", "PercentProcessorTime", "PrivateBytes"], \
            provider="64", timeout_duration=50)
        metrics.sample()
        ts = int(time.time())

        processes = []
        for metric in metrics:
            id = metric.get("IDProcess")
            name = metric.get("Name")
            cpuPct = metric.get("PercentProcessorTime")
            memBytes = metric.get("PrivateBytes")
            process = (id, name, cpuPct, memBytes)
            processes.append(process)

        # Sort by memory
        tmpsorted = sorted(processes, key=lambda process: process[3], reverse=True)
        # Take the top N processes with highest memory usage
        top_n_mem = tmpsorted[:7]

        #self.log_info(top_n_mem)
        for p in top_n_mem:
            id = p[0]
            name = utils.remove_invalid_characters(p[1])
            mem = p[3]
            if name != "_Total" and name != "Idle":
                self._readq.nput("mem.topN %d %f pid_cmd=%d_%s" % (ts, mem, id, name))


        # Sort by cpu
        tmpsorted = sorted(processes, key=lambda process: process[2], reverse=True)
        # Take the top 5 processes with highest memory usage
        top_n_cpu = tmpsorted[:7]

        #self.log_info(top_n_cpu)
        for p in top_n_cpu:
            id = p[0]
            name = utils.remove_invalid_characters(p[1])
            cpu = p[2]
            if name != "_Total" and name != "Idle":
                self._readq.nput("cpu.topN %d %f pid_cmd=%d_%s" % (ts, cpu, id, name))


if __name__ == "__main__":
    test_inst = Win32TopN(None, None, Queue())
    test_inst()
