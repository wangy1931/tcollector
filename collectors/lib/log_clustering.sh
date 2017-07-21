#!/bin/bash

PID=$(/usr/bin/pgrep -f log-clustering) 
TSTAMP=$(date +%s)

STATS=$(/data/jdk1.8.0_112/bin/jstat -gcutil $PID | tr '\n' ' ')
read -r -a array <<< "$STATS"
if [ ${#array[@]} -lt 4 ]; then
    exit 2
fi
for i in {0..10}; do
    let "j = i + 11"
    echo "log.clustering.jstat.${array[$i]} $TSTAMP ${array[$j]} host=$HOSTNAME"
done
