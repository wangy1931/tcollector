@echo off
set ORG_TOKEN=%1%
set CLIENT_ID=%2%
set AGENT_URL=%3%
set METRIC_SERVER_HOST=%4%
set ALERTD_SERVER=%5%
set SERVICE_NAME=cloudwiz-agentd
window_deploy.exe --ORG_TOKEN=%ORG_TOKEN% --CLIENT_ID=%CLIENT_ID% --AGENT_URL=%AGENT_URL% --METRIC_SERVER_HOST=%METRIC_SERVER_HOST% --ALERTD_SERVER=%ALERTD_SERVER%

nssm.exe install %SERVICE_NAME%  runner.exe
nssm.exe set %SERVICE_NAME% AppDirectory %cd%
nssm.exe set %SERVICE_NAME%  AppParameters  --ssl --port 443 --logfile logs\collector.log  -P runs\collector.pid --dedup-interval 0 -H %METRIC_SERVER_HOST%
nssm.exe start %SERVICE_NAME%
powershell -f C:\agentd\winlogbeat-5.4.3-windows-x86_64\install-service-winlogbeat.ps1


