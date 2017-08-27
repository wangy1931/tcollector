#!/usr/bin/env python

import cx_Oracle
import time
from collectors.lib import utils
from collectors.lib.collectorbase import CollectorBase

# you can add your sql to get metrics .
# try to use [ | ] to cut the string.
# in this case the first and second is  metrics name and val . after all is tags

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

        customize_section = dict(self._config.items("customize"))
        del customize_section["interval"]
        del customize_section["enabled"]
        del customize_section["collectorclass"]
        self.customize = customize_section

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
                        self.log_error("Some exception when execute exception, key=%s  %s" % (key,e))
                        pass

                for cus_key,cus_sql in self.customize.iteritems():
                    try:
                        self.cur.execute(cus_sql)
                        res = self.cur.fetchall()
                        customer = cus_key.split("|")
                        cus_metric = customer[0]

                        for row in res:
                            i = 1
                            tags_str = " "

                            for col in row[1:]:
                                tag_key = customer[i+1]
                                tag_val = utils.remove_invalid_characters(str(col))
                                tags_str = tags_str + " %s=%s" %(tag_key, tag_val)
                                i = i+1

                            self.log_info(cus_metric)
                            self.log_info(row[0])
                            self.log_info(tags_str)
                            self._readq.nput("oracle.%s %s %s %s" % (cus_metric ,int(time.time()), row[0], tags_str))


                    except Exception as e:
                        self.log_error("Some exception when customer sql execute exception, key=%s  %s" % (cus_key,e))
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