#!/usr/bin/env python
# This file is part of tcollector.
# Copyright (C) 2013 The tcollector Authors.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version. This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser
# General Public License for more details. You should have received a copy
# of the GNU Lesser General Public License along with this program. If not,
# see <http://www.gnu.org/licenses/>.
"""
Collector for PostgreSQL.

Please, set login/password at etc/postgresql.conf .
Collector uses socket file for DB connection so set 'unix_socket_directory'
at postgresql.conf .
"""

# setup 1: create user
# create user cloudwiz_user with password 'cloudwiz_pass';
# grant SELECT ON pg_stat_database to cloudwiz_user;

import os
import time
import socket

try:
  import psycopg2
except ImportError:
  psycopg2 = None # handled in main()

CONNECT_TIMEOUT = 2 # seconds

from collectors.lib import utils
from collectors.lib.collectorbase import CollectorBase

# Directories under which to search socket files
SEARCH_DIRS = frozenset([
  "/var/run/postgresql", # Debian default
  "/var/pgsql_socket", # MacOS default
  "/usr/local/var/postgres", # custom compilation
  "/tmp", # custom compilation
])

class Postgresql(CollectorBase):

  def __init__(self, config, logger, readq):
    super(Postgresql, self).__init__(config, logger, readq)
    """Collects and dumps stats from a PostgreSQL server."""
    if psycopg2 is None:
      raise Exception("error: Python module 'psycopg2' is missing")  # Ask tcollector to not respawn us

    self.sockdir = self.find_sockdir()
    self.host = self.get_config('host')
    if self.host:
      self.sockdir = self.host
    self.user = self.get_config('user')
    self.password = self.get_config('password')
    self.db = None
    if not self.sockdir:  # Nothing to monitor
      raise Exception("error: Can't find postgresql socket file")  # Ask tcollector to not respawn us

  def __call__(self):
    if self.db is None:
      try:
        self.db = self.postgres_connect(self.sockdir)
        self.db.autocommit = True
      except Exception as e:
        self.log_error("can't access postgresql %s" % e)
        self._readq.nput("postgresql.state %i 1" % time.time())
        return

    try:
      self.collect(self.db)
    except :
      self._readq.nput("postgresql.state %i 1" % time.time())
      return
    finally:
      self.db.close()
      self.db = None

  def find_sockdir(self):
    """Returns a path to PostgreSQL socket file to monitor."""
    for dir in SEARCH_DIRS:
      for dirpath, dirnames, dirfiles in os.walk(dir, followlinks=True):
        for name in dirfiles:
          # ensure selection of PostgreSQL socket only
          if (utils.is_sockfile(os.path.join(dirpath, name))
              and "PGSQL" in name):
            return(dirpath)

  def postgres_connect(self, sockdir):
    try:
      return psycopg2.connect("host='%s' user='%s' password='%s' "
                              "connect_timeout='%s' dbname=postgres"
                              % (sockdir, self.user, self.password,
                                 CONNECT_TIMEOUT))
    except (StandardError, EnvironmentError, EOFError, RuntimeError, socket.error, interface_error, programming_error), e:
      self._readq.nput("postgresql.state %i 1" % time.time())
      self.log_error("Couldn't connect to DB :%s" % (e))
      raise Exception("can't connect postgresql")

  def collect(self, db):
    """
    Collects and prints stats.

    Here we collect only general info, for full list of data for collection
    see http://www.postgresql.org/docs/9.2/static/monitoring-stats.html
    """
    try:
      cursor = db.cursor()

      # general statics
      cursor.execute("SELECT pg_stat_database.*, pg_database_size"
                     " (pg_database.datname) AS size FROM pg_database JOIN"
                     " pg_stat_database ON pg_database.datname ="
                     " pg_stat_database.datname WHERE pg_stat_database.datname"
                     " NOT IN ('template0', 'template1', 'postgres')")
      ts = time.time()
      stats = cursor.fetchall()

      #  datid |  datname   | numbackends | xact_commit | xact_rollback | blks_read  |  blks_hit   | tup_returned | tup_fetched | tup_inserted | tup_updated | tup_deleted | conflicts | temp_files |  temp_bytes  | deadlocks | blk_read_time | blk_write_time |          stats_reset          |     size
      result = {}
      for stat in stats:
        database = stat[1]
        result[database] = stat

      for database in result:
        for i in range(2,len(cursor.description)):
          metric = cursor.description[i].name
          value = result[database][i]
          try:
            if metric in ("stats_reset"):
              continue
            self._readq.nput("postgresql.%s %i %s database=%s" % (metric, ts, value, database))
            self._readq.nput("postgresql.state %i 0" % ts)
          except:
            self.log_error("got here")
            continue

      # connections
      cursor.execute("SELECT datname, count(datname) FROM pg_stat_activity"
                     " GROUP BY pg_stat_activity.datname")
      ts = time.time()
      connections = cursor.fetchall()

      for database, connection in connections:
        self._readq.nput("postgresql.connections %i %s database=%s" % (ts, connection, database))

    except (StandardError, EnvironmentError, EOFError, RuntimeError, socket.error, interface_error, programming_error), e:
      self._readq.nput("postgresql.state %i 1" % time.time())
      self.log_error("error: failed to collect data: %s" % e)