import time
try:
    import pyhs2
except ImportError:
    pyhs2 = None
from collectors.lib.collectorbase import CollectorBase


class Hive(CollectorBase):
    def __init__(self, config, logger, readq):
        super(Hive, self).__init__(config, logger, readq)
        self.user = self.get_config("user", 'root')
        self.password = self.get_config("password", None)
        self.host = self.get_config("host", 'localhost')
        self.port = int(self.get_config("port", 10000))
        self.database = self.get_config("database", 'default')
        self.timeout = int(self.get_config("timeout", 2000))
        self.conn = None

    def __call__(self):
        try:
            self.conn = pyhs2.connect(host=self.host, port=self.port, authMechanism="PLAIN", user=self.user,
                                  password=self.password, database=self.database, timeout=self.timeout)

            if self.conn is None:
                raise Exception("can't connect hiveserver")

            cur = self.conn.cursor()
            cur.execute("show tables")
            if len(cur.fetch()) >0 :
                self._readq.nput("hive.state %s %s" % (int(time.time()), '0'))
            else:
                raise Exception("can not find any tables")
        except Exception as e:
            self._readq.nput("hive.state %s %s" % (int(time.time()), '1'))
            self.log_error(e)

        finally:
            if self.conn is not None:
                self.conn.close()