param($active,$service)
$actives='start','stop','status','restart'
$services="cloudwiz-agent:collector","cloudwiz-agent:filebeat","all"
function get_service($service_name){
    $service=Get-Service $service_name -ErrorAction SilentlyContinue
    return $service
}
function get_service_obj($service_name){
    $service = Get-WmiObject -Class Win32_Service -Filter "name='$service_name'"

    return $service
}
function get_service_status( $service_name){

    Start-Sleep -s 2
    $service=get_service $service_name
    if ($service){
    $service_status=$service.status
    return "$service_name `t $service_status"
    }
}
function start_service($service_name){
    Switch ($service_name){
    {$_ -eq "cloudwiz-agent:filebeat" -or $_ -eq "all" }{
        $filebeat=get_service "cloudwiz-agent:filebeat" ;
        if ($filebeat){
            $cmd_str="cd /opt/cloudwiz-agent/agent & filebeat_conf_imp.exe";
            cmd /c $cmd_str;
            $filebeat_obj=get_service_obj "cloudwiz-agent:filebeat";
            $filebeat_obj.startService();
            }
     }
    {$_ -eq "cloudwiz-agent:collector" -or $_ -eq "all" }{
        $collector=get_service "cloudwiz-agent:collector" ;
        if ($collector){
            $collect_obj=get_service_obj "cloudwiz-agent:collector";
            $collect_obj.startService();
            }
    }
    }
    get_services_status $service_name
 }

 function stop_service($service_name){
    Switch ($service_name){
    {$_ -eq "cloudwiz-agent:filebeat" -or $_ -eq "all" }{ $filebeat=get_service "cloudwiz-agent:filebeat" ; if ($filebeat.status -ne 'Stopped'){$filebeat.Stop()}}
    {$_ -eq "cloudwiz-agent:collector" -or $_ -eq "all" }{ $collector=get_service "cloudwiz-agent:collector" ; if ($collector.status -ne 'Stopped'){$collector.Stop()}}
    }
    get_services_status $service_name
 }
function get_services_status( $service_name){
    Switch ($service_name){
    {$_ -eq "cloudwiz-agent:filebeat" -or $_ -eq "all" }{get_service_status "cloudwiz-agent:filebeat" }
    {$_ -eq "cloudwiz-agent:collector" -or $_ -eq "all" }{get_service_status "cloudwiz-agent:collector"}
    }
}
function control($active,$service){
     switch($active){
     {$active -eq "start" }{start_service $service}
     {$active -eq "stop"}{ stop_service $service}
     {$active -eq "status"}{ get_services_status $service}
     {$active -eq "restart"}{ stop_service $service;start_service $service}
     }
}
if ( $actives -contains $active -or  $services -contains $services ){
   control $active $service
}else{
   echo "*** Unknown syntax: $active"
   exit 1
}