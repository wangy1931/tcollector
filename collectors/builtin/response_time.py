import requests
import time
from collectors.lib.collectorbase import CollectorBase


class ResponseTime(CollectorBase):
    def __init__(self, config, logger, readq):
        super(ResponseTime, self).__init__(config, logger, readq)
        self.urls = eval(self.get_config("urls"))
        self.response_time = {}

    def __call__(self):
        if len(self.urls):
            for service in self.urls:
                ts = time.time()
                try:
                    tag = "url=%s" % service
                    requests.get(self.urls[service]['url'], timeout=int(self.urls[service]['timeout_sec']))
                    self.response_time[service] = time.time() - ts
                    self._readq.nput("respondtime.duration %s %s %s" %
                                     (int(time.time()), self.response_time[service], tag))
                    self._readq.nput("respondtime.state %s %s %s" %
                                     (int(time.time()), "0", tag))
                except Exception:
                    self._readq.nput("respondtime.duration %s %s %s" %
                                     (int(time.time()), str(self.urls[service]['timeout_sec']), tag))
                    self._readq.nput("respondtime.state %s %s %s" %
                                     (int(time.time()), "1", tag))
