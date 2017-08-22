# -*- coding: utf-8 -*-
import codecs
import os
import time

from datetime import datetime, timedelta
import pythoncom
import wmi

from collectors.lib.collectorbase import CollectorBase
from collectors.lib.utils import TestQueue

record_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../event_last_query.conf')
log_file_path = 'c:\\opt\\cloudwiz-agent\\altenv\\var\\log\\events.log'


class Win32Events(CollectorBase):
    def __init__(self, config, logger, readq):
        super(Win32Events, self).__init__(config, logger, readq)

    def __call__(self):
        try:
            pythoncom.CoInitialize()

            last_query = self.get_last_query()
            c = wmi.WMI()
            wql = 'SELECT * FROM Win32_NTLogEvent WHERE EventType < 3 '
            if last_query:
                wql += "AND TimeGenerated > '" + last_query + "'"
            else:
                d = datetime.now()
                t = timedelta(days=15)
                start_time = d - t
                wmi_time = wmi.from_time(start_time.year, start_time.month, start_time.day, start_time.hour, start_time.minute, start_time.second, 0, 0)
                wql += "AND TimeGenerated > '" + wmi_time + "'"

            timestamp = 0
            time_t = None
            with codecs.open(log_file_path, 'a', 'utf-8') as f:
                for ev in c.query(wql):
                    time_gen = self.fix_date(ev.TimeGenerated)
                    # rewrite to log file
                    f.write(u'{0} {1} {2} {3} {4} {5} {6}\n'.format(
                        time.strftime('%Y-%m-%d %H:%M:%S', time_gen),
                        ev.ComputerName,
                        ev.EventCode,
                        ev.EventType,
                        ev.LogFile,
                        ev.SourceName,
                        ev.Message))

                    t = time.mktime(time_gen)
                    if timestamp < t:
                        timestamp = t
                        time_t = ev.TimeGenerated

            # save time to log
            if time_t:
                self.set_last_query(time_t)

            self._readq.nput('scan.state %s %s' % (int(time.time()), '0'))
        except Exception as e:
            self.log_error('cannot send host scan result to alertd %s' % e)
            self._readq.nput('scan.state %s %s' % (int(time.time()), '1'))
        finally:
            pythoncom.CoUninitialize()

    def fix_date(self, wmi_time):
        time_tuple = wmi.to_time(wmi_time)
        if len(time_tuple) == 8:
            # fix time tuple by add 0 to the end
            l = list(time_tuple)
            l.insert(7, 0)
            if l[8] is None:
                l[8] = 0
            else:
                l[8] = int(l[8])
            time_tuple = tuple(l)

        return time_tuple

    def get_last_query(self):
        with open(record_file_path, 'w+') as f:
            dt = f.readline()
        return dt

    def set_last_query(self, time_t):
        # mode 'w' will truncate the file when open
        with open(record_file_path, 'w') as f:
            f.write(time_t)

if __name__ == "__main__":
    memstats3_inst = Win32Events(None, None, TestQueue())
    memstats3_inst.__call__()
