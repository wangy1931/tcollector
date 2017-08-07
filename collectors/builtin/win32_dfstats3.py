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
from Queue import Queue
from checks.libs.wmi.sampler import WMISampler
from functools import partial
import logging
import numbers

from collectors.lib.collectorbase import CollectorBase

#WMISampler = None

class Win32Dfstats3(CollectorBase):

    def __init__(self, config, logger, readq):
        super(Win32Dfstats3, self).__init__(config, logger, readq)
        # log = logging.getLogger("C:\\logs\\test.log")
        self.WMISampler = partial(WMISampler, logger)

    def __call__(self):
        metrics = self.WMISampler("Win32_LogicalDisk", \
		    ["DeviceID", \
			 "FreeSpace", \
			 "Size"], \
			 provider="64", timeout_duration=50)
        metrics.sample()
        ts = int(time.time())

        for metric in metrics:
            drive_list=str(metric.get("deviceid")).split(":")
            if len(drive_list) >0 :
                drive = drive_list[0]
            else:
                drive="C"
            for key, value in metric.iteritems():
                if isinstance(value, numbers.Number):
                    self._readq.nput("system.fs.%s %d %f drive=%s" % (key, ts, value, drive))


if __name__ == "__main__":
    dfstats3_inst = Win32Dfstats3(None, None, Queue())
    dfstats3_inst()
