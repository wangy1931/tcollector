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

from collectors.lib.collectorbase import CollectorBase
import checks.system.win32 as w32


class Win32Memstats(CollectorBase):

    def __init__(self, config, logger, readq):
        super(Win32Memstats, self).__init__(config, logger, readq)


    def __call__(self):
        mem = w32.Memory(self._logger)
        config = dict( device_blacklist_re=None )
        metrics = mem.check(config)

        for metric in metrics:
            tags = ""
            for key, value in metric[3].iteritems():
                tags += (" %s=%s" % (key, value.replace(':','')))
            self._readq.nput("%s %d %f%s" % (metric[0], metric[1], metric[2], tags))


if __name__ == "__main__":
    memstats3_inst = Win32Memstats(None, None, Queue())
    memstats3_inst()
