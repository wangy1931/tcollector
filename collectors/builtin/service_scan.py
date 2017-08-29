import time

import psutil

from collectors.lib import utils
from collectors.lib.collectorbase import CollectorBase
from collectors.lib.utils import TestQueue
from win32_host_scan import Win32HostScan


class ServiceScan(CollectorBase):
    def __init__(self, config, logger, readq):
        super(ServiceScan, self).__init__(config, logger, readq)

    def __call__(self):
        try:
            all_proc = []
            host, ip = Win32HostScan.get_hostname_and_ip(self._logger)

            for proc in psutil.process_iter():
                try:
                    all_proc.append((" ".join(proc.cmdline())).encode('utf-8').strip())
                except:
                    pass
                    all_proc.append(proc.name())

            service = {
                "host": host,
                "ip": ip,
                "process": all_proc
            }
            utils.alertd_post_sender("/cmdb/agent/service/scan", service)
            self._readq.nput("scan.state %s %s" % (int(time.time()), '0'))
        except Exception as e:
            self.log_error("can't send scan result to alertd %s" % e)
            self._readq.nput("scan.state %s %s" % (int(time.time()), '1'))


if __name__ == "__main__":
    test = ServiceScan(None, None, TestQueue())
    test.__call__()
