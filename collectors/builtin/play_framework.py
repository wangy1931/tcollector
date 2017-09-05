import time
import ast
from collectors.lib.jolokia_agent_collector_base import JolokiaAgentCollectorBase
from collectors.lib.jolokia import JolokiaParserBase
from collectors.lib.collectorbase import CollectorBase

class PlayFramework(CollectorBase):
    def __init__(self, config, logger, readq):
        super(PlayFramework, self).__init__(config, logger, readq)
        self.play_collectors = {}
        self.servers = ast.literal_eval(self.get_config("process_names"))
        if self.servers is None:
            raise LookupError("process_names must be set in collector config file")

        for server in self.servers:
            self.play_collectors[server['name']] = PlayWarper(config, logger, readq, server['process'], server['name'], int(server['port']))

    def __call__(self, *args, **kwargs):
        for process_name, warper in self.play_collectors.iteritems():
            try:
                self.log_info("collect for play  %s", process_name)
                warper()
                self._readq.nput("play.state %s %s" % (int(time.time()), '0'))
            except Exception as e:
                self._readq.nput("play.state %s %s" % (int(time.time()), '1'))
                self.log_error("failed to play  collect for application %s, %s" %(process_name, e))

class PlayWarper(JolokiaAgentCollectorBase):
    JMX_REQUEST_JSON = r'''[
     {
        "type" : "read",
        "mbean" : "java.lang:type=Threading",
        "attribute": ["CurrentThreadCpuTime", "PeakThreadCount", "DaemonThreadCount", "TotalStartedThreadCount", "CurrentThreadUserTime", "ThreadCount"]
     },
     {
        "type" : "read",
        "mbean" : "java.lang:type=Threading",
        "attribute": ["CurrentThreadCpuTime", "PeakThreadCount", "DaemonThreadCount", "TotalStartedThreadCount", "CurrentThreadUserTime", "ThreadCount"]
     },
     {
      "type": "read",
      "mbean": "java.lang:type=ClassLoading",
      "attribute": ["LoadedClassCount","UnloadedClassCount"]
     },
     {
      "type": "read",
      "mbean": "java.lang:name=PS Scavenge,type=GarbageCollector",
      "attribute": [
        "LastGcInfo",
        "CollectionCount",
        "CollectionTime"]
     },
     {
        "type" : "read",
        "mbean" : "java.lang:type=OperatingSystem",
        "attribute" : ["FreePhysicalMemorySize","FreeSwapSpaceSize","AvailableProcessors","ProcessCpuLoad",
        "TotalSwapSpaceSize", "ProcessCpuTime", "SystemLoadAverage", "OpenFileDescriptorCount",
        "MaxFileDescriptorCount", "TotalPhysicalMemorySize", "CommittedVirtualMemorySize", "SystemCpuLoad"]
     }
     ]'''

    CHECK_WEBLOGIC_CONSUMER_PID_INTERVAL = 300  # seconds, this is in case jolokia restart

    def __init__(self, config, logger, readq, process_name, server_name, port):
        parsers = {
            "java.lang:type=Threading": PlayThreadStatus(logger, server_name),
            "java.lang:type=ClassLoading": PlayClassLoader(logger, server_name),
            "java.lang:type=Memory": PlayMemoryParser(logger, server_name),
            "java.lang:name=PS Scavenge,type=GarbageCollector": JolokiaGCParser(logger, server_name),
            "java.lang:type=OperatingSystem": PlayOSParser(logger,server_name),
            }
        super(PlayWarper, self).__init__(config, logger, readq, PlayWarper.JMX_REQUEST_JSON, parsers, process_name, PlayWarper.CHECK_WEBLOGIC_CONSUMER_PID_INTERVAL, port)
        self.log_info("play warpper init : %s", server_name)


class PlayThreadStatus(JolokiaParserBase):
    def __init__(self, logger, server_name):
        super(PlayThreadStatus, self).__init__(logger)
        self.metrics = ["ThreadCount", "TotalStartedThreadCount", "StandbyThreadCount"]
        self.additional_tags = "server=%s"%server_name

    def valid_metrics(self):
        return self.metrics

    def metric_name(self, name):
        return "%s.%s"%("play.thread", name)

class PlayOSParser(JolokiaParserBase):
    def __init__(self, logger, server_name):
        super(PlayOSParser, self).__init__(logger)
        self.additional_tags = "server=%s"%server_name


    def valid_metrics(self):
        return ["FreePhysicalMemorySize", "FreeSwapSpaceSize", "AvailableProcessors", "ProcessCpuLoad", "TotalSwapSpaceSize",
                "ProcessCpuTime", "SystemLoadAverage", "OpenFileDescriptorCount", "MaxFileDescriptorCount", "TotalPhysicalMemorySize",
                "CommittedVirtualMemorySize", "SystemCpuLoad"]

    def metric_name(self, name):
        return "play.os.%s"%name

class PlayClassLoader(JolokiaParserBase):
    def __init__(self, logger, server_name):
        super(PlayClassLoader, self).__init__(logger)
        self.metrics = ["LoadedClassCount", "UnloadedClassCount"]
        self.additional_tags = "server=%s"%server_name

    def valid_metrics(self):
        return self.metrics

    def metric_name(self, name):
        return "%s.%s"%("play.classloader", name)

class PlayMemoryParser(JolokiaParserBase):
    def __init__(self, logger, server_name):
        super(PlayMemoryParser, self).__init__(logger)
        self.additional_tags = "server=%s"%server_name

    def metric_dict(self, json_dict):
        nonheapmem_dict = json_dict["value"]["NonHeapMemoryUsage"]
        heapmem_dict = json_dict["value"]["HeapMemoryUsage"]
        merged_dict = {"nonheap." + key: nonheapmem_dict[key] for key in nonheapmem_dict.keys()}
        merged_dict.update({"heap." + key: heapmem_dict[key] for key in heapmem_dict.keys()})
        return merged_dict

    def valid_metrics(self):
        return ["nonheap.max", "nonheap.committed", "nonheap.init", "nonheap.used", "heap.max", "heap.committed",
                "heap.init", "heap.used"]

    def metric_name(self, name):
        return  "%s.%s"%("play.memory", name)

class JolokiaGCParser(JolokiaParserBase):
    def __init__(self, logger, server_name):
        self.additional_tags = "server=%s"%server_name
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
        metrics_dict.update({"GcThreadCount": json_dict["value"]["LastGcInfo"]["GcThreadCount"]})
        metrics_dict.update({"CollectionCount": json_dict["value"]["CollectionCount"]})
        metrics_dict.update({"CollectionTime": json_dict["value"]["CollectionTime"]})

        return metrics_dict

    def valid_metrics(self):
        return ["GcThreadCount", "CollectionCount", "CollectionTime",
                "survivorspace.max", "survivorspace.committed", "survivorspace.init", "survivorspace.used",
                "edenspace.max", "edenspace.committed", "edenspace.init", "edenspace.used",
                "oldgen.max", "oldgen.committed", "oldgen.init", "oldgen.used",
                "codecache.max", "codecache.committed", "codecache.init", "codecache.used"]

    def metric_name(self, name):
        return "%s.%s"%("play.scavenge.gc", name)