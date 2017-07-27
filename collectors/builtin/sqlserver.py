import time
import pyodbc
from collectors.lib.collectorbase import CollectorBase

class Sqlserver(CollectorBase):
    SQL = "SELECT  counter_name, cntr_value FROM sys.dm_os_performance_counters where counter_name ='%s';"
    METRICS = [
        ('sqlserver.buffer.cache_hit_ratio', 'Buffer cache hit ratio'),  # RAW_LARGE_FRACTION
        ('sqlserver.buffer.page_life_expectancy', 'Page life expectancy'),  # LARGE_RAWCOUNT
        ('sqlserver.stats.batch_requests', 'Batch Requests/sec'),  # BULK_COUNT
        ('sqlserver.stats.sql_compilations', 'SQL Compilations/sec'),  # BULK_COUNT
        ('sqlserver.stats.sql_recompilations', 'SQL Re-Compilations/sec'),  # BULK_COUNT
        ('sqlserver.stats.connections', 'User Connections'),  # LARGE_RAWCOUNT
        ('sqlserver.stats.lock_waits', 'Lock Waits/sec'),  # BULK_COUNT
        ('sqlserver.access.page_splits', 'Page Splits/sec'),  # BULK_COUNT
        ('sqlserver.stats.procs_blocked', 'Processes blocked'),  # LARGE_RAWCOUNT
        ('sqlserver.buffer.checkpoint_pages', 'Checkpoint pages/sec')  # BULK_COUNT
    ]

    def __init__(self, config, logger, readq):
        CollectorBase.__init__(self, config, logger, readq)
        server=self.get_config("server")
        driver=""
        if len(pyodbc.drivers())>0:
            driver=pyodbc.drivers()[0]
        else:
            self.log_error("sqlserver's driver is None,please install sqlserver's driver!")
            raise Exception("sqlserver's driver is None,please install sqlserver's driver!")
        user=self.get_config("username")
        passwd=self.get_config("password")
        database=self.get_config("database","master")
        self.conn_str='DRIVER={%s};SERVER=%s;DATABASE=%s;UID=%s;PWD=%s'%(driver,server,database,user,passwd)

    def __call__(self):
        self.ts=time.time()
        self.check()

    def check(self):
        try:
            cnxn = pyodbc.connect(self.conn_str)
            cursor = cnxn.cursor()
            for metric, name in self.METRICS:
                try:
                    cursor.execute(self.SQL % name)
                    row = cursor.fetchone()
                    val=row[1]
                    self._readq.nput("sqlserver.%s %d %s" % (metric,self.ts, val))
                except Exception,e:
                    self.log_warn("metric of name  is %s is None "%metric)
            self._readq.nput("sqlserver.status %d %s" % (self.ts, '0'))
            cnxn.close()
        except pyodbc.Error, error:
            message=""
            for e in error:
                 message +=str(e)
            self.log_error("sqlserver collector Error is %s"%message)
            self._readq.nput("sqlserver.status %d %s" % ( self.ts, '1'))


