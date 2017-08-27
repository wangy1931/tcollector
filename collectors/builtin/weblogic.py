import time
import ast
from collectors.lib.jolokia_agent_collector_base import JolokiaAgentCollectorBase
from collectors.lib.jolokia import JolokiaParserBase
from collectors.lib.collectorbase import CollectorBase

class Weblogic(CollectorBase):
    def __init__(self, config, logger, readq):
        super(Weblogic, self).__init__(config, logger, readq)
        self.weblogic_collectors = {}
        self.servers = ast.literal_eval(self.get_config("process_names"))
        if self.servers is None:
            raise LookupError("process_names must be set in collector config file")

        for server in self.servers:
            self.weblogic_collectors[server['name']] = WeblogicWarper(config, logger, readq, server['process'], server['name'], server['port'])

    def __call__(self, *args, **kwargs):
        for process_name, warper in self.weblogic_collectors.iteritems():
            try:
                self.log_info("collect for weblogic  %s", process_name)
                self._readq.nput("weblogic.state %s %s" % (int(time.time()), '0'))
                warper()
            except:
                self._readq.nput("weblogic.state %s %s" % (int(time.time()), '1'))
                self.log_error("failed to weblogic  collect for application %s", process_name)

class WeblogicWarper(JolokiaAgentCollectorBase):
    JMX_REQUEST_JSON = r'''[
    {
      "type": "read",
      "mbean": "java.lang:type=Threading",
      "attribute": ["ThreadCount","TotalStartedThreadCount"]
    },
    {
      "type": "read",
      "mbean": "java.lang:type=ClassLoading",
      "attribute": ["LoadedClassCount","UnloadedClassCount"]
    },
    {
      "type": "read",
      "mbean":"com.bea:ServerRuntime=*,Name=ThreadPoolRuntime,Type=ThreadPoolRuntime",
      "attribute": ["HoggingThreadCount","ExecuteThreadIdleCount","StandbyThreadCount"]
    },
    {
      "type": "read",
      "mbean":"com.bea:ServerRuntime=*,Name=JTARuntime,Type=JTARuntime",
      "attribute": ["TransactionTotalCount","TransactionCommittedTotalCount","TransactionRolledBackTotalCount","TransactionAbandonedTotalCount"]
    },
    {
        "type": "read",
        "mbean": "com.bea:ServerRuntime=*,Name=*,Type=JDBCDataSourceRuntime",
        "attribute": [
            "NumAvailable",
            "CurrCapacity",
            "ConnectionsTotalCount",
            "ActiveConnectionsCurrentCount",
            "LeakedConnectionCount",
            "PrepStmtCacheCurrentSize",
            "WaitingForConnectionCurrentCount",
            "WaitingForConnectionTotal",
            "WaitingForConnectionSuccessTotal",
            "WaitingForConnectionFailureTotal"
        ]
    },
    {
        "type": "read",
        "mbean": "com.bea:ServerRuntime=*,Name=*,ApplicationRuntime=*,Type=EJBPoolRuntime,EJBComponentRuntime=*,*",
        "attribute": [
            "AccessTotalCount - MissTotalCount",
            "MissTotalCount",
            "WaiterCurrentCount",
            "DestroyedTotalCount",
            "BeansInUseCurrentCount",
            "PooledBeansCurrentCount",
            "TransactionsCommittedTotalCount +TransactionsRolledBackTotalCount +TransactionsTimedOutTotalCount",
            "TransactionsCommittedTotalCount",
            "TransactionsRolledBackTotalCount",
            "TransactionsTimedOutTotalCount",
        ]
    },
    {
      "type": "read",
      "mbean": "java.lang:name=PS Scavenge,type=GarbageCollector",
      "attribute": [
        "LastGcInfo",
        "CollectionCount",
        "CollectionTime"
      ]
    }
    ]'''

    CHECK_WEBLOGIC_CONSUMER_PID_INTERVAL = 300  # seconds, this is in case kafka restart

    def __init__(self, config, logger, readq, process_name, server_name, port):
        parsers = {
            "java.lang:type=Threading": WeblogicThreadStatus(logger, server_name),
            "java.lang:type=ClassLoading": WeblogicClassLoader(logger, server_name),
            "com.bea:ServerRuntime=*,Name=ThreadPoolRuntime,Type=ThreadPoolRuntime": WeblogicThreadPoolRuntime(logger, server_name),
            "java.lang:name=PS Scavenge,type=GarbageCollector": "JolokiaGCParser",
            "com.bea:ServerRuntime=*,Name=JTARuntime,Type=JTARuntime": WeblogicJTARuntime(logger, server_name),
            "com.bea:ServerRuntime=*,Name=*,Type=JDBCDataSourceRuntime": WeblogicJDBCDataSourceRuntime(logger, server_name),
            "com.bea:ServerRuntime=*,Name=*,ApplicationRuntime=*,Type=EJBPoolRuntime,EJBComponentRuntime=*,*": WeblogicEJBPoolRuntime(logger, server_name),
        }
        super(WeblogicWarper, self).__init__(config, logger, readq, WeblogicWarper.JMX_REQUEST_JSON, parsers, process_name, WeblogicWarper.CHECK_WEBLOGIC_CONSUMER_PID_INTERVAL, port)


class WeblogicThreadStatus(JolokiaParserBase):
    def __init__(self, logger, server_name):
        super(WeblogicThreadStatus, self).__init__(logger)
        self.metrics = ["ThreadCount", "TotalStartedThreadCount", "StandbyThreadCount"]
        self.additional_tags = "server=%s" % server_name

    def valid_metrics(self):
        return self.metrics

    def metric_name(self, name):
        return "%s.%s" % ("weblogic.thread", name)


