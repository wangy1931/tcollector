#!/bin/bash

color_red=$(tput setaf 1)
color_normal=$(tput sgr0)
color_green=$(tput setaf 2)

agent_install_folder="/opt/cloudwiz-agent"
supervisor_conf_file="${agent_install_folder}/altenv/etc/supervisord.conf"
mysql_conf_file=${agent_install_folder}/agent/collectors/conf/mysql.conf
mysql_stats_user="cloudwiz_user"
mysql_stats_pass="cloudwiz_pass"
mysql_priv_user="root"

function display_usage() {
 log_info "$0 [-u privilege_user, e.g. user to connec to mysql, default is root] [-l localpath/to/MySQL-python-1.2.5.zip]"
}

function check_root() {
  if [[ "$USER" != "root" ]]; then
    echo "please run as: sudo $0"
    exit 1
  fi
}

function abort_if_failed() {
  if [ $? -ne 0 ]; then
    printf "${color_red}$1. abort!${color_normal}\n"
    exit 1
  fi
}

function log_info() {
  printf "${color_green}$1${color_normal}\n"
}

while getopts ":hu:l:" opt; do
  case $opt in
    h)
        display_usage
        exit 0
        ;;
    u)
      mysql_priv_user=$OPTARG
      ;;
    l)
      libpath=$OPTARG
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      display_usage
      exit 1
      ;;
    :)
      echo "Option -$OPTARG requires an argument." >&2
      display_usage
      exit 1
      ;;
  esac
done

read -p "the mysql collector will create a mysql user called ${mysql_stats_user}. If you have a user in use with the same name, abort now and contact cloudwiz support person. Otherwise, press any key to continue."

check_root

if [ ! -d "$agent_install_folder" ]; then
    printf "${color_red}cloudwiz-agent installation folder ($agent_install_folder) does not exist. abort!${color_normal}\n"
    exit 1
fi

if [ ! -f "$mysql_conf_file" ]; then
    printf "${color_red}mysql collector conf file $mysql_conf_file does not exist. abort!${color_normal}\n"
    exit 1
fi

command -v mysql > /dev/null 2>&1 || { echo >&2 "mysql command does not exist.  Aborting."; exit 1; }
mysql -u "$mysql_priv_user" -p -e "CREATE USER '${mysql_stats_user}'@'localhost' IDENTIFIED BY '${mysql_stats_pass}'"
log_info "CREATE USER '${mysql_stats_user}'@'localhost' IDENTIFIED BY '${mysql_stats_pass}'"
log_info "type in password for mysql user $mysql_priv_user"
mysql -u "$mysql_priv_user" -p -e "GRANT USAGE ON *.* TO '${mysql_stats_user}'@'localhost'; DROP USER '${mysql_stats_user}'@'localhost'; GRANT PROCESS, REPLICATION CLIENT ON *.* TO '${mysql_stats_user}'@'localhost' IDENTIFIED BY '${mysql_stats_pass}'"
abort_if_failed "failed to create stats user '${mysql_stats_user}'@'localhost'"

log_info "config mysql stats user/pass in ${mysql_conf_file} s/user:.*/user: ${mysql_stats_user}/g"
sed -i -e "s/enabled:.*/enabled: True/g" -e "s/user:.*/user: ${mysql_stats_user}/g" -e "s/pass:.*/pass: ${mysql_stats_pass}/g" ${mysql_conf_file}
abort_if_failed "failed to config mysql collector conf file"


log_info "Complete!"
