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

try:
    import json
    import time
except ImportError:
    json = None

from Queue import Queue
from collectors.lib.hadoop_http import HadoopCollectorBase
from collectors.lib.hadoop_http import HadoopNode

REPLACEMENTS = {
    "rpcdetailedactivityforport": ["rpc_activity"],
    "rpcactivityforport": ["rpc_activity"]
}


class HadoopNameNode(HadoopCollectorBase):
    def __init__(self, config, logger, readq):
        super(HadoopNameNode, self).__init__(config, logger, readq, REPLACEMENTS, HadoopNode)
        self.service = self.get_config('service', 'hadoop')
        self.daemon = self.get_config('daemon', 'namenode')
        self.host = self.get_config('host', 'localhost')
        self.port = self.get_config('port', 50070)


    def __call__(self):
        self.call("hadoop.namenode.state")



if __name__ == "__main__":
    from collectors.lib.utils import TestQueue
    from collectors.lib.utils import TestLogger

    hadoopdatanode_inst = HadoopNameNode(None, TestLogger(), TestQueue())
    hadoopdatanode_inst()