class WeblogicClassLoader(JolokiaParserBase):
    def __init__(self, logger, server_name):
        super(WeblogicClassLoader, self).__init__(logger)
        self.metrics = ["LoadedClassCount", "UnloadedClassCount"]
        self.additional_tags = "server=%s" % server_name

    def valid_metrics(self):
        return self.metrics

    def metric_name(self, name):
        return "%s.%s" % ("weblogic.classloader", name)


class WeblogicThreadPoolRuntime(JolokiaParserBase):
    def __init__(self, logger, server_name):
        super(WeblogicThreadPoolRuntime, self).__init__(logger)
        self.metrics = ["HoggingThreadCount","ExecuteThreadIdleCount","StandbyThreadCount"]
        self.additional_tags = "server=%s" % server_name

    def valid_metrics(self):
        return self.metrics

    def metric_name(self, name):
        return "%s.%s" % ("weblogic.threadpool", name)


class WeblogicJTARuntime(JolokiaParserBase):
    def __init__(self, logger, server_name):
        super(WeblogicJTARuntime, self).__init__(logger)
        self.metrics = ["TransactionTotalCount","TransactionCommittedTotalCount","TransactionRolledBackTotalCount","TransactionAbandonedTotalCount"]
        self.additional_tags = "server=%s" % server_name

    def valid_metrics(self):
        return self.metrics

    def metric_name(self, name):
        return "%s.%s" % ("weblogic.jta", name)

class WeblogicJDBCDataSourceRuntime(JolokiaParserBase):
    def __init__(self, logger, server_name):
        super(WeblogicClassLoader, self).__init__(logger)
        self.metrics = [
            "NumAvailable",
            "CurrCapacity",
            "ConnectionsTotalCount",
            "ActiveConnectionsCurrentCount",
            "LeakedConnectionCount",
            "PrepStmtCacheCurrentSize",
            "WaitingForConnectionCurrentCount",
            "WaitingForConnectionTotal",
            "WaitingForConnectionSuccessTotal",
            "WaitingForConnectionFailureTotal"
        ]
        self.additional_tags = "server=%s" % server_name

    def valid_metrics(self):
        return self.metrics

    def metric_name(self, name):
        return "%s.%s" % ("weblogic.datasource", name)

class WeblogicEJBPoolRuntime(JolokiaParserBase):
    def __init__(self, logger, server_name):
        super(WeblogicEJBPoolRuntime, self).__init__(logger)
        self.metrics = [
            "NumAvailable",
            "CurrCapacity",
            "ConnectionsTotalCount",
            "ActiveConnectionsCurrentCount",
            "LeakedConnectionCount",
            "PrepStmtCacheCurrentSize",
            "WaitingForConnectionCurrentCount",
            "WaitingForConnectionTotal",
            "WaitingForConnectionSuccessTotal",
            "WaitingForConnectionFailureTotal"
        ]
        self.additional_tags = "server=%s" % server_name

    def valid_metrics(self):
        return self.metrics

    def metric_name(self, name):
        return "%s.%s" % ("weblogic.ejb", name)


class JolokiaGCParser(JolokiaParserBase):
    def __init__(self, logger):
        self.additional_tags = "server=%s" % server_name
        super(JolokiaGCParser, self).__init__(logger)

    def metric_dict(self, json_dict):
        metrics_dict = {}

        survivorspace_dict = json_dict["value"]["LastGcInfo"]["memoryUsageAfterGc"]["PS Survivor Space"]
        metrics_dict.update({"survivorspace." + key: survivorspace_dict[key] for key in survivorspace_dict.keys()})

        edenspace_dict = json_dict["value"]["LastGcInfo"]["memoryUsageAfterGc"]["PS Eden Space"]
        metrics_dict.update({"edenspace." + key: edenspace_dict[key] for key in edenspace_dict.keys()})

        oldgen_dict = json_dict["value"]["LastGcInfo"]["memoryUsageAfterGc"]["PS Old Gen"]
        metrics_dict.update({"oldgen." + key: oldgen_dict[key] for key in oldgen_dict.keys()})

        codecache_dict = json_dict["value"]["LastGcInfo"]["memoryUsageAfterGc"]["Code Cache"]
        metrics_dict.update({"codecache." + key: codecache_dict[key] for key in codecache_dict.keys()})

        permgen_dict = json_dict["value"]["LastGcInfo"]["memoryUsageAfterGc"]["PS Perm Gen"]
        metrics_dict.update({"permgen." + key: permgen_dict[key] for key in permgen_dict.keys()})

        metrics_dict.update({"GcThreadCount": json_dict["value"]["LastGcInfo"]["GcThreadCount"]})
        metrics_dict.update({"CollectionCount": json_dict["value"]["CollectionCount"]})
        metrics_dict.update({"CollectionTime": json_dict["value"]["CollectionTime"]})

        return metrics_dict

    def valid_metrics(self):
        return ["GcThreadCount", "CollectionCount", "CollectionTime",
                "survivorspace.max", "survivorspace.committed", "survivorspace.init", "survivorspace.used",
                "edenspace.max", "edenspace.committed", "edenspace.init", "edenspace.used",
                "oldgen.max", "oldgen.committed", "oldgen.init", "oldgen.used",
                "codecache.max", "codecache.committed", "codecache.init", "codecache.used",
                "permgen.max", "permgen.committed", "permgen.init", "permgen.used"]

    def metric_name(self, name):
        return "%s.%s" % ("weblogic.scavenge.gc", name)