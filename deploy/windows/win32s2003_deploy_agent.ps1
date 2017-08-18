$client = new-object System.Net.WebClient;
$target='C:\tmp\cloudwiz-agent.zip'
$filebeat_service="cloudwiz-agent:filebeat"
$collector_service="cloudwiz-agent:collector"
$root_dir='c:\opt\cloudwiz-agent'
$zip_path='C:\tmp\cloudwiz-agent-amd64.zip'
if(!(Test-Path $zip_path)){
    $client.DownloadFile('https://download.cloudwiz.cn/agent/windows/cloudwiz-agent-amd64.zip',$zip_path)
}

function UnzipFile([string]$souceFile, [string]$targetFolder)
{
    if(!(Test-Path $targetFolder))
    {
        mkdir $targetFolder
    }
    $shellApp = New-Object -ComObject Shell.Application
    $files = $shellApp.NameSpace($souceFile).Items()
    $files|%{if (Test-Path ("$targetFolder/{0}" -f  $_.name )){Remove-Item ("$targetFolder/{0}" -f  $_.name) -Force -Recurse}}
    $shellApp.NameSpace($targetFolder).CopyHere($files)
}
function isExist([string]$dir){
    if ( !(Test-Path $dir)){
    new-item -path c:\  -name $dir -type directory;
    }
}
function log_info($log){
     echo $log
}
function run_cmd($dir,$cmd){
     $cmd_str="cd $dir &  $cmd"
     log_info("executed $cmd_str")
     cmd /c $cmd_str
}

Function unzip{
    UnzipFile  $zip_path $root_dir
    rename-item -path "c:/opt/cloudwiz-agent/filebeat-5.4.2-windows-x86_64" -Newname "c:/opt/cloudwiz-agent/filebeat"
}
function judge_service($service_name){
  if (Get-Service $service_name -ErrorAction SilentlyContinue) {
      $service = Get-WmiObject -Class Win32_Service -Filter "name='$service_name'"
      $service.StopService()
      return 1;
  }else{
      return 0;
  }
}
function install_collector_service(){
  $SERVICE_NAME=$collector_service
  $collector_dir="$root_dir\agent"
  log_info "init config"
  $deploy_str="windows_deploy.exe --ORG_TOKEN=$ORG_TOKEN --SYSTEM_ID=$SYSTEM_ID --CLIENT_ID=$CLIENT_ID --AGENT_URL=$AGENT_URL --METRIC_SERVER_HOST=$METRIC_SERVER_HOST --ALERTD_SERVER=$ALERTD_SERVER"
  run_cmd $collector_dir  $deploy_str

  $ins_service_str="cloudwiz-service.exe install $SERVICE_NAME runner.exe"
  run_cmd $collector_dir $ins_service_str

  $set_dir_to_service="cloudwiz-service.exe set $SERVICE_NAME AppDirectory $root_dir\agent"
  run_cmd $collector_dir $set_dir_to_service

  $set_parameters_to_service="cloudwiz-service.exe set $SERVICE_NAME  AppParameters  --ssl --port 443 --logfile ..\altenv\var\log\collector.log  -P ..\altenv\var\run\collector.pid --dedup-interval 0 -H $METRIC_SERVER_HOST"
  run_cmd $collector_dir $set_parameters_to_service

}
function install_filebeat_service(){
   $workdir="$root_dir\filebeat"
   New-Service -name $filebeat_service `
  -displayName $filebeat_service `
  -binaryPathName "`"$workdir\\filebeat.exe`" -c `"$workdir\\filebeat.yml`" -path.home `"$workdir`" -path.data `"C:\\ProgramData\\filebeat`""

}
function keep_file($source,$target){
    if( test-path $source){
     Remove-Item $target
     Copy-Item $source  $target
  }
}
function upgrate_service(){
  Copy-Item $root_dir  c:/tmp/cloudwiz-agent-bak
  Remove-Item $root_dir
  unzip
  keep_file "c:/tmp/cloudwiz-agent-bak/agent/conf" "$root_dir/agent/conf"
  keep_file "c:/tmp/cloudwiz-agent-bak/filebeat/user.conf" "$root_dir/filebeat/user.conf"
}
function start_collector($collector_name){
    $cmd_str="cd c:/opt/cloudwiz-agent/agent & collector_mgr enable $collector_name"
    cmd /c $cmd_str
}
function start_all_default_collector(){
    $cmd_str="cd c:/opt/cloudwiz-agent/agent & collector_mgr disable all"
    cmd /c $cmd_str
     $collector_list="summary","win32_host_scan","service_scan","win32_cpustats","win32_dfstats","win32_top_n","win32_iostats","win32_memstats","win32_procstats","win32_netstats","win32_events"
     foreach($collector in $collector_list){
         start_collector $collector
     }
}
function execute(){
   if(judge_service $collector_service -or judge_service $filebeat_service){
       upgrate_service
   } else{
      unzip
      install_collector_service
      install_filebeat_service
   }
   start_all_default_collector
   log_info "Done!"
   log_info "run '/opt/cloudwiz-agent/altenv/bin/supervisorctl.bat start all' to start ! "
}

execute
