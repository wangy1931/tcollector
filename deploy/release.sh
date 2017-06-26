#!/bin/bash
current_time=$(date "+%Y.%m.%d-%H.%M.%S")
source common.sh
OS=$1
version=$2
pushd /root/src/tcollector/deploy
git pull
sudo ./build.sh -h /root/src/tcollector/
popd

scp -r /tmp/publish/RedHat root@172.17.0.1:/data/workspace/tcollector/release/${OS}-${version}-$current_time