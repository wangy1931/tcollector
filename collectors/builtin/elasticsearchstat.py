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
"""Nginx stats for TSDB"""

import time
import json
import urllib2
from collectors.lib.collectorbase import CollectorBase


# There are two ways to collect Nginx's stats.
# 1. [yi-ThinkPad-T430 scripts (master)]$ curl http://localhost:8080/nginx_status
# Active connections: 2 
# server accepts handled requests
#  4 4 11 
# Reading: 0 Writing: 1 Waiting: 1

class Elasticsearchstat(CollectorBase):

    def __init__(self, config, logger, readq):
        super(Elasticsearchstat, self).__init__(config, logger, readq)
        self.port = self.get_config('port', 9200)
        self.host = self.get_config('host', "localhost")
        self.es_url_node="http://%s:%s/_nodes/stats"%(self.host,self.port)
        self.es_url_health = "http://%s:%s/_cat/health" % (self.host, self.port)
        self.es_status_dict = { "green": "0", "yellow": "1", "red": "2"}

    def __call__(self):
        try:
            self.collect_es_health()
            self.collect_es_node()
            self._readq.nput("elasticsearch.%s %s %s" % ("state", int(time.time()), "0"))
        except Exception,e:
            self.log_exception("collector of elasticsearch is failed! Because %s"%e.message)
            self._readq.nput("elasticsearch.%s %s %s" % ("state", int(time.time()), "1"))



    def collect_es_health(self):
        line = urllib2.urlopen(self.es_url_health, timeout=20).read()
        if line != "":
            list = line.split(" ")
            if len(list)>=14:
                timestamp = list[0]
                status = self.es_status_dict[list[3]]
                total = list[4]
                data = list[5]
                shards_total = list[6]
                shards_primary = list[7]
                shards_relocating = list[8]
                shards_initializing = list[9]
                shards_unassigned = list[10]
                shards_active = list[13].replace("%", "")
                self._readq.nput("elasticsearch.elasticsearch.status %s %s " % (timestamp, status))
                self._readq.nput("elasticsearch.elasticsearch.node.total %s %s" % (timestamp, total))
                self._readq.nput("elasticsearch.elasticsearch.node.data %s %s" % (timestamp, data))
                self._readq.nput("elasticsearch.elasticsearch.shards.total %s %s" % (timestamp, shards_total))
                self._readq.nput("elasticsearch.elasticsearch.shards.primary %s %s" % (timestamp, shards_primary))
                self._readq.nput("elasticsearch.elasticsearch.shards.relocating %s %s" % (timestamp, shards_relocating))
                self._readq.nput("elasticsearch.elasticsearch.shards.initializing %s %s" % (timestamp, shards_initializing))
                self._readq.nput("elasticsearch.elasticsearch.shards.unassigned %s %s" % (timestamp, shards_unassigned))
                self._readq.nput("elasticsearch.elasticsearch.shards.active %s %s" % (timestamp, shards_active))
            else:
                self.log_warn("get es health fail!!")

    def collect_es_node(self):
        response = urllib2.urlopen(self.es_url_node, timeout=20).read()
        ts = int(time.time())
        parsed = json.loads(response)
        cluster = parsed['cluster_name'].lower()
        for node in parsed['nodes']:
            # collecting metrics
            name = parsed['nodes'][node]['name'].lower()
            indices = parsed['nodes'][node]['indices']

            docs_count = indices['docs']['count']
            bytes_count = indices['store']['size_in_bytes']
            throttle_ms = indices['store']['throttle_time_in_millis']

            index_total = indices['indexing']['index_total']
            if index_total == 0:
                index_total = 1
            index_ms = indices['indexing']['index_time_in_millis']
            index_avg = index_ms / index_total
            index_current = indices['indexing']['index_current']
            index_failed = indices['indexing']['index_failed']

            query_current = indices['search']['query_current']
            query_total = indices['search']['query_total']
            if query_total == 0:
                query_total = 1
            query_ms = indices['search']['query_time_in_millis']
            query_avg = query_ms / query_total
            fetch_current = indices['search']['fetch_current']
            fetch_total = indices['search']['fetch_total']
            if fetch_total == 0:
                fetch_total = 1
            fetch_ms = indices['search']['fetch_time_in_millis']
            fetch_avg = fetch_ms / fetch_total

            fielddata_size = indices['fielddata']['memory_size_in_bytes']
            fielddata_evictions = indices['fielddata']['evictions']
            query_cache_bytes = indices['query_cache']['memory_size_in_bytes']
            query_evictions = indices['query_cache']['evictions']
            jvm = parsed['nodes'][node]['jvm']
            young_count = jvm['gc']['collectors']['young']['collection_count']

            if young_count == 0:
                young_count = 1

            young_ms = jvm['gc']['collectors']['young']['collection_time_in_millis']
            young_avg = young_ms / young_count
            old_count = jvm['gc']['collectors']['old']['collection_count']

            if old_count == 0:
                old_count = 1
            old_ms = jvm['gc']['collectors']['old']['collection_time_in_millis']
            old_avg = old_ms / old_count
            heap_used_pct = jvm['mem']['heap_used_percent']
            heap_committed = jvm['mem']['heap_committed_in_bytes']
            os = parsed['nodes'][node]['os']
            cpu_pct = os['cpu_percent'] if os.has_key('cpu_percent') else parsed['nodes'][node]['process']['cpu'][
                'percent']
            cpu_load = os['load_average']
            mem_swap_used = os['swap']['used_in_bytes']

            fs = parsed['nodes'][node]['fs']

            # fs_avail = fs['data']['available_in_bytes']

            http = parsed['nodes'][node]['http']

            http_open = http['current_open']

            thread = parsed['nodes'][node]['thread_pool']

            bulk_queue = thread['bulk']['queue']
            bulk_rejected = thread['bulk']['rejected']
            flush_queue = thread['flush']['queue']
            flush_rejected = thread['flush']['rejected']
            index_queue = thread['index']['queue']
            index_rejected = thread['index']['rejected']
            listener_queue = thread['listener']['queue']
            listener_rejected = thread['listener']['rejected']
            mgmt_queue = thread['management']['queue']
            mgmt_rejected = thread['management']['rejected']
            search_queue = thread['search']['queue']
            search_rejected = thread['search']['rejected']

            # print metrics to stdout
            self._readq.nput( 'elasticsearch.{0}.nodes.indices.docs_count {1} {2}  tags="node={3}"'.format(cluster, ts, docs_count,
                                                                                                name))
            self._readq.nput( 'elasticsearch.{0}.nodes.indices.bytes_count {1} {2}  tags="node={3}"'.format(cluster, ts,
                                                                                                 bytes_count,
                                                                                                 name))
            self._readq.nput( 'elasticsearch.{0}.nodes.indices.throttle_ms {1} {2}  tags="node={3}"'.format(cluster, ts,
                                                                                                 throttle_ms,
                                                                                                 name))
            self._readq.nput( 'elasticsearch.{0}.nodes.indices.index_total {1} {2}  tags="node={3}"'.format(cluster, ts,
                                                                                                 index_total,
                                                                                                 name))
            self._readq.nput( 'elasticsearch.{0}.nodes.indices.index_avg {1} {2}  tags="node={3}"'.format(cluster, ts, index_avg,
                                                                                               name))
            self._readq.nput( 'elasticsearch.{0}.nodes.indices.index_current {1} {2}  tags="node={3}"'.format(cluster, ts,
                                                                                                   index_current,
                                                                                                   name))
            self._readq.nput( 'elasticsearch.{0}.nodes.indices.index_failed {1} {2}  tags="node={3}"'.format(cluster, ts,
                                                                                                  index_failed,
                                                                                                  name))
            self._readq.nput( 'elasticsearch.{0}.nodes.indices.query_current {1} {2}  tags="node={3}"'.format(cluster, ts,
                                                                                                   query_current,
                                                                                                   name))
            self._readq.nput( 'elasticsearch.{0}.nodes.indices.query_total {1} {2}  tags="node={3}"'.format(cluster, ts,
                                                                                                 query_total,
                                                                                                 name))
            self._readq.nput( 'elasticsearch.{0}.nodes.indices.query_avg {1} {2}  tags="node={3}"'.format(cluster, ts, query_avg,
                                                                                               name))
            self._readq.nput( 'elasticsearch.{0}.nodes.indices.fetch_current {1} {2}  tags="node={3}"'.format(cluster, ts,
                                                                                                   fetch_current,
                                                                                                   name))
            self._readq.nput( 'elasticsearch.{0}.nodes.indices.fetch_total {1} {2}  tags="node={3}"'.format(cluster, ts,
                                                                                                 fetch_total,
                                                                                                 name))
            self._readq.nput( 'elasticsearch.{0}.nodes.indices.fetch_avg {1} {2}  tags="node={3}"'.format(cluster, ts, fetch_avg,
                                                                                               name))
            self._readq.nput( 'elasticsearch.{0}.nodes.indices.fielddata_size {1} {2}  tags="node={3}"'.format(cluster, ts,
                                                                                                    fielddata_size,
                                                                                                    name))
            self._readq.nput( 'elasticsearch.{0}.nodes.indices.fielddata_evictions {1} {2}  tags="node={3}"'.format(cluster, ts,
                                                                                                         fielddata_evictions,
                                                                                                         name))
            self._readq.nput( 'elasticsearch.{0}.nodes.indices.query_cache_bytes {1} {2}  tags="node={3}"'.format(cluster, ts,
                                                                                                       query_cache_bytes,
                                                                                                       name))
            self._readq.nput( 'elasticsearch.{0}.nodes.indices.query_evictions {1} {2}  tags="node={3}"'.format(cluster, ts,
                                                                                                     query_evictions,
                                                                                                     name))
            self._readq.nput( 'elasticsearch.{0}.nodes.jvm.young_count {1} {2}  tags="node={3}"'.format(cluster, ts, young_count,
                                                                                             name))
            self._readq.nput( 'elasticsearch.{0}.nodes.jvm.young_avg {1} {2}  tags="node={3}"'.format(cluster, ts, young_avg,
                                                                                           name))
            self._readq.nput( 'elasticsearch.{0}.nodes.jvm.old_count {1} {2}  tags="node={3}"'.format(cluster, ts, old_count,
                                                                                           name))
            self._readq.nput( 'elasticsearch.{0}.nodes.jvm.old_avg {1} {2}  tags="node={3}"'.format(cluster, ts, old_avg,
                                                                                         name))
            self._readq.nput( 'elasticsearch.{0}.nodes.jvm.heap_used_pct {1} {2}  tags="node={3}"'.format(cluster, ts,
                                                                                               heap_used_pct,
                                                                                               name))
            self._readq.nput( 'elasticsearch.{0}.nodes.jvm.heap_committed {1} {2}  tags="node={3}"'.format(cluster, ts,
                                                                                                heap_committed,
                                                                                                name))
            self._readq.nput( 'elasticsearch.{0}.nodes.os.cpu_pct {1} {2}  tags="node={3}"'.format(cluster, ts, cpu_pct,
                                                                                        name))
            self._readq.nput( 'elasticsearch.{0}.nodes.os.cpu_load {1} {2}  tags="node={3}"'.format(cluster, ts, cpu_load,
                                                                                         name))
            self._readq.nput( 'elasticsearch.{0}.nodes.os.mem_swap_used {1} {2}  tags="node={3}"'.format(cluster, ts,
                                                                                              mem_swap_used,
                                                                                              name))
            self._readq.nput( 'elasticsearch.{0}.nodes.http.current_open {1} {2}  tags="node={3}"'.format(cluster, ts, http_open,
                                                                                               name))
            self._readq.nput( 'elasticsearch.{0}.nodes.thread.bulk_queue {1} {2}  tags="node={3}"'.format(cluster, ts, bulk_queue,
                                                                                               name))
            self._readq.nput( 'elasticsearch.{0}.nodes.thread.bulk_rejected {1} {2}  tags="node={3}"'.format(cluster, ts,
                                                                                                  bulk_rejected,
                                                                                                  name))
            self._readq.nput( 'elasticsearch.{0}.nodes.thread.flush_queue {1} {2}  tags="node={3}"'.format(cluster, ts,
                                                                                                flush_queue,
                                                                                                name))
            self._readq.nput( 'elasticsearch.{0}.nodes.thread.flush_rejected {1} {2}  tags="node={3}"'.format(cluster, ts,
                                                                                                   flush_rejected,
                                                                                                   name))
            self._readq.nput( 'elasticsearch.{0}.nodes.thread.index_queue {1} {2}  tags="node={3}"'.format(cluster, ts,
                                                                                                index_queue,
                                                                                                name))
            self._readq.nput( 'elasticsearch.{0}.nodes.thread.index_rejected {1} {2}  tags="node={3}"'.format(cluster, ts,
                                                                                                   index_rejected,
                                                                                                   name))
            self._readq.nput( 'elasticsearch.{0}.nodes.thread.listener_queue {1} {2}  tags="node={3}"'.format(cluster, ts,
                                                                                                   listener_queue,
                                                                                                   name))
            self._readq.nput( 'elasticsearch.{0}.nodes.thread.listener_rejected {1} {2}  tags="node={3}"'.format(cluster, ts,
                                                                                                      listener_rejected,
                                                                                                      name))
            self._readq.nput( 'elasticsearch.{0}.nodes.thread.mgmt_queue {1} {2}  tags="node={3}"'.format(cluster, ts, mgmt_queue,
                                                                                               name))
            self._readq.nput( 'elasticsearch.{0}.nodes.thread.mgmt_rejected {1} {2}  tags="node={3}"'.format(cluster, ts,
                                                                                                  mgmt_rejected,
                                                                                                  name))
            self._readq.nput( 'elasticsearch.{0}.nodes.thread.search_queue {1} {2}  tags="node={3}"'.format(cluster, ts,
                                                                                                 search_queue,
                                                                                                 name))
            self._readq.nput( 'elasticsearch.{0}.nodes.thread.search_rejected {1} {2}  tags="node={3}"'.format(cluster, ts,
                                                                                                    search_rejected,
                                                                                                    name))

