运行安装命令
powershell -Command if ( !(Test-Path C:\tmp)){ new-item -path c:\  -name tmp -type directory;}Set-ExecutionPolicy unrestricted; $client = new-object System.Net.WebClient;if(!(Test-Path C:/tmp/windows_deploy_agent.ps1)){$client.DownloadFile('https://download.cloudwiz.cn/agent/windows_deploy_agent.ps1','C:/tmp/windows_deploy_agent.ps1'); } $ORG_TOKEN='8622c8d8feec6d11ee94b5efd1a1eb023785f147';$CLIENT_ID='2';$SYSTEM_ID='18';$METRIC_SERVER_HOST='tsdb.cloudwiz.cn';$ALERTD_SERVER='https://alert.cloudwiz.cn';$AGENT_URL='https://download.cloudwiz.cn/agent';$UPDATA='False';c:/tmp/windows_deploy_agent.ps1;

运行删除命令
cd /opt/cloudwiz-agent/agent
cloudwiz-service.exe remove  "cloudwiz-agent:collector"
sc delete "cloudwiz-agent:filebeat"
cd /

打包命令
windows_build.bat