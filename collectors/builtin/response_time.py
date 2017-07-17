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
                ts = time.clock()
                try:
                    requests.get(self.urls[service]['url'], timeout=int(self.urls[service]['timeout']))
                    self.response_time[service] = time.clock() - ts
                    self._readq.nput("%s.respondtime %s %s" %
                                     (service, int(time.time()), self.response_time[service]))
                    self._readq.nput("%s.respondtime.state %s %s" %
                                     (service, int(time.time()), "0"))
                except Exception:
                    self._readq.nput("%s.respondtime %s %s" %
                                     (service, int(time.time()), str(self.urls[service]['timeout'])))
                    self._readq.nput("%s.respondtime.state %s %s" %
                                     (service, int(time.time()), "1"))
