#!/usr/bin/python
# This file is part of tcollector.
# Copyright (C) 2010-2013  The tcollector Authors.
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
"""Service startup stats for TSDB"""

import time
import ast
from subprocess import Popen, PIPE, CalledProcessError, STDOUT


from collectors.lib import utils
from collectors.lib.collectorbase import CollectorBase

# We collect service startup time (in sec) by calling "ps -eo pid,lstart,cmd".
# We need to add to services_startup.conf list of processes to be monitored.
# The command "ps -eo pid,lstart,cmd" returns pid, start time, and command of all long
# running services in current host. We will grep list of services in the config.
# Then we will send metric="startAtSec", tags:(service=<name>), ts=startTimeInSec.
# Note that ts=startTimeInSec instead of current time. Thus, we will have single data point
# for each startup event of a service.

class ServicesStartup(CollectorBase):
    def print_metric(self, ts, value, tags=""):
        if value is not None:
            self._readq.nput("service.startAtSec %d %s %s" % (ts, value, tags))

    def __init__(self, config, logger, readq):
        super(ServicesStartup, self).__init__(config, logger, readq)
        self.initialize = True
        self.services_before = []
        self.services_after = []
        self.services = ast.literal_eval(self.get_config("services"))

    def __call__(self):
        try:
            p = Popen('ps -eo pid,lstart,cmd', shell=True, stdout=PIPE, stderr=STDOUT)
            for line in p.stdout.readlines():
                self.process(line)

            self.initialize = False
            retval = p.wait()
            if retval:
                raise CalledProcessError(ret, "ps -eo pid,lstart,cmd", "ps returned code %i" % retval)
            self.swap()
        except OSError as e1:
            self.log_exception("ps -eo pid,lstart,cmd fails. [%s]", e1)
            return
                                                      
        except CalledProcessError as e:
            self.log_exception("Error run ps in subprocess. [%s]", e)                            
            return
       
    def process(self, line):
        for service in self.services:
            service = service.strip()
            if service in line:
                if self.initialize:
                    self.services_before.append(service)

                self.services_after.append(service)
                tokens = line.split()
                time_str="%s %s %s %s"%(tokens[2], tokens[3], tokens[4], tokens[5])
                d = time.strptime(time_str, "%b %d %H:%M:%S %Y")
                startup_sec = int(time.mktime(d))

                service_tag = "service=%s.%s"%(tokens[0], utils.remove_invalid_characters(service))
                self.print_metric(startup_sec, startup_sec, service_tag)

    def swap(self):
        print self.services_before
        print self.services_after
        stop_services = [item for item in self.services_before if item not in self.services_after]
        print stop_services
        for service in stop_services:
            self._readq.nput("service.stopAsSec %d %s %s" % (int(time.time()), 1, "service=%s"% utils.remove_invalid_characters(service)))
        self.services_before = self.services_after
        self.services_after = []