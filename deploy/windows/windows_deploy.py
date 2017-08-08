import massedit
import sys


#window_deploy.exe --ORG_TOKEN=8622c8d8feec6d11ee94b5efd1a1eb023785f147 --CLIENT_ID=2 --METRIC_SERVER_HOST=tsdb.cloudwiz.cn --ALERTD_SERVER=https://alert.cloudwiz.cn --AGENT_URL=https://download.cloudwiz.cn/agent
import getopt
def usage():
    print "windows_deploy.exe --ORG_TOKEN=<token> --CLIENT_ID=<id> [--AGENT_URL=<agent-tarball_url> --METRIC_SERVER_HOST=<server> --ALERTD_SERVER=<alert_server:port>] [-h] [-snmp] [-update]"

try:
    options,args = getopt.getopt(sys.argv[1:],"", ["help","ORG_TOKEN=","CLIENT_ID=","METRIC_SERVER_HOST=","ALERTD_SERVER=","AGENT_URL=","SYSTEM_ID="])
except Exception,e:
    print e.message
    sys.exit()

for name,value in options:
    if name in ("-h","--help"):
        usage()
    if name in ("--ORG_TOKEN"):
         ORG_TOKEN=value
    if name in ("--CLIENT_ID"):
        CLIENT_ID=value
    if name in ("--AGENT_URL"):
        AGENT_URL = value
    if name in ("--METRIC_SERVER_HOST"):
        METRIC_SERVER_HOST = value
    if name in ("--ALERTD_SERVER"):
        ALERTD_SERVER = value
    if name in ("--SYSTEM_ID"):
        SYSTEM_ID=value

def abort_if_failed(func,message,**kwags):
    try:

        func(**kwags)
    except Exception,e:
        sys.stdout(message+str(e.message))
        print message+str(e.message)
        raise
def edit_file(re,replace_string,filenames = ['runner.conf']):
    massedit.edit_files(filenames, ['re.sub("%s", "%s", line)'% (re,replace_string)], dry_run=False)
# set_token=edit_file('^token *=.*', 'token=%s'%ORG_TOKEN)
message="failed to set ORG_TOKEN value in runner.conf file\n"
set_token=edit_file
abort_if_failed(set_token,message,re='^token *=.*',replace_string='token=%s'%ORG_TOKEN)

set_metric_server_host=edit_file
message="failed to set_metric_server_host "
abort_if_failed(set_metric_server_host,message,re='^host*=.*',replace_string='host=%s'%METRIC_SERVER_HOST)

set_run_metric_server_host=edit_file
message="failed to set_run_metric_server_host"
abort_if_failed(set_run_metric_server_host,message,re='-H .*',replace_string='-H %s '%METRIC_SERVER_HOST,filenames=['run.bat'])

OS="windows"
set_os=edit_file
message="failed to update PLATFORM in version.json"
abort_if_failed(set_os,message,re='%PLATFORM%',replace_string=OS,filenames=['version.json'])
set_filebeat_token=edit_file
abort_if_failed(set_filebeat_token,message="",re='<token>',replace_string=ORG_TOKEN,filenames=['../filebeat/common.conf'])
abort_if_failed(set_filebeat_token,message="",re='<orgid>',replace_string=CLIENT_ID,filenames=['../filebeat/common.conf'])
abort_if_failed(set_filebeat_token,message="",re='<sysid>',replace_string=SYSTEM_ID,filenames=['../filebeat/common.conf'])
abort_if_failed(set_filebeat_token,message="",re='<sysid>',replace_string=SYSTEM_ID,filenames=['../filebeat/filebeat_template.yml'])
abort_if_failed(set_filebeat_token,message="",re='<orgid>',replace_string=CLIENT_ID,filenames=['../filebeat/filebeat_template.yml'])
abort_if_failed(set_filebeat_token,message="",re='<basedir>',replace_string="C:/opt/cloudwiz-agent",filenames=['../filebeat/filebeat_template.yml'])

LOG_SERVER_HOST_PORT=METRIC_SERVER_HOST+":9906"
abort_if_failed(set_filebeat_token,message="",re='<log-server-host-port>',replace_string=LOG_SERVER_HOST_PORT,filenames=['../filebeat/filebeat_template.yml'])