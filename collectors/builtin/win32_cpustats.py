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

"""import various /proc stats from /proc into TSDB"""


import os
import re
import sys
import time
import glob
import psutil
from Queue import Queue

from collectors.lib.collectorbase import CollectorBase
import checks.system.win32 as w32

class Win32Cpustats(CollectorBase):

    def __init__(self, config, logger, readq):
        super(Win32Cpustats, self).__init__(config, logger, readq)

    def __call__(self):
        ts = int(time.time())
        cpu_percent = psutil.cpu_times_percent()

        self._readq.nput('system.cpu.user %d %f' % (ts, cpu_percent.user / psutil.cpu_count()))
        self._readq.nput('cpu.usr %d %f' % (ts, cpu_percent.user / psutil.cpu_count()))
        self._readq.nput('system.cpu.idle %d %f' % (ts, cpu_percent.idle / psutil.cpu_count()))
        self._readq.nput('system.cpu.system %d %f' % (ts, cpu_percent.system / psutil.cpu_count()))
        self._readq.nput('system.cpu.interrupt %d %f' % (ts, cpu_percent.interrupt / psutil.cpu_count()))

    def xxx__call__(self):
        cpu = w32.Cpu(None)
        config = dict( device_blacklist_re=None )
        cpu.check(config)
        metrics = cpu.check(config)
        self.log_info(metrics)

        for metric in metrics:
            tags = ""
            for key, value in metric[3].iteritems():
                tags += (" %s=%s" % (key, value.replace(':','')))
            self._readq.nput("%s %d %f%s" % (metric[0], metric[1], metric[2], tags))


if __name__ == "__main__":
    cpustats3_inst = Win32Cpustats(None, None, Queue())
    cpustats3_inst()
