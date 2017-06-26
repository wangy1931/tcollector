#!/bin/bash
current_time=$(date "+%Y.%m.%d-%H.%M.%S")
source common.sh
OS=$(get_os)
version=$1
pushd /root/src/tcollector/deploy
git pull
sudo ./build.sh -h /root/src/tcollector/
popd

scp -r /tmp/publish/${OS} root@172.17.0.1:/data/workspace/tcollector/release/${OS}-${version}-$current_time