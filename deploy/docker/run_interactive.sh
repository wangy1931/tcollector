#!/bin/bash

if [ $# -lt 1 ]; then
    echo "Usage: $0 <image> [<cmd>]"
    exit 1
fi

echo "Running docker image $@"

docker run -i -t $@

exit $?
