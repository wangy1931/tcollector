#!/usr/bin/python

import time
import json
import urllib2
from collectors.lib.collectorbase import CollectorBase


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
        try:
            line = urllib2.urlopen(self.es_url_health, timeout=20).read()
            if line != "":
                list = line.split(" ")
                if len(list)>=14:
                    timestamp = list[0]
                    cluster=list[2]
                    status = self.es_status_dict[list[3]]
                    total = list[4]
                    data = list[5]
                    shards_total = list[6]
                    shards_primary = list[7]
                    shards_relocating = list[8]
                    shards_initializing = list[9]
                    shards_unassigned = list[10]
                    shards_active = list[13].replace("%", "")
                    self._readq.nput("elasticsearch.status %s %s cluster=%s" % (timestamp, status,cluster))
                    self._readq.nput("elasticsearch.node.total %s %s cluster=%s" % (timestamp, total,cluster))
                    self._readq.nput("elasticsearch.node.data %s %s cluster=%s" % (timestamp, data,cluster))
                    self._readq.nput("elasticsearch.shards.total %s %s cluster=%s" % (timestamp, shards_total,cluster))
                    self._readq.nput("elasticsearch.shards.primary %s %s cluster=%s" % (timestamp, shards_primary,cluster))
                    self._readq.nput("elasticsearch.shards.relocating %s %s cluster=%s" % (timestamp, shards_relocating,cluster))
                    self._readq.nput("elasticsearch.shards.initializing %s %s cluster=%s" % (timestamp, shards_initializing,cluster))
                    self._readq.nput("elasticsearch.shards.unassigned %s %s cluster=%s" % (timestamp, shards_unassigned,cluster))
                    self._readq.nput("elasticsearch.shards.active %s %s cluster=%s" % (timestamp, shards_active,cluster))
                else:
                    self.log_warn("get es health fail!!")
        except Exception,e:
            self.log_exception("get es health fail!!url is %s"%self.es_url_health)
            raise

    def collect_es_node(self):
        try:
            response = urllib2.urlopen(self.es_url_node, timeout=20).read()
            ts = int(time.time())
            parsed = json.loads(response)
            cluster = parsed['cluster_name'].lower()
            for node in parsed['nodes']:
                # collecting metrics
                name = "_".join(parsed['nodes'][node]['name'].lower().split())
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
                self._readq.nput( 'elasticsearch.nodes.indices.docs_count {1} {2}  node={3} cluster={0}'.format(cluster, ts, docs_count,
                                                                                                    name))
                self._readq.nput( 'elasticsearch.nodes.indices.bytes_count {1} {2}  node={3} cluster={0}'.format(cluster, ts,
                                                                                                     bytes_count,
                                                                                                     name))
                self._readq.nput( 'elasticsearch.nodes.indices.throttle_ms {1} {2}  node={3} cluster={0}'.format(cluster, ts,
                                                                                                     throttle_ms,
                                                                                                     name))
                self._readq.nput( 'elasticsearch.nodes.indices.index_total {1} {2}  node={3} cluster={0}'.format(cluster, ts,
                                                                                                     index_total,
                                                                                                     name))
                self._readq.nput( 'elasticsearch.nodes.indices.index_avg {1} {2}  node={3} cluster={0}'.format(cluster, ts, index_avg,
                                                                                                   name))
                self._readq.nput( 'elasticsearch.nodes.indices.index_current {1} {2}  node={3} cluster={0}'.format(cluster, ts,
                                                                                                       index_current,
                                                                                                       name))
                self._readq.nput( 'elasticsearch.nodes.indices.index_failed {1} {2}  node={3} cluster={0}'.format(cluster, ts,
                                                                                                      index_failed,
                                                                                                      name))
                self._readq.nput( 'elasticsearch.nodes.indices.query_current {1} {2}  node={3} cluster={0}'.format(cluster, ts,
                                                                                                       query_current,
                                                                                                       name))
                self._readq.nput( 'elasticsearch.nodes.indices.query_total {1} {2}  node={3} cluster={0}'.format(cluster, ts,
                                                                                                     query_total,
                                                                                                     name))
                self._readq.nput( 'elasticsearch.nodes.indices.query_avg {1} {2}  node={3} cluster={0}'.format(cluster, ts, query_avg,
                                                                                                   name))
                self._readq.nput( 'elasticsearch.nodes.indices.fetch_current {1} {2}  node={3} cluster={0}'.format(cluster, ts,
                                                                                                       fetch_current,
                                                                                                       name))
                self._readq.nput( 'elasticsearch.nodes.indices.fetch_total {1} {2}  node={3} cluster={0}'.format(cluster, ts,
                                                                                                     fetch_total,
                                                                                                     name))
                self._readq.nput( 'elasticsearch.nodes.indices.fetch_avg {1} {2}  node={3} cluster={0}'.format(cluster, ts, fetch_avg,
                                                                                                   name))
                self._readq.nput( 'elasticsearch.nodes.indices.fielddata_size {1} {2}  node={3} cluster={0}'.format(cluster, ts,
                                                                                                        fielddata_size,
                                                                                                        name))
                self._readq.nput( 'elasticsearch.nodes.indices.fielddata_evictions {1} {2}  node={3} cluster={0}'.format(cluster, ts,
                                                                                                             fielddata_evictions,
                                                                                                             name))
                self._readq.nput( 'elasticsearch.nodes.indices.query_cache_bytes {1} {2}  node={3} cluster={0}'.format(cluster, ts,
                                                                                                           query_cache_bytes,
                                                                                                           name))
                self._readq.nput( 'elasticsearch.nodes.indices.query_evictions {1} {2}  node={3} cluster={0}'.format(cluster, ts,
                                                                                                         query_evictions,
                                                                                                         name))
                self._readq.nput( 'elasticsearch.nodes.jvm.young_count {1} {2}  node={3} cluster={0}'.format(cluster, ts, young_count,
                                                                                                 name))
                self._readq.nput( 'elasticsearch.nodes.jvm.young_avg {1} {2}  node={3} cluster={0}'.format(cluster, ts, young_avg,
                                                                                               name))
                self._readq.nput( 'elasticsearch.nodes.jvm.old_count {1} {2}  node={3} cluster={0}'.format(cluster, ts, old_count,
                                                                                               name))
                self._readq.nput( 'elasticsearch.nodes.jvm.old_avg {1} {2}  node={3} cluster={0}'.format(cluster, ts, old_avg,
                                                                                             name))
                self._readq.nput( 'elasticsearch.nodes.jvm.heap_used_pct {1} {2}  node={3} cluster={0}'.format(cluster, ts,
                                                                                                   heap_used_pct,
                                                                                                   name))
                self._readq.nput( 'elasticsearch.nodes.jvm.heap_committed {1} {2}  node={3} cluster={0}'.format(cluster, ts,
                                                                                                    heap_committed,
                                                                                                    name))
                self._readq.nput( 'elasticsearch.nodes.os.cpu_pct {1} {2}  node={3} cluster={0}'.format(cluster, ts, cpu_pct,
                                                                                            name))
                self._readq.nput( 'elasticsearch.nodes.os.cpu_load {1} {2}  node={3} cluster={0}'.format(cluster, ts, cpu_load,
                                                                                             name))
                self._readq.nput( 'elasticsearch.nodes.os.mem_swap_used {1} {2}  node={3} cluster={0}'.format(cluster, ts,
                                                                                                  mem_swap_used,
                                                                                                  name))
                self._readq.nput( 'elasticsearch.nodes.http.current_open {1} {2}  node={3} cluster={0}'.format(cluster, ts, http_open,
                                                                                                   name))
                self._readq.nput( 'elasticsearch.nodes.thread.bulk_queue {1} {2}  node={3} cluster={0}'.format(cluster, ts, bulk_queue,
                                                                                                   name))
                self._readq.nput( 'elasticsearch.nodes.thread.bulk_rejected {1} {2}  node={3} cluster={0}'.format(cluster, ts,
                                                                                                      bulk_rejected,
                                                                                                      name))
                self._readq.nput( 'elasticsearch.nodes.thread.flush_queue {1} {2}  node={3} cluster={0}'.format(cluster, ts,
                                                                                                    flush_queue,
                                                                                                    name))
                self._readq.nput( 'elasticsearch.nodes.thread.flush_rejected {1} {2}  node={3} cluster={0}'.format(cluster, ts,
                                                                                                       flush_rejected,
                                                                                                       name))
                self._readq.nput( 'elasticsearch.nodes.thread.index_queue {1} {2}  node={3} cluster={0}'.format(cluster, ts,
                                                                                                    index_queue,
                                                                                                    name))
                self._readq.nput( 'elasticsearch.nodes.thread.index_rejected {1} {2}  node={3} cluster={0}'.format(cluster, ts,
                                                                                                       index_rejected,
                                                                                                       name))
                self._readq.nput( 'elasticsearch.nodes.thread.listener_queue {1} {2}  node={3} cluster={0}'.format(cluster, ts,
                                                                                                       listener_queue,
                                                                                                       name))
                self._readq.nput( 'elasticsearch.nodes.thread.listener_rejected {1} {2}  node={3} cluster={0}'.format(cluster, ts,
                                                                                                          listener_rejected,
                                                                                                          name))
                self._readq.nput( 'elasticsearch.nodes.thread.mgmt_queue {1} {2}  node={3} cluster={0}'.format(cluster, ts, mgmt_queue,
                                                                                                   name))
                self._readq.nput( 'elasticsearch.nodes.thread.mgmt_rejected {1} {2}  node={3} cluster={0}'.format(cluster, ts,
                                                                                                      mgmt_rejected,
                                                                                                      name))
                self._readq.nput( 'elasticsearch.nodes.thread.search_queue {1} {2}  node={3} cluster={0}'.format(cluster, ts,
                                                                                                     search_queue,
                                                                                                     name))
                self._readq.nput( 'elasticsearch.nodes.thread.search_rejected {1} {2}  node={3} cluster={0}'.format(cluster, ts,
                                                                                                        search_rejected,
                                                                                                        name))
        except Exception,e:
            self.log_exception("get es node fail!!url is %s" % self.es_url_node)
            raise
