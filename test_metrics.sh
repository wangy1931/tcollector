#!/usr/bin/env bash


collect_list=`./collector_mgr.py list`
collect_names=$(./test_metrics.py get_names "$collect_list")
./collector_mgr.py disable all > /dev/null
for collect_name in $collect_names ;
do
   echo "start test collector $collect_name"
   ./collector_mgr.py enable $collect_name > /dev/null
   ./run -T
   ./collector_mgr.py disable $collect_name > /dev/null
done

for collect_name in $collect_names ;
do
 ./collector_mgr.py enable $collect_name > /dev/null
done