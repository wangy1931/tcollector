#!/usr/bin/env python

import cx_Oracle
import time
from collectors.lib.collectorbase import CollectorBase


# 默认配置了很多 sql 语句, 也可以动态加入.
# 通过 |  来切分.
# 默认前两个位置标识 metricsname 和 val 后面默认为是tag , 同时sql 查询出来的位置也要吻合.

class Oracle(CollectorBase):
    def __init__(self, config, logger, readq):
        super(Oracle, self).__init__(config, logger, readq)
        self.username = self.get_config("username")
        self.password = self.get_config("password")
        self.host = self.get_config("host", "127.0.0.1")
        self.database = self.get_config("database")
        self.port = self.get_config("port", "1521")
        self.db = None
        section =  dict(self._config.items("sql"))
        # remove default config section
        del section["interval"]
        del section["enabled"]
        del section["collectorclass"]
        self.sqls = section

    def __call__(self):
        try:
            self.db_connect()
            try:
                for key, sql in self.sqls.iteritems():
                    try:
                        self.cur.execute(sql)
                        res = self.cur.fetchone()
                        metric = key.split("|")[0]
                        if res[0] is not None:
                            self._readq.nput("oracle.%s %s %s" % (metric ,int(time.time()), res[0]))
                    except Exception as e:
                        self.log_error("Some exception when execute exception, key=%s /n %s" % (key,e))
                        pass

                self._readq.nput("oracle.state %s 0" % int(time.time()))
            finally:
                self.cur.close()
                self.db_close()
        except Exception as e:
            self.log_error(e)
            self._readq.nput("oracle.state %s 1" % int(time.time()))
            self.log_error("oralce collector does not work")

    def db_connect(self):
        try:
            self.db = cx_Oracle.connect(
                "{0}/{1}@{2}/{3}".format(self.username, self.password, self.host, self.database))
            self.cur = self.db.cursor()
        except Exception as e:
            self.log_error(
                "can't connect oracle : {0}/{1}@{2}/{3}".format(self.username, self.password, self.host, self.database))
            raise

    def db_close(self):
        self.db.close()