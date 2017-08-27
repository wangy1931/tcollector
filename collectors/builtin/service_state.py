import psutil
import socket
import time

from collectors.lib import utils
from collectors.lib.collectorbase import CollectorBase

# We assume service_name_to_cmd_map = { 'procXYZ' : "its unique cmd', 'proc123': 'unique cmd' } in config.
class ServiceState(CollectorBase):
    def __init__(self, config, logger, readq):
        super(ServiceState, self).__init__(config, logger, readq)
        self.svc_name_to_cmd_map = eval(self.get_config("service_name_to_cmd_map"))

    def __call__(self):
        try:
            # In config, we define a map from svc name to its unique command.
            # For each svc, let's check if it's cmd is in list of processes detected by psutil.
            for svc in self.svc_name_to_cmd_map:
                svc_state = 1 # assume not there.
                for proc in psutil.process_iter():
                    cmd = ""
                    try:
                        cmd = " ".join(proc.cmdline())
                    except:
                        pass
                        cmd = proc.name()

                    # if find the svc cmd in list of process, its state is 0
                    self.log_info("svcCmd=%s, cmd=%s" % (self.svc_name_to_cmd_map[svc], cmd))
                    if self.svc_name_to_cmd_map[svc] in cmd:
                        svc_state = 0
                        break

	            utils.remove_invalid_characters(svc)
                self._readq.nput("%s.state %s %s" % (svc, int(time.time()), svc_state))
        except Exception as e:
            self.log_error("can't find processes. %s" % e)
