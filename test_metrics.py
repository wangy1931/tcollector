#!/usr/bin/env python
import sys
# import json
def get_collector_list(collectors):
    true_collectors = []
    for collector in collectors:
        collector = collector.lower()
        if "true" in collector:
            true_collectors.append(collector.split('true')[0].replace(" ", ""))
    print " ".join(true_collectors)

if __name__ == '__main__':
    if sys.argv[1]=="get_names":
        collectors = sys.argv[2].split("\n")
        get_collector_list(collectors)


