import ssdb
import re
import time
from collectors.lib.collectorbase import CollectorBase



class SsdbState(CollectorBase):

    def __init__(self, config, logger, readq):
        super(SsdbState, self).__init__(config, logger, readq)
        self.single_metrics=["links", "total_calls", "dbsize"]
        self.mul_metrics=["binlogs"]

    def __call__(self):
        self.timestamp=int(time.time())

        try:
            self.conn=self.get_connect()
        except Exception,e:
            self._readq.nput("ssdb.state %s %s"%(self.timestamp,"1"))
            self.log_error("can not connect ssdb!because %s"%e)
            return

        try:
            self.get_metrics()
            self._readq.nput("ssdb.state %s %s" % (self.timestamp, "0"))
        except Exception,e:
            self._readq.nput("ssdb.state %s %s" % (self.timestamp, "1"))
            self.log_error("can not get ssdb metrics,because %s" % e)
        finally:
            self.colse_ssdb()

    def get_metrics(self):
        list = self.conn.info()[1:]
        metrics_dict = {list[i]: list[i+1] for i in range(0, len(list), 2)}

        for metric in self.single_metrics:
            if metrics_dict.has_key(metric):
                self._readq.nput("ssdb.{0} {1} {2}".format(metric,self.timestamp, metrics_dict[metric]))

        for metric in self.mul_metrics:
            if metrics_dict.has_key(metric):
                val_str_list = metrics_dict[metric].replace(" ", "").split("\n")
                for str in val_str_list:
                    kv = str.split(":")
                    self._readq.nput("ssdb.{0}.{1} {2} {3}".format(metric,kv[0], self.timestamp, kv[1]))

        cmd_list = self.conn.info("cmd")
        cmd_str_list = []

        for cmd in cmd_list[13:]:
            nums = re.findall(r"[0-9]{1,}", cmd)
            if len(nums) > 0 and len(cmd_str_list) > 0:
                self.send_cmd_data(cmd_str_list.pop(), nums)
            else:
                cmd_str_list.append(cmd)

    def send_cmd_data(self,cmd, nums):
        self._readq.nput("ssdb.{0}.calls {1} {2}".format(cmd, self.timestamp, nums[0]))
        self._readq.nput("ssdb.{0}.time_wait {1} {2}".format(cmd, self.timestamp, nums[1]))
        self._readq.nput("ssdb.{0}.time_proc {1} {2}".format(cmd, self.timestamp, nums[2]))

    def get_config(self):
        return ssdb.Client()

    def colse_ssdb(self):
        self.conn.close()


