#!/bin/bash
cd $(dirname $0)
current_time=$(date "+%Y.%m.%d-%H.%M.%S")
source common.sh
OS=$(get_os)
version=$1
pushd /root/src/tcollector/deploy
sudo ./build.sh -h /root/src/tcollector/
popd

scp -r /tmp/publish/RedHat root@172.17.0.1:/data/workspace/tcollector/release/${OS}-${version}-$current_time