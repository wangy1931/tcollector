import time
from collectors.lib.collectorbase import CollectorBase
import requests

header={
"Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
"Accept-Encoding":"gzip, deflate, br",
"Accept-Language":"zh-CN,zh;q=0.8",
"Connection":"keep-alive"
}
class Apache(CollectorBase):

    def __init__(self, config, logger, readq):
        super(Apache, self).__init__(config, logger, readq)
        self.connect_timeout = int(self.get_config('connect_timeout', 5))
        self.receive_timeout = int(self.get_config('receive_timeout', 15))
        self.url = self.get_config('apache_url')
        self.disable_ssl_validation = bool(self.get_config('disable_ssl_validation', False))
        self.auth = None
        apache_user=self.get_config('apache_user',None)
        apache_password=self.get_config('apache_password',None)
        if apache_user is not None and  apache_password is not None:
            self.auth=(apache_user,apache_password)
        self.KEY_VALUES={
            'IdleWorkers': 'apache.performance.idle_workers',
            'BusyWorkers': 'apache.performance.busy_workers',
            'CPULoad': 'apache.performance.cpu_load',
            'Uptime': 'apache.performance.uptime',
            'Total kBytes': 'apache.net.bytes',
            'Total Accesses': 'apache.net.hits',
            'ConnsTotal': 'apache.conns_total',
            'ConnsAsyncWriting': 'apache.conns_async_writing',
            'ConnsAsyncKeepAlive': 'apache.conns_async_keep_alive',
            'ConnsAsyncClosing': 'apache.conns_async_closing',
            'Total kBytes': 'apache.net.bytes_per_s',
            'Total Accesses': 'apache.net.request_per_s'
        }



    def __call__(self):
        self.ts = time.time()
        self.exe()

    def exe(self):
        try:
            r = requests.get(self.url,auth=self.auth, headers=header,
                             verify=not self.disable_ssl_validation,
                             timeout=(self.connect_timeout, self.receive_timeout))
            r.raise_for_status()
            response = r.content
            self.set_metric_value(response)
        except Exception as e:
            self.log_error("Caught exception %s" % str(e))
            self._readq.nput("%s %d %s" % ("apache.state", self.ts, "1"))
        else:
            self._readq.nput("%s %d %s" % ("apache.state", self.ts, "0"))


    def set_metric_value(self,response):
        for line in response.splitlines():
            values = line.split(': ')
            if len(values) == 2:
                metric, value = values
                try:
                    value = float(value)
                except ValueError:
                    continue

                if metric == 'Total kBytes':
                    value = value * 1024

                if metric in self.KEY_VALUES:
                    metric_name = self.KEY_VALUES[metric]
                    self._readq.nput("%s %d %s" % (metric_name,self.ts,str(value)))
                else:
                    self.log_warn("%s not in KEYS" % (metric))
