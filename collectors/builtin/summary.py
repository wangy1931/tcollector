import os
import json
import platform
import time
from time import localtime, strftime
from collectors.lib import utils
from collectors.lib.collectorbase import CollectorBase

SERVICE_RUNNING_TIME = [
    'hadoop',
    'hbase',
    'kafka',
    'mysql',
    'spark',
    'storm',
    'yarn',
    'zookeeper'
]


class Summary(CollectorBase):
    def __init__(self, config, logger, readq):
        super(Summary, self).__init__(config, logger, readq)
        ## would be send when the collector start
        runner_config = utils.load_runner_conf()
        version = runner_config.get('base', 'version')
        commit = runner_config.get('base', 'commit')
        token = runner_config.get('base', 'token')
        self.running_time = 0
        self.interval = self.get_config('interval')

        ip = None
        try:
            ip = utils.get_ip(self._logger)
        except Exception:
            self.log_error("can't get ip address")

        try:
            services = self.get_config_json()
            utils.summary_sender("collector.service", {}, {"type": "service"}, services)
            summary = {
                "version": version,
                "commitId": commit,
                "token": token,
                "start_time": strftime("%Y-%m-%d %H:%M:%S", localtime()),
                "os_version": platform.platform()
            }

            if ip is not None:
                summary["ip"] = ip
                utils.summary_sender_info("collector.ip", {"value": ip})

            utils.summary_sender_info("collector.os", {"value": platform.platform()})
            utils.summary_sender("collector.summary", {}, {"type": "service"}, [summary])
        except Exception as e:
            self.log_error("can't send summary data when init.  %s" % e)

    def __call__(self):
        self.running_time = self.running_time + int(self.interval)
        self._readq.nput("collector.state %s %s" % (int(time.time()), '0'))
        self._readq.nput("collector.runningTime %s %s" % (int(time.time()), self.running_time))


    def get_config_json(self) :
        conf_json = "{}"
        try:
            conf_json = json.loads(
                os.popen(
                    os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../collector_mgr.py")+' json'
                ).read())
        except:
            self.log_error("can't get config json")
            pass

        return conf_json