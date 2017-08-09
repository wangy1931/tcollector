#!/usr/bin/env python
# setup 1: create user
# create user cloudwiz_user with password 'cloudwiz_pass';
# grant SELECT ON pg_stat_database to cloudwiz_user;

import time
import socket

try:
    import psycopg2
except ImportError:
    psycopg2 = None  # handled in main()

CONNECT_TIMEOUT = 2  # seconds

from collectors.lib.collectorbase import CollectorBase

TABLE_COUNT_LIMIT = 200
# Directories under which to search socket files
SEARCH_DIRS = frozenset([
    "/var/run/postgresql",  # Debian default
    "/var/pgsql_socket",  # MacOS default
    "/usr/local/var/postgres",  # custom compilation
    "/tmp",  # custom compilation
])


def psycopg2_connect(*args, **kwargs):
    if 'ssl' in kwargs:
        del kwargs['ssl']
    if 'unix_sock' in kwargs:
        kwargs['host'] = kwargs['unix_sock']
        del kwargs['unix_sock']
    return psycopg2.connect(*args, **kwargs)


class Postgresql(CollectorBase):
    DB_METRICS = {
        'descriptors': [
            ('datname', 'db')
        ],
        'metrics': {},
        'query': """
    SELECT datname,
           %s
      FROM pg_stat_database
     WHERE datname not ilike 'template%%'
       AND datname not ilike 'postgres'
       AND datname not ilike 'rdsadmin'
    """,
        'relation': False,
    }

    COMMON_METRICS = {
        'numbackends': 'postgresql.connections',
        'xact_commit': 'postgresql.commits',
        'xact_rollback': 'postgresql.rollbacks',
        'blks_read': 'postgresql.disk_read',
        'blks_hit': 'postgresql.buffer_hit',
        'tup_returned': 'postgresql.rows_returned',
        'tup_fetched': 'postgresql.rows_fetched',
        'tup_inserted': 'postgresql.rows_inserted',
        'tup_updated': 'postgresql.rows_updated',
        'tup_deleted': 'postgresql.rows_deleted',
    }

    DATABASE_SIZE_METRICS = {
        'pg_database_size(datname) as pg_database_size': 'postgresql.database_size',
    }

    NEWER_92_METRICS = {
        'deadlocks': 'postgresql.deadlocks',
        'temp_bytes': 'postgresql.temp_bytes',
        'temp_files': 'postgresql.temp_files',
    }

    BGW_METRICS = {
        'descriptors': [],
        'metrics': {},
        'query': "select %s FROM pg_stat_bgwriter",
        'relation': False,
    }

    COMMON_BGW_METRICS = {
        'checkpoints_timed': 'postgresql.bgwriter.checkpoints_timed',
        'checkpoints_req': 'postgresql.bgwriter.checkpoints_requested',
        'buffers_checkpoint': 'postgresql.bgwriter.buffers_checkpoint',
        'buffers_clean': 'postgresql.bgwriter.buffers_clean',
        'maxwritten_clean': 'postgresql.bgwriter.maxwritten_clean',
        'buffers_backend': 'postgresql.bgwriter.buffers_backend',
        'buffers_alloc': 'postgresql.bgwriter.buffers_alloc',
    }

    NEWER_91_BGW_METRICS = {
        'buffers_backend_fsync': 'postgresql.bgwriter.buffers_backend_fsync',
    }

    NEWER_92_BGW_METRICS = {
        'checkpoint_write_time': 'postgresql.bgwriter.write_time',
        'checkpoint_sync_time': 'postgresql.bgwriter.sync_time',
    }

    ARCHIVER_METRICS = {
        'descriptors': [],
        'metrics': {},
        'query': "select %s FROM pg_stat_archiver",
        'relation': False,
    }

    COMMON_ARCHIVER_METRICS = {
        'archived_count': 'postgresql.archiver.archived_count',
        'failed_count': 'postgresql.archiver.failed_count',
    }

    LOCK_METRICS = {
        'descriptors': [
            ('mode', 'lock_mode'),
            ('relname', 'table'),
        ],
        'metrics': {
            'lock_count': 'postgresql.locks',
        },
        'query': """
    SELECT mode,
           pc.relname,
           count(*) AS %s
      FROM pg_locks l
      JOIN pg_class pc ON (l.relation = pc.oid)
     WHERE l.mode IS NOT NULL
       AND pc.relname NOT LIKE 'pg_%%'
     GROUP BY pc.relname, mode""",
        'relation': False,
    }

    REL_METRICS = {
        'descriptors': [
            ('relname', 'table'),
            ('schemaname', 'schema'),
        ],
        'metrics': {
            'seq_scan': 'postgresql.seq_scans',
            'seq_tup_read': 'postgresql.seq_rows_read',
            'idx_scan': 'postgresql.index_scans',
            'idx_tup_fetch': 'postgresql.index_rows_fetched',
            'n_tup_ins': 'postgresql.rows_inserted',
            'n_tup_upd': 'postgresql.rows_updated',
            'n_tup_del': 'postgresql.rows_deleted',
            'n_tup_hot_upd': 'postgresql.rows_hot_updated',
            'n_live_tup': 'postgresql.live_rows',
            'n_dead_tup': 'postgresql.dead_rows',
        },
        'query': """
    SELECT relname,schemaname,%s
      FROM pg_stat_user_tables
     WHERE relname = ANY(array[%s])""",
        'relation': True,
    }

    IDX_METRICS = {
        'descriptors': [
            ('relname', 'table'),
            ('schemaname', 'schema'),
            ('indexrelname', 'index')
        ],
        'metrics': {
            'idx_scan': 'postgresql.index_scans',
            'idx_tup_read': 'postgresql.index_rows_read',
            'idx_tup_fetch': 'postgresql.index_rows_fetched',
        },
        'query': """
    SELECT relname,
           schemaname,
           indexrelname,
           %s
      FROM pg_stat_user_indexes
     WHERE relname = ANY(array[%s])""",
        'relation': True,
    }

    SIZE_METRICS = {
        'descriptors': [
            ('relname', 'table'),
        ],
        'metrics': {
            'pg_table_size(C.oid) as table_size': 'postgresql.table_size',
            'pg_indexes_size(C.oid) as index_size': 'postgresql.index_size',
            'pg_total_relation_size(C.oid) as total_size': 'postgresql.total_size',
        },
        'relation': True,
        'query': """
    SELECT
      relname,
      %s
    FROM pg_class C
    LEFT JOIN pg_namespace N ON (N.oid = C.relnamespace)
    WHERE nspname NOT IN ('pg_catalog', 'information_schema') AND
      nspname !~ '^pg_toast' AND
      relkind IN ('r') AND
      relname = ANY(array[%s])"""
    }

    COUNT_METRICS = {
        'descriptors': [
            ('schemaname', 'schema')
        ],
        'metrics': {
            'pg_stat_user_tables': 'postgresql.table.count',
        },
        'relation': False,
        'query': """
    SELECT schemaname, count(*) FROM
    (
      SELECT schemaname
      FROM %s
      ORDER BY schemaname, relname
      LIMIT {table_count_limit}
    ) AS subquery GROUP BY schemaname
            """.format(table_count_limit=TABLE_COUNT_LIMIT)
    }

    REPLICATION_METRICS_9_1 = {
        'CASE WHEN pg_last_xlog_receive_location() = pg_last_xlog_replay_location() THEN 0 ELSE GREATEST (0, EXTRACT (EPOCH FROM now() - pg_last_xact_replay_timestamp())) END':
            'postgresql.replication_delay',
    }

    REPLICATION_METRICS_9_2 = {
        'abs(pg_xlog_location_diff(pg_last_xlog_receive_location(), pg_last_xlog_replay_location())) AS replication_delay_bytes':
            'postgres.replication_delay_bytes'
    }

    REPLICATION_METRICS = {
        'descriptors': [],
        'metrics': {},
        'relation': False,
        'query': """
    SELECT %s
     WHERE (SELECT pg_is_in_recovery())"""
    }

    CONNECTION_METRICS = {
        'descriptors': [],
        'metrics': {
            'MAX(setting) AS max_connections': 'postgresql.max_connections',
            'SUM(numbackends)/MAX(setting) AS pct_connections': 'postgresql.percent_usage_connections',
        },
        'relation': False,
        'query': """
    WITH max_con AS (SELECT setting::float FROM pg_settings WHERE name = 'max_connections')
    SELECT %s
      FROM pg_stat_database, max_con
    """
    }

    STATIO_METRICS = {
        'descriptors': [
            ('relname', 'table'),
            ('schemaname', 'schema')
        ],
        'metrics': {
            'heap_blks_read': 'postgresql.heap_blocks_read',
            'heap_blks_hit': 'postgresql.heap_blocks_hit',
            'idx_blks_read': 'postgresql.index_blocks_read',
            'idx_blks_hit': 'postgresql.index_blocks_hit',
            'toast_blks_read': 'postgresql.toast_blocks_read',
            'toast_blks_hit': 'postgresql.toast_blocks_hit',
            'tidx_blks_read': 'postgresql.toast_index_blocks_read',
            'tidx_blks_hit': 'postgresql.toast_index_blocks_hit',
        },
        'query': """
    SELECT relname,
           schemaname,
           %s
      FROM pg_statio_user_tables
     WHERE relname = ANY(array[%s])""",
        'relation': True,
    }

    FUNCTION_METRICS = {
        'descriptors': [
            ('schemaname', 'schema'),
            ('funcname', 'function'),
        ],
        'metrics': {
            'calls': 'postgresql.function.calls',
            'total_time': 'postgresql.function.total_time',
            'self_time': 'postgresql.function.self_time',
        },
        'query': """
    WITH overloaded_funcs AS (
     SELECT funcname
       FROM pg_stat_user_functions s
      GROUP BY s.funcname
     HAVING COUNT(*) > 1
    )
    SELECT s.schemaname,
           CASE WHEN o.funcname is null THEN p.proname
                else p.proname || '_' || array_to_string(p.proargnames, '_')
            END funcname,
            %s
      FROM pg_proc p
      JOIN pg_stat_user_functions s
        ON p.oid = s.funcid
      LEFT join overloaded_funcs o
        ON o.funcname = s.funcname;
    """,
        'relation': False
    }

    def __init__(self, config, logger, readq):
        super(Postgresql, self).__init__(config, logger, readq)
        self.dbs = {}
        self.versions = {}
        self.instance_metrics = {}
        self.bgw_metrics = {}
        self.archiver_metrics = {}
        self.db_instance_metrics = []
        self.db_bgw_metrics = []
        self.db_archiver_metrics = []
        self.replication_metrics = {}
        self.custom_metrics = {}

        if psycopg2 is None:
            raise Exception("error: Python module 'psycopg2' is missing")  # Ask tcollector to not respawn us

        self.host = self.get_config('host')
        self.port = self.get_config('port', '5432')
        self.user = self.get_config('user', 'cloudwiz_user')
        self.password = self.get_config('password', 'cloudwiz_pass')
        self.dbname = self.get_config('dbname', None)
        self.relations = eval(self.get_config('relations', '[]'))
        self.key = (self.host, self.port, self.dbname)

        if self.relations and not self.dbname:
            self.log_warn('"dbname" parameter must be set when using the "relations" parameter.')

        if self.dbname is None:
            self.dbname = 'postgres'

    def __call__(self):
        count_metrics = True
        database_size_metrics = True
        function_metrics = True
        connect_fct, interface_error, programming_error = self._get_pg_attrs()
        try:
            self.db = self.get_connection(self.key, self.host, self.port, self.user, self.password, self.dbname,
                                          connect_fct)
            version = self._get_version(self.key, self.db)
            self.log_info("Running check against version %s" % version)
            self._collect_stats(self.key, self.db, self.relations, function_metrics, count_metrics,
                                database_size_metrics, interface_error, programming_error)
        except Exception:
            self.log_error("Failed to connect")
            self.log_info("Resetting the connection")
            self.db = self.get_connection(self.key, self.host, self.port, self.user, self.password, self.dbname,
                                          connect_fct, use_cached=False)
            self._collect_stats(self.key, self.db, self.relations, function_metrics, count_metrics,
                                database_size_metrics, interface_error, programming_error)

        if self.db is not None:
            try:
                # commit to close the current query transaction
                self.db.commit()
            except Exception as e:
                self.log_warn("Unable to commit: {0}".format(e))

    def _build_relations_config(self, relations):
        """Builds a dictionary from relations configuration while maintaining compatibility
        """
        config = {}
        for relation in relations:
            config[relation] = {'relation_name': relation, 'schemas': []}

        return config

    # Core function
    def _collect_stats(self, key, db, relations, function_metrics, count_metrics, database_size_metrics,
                       interface_error, programming_error):
        """Query pg_stat_* for various metrics
        If relations is not an empty list, gather per-relation metrics
        on top of that.
        If custom_metrics is not an empty list, gather custom metrics defined in postgres.yaml
        """

        metric_scope = [
            self.CONNECTION_METRICS,
            self.LOCK_METRICS,
        ]

        if function_metrics:
            metric_scope.append(self.FUNCTION_METRICS)

        if count_metrics:
            metric_scope.append(self.COUNT_METRICS)

        # These are added only once per PG server, thus the test
        db_instance_metrics = self._get_instance_metrics(key, db, database_size_metrics)
        bgw_instance_metrics = self._get_bgw_metrics(key, db)
        archiver_instance_metrics = self._get_archiver_metrics(key, db)

        if db_instance_metrics is not None:
            self.DB_METRICS['metrics'] = db_instance_metrics
            metric_scope.append(self.DB_METRICS)

        if bgw_instance_metrics is not None:
            self.BGW_METRICS['metrics'] = bgw_instance_metrics
            metric_scope.append(self.BGW_METRICS)

        if archiver_instance_metrics is not None:
            self.ARCHIVER_METRICS['metrics'] = archiver_instance_metrics
            metric_scope.append(self.ARCHIVER_METRICS)

        if relations:
            metric_scope += [
                self.REL_METRICS,
                self.IDX_METRICS,
                self.SIZE_METRICS,
                self.STATIO_METRICS
            ]
        relations_config = self._build_relations_config(relations)

        replication_metrics = self._get_replication_metrics(key, db)
        if replication_metrics is not None:
            self.REPLICATION_METRICS['metrics'] = replication_metrics
            metric_scope.append(self.REPLICATION_METRICS)

        full_metric_scope = list(metric_scope)

        try:
            cursor = db.cursor()

            for scope in full_metric_scope:
                # build query
                cols = scope['metrics'].keys()  # list of metrics to query, in some order
                # we must remember that order to parse results
                try:
                    if scope['relation'] and len(relations) > 0:
                        relnames = ', '.join("'{0}'".format(w) for w in relations_config.iterkeys())
                        query = scope['query'] % (", ".join(cols), "%s")  # Keep the last %s intact
                        self.log_info("Running query: %s with relations: %s" % (query, relnames))
                        cursor.execute(query % (relnames))
                    else:
                        query = scope['query'] % (", ".join(cols))
                        self.log_info("Running query: %s" % query)
                        cursor.execute(query.replace(r'%', r'%%'))

                    results = cursor.fetchall()
                except programming_error as e:
                    self.log_error("Not all metrics may be available: %s" % str(e))
                    continue

                if not results:
                    continue

                if scope == self.DB_METRICS:
                    self._readq.nput("postgresql.db.count %i %d" % (time.time(), len(results)))

                desc = scope['descriptors']

                # parse & submit results
                # A row should look like this
                # (descriptor, descriptor, ..., value, value, value, value, ...)
                # with descriptor a PG relation or index name, which we use to create the tags
                for row in results:
                    # Check that all columns will be processed
                    assert len(row) == len(cols) + len(desc)

                    # build a map of descriptors and their values
                    desc_map = dict(zip([x[1] for x in desc], row[0:len(desc)]))
                    # Build tags
                    # descriptors are: (pg_name, dd_tag_name): value
                    # Special-case the "db" tag, which overrides the one that is passed as instance_tag
                    # The reason is that pg_stat_database returns all databases regardless of the
                    # connection.
                    tags = []
                    tags += [("%s=%s" % (k, v)) for (k, v) in desc_map.iteritems()]

                    # [(metric-map, value), (metric-map, value), ...]
                    # metric-map is: (dd_name, "float"|"float")
                    # shift the results since the first columns will be the "descriptors"
                    values = zip([scope['metrics'][c] for c in cols], row[len(desc):])
                    # To submit simply call the function for each value v
                    # v[0] == (metric_name, submit_function)
                    # v[1] == the actual value
                    # tags are
                    for v in values:
                        if v[1] == None:
                            self._readq.nput("%s %i %s" % (v[0], time.time(), 0))
                        else:
                            self._readq.nput("%s %i %s" % (v[0], time.time(), v[1]))

            cursor.close()
        except interface_error as e:
            self.log_error("Connection error: %s" % str(e))
            raise Exception
        except socket.error as e:
            self.log_error("Connection error: %s" % str(e))
            raise Exception

    def _get_pg_attrs(self):
        if psycopg2 is None:
            self.log_error("Unable to import psycopg2, falling back to pg8000")
        else:
            return psycopg2_connect, psycopg2.InterfaceError, psycopg2.ProgrammingError

    def _get_version(self, key, db):
        if key not in self.versions:
            cursor = db.cursor()
            cursor.execute('SHOW SERVER_VERSION;')
            result = cursor.fetchone()
            try:
                version = map(int, result[0].split('.'))
            except Exception:
                version = result[0]
            self.versions[key] = version
        return self.versions[key]

    def _get_instance_metrics(self, key, db, database_size_metrics):
        """Use either COMMON_METRICS or COMMON_METRICS + NEWER_92_METRICS
        depending on the postgres version.
        Uses a dictionnary to save the result for each instance
        """
        # Extended 9.2+ metrics if needed
        metrics = self.instance_metrics.get(key)

        if metrics is None:
            # Hack to make sure that if we have multiple instances that connect to
            # the same host, port, we don't collect metrics twice
            # as it will result in https://github.com/DataDog/dd-agent/issues/1211
            sub_key = key[:2]
            if sub_key in self.db_instance_metrics:
                self.instance_metrics[key] = None
                self.log_info("Not collecting instance metrics for key: {0} as"
                              " they are already collected by another instance".format(key))
                return None

            self.db_instance_metrics.append(sub_key)

            if self._is_9_2_or_above(key, db):
                self.instance_metrics[key] = dict(self.COMMON_METRICS, **self.NEWER_92_METRICS)
            else:
                self.instance_metrics[key] = dict(self.COMMON_METRICS)

            if database_size_metrics:
                self.instance_metrics[key] = dict(self.instance_metrics[key], **self.DATABASE_SIZE_METRICS)

            metrics = self.instance_metrics.get(key)
        return metrics

    def _get_bgw_metrics(self, key, db):
        """Use either COMMON_BGW_METRICS or COMMON_BGW_METRICS + NEWER_92_BGW_METRICS
        depending on the postgres version.
        Uses a dictionnary to save the result for each instance
        """
        # Extended 9.2+ metrics if needed
        metrics = self.bgw_metrics.get(key)

        if metrics is None:
            # Hack to make sure that if we have multiple instances that connect to
            # the same host, port, we don't collect metrics twice
            # as it will result in https://github.com/DataDog/dd-agent/issues/1211
            sub_key = key[:2]
            if sub_key in self.db_bgw_metrics:
                self.bgw_metrics[key] = None
                self.log_info("Not collecting bgw metrics for key: {0} as"
                              " they are already collected by another instance".format(key))
                return None

            self.db_bgw_metrics.append(sub_key)

            self.bgw_metrics[key] = dict(self.COMMON_BGW_METRICS)
            if self._is_9_1_or_above(key, db):
                self.bgw_metrics[key].update(self.NEWER_91_BGW_METRICS)
            if self._is_9_2_or_above(key, db):
                self.bgw_metrics[key].update(self.NEWER_92_BGW_METRICS)
            metrics = self.bgw_metrics.get(key)
        return metrics

    def _get_archiver_metrics(self, key, db):
        """Use COMMON_ARCHIVER_METRICS to read from pg_stat_archiver as
        defined in 9.4 (first version to have this table).
        Uses a dictionary to save the result for each instance
        """
        # While there's only one set for now, prepare for future additions to
        # the table, mirroring _get_bgw_metrics()
        metrics = self.archiver_metrics.get(key)

        if self._is_9_4_or_above(key, db) and metrics is None:
            # Collect from only one instance. See _get_bgw_metrics() for details on why.
            sub_key = key[:2]
            if sub_key in self.db_archiver_metrics:
                self.archiver_metrics[key] = None
                self.log_info("Not collecting archiver metrics for key: {0} as"
                              " they are already collected by another instance".format(key))
                return None

            self.db_archiver_metrics.append(sub_key)

            self.archiver_metrics[key] = dict(self.COMMON_ARCHIVER_METRICS)
            metrics = self.archiver_metrics.get(key)
        return metrics

    def _get_replication_metrics(self, key, db):
        """ Use either REPLICATION_METRICS_9_1 or REPLICATION_METRICS_9_1 + REPLICATION_METRICS_9_2
        depending on the postgres version.
        Uses a dictionnary to save the result for each instance
        """
        metrics = self.replication_metrics.get(key)
        if self._is_9_1_or_above(key, db) and metrics is None:
            self.replication_metrics[key] = dict(self.REPLICATION_METRICS_9_1)
            if self._is_9_2_or_above(key, db):
                self.replication_metrics[key].update(self.REPLICATION_METRICS_9_2)
            metrics = self.replication_metrics.get(key)
        return metrics

    def _is_above(self, key, db, version_to_compare):
        version = self._get_version(key, db)
        if type(version) == list:
            return version >= version_to_compare

        return False

    def _is_9_1_or_above(self, key, db):
        return self._is_above(key, db, [9, 1, 0])

    def _is_9_2_or_above(self, key, db):
        return self._is_above(key, db, [9, 2, 0])

    def _is_9_4_or_above(self, key, db):
        return self._is_above(key, db, [9, 4, 0])

    def get_connection(self, key, host, port, user, password, dbname, connect_fct, use_cached=True):
        "Get and memoize connections to instances"
        if key in self.dbs and use_cached:
            return self.dbs[key]

        elif host != "" and user != "":
            try:
                if host == 'localhost' and password == '':
                    # Use ident method
                    connection = connect_fct("user=%s dbname=%s" % (user, dbname))
                elif port != '':
                    connection = connect_fct(host=host, port=port, user=user,
                                             password=password, database=dbname)
                elif host.startswith('/'):
                    # If the hostname starts with /, it's probably a path
                    # to a UNIX socket. This is similar behaviour to psql
                    connection = connect_fct(unix_sock=host, user=user,
                                             password=password, database=dbname)
                else:
                    connection = connect_fct(host=host, user=user, password=password,
                                             database=dbname)
                self._readq.nput("postgresql.state %i 0" % time.time())
            except Exception as e:
                self._readq.nput("postgresql.state %i 1" % time.time())
                message = u'Error establishing postgres connection: %s' % (str(e))
                self.log_error(message)
        else:
            if not host:
                raise Exception("Please specify a Postgres host to connect to.")
            elif not user:
                raise Exception("Please specify a user to connect to Postgres as.")
            self._readq.nput("postgresql.state %i 1" % time.time())
        self.dbs[key] = connection
        return connection
