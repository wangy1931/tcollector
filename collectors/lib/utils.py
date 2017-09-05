#!/usr/bin/python
# This file is part of tcollector.
# Copyright (C) 2013  The tcollector Authors.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.  This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser
# General Public License for more details.  You should have received a copy
# of the GNU Lesser General Public License along with this program.  If not,
# see <http://www.gnu.org/licenses/>.

"""Common utility functions shared for Python collectors"""

import os
import stat
import pwd
import errno
import sys
import requests
import subprocess
import socket
import ConfigParser
import re
from Queue import Queue
from collectors.lib.inventory.linux_network import LinuxNetwork
from collectors.lib.inventory.linux_platform import Platform

# If we're running as root and this user exists, we'll drop privileges.
USER = "cwiz-user"


class RevertibleLowPrivilegeUser(object):
    def __init__(self, low_privelege_user, logger):
        self.low_privilege_user = low_privelege_user
        self.logger = logger

    def __enter__(self):
        pass
#        if os.geteuid() != 0:
#            return
#        try:
#            ent = pwd.getpwnam(self.low_privilege_user)
#        except KeyError:
#            return

#        self.logger.info("set to lower-privilege user %s", self.low_privilege_user)
#        os.setegid(ent.pw_gid)
#        os.seteuid(ent.pw_uid)

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
#       self.logger.info("revert. set current euser %s back to %s", os.geteuid(), os.getuid())
#       os.seteuid(os.getuid())


def lower_privileges(logger, user=USER):
    return RevertibleLowPrivilegeUser(user, logger)


# deprecated. use "with lower_privileges()" instead
def drop_privileges(user=USER):
    """Drops privileges if running as root."""
    try:
        ent = pwd.getpwnam(user)
    except KeyError:
        return

    if os.getuid() != 0:
        return

    os.setgid(ent.pw_gid)
    os.setuid(ent.pw_uid)


def is_sockfile(path):
    """Returns whether or not the given path is a socket file."""
    try:
        s = os.stat(path)
    except OSError, (no, e):
        if no == errno.ENOENT:
            return False
        err("warning: couldn't stat(%r): %s" % (path, e))
        return None
    return s.st_mode & stat.S_IFSOCK == stat.S_IFSOCK


def err(msg):
    print >> sys.stderr, msg


def is_numeric(value):
    return isinstance(value, (int, long, float)) and (not isinstance(value, bool))


def remove_invalid_characters(str):
    """removes characters unacceptable by opentsdb"""
    replaced = False
    lstr = list(str)
    for i, c in enumerate(lstr):
        if not (('a' <= c <= 'z') or ('A' <= c <= 'Z') or ('0' <= c <= '9') or c == '-' or c == '_' or
                c == '.' or c == '/' or c.isalpha()):
            lstr[i] = '_'
            replaced = True
    if replaced:
        return "".join(lstr)
    else:
        return str



def get_pid_and_user_by_pname(process_unique_string):
    commond_line = "ps -ef | grep -e '%s'" % process_unique_string
    pid_user_cmds = subprocess.check_output(commond_line, shell=True).split('\n')

    for pid_user_cmd in pid_user_cmds:
        if pid_user_cmd != '' and 'grep' not in pid_user_cmd:
            pid_user_info_list = pid_user_cmd.split(" ")
            return pid_user_info_list[1],pid_user_info_list[0]

    return None, None


def summary_sender_info(name, info):
    summary_sender(name, {}, info, {})

def summary_sender(name, tag, info, content):
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    host = socket.gethostname()
    runner_config = load_runner_conf()
    token = runner_config.get('base', 'token')
    cookies = dict(_token=token)
    metrics_server = runner_config.get('base', 'alertd_server_and_port')
    data = {}
    data['name'] = name
    data['tag'] = {"host": host}
    data['tag'].update(tag)
    data['info'] = info
    data['content'] = content
    requests.post('%s/summary?token=%s' % (metrics_server, token), json=data, headers=headers, cookies=cookies, timeout=20)


def alertd_post_sender(url, data):
    runner_config = load_runner_conf()
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    metrics_server = runner_config.get('base', 'alertd_server_and_port')
    token = runner_config.get('base', 'token')
    cookies = dict(_token=token)
    #print '%s%s?token=%s' % (metrics_server, url, token)
    requests.post('%s%s?token=%s' % (metrics_server, url, token), json=data, headers=headers, cookies=cookies, timeout=20)


def get_ip(logger):
    network = LinuxNetwork(logger).populate()
    default_v4 = network.get('default_ipv4')

    if default_v4.get('address') is not None:
        ipv4 = default_v4.get('address')
    else:
        ipv4 = get_ip_by_host(logger)
    return ipv4


def get_ip_by_host(logger):
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception as e:
        logger.error("can't get ip by hostname: {}".format(e))
        return None


def get_hostname(logger):
    try:
        platform = Platform().collect()
        return platform.get('nodename')
    except:
        logger.error("can't get hostname from platform ")
        return socket.gethostname()

def load_runner_conf():
    runner_config_path = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '../..', 'runner.conf'))
    runner_config = ConfigParser.SafeConfigParser({"alertd_server_and_port": 'http://localhost:5001'})
    runner_config.read(runner_config_path)
    return runner_config


class TestQueue(Queue):
    def nput(self, value):
        print value


class TestLogger(object):
        # below are convenient methods available to all collectors
    def info(self, msg, *args, **kwargs):
        sys.stdout.write("INFO: " + msg % args)

    def error(self, msg, *args, **kwargs):
        sys.stderr.write("ERROR: " + msg % args)

    def warn(self, msg, *args, **kwargs):
        sys.stdout.write("WARN: " + msg % args)

    def exception(self, msg, *args, **kwargs):
        sys.stderr.write("ERROR: " + msg % args)

