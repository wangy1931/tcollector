#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
    iftop 要使用较高的版本. centos 中建议  1.0pre4 以上.
"""
import subprocess
import socket
import json
import time

from collectors.lib.collectorbase import CollectorBase

collect_cmd = 'sudo -i iftop -i eth0 -b -t -s 10 -n'


class Iftop(CollectorBase):
    def __init__(self, config, logger, readq):
        super(Iftop, self).__init__(config, logger, readq)

    def __call__(self):
        try:
            ip = get_internal_ip()
            std_out = collect()
            raw_pairs = parser_iftop_stdout_to_pair(std_out)
            pairs = []
            for raw_pair in raw_pairs:
                pair = parser_flow_pair(raw_pair)
                # self.log_info(pair)
                if pair:
                    # print(pair)
                    tags = "ip=" + str(pair['dest'])
                    self._readq.nput('iftop.traffic.in %i %d %s' % (time.time(), int(pair['in']), tags))
                    self._readq.nput('iftop.traffic.out %i %d %s' % (time.time(), int(pair['out']), tags))
            self._readq.nput('iftop.status %s %s' % (int(time.time()), '0'))
        except Exception as e:
            self._readq.nput('iftop.status %s %s' % (int(time.time()), '1'))
            msg = "Error executing check: {}".format(e)
            self.log_error(msg)


def system(cmd):
    '''
    @summary: excute a subprocess return util subprocess stopped
    @param cmd: a string that need to excute in subprocess
    @result: return_code, stdout, stderr
    '''
    process = subprocess.Popen(
        args=cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    std_out, std_err = process.communicate()
    return_code = process.poll()
    return return_code, std_out, std_err


def collect():
    rt, std_out, stderr = system(collect_cmd)
    if rt:
        print "collect error, reason:%s\n %s" % (std_out, stderr)
        return
    else:
        return std_out


def valid_ip(address):
    # print(address.split(':')[0])
    try:
        socket.inet_aton(address.split(':')[0])
        return True
    except:
        return False


def parser_iftop_stdout_to_pair(stdout):
    start = True
    end = False
    pair_begin = start
    tlines = []
    ret = []
    for line in stdout.split('\n'):
        compute = False
        try:
            if valid_ip(line.split()[1]):
                pair_begin = start
                tlines.append(line)
                compute = True
            if not compute and valid_ip(line.split()[0]):
                pair_begin = end
                tlines.append(line)
                source_line = False
            if pair_begin == end:
                if tlines:
                    ret.append(tlines)
                    tlines = []
        except:
            pass
    return ret


def parser_flow_pair(pair):
    val = {}
    source = pair[0]
    dest = pair[1]
    source_ip = source.split()[1]
    source_to_dist = source.split()[4]
    dest_ip = dest.split()[0]
    dist_to_source = dest.split()[3]
    val["source"] = source_ip
    val["dest"] = dest_ip
    val["out"] = convert_to_bit(source_to_dist)
    val["in"] = convert_to_bit(dist_to_source)
    return val


def convert_to_bit(nbit):
    if nbit.endswith("Kb"):
        return float(nbit[0:-2]) * 1024
    elif nbit.endswith("Mb"):
        return float(nbit[0:-2]) * 1024 * 1024
    else:
        return float(nbit[0:-1])


def get_internal_ip():
    return socket.getaddrinfo(socket.gethostname(), None)[0][-1][0]


'''
def format_pairs(pairs):
    output = []
    item_out = {}
    item_out["timestamp"] = int(time.time())
    item_out["endpoint"] = socket.gethostname()
    item_out["counterType"] = "GAUGE"
    item_out["step"] = 60
    item_out["tags"] = ""
    item_out["metric"] = "network.out.total"
    item_out["value"] = 0
    item_in = item_out.copy()
    item_in["metric"] = "network.in.total"

    for pair in pairs:
        item = {}
        item["timestamp"] = int(time.time())
        item["endpoint"] = socket.gethostname()
        item["counterType"] = "GAUGE"
        item["step"] = 60
        item["tags"] = "ip=" + pair["dest"]
        item["metric"] = "network.out"
        item["value"] = int(pair["out"])
        item_out["value"] += int(pair["out"])
        output.append(item)
        new_item = item.copy()
        new_item["metric"] = "network.in"
        new_item["value"] = int(pair["in"])
        item_in["value"] += int(pair["in"])
        output.append(new_item)
    output.append(item_in)
    output.append(item_out)
    return json.dumps(output)
'''
