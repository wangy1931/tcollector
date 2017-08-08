#!/usr/bin/env bash
cp windows_setup.py ../..
cd ../..
mkdir logs

copy windows_setup.py ..\..\
cd ..\..\
mkdir logs
echo "" >> logs\collector.log
mkdir runs
echo "" >> runs\collector.pid

python windows_setup.py build
cd build
mkdir agent
cp -r exe.linux-x86_64-2.7/*  agent/
cd agent/collectors
rm -rf  0 30 300
cd ../..
rm -rf   ../deploy/releases/windows/cloudwiz-agent-amd64.zip
zip   -r ../deploy/releases/windows/cloudwiz-agent-amd64.zip agent
cd ../deploy/workspace

cp -r ../windows/user.conf filebeat-5.4.2-windows-x86_64
cp -r ../windows/common.conf filebeat-5.4.2-windows-x86_64
cp -r ../windows/filebeat_template.yml filebeat-5.4.2-windows-x86_64
zip  -r ../releases/windows/cloudwiz-agent-amd64.zip filebeat-5.4.2-windows-x86_64
cd ../windows
zip  -r ../releases/windows/cloudwiz-agent-amd64.zip altenv
cd ../..
rm -rf build
rm -rf logs
rm -rf  runs
rm -rf  windows_setup.py
cd deploy/windows