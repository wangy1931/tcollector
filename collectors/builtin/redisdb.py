
from collectors.lib.collectorbase import CollectorBase
from collections import defaultdict
import re
import time
import redis


class Redisdb(CollectorBase):
    DEFAULT_MAX_SLOW_ENTRIES = 128
    MAX_SLOW_ENTRIES_KEY = "slowlog-max-len"
    REPL_KEY = 'master_link_status'
    LINK_DOWN_KEY = 'master_link_down_since_seconds'
    db_key_pattern = re.compile(r'^db\d+')
    subkeys = ['keys', 'expires']
    slave_key_pattern = re.compile(r'^slave\d+')
    GAUGE_KEYS = {
        # Append-only metrics
        'aof_last_rewrite_time_sec':    'redis.aof.last_rewrite_time',
        'aof_rewrite_in_progress':      'redis.aof.rewrite',
        'aof_current_size':             'redis.aof.size',
        'aof_buffer_length':            'redis.aof.buffer_length',

        # Network
        'connected_clients':            'redis.net.clients',
        'connected_slaves':             'redis.net.slaves',
        'rejected_connections':         'redis.net.rejected',

        # clients
        'blocked_clients':              'redis.clients.blocked',
        'client_biggest_input_buf':     'redis.clients.biggest_input_buf',
        'client_longest_output_list':   'redis.clients.longest_output_list',

        # Keys
        'evicted_keys':                 'redis.keys.evicted',
        'expired_keys':                 'redis.keys.expired',

        # stats
        'latest_fork_usec':             'redis.perf.latest_fork_usec',
        'bytes_received_per_sec':       'redis.bytes_received_per_sec',
        'bytes_sent_per_sec':           'redis.bytes_sent_per_sec',
        # Note: 'bytes_received_per_sec' and 'bytes_sent_per_sec' are only
        # available on Azure Redis

        # pubsub
        'pubsub_channels':              'redis.pubsub.channels',
        'pubsub_patterns':              'redis.pubsub.patterns',

        # rdb
        'rdb_bgsave_in_progress':       'redis.rdb.bgsave',
        'rdb_changes_since_last_save':  'redis.rdb.changes_since_last',
        'rdb_last_bgsave_time_sec':     'redis.rdb.last_bgsave_time',

        # memory
        'mem_fragmentation_ratio':      'redis.mem.fragmentation_ratio',
        'used_memory':                  'redis.mem.used',
        'used_memory_lua':              'redis.mem.lua',
        'used_memory_peak':             'redis.mem.peak',
        'used_memory_rss':              'redis.mem.rss',

        # replication
        'master_last_io_seconds_ago':   'redis.replication.last_io_seconds_ago',
        'master_sync_in_progress':      'redis.replication.sync',
        'master_sync_left_bytes':       'redis.replication.sync_left_bytes',
        'repl_backlog_histlen':         'redis.replication.backlog_histlen',
        'master_repl_offset':           'redis.replication.master_repl_offset',
        'slave_repl_offset':            'redis.replication.slave_repl_offset'
    }
    RATE_KEYS = {
        # cpu
        'used_cpu_sys': 'redis.cpu.sys',
        'used_cpu_sys_children': 'redis.cpu.sys_children',
        'used_cpu_user': 'redis.cpu.user',
        'used_cpu_user_children': 'redis.cpu.user_children',

        # stats
        'keyspace_hits': 'redis.stats.keyspace_hits',
        'keyspace_misses': 'redis.stats.keyspace_misses',
    }

    def __init__(self, config, logger, readq):
        super(Redisdb, self).__init__(config, logger, readq)
        self.redis_key = (self.get_config('host'),self.get_config('port'),self.get_config('db'))
        self.conf_dict={}
        self.connections = {}
        self._parse_from_conf_to_dict(config)
        self.last_timestamp_seen = defaultdict(int)

    def __call__(self):
        self.ts=time.time()
        self.check()


    def _parse_from_conf_to_dict(self,config):
        for key,value in config.items('base'):
            self.conf_dict[key]=value

    def _parse_dict_string(self, string, key, default):
        try:
            for item in string.split(','):
                k, v = item.rsplit('=', 1)
                if k == key:
                    try:
                        return int(v)
                    except ValueError:
                        return v
            return default
        except Exception:
            self.log_error("Cannot parse dictionary string: %s" % string)
            return default

    def _get_conn(self):
        key = self.redis_key
        if key not in self.connections:
            try:
                list_params = ['host', 'port', 'db', 'password', 'socket_timeout',
                               'connection_pool', 'charset', 'errors', 'unix_socket_path', 'ssl',
                               'ssl_certfile', 'ssl_keyfile', 'ssl_ca_certs', 'ssl_cert_reqs']

                self.conf_dict['socket_timeout'] = self.conf_dict.get('socket_timeout', 5)
                connection_params = dict((k, self.conf_dict[k]) for k in list_params if k in self.conf_dict)
                self.connections[key] = redis.Redis(**connection_params)
            except Exception :
                self.log_error("You need a redis library that supports authenticated connections. Try sudo easy_install redis.")
                self.send_info_guage("redis.state","1")

        return self.connections[key]

    def _check_db(self, custom_tags=None):
        conn = self._get_conn()
        tags = custom_tags
        start = time.time()
        try:
            info = conn.info()
            tags = sorted(tags + ["redis_role=%s" % info["role"]])
            self.send_info_guage('redis.state', "0")
        except ValueError:
            self.send_info_guage('redis.state', "1")
        except Exception:
            self.send_info_guage('redis.state', "1")

        latency_ms = round((time.time() - start) * 1000, 2)
        self.send_info_guage('redis.info.latency_ms', latency_ms, tags=tags)

        for key in info.keys():
            if self.db_key_pattern.match(key):
                db_tags = list(tags) + ["redis_db=" + key]
                expires_keys = info[key]["expires"]
                total_keys = info[key]["keys"]
                persist_keys = total_keys - expires_keys
                self.send_info_guage("redis.persist", persist_keys,db_tags)
                self.send_info_guage("redis.persist.percent", 100.0 * persist_keys / total_keys,db_tags)
                self.send_info_guage("redis.expires.percent", 100.0 * expires_keys / total_keys,db_tags)

                for subkey in self.subkeys:
                    val = -1
                    try:
                        val = info[key].get(subkey, -1)
                    except AttributeError:
                        val = self._parse_dict_string(info[key], subkey, -1)
                    metric = '.'.join(['redis', subkey])
                    self.send_info_guage(metric,val,tags=db_tags)



        for info_name, value in info.iteritems():
            if info_name in self.GAUGE_KEYS:
                self.send_info_guage(self.GAUGE_KEYS[info_name], info[info_name], tags=tags)
            elif info_name in self.RATE_KEYS:
                self.send_info_rate(self.RATE_KEYS[info_name], info[info_name], tags=tags)

        self.send_info_rate('redis.net.commands', info['total_commands_processed'], tags=tags)
        key_list =self.conf_dict.get('keys')

        if key_list is not None:
            if not isinstance(key_list, list) or len(key_list) == 0:
                self.log_warn("keys in redis configuration is either not a list or empty")
            else:
                l_tags = list(tags)
                for key in key_list:
                    key_type = conn.type(key)
                    key_tags = l_tags + ['key=' + key]

                    if key_type == 'list':
                        self.send_info_guage('redis.key.length', conn.llen(key), tags=key_tags)
                    elif key_type == 'set':
                        self.send_info_guage('redis.key.length', conn.scard(key), tags=key_tags)
                    elif key_type == 'zset':
                        self.send_info_guage('redis.key.length', conn.zcard(key), tags=key_tags)
                    elif key_type == 'hash':
                        self.send_info_guage('redis.key.length', conn.hlen(key), tags=key_tags)
                    else:
                        if self.conf_dict.get("warn_on_missing_keys", True):
                            self.log_warn("{0} key not found in redis".format(key))
                        self.send_info_guage('redis.key.length', 0, tags=key_tags)

        self._check_replication(info, tags)
        if self.conf_dict.get("command_stats", False):
            self._check_command_stats(conn, tags)

    def _check_replication(self, info, tags):
        for key in info:
            if self.slave_key_pattern.match(key) and isinstance(info[key], dict):
                slave_offset = info[key].get('offset')
                master_offset = info.get('master_repl_offset')
                if slave_offset and master_offset and master_offset - slave_offset >= 0:
                    delay = master_offset - slave_offset
                    slave_tags = tags[:]
                    for slave_tag in ('ip', 'port'):
                        if slave_tag in info[key]:
                            slave_tags.append('slave_{0}:{1}'.format(slave_tag, info[key][slave_tag]))
                    slave_tags.append('slave_id:%s' % key.lstrip('slave'))
                    self.send_info_guage('redis.replication.delay', delay, tags=slave_tags)

        if self.REPL_KEY in info:
            if info[self.REPL_KEY] == 'up':
                status ="0"
                down_seconds = 0
            else:
                status = "1"
                down_seconds = info[self.LINK_DOWN_KEY]

            self.send_info_guage('redis.replication.master_link_status', status, tags=tags)
            self.send_info_guage('redis.replication.master_link_down_since_seconds', down_seconds, tags=tags)

    def _check_slowlog(self, custom_tags):
        conn = self._get_conn()
        tags = custom_tags
        if not self.conf_dict.get(self.MAX_SLOW_ENTRIES_KEY):
            try:
                max_slow_entries = int(conn.config_get(self.MAX_SLOW_ENTRIES_KEY)[self.MAX_SLOW_ENTRIES_KEY])
                if max_slow_entries > self.DEFAULT_MAX_SLOW_ENTRIES:
                    self.log_warn("Redis {0} is higher than {1}. Defaulting to {1}."
                                 "If you need a higher value, please set {0} in your check config"
                                 .format(self.MAX_SLOW_ENTRIES_KEY, self.DEFAULT_MAX_SLOW_ENTRIES))
            except redis.ResponseError:
                max_slow_entries = self.DEFAULT_MAX_SLOW_ENTRIES
        else:
            max_slow_entries = int(self.conf_dict.get(self.MAX_SLOW_ENTRIES_KEY))

        ts_key = self.redis_key
        slowlogs = conn.slowlog_get(max_slow_entries)

        slowlogs = [s for s in slowlogs if s['start_time'] >self.last_timestamp_seen[ts_key]]

        max_ts = 0
        for slowlog in slowlogs:
            if slowlog['start_time'] > max_ts:
                max_ts = slowlog['start_time']
            slowlog_tags = list(tags)
            command = slowlog['command'].split()
            if command:
                slowlog_tags.append('command:{0}'.format(command[0]))

            value = slowlog['duration']
            self.send_info_guage('redis.slowlog.micros', value, tags=slowlog_tags)

        self.last_timestamp_seen[ts_key] = max_ts

    def _check_command_stats(self, conn, tags):
        try:
            command_stats = conn.info("commandstats")
        except Exception:
            self.log_warn("Could not retrieve command stats from Redis."
                         "INFO COMMANDSTATS only works with Redis >= 2.6.")
            return

        for key, stats in command_stats.iteritems():
            command = key.split('_', 1)[1]
            command_tags = tags + ['command:%s' % command]
            self.send_info_guage('redis.command.calls', stats['calls'], tags=command_tags)
            self.send_info_guage('redis.command.usec_per_call', stats['usec_per_call'], tags=command_tags)

    def check(self):
        if ("host" not in self.conf_dict or "port" not in self.conf_dict) and "unix_socket_path" not in self.conf_dict:
            raise Exception("You must specify a host/port couple or a unix_socket_path")
        custom_tags = self.conf_dict.get('tags', [])
        self._check_db(custom_tags)
        self._check_slowlog(custom_tags)

