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
from collectors.lib.checks.libs.wmi.sampler import WMISampler
from functools import partial
import logging
import numbers


from collectors.lib.collectorbase import CollectorBase

#WMISampler = None

class Win32Iisstats(CollectorBase):

    def __init__(self, config, logger, readq):
        super(Win32Iisstats, self).__init__(config, logger, readq)
        # log = logging.getLogger("C:\\logs\\test.log")
        self.WMISampler = partial(WMISampler, logger)

    def __call__(self):
        iis_alive = False
        try:
            metrics = self.WMISampler("Win32_PerfFormattedData_W3SVC_WebService", \
                                      ["AnonymousUsersPersec", \
                                       "BytesReceivedPersec", \
                                       "BytesSentPersec", \
                                       "BytesTotalPersec", \
                                       "CGIRequestsPersec", \
                                       "ConnectionAttemptsPersec", \
                                       "CopyRequestsPersec", \
                                       "CurrentAnonymousUsers", \
                                       "CurrentBlockedAsyncIORequests", \
                                       "Currentblockedbandwidthbytes", \
                                       "CurrentCALcountforauthenticatedusers", \
                                       "CurrentCALcountforSSLconnections", \
                                       "CurrentCGIRequests", \
                                       "CurrentConnections", \
                                       "CurrentISAPIExtensionRequests", \
                                       "CurrentNonAnonymousUsers", \
                                       "FilesPersec", \
                                       "FilesReceivedPersec", \
                                       "FilesSentPersec", \
                                       "GetRequestsPersec", \
                                       "HeadRequestsPersec", \
                                       "ISAPIExtensionRequestsPersec", \
                                       "LockedErrorsPersec", \
                                       "LockRequestsPersec", \
                                       "LogonAttemptsPersec", \
                                       "MaximumAnonymousUsers", \
                                       "MaximumCALcountforauthenticatedusers", \
                                       "MaximumCALcountforSSLconnections", \
                                       "MaximumCGIRequests", \
                                       "MaximumConnections", \
                                       "MaximumISAPIExtensionRequests", \
                                       "MaximumNonAnonymousUsers", \
                                       "MeasuredAsyncIOBandwidthUsage", \
                                       "MkcolRequestsPersec", \
                                       "MoveRequestsPersec", \
                                       "NonAnonymousUsersPersec", \
                                       "NotFoundErrorsPersec", \
                                       "OptionsRequestsPersec", \
                                       "OtherRequestMethodsPersec", \
                                       "PostRequestsPersec", \
                                       "PropfindRequestsPersec", \
                                       "ProppatchRequestsPersec", \
                                       "PutRequestsPersec", \
                                       "SearchRequestsPersec", \
                                       "ServiceUptime", \
                                       "TotalAllowedAsyncIORequests", \
                                       "TotalAnonymousUsers", \
                                       "TotalBlockedAsyncIORequests", \
                                       "Totalblockedbandwidthbytes", \
                                       "TotalBytesReceived", \
                                       "TotalBytesSent", \
                                       "TotalBytesTransferred", \
                                       "TotalCGIRequests", \
                                       "TotalConnectionAttemptsallinstances", \
                                       "TotalCopyRequests", \
                                       "TotalcountoffailedCALrequestsforauthenticatedusers", \
                                       "TotalcountoffailedCALrequestsforSSLconnections", \
                                       "TotalDeleteRequests", \
                                       "TotalFilesReceived", \
                                       "TotalFilesSent", \
                                       "TotalFilesTransferred", \
                                       "TotalGetRequests", \
                                       "TotalHeadRequests", \
                                       "TotalISAPIExtensionRequests", \
                                       "TotalLockedErrors", \
                                       "TotalLockRequests", \
                                       "TotalLogonAttempts", \
                                       "TotalMethodRequests", \
                                       "TotalMethodRequestsPersec", \
                                       "TotalMkcolRequests", \
                                       "TotalMoveRequests", \
                                       "TotalNonAnonymousUsers", \
                                       "TotalNotFoundErrors", \
                                       "TotalOptionsRequests", \
                                       "TotalOtherRequestMethods", \
                                       "TotalPostRequests", \
                                       "TotalPropfindRequests", \
                                       "TotalProppatchRequests", \
                                       "TotalPutRequests", \
                                       "TotalRejectedAsyncIORequests", \
                                       "TotalSearchRequests", \
                                       "TotalTraceRequests", \
                                       "TotalUnlockRequests", \
                                       "TraceRequestsPersec", \
                                       "UnlockRequestsPersec"], \
                                      provider="64", timeout_duration=50)
            metrics.sample()
            ts = int(time.time())

            for metric in metrics:
                iis_alive = True
                for key, value in metric.iteritems():
                    if isinstance(value, numbers.Number):
                        self._readq.nput("webservice.%s %d %f" % (key, ts, value))
        except:
            iis_alive = False

        if iis_alive:
            self._readq.nput("iis.state %d %f" % (int(time.time()), 0))
        else :
            self._readq.nput("iis.state %d %f" % (int(time.time()), 1))

if __name__ == "__main__":
    iisstats_inst = Win32Iisstats(None, None, Queue())
    iisstats_inst()
