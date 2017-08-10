@echo off
copy windows_setup.py ..\..\
cd ..\..\
mkdir logs
echo "" >> logs\collector.log
mkdir runs
echo "" >> runs\collector.pid

python windows_setup.py build
cd build\
mkdir agent
xcopy  /s exe.win-amd64-2.7  agent
cd agent\collectors
rd /s /q 0 30 300
cd ..\..
del  /q ..\deploy\releases\windows\cloudwiz-agent-amd64.zip
C:\"Program Files"\7-Zip\7z a  -r ..\deploy\releases\windows\cloudwiz-agent-amd64.zip agent
cd ..\deploy\workspace
xcopy  /s /y ..\windows\user.conf filebeat-5.4.2-windows-x86_64
xcopy /s /y ..\windows\common.conf filebeat-5.4.2-windows-x86_64
xcopy /s /y ..\windows\filebeat_template.yml filebeat-5.4.2-windows-x86_64
C:\"Program Files"\7-Zip\7z a  -r ..\releases\windows\cloudwiz-agent-amd64.zip filebeat-5.4.2-windows-x86_64
cd ..\windows
C:\"Program Files"\7-Zip\7z a  -r ..\releases\windows\cloudwiz-agent-amd64.zip altenv
cd ..\..
rd /s /q build
rd /s /q logs
rd /s /q runs
del  /q windows_setup.py
cd deploy/windows