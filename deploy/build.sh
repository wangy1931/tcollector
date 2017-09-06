#!/bin/bash
basedir=$(cd $(dirname $0); pwd)
source ${basedir}/common.sh
agent_folder_name="agent"
workspace_folder="${basedir}/workspace"
agent_install_folder="/opt/cloudwiz-agent"
agent_install_folder_escaped="\/opt\/cloudwiz-agent"
agent_install_python_escaped="\/opt\/cloudwiz-agent\/altenv\/bin\/python"
altenv_folder="${agent_install_folder}/altenv"
altenv_bin_folder="${altenv_folder}/bin"
altenv_etc_folder="${altenv_folder}/etc"
altenv_var_folder="${altenv_folder}/var"
altenv_usr_folder="${altenv_folder}/usr"
altenv_run_folder="${altenv_var_folder}/run"
altenv_log_folder="${altenv_var_folder}/log"
altenv_ssl_folder="${altenv_usr_folder}/local/ssl"
agent_collector_folder="${agent_install_folder}/$agent_folder_name"
lib_folder="${agent_collector_folder}/lib"
local_config_folder="${agent_collector_folder}/local_config"
snmp_folder="${agent_install_folder}/snmp"
publish_location="./releases"
tmp_python_ssl="/tmp_python_ssl"
function display_usage() {
 log_info "$0 [-c] [-s] [-h] <path/to/tcollector/root>"
}

function fix_python_recursively() {
  for i in "$1"/*; do
    if [ -d "$i" ];then
      fix_python_recursively "$i"
    elif [[ ${i: -3} == ".py" ]]; then
      sed -i "s/\#\!.*/\#\!${agent_install_python_escaped}/g" "$i"
    fi
  done
}

function _md5() {
  if which md5sum >/dev/null 2>&1; then
    md5sum "$1" | awk '{ print $1 }'
    echo >&2 "switch md5sum to publish md5 key"
  else
    md5 -q "$1"
    echo >&2 "switch md5 to publish md5 key"
  fi
}
function save_python_and_ssl(){
     mkdir -p "${tmp_python_ssl}"
     cp -r -f ${agent_install_folder} ${tmp_python_ssl}
}
os_type=$(get_os)
bitness=$(uname -m)

check_root

#parse cmdline
while getopts "csh" flag; do
  case "$flag" in
    c)   clean=true;;
    s)   skip=true;;
    h)   ssl=true;;
    *) exit 1
  esac
done
if [ $(( $# - $OPTIND )) -lt 0 ]; then
  log_info 'wrong number of parameters'
  display_usage
  exit 1
fi
collector_source_path=${@:$OPTIND:1}

if [[ -z $collector_source_path ]]; then
  log_info "collector source path root is not set"
  display_usage
  exit 1
fi

if [[ ! -d $collector_source_path ]]; then
  log_info "directory $collector_source_path does not exist"
  exit 1
fi

if [[ "$clean" = true ]]; then
  log_info "clean, remove ${workspace_folder}"
  rm -rf ${workspace_folder}
fi

if [[ ! "$skip" = true ]]; then
  if [ ! -d ${tmp_python_ssl} ] ;then
      log_info "recreate ${agent_install_folder}"
      rm -rf ${agent_install_folder}
      abort_if_failed "failed to delete ${agent_install_folder}"
      mkdir -p "${agent_collector_folder}"
      mkdir -p "${workspace_folder}"
      mkdir -p "${altenv_etc_folder}"
      mkdir -p "${altenv_run_folder}"
      mkdir -p "${altenv_log_folder}"

      log_info 'build openssl...'
      if [[ ! -f ${workspace_folder}/openssl-1.0.2j.tar.gz ]]; then
        log_info 'download openssl-1.0.2j package'
        wget --directory-prefix="${workspace_folder}" https://download.cloudwiz.cn/package/openssl-1.0.2j.tar.gz
        abort_if_failed 'failed to download openssl-1.0.2j package'
      fi
      tar -xzf "${workspace_folder}"/openssl-1.0.2j.tar.gz -C "${workspace_folder}"
      abort_if_failed 'failed to extract openssl-1.0.2j tarball'

      pushd "${workspace_folder}"/openssl-1.0.2j
      ./config --prefix="${altenv_ssl_folder}" --openssldir="${altenv_ssl_folder}"
      abort_if_failed 'openssl build: failed to run configure'
      make
      abort_if_failed 'openssl build: failed to run make'
      make install
      abort_if_failed 'openssl build: failed to run make install'
      popd
      log_info 'finish building openssl-1.0.2j'

      log_info 'setup python environment'
      if [[ ! -f ${workspace_folder}/Python-2.7.11.tgz ]]; then
        log_info 'download python-2.7.11 package'
        wget --directory-prefix="${workspace_folder}" https://download.cloudwiz.cn/package/Python-2.7.11.tgz
        abort_if_failed 'failed to download python-2.7.11 package'
      fi
      rm -rf "${workspace_folder}"/Python-2.7.11
      abort_if_failed "failed to remove folder ${workspace_folder}/Python-2.7.11"
      tar -xzf "${workspace_folder}"/Python-2.7.11.tgz -C "${workspace_folder}"
      abort_if_failed 'failed to extract python-2.7.11 tarball'

      pushd "${workspace_folder}"/Python-2.7.11
      sed -i "s/^#_socket /_socket /" Modules/Setup.dist
      abort_if_failed "failed to update Modules/Setup.dist to uncomment SSL 0"
      sed -i "s/^#SSL=/SSL=${altenv_folder//\//\\/}/" Modules/Setup.dist
      abort_if_failed "failed to update Modules/Setup.dist to uncomment SSL 1"
      sed -i "s/^#_ssl _ssl/_ssl _ssl/" Modules/Setup.dist
      abort_if_failed "failed to update Modules/Setup.dist to uncomment SSL 2"
      sed -i "s/^#\t-DUSE_SSL/\t-DUSE_SSL/" Modules/Setup.dist
      abort_if_failed "failed to update Modules/Setup.dist to uncomment SSL 3"
      sed -i "s/^#\t-L\$(SSL)/\t-L\$(SSL)/" Modules/Setup.dist
      abort_if_failed "failed to update Modules/Setup.dist to uncomment SSL 4"
      ./configure --prefix="${altenv_folder}"
      abort_if_failed 'python build: failed to run configure'
      make install
      abort_if_failed 'python build: failed to run make'
      popd
      log_info 'finish building python-2.7.11'
      save_python_and_ssl
  else
      log_info "recreate ${agent_install_folder}"
      rm -rf ${agent_install_folder}
      abort_if_failed "failed to delete ${agent_install_folder}"
      mkdir -p "${agent_collector_folder}"
      log_info " cp -r -f ${tmp_python_ssl}  ${agent_install_folder}"
      cp -r -f ${tmp_python_ssl}/cloudwiz-agent/*  ${agent_install_folder}

  fi

  log_info 'setup supervisord and its dependencies ...'
  log_info 'set up setuptools ...'
  if [[ ! -f ${workspace_folder}/setuptools-20.2.2.tar.gz ]]; then
    log_info 'download setuptools-20.2.2 tarball'
    wget --directory-prefix="${workspace_folder}" https://download.cloudwiz.cn/package/setuptools-20.2.2.tar.gz#md5=bf37191cb4c1472fb61e6f933d2006b1
    abort_if_failed 'failed to download setuptools-20.2.2 tarball'
  fi
  tar -xzf "${workspace_folder}"/setuptools-20.2.2.tar.gz -C "${workspace_folder}"
  abort_if_failed 'failed to extract setuptools tarball'

  pushd "${workspace_folder}"/setuptools-20.2.2
  "${altenv_bin_folder}"/python setup.py install --prefix="${altenv_folder}"
  abort_if_failed 'failed to install setuptools'
  popd
  log_info 'finish setting up setuptools'

  log_info 'pip install packages'
  "${altenv_bin_folder}"/easy_install -i http://mirrors.aliyun.com/pypi/simple --prefix="${altenv_folder}" `cat requirement.txt`
  abort_if_failed 'failed to pip install packages'
  #ssdb.py is not install using pip
   log_info 'set up spp-0.0.7.tar.gz ...'
  if [[ ! -f ${workspace_folder}/spp-0.0.7.tar.gz ]]; then
    log_info 'download spp-0.0.7 tarball'
    wget --directory-prefix="${workspace_folder}" https://download.cloudwiz.cn/package/spp-0.0.7.tar.gz
    abort_if_failed 'failed to download spp-0.0.7'
  fi
  tar -xzf "${workspace_folder}"/spp-0.0.7.tar.gz -C "${workspace_folder}"
  abort_if_failed 'failed to extract spp-0.0.7 tarball'

  pushd "${workspace_folder}"/spp-0.0.7
  "${altenv_bin_folder}"/python setup.py install --prefix="${altenv_folder}"
  abort_if_failed 'failed to install spp-0.0.7'
  popd
  log_info 'finish setting up spp-0.0.7'

  log_info 'set up ssdb.py ...'
  if [[ ! -f ${workspace_folder}/ssdb.py-0.1.8.tar.gz ]]; then
    log_info 'download ssdb.py-0.1.8 tarball'
    wget --directory-prefix="${workspace_folder}" https://download.cloudwiz.cn/package/ssdb.py-0.1.8.tar.gz
    abort_if_failed 'failed to download ssdb.py-0.1.8'
  fi
  tar -xzf "${workspace_folder}"/ssdb.py-0.1.8.tar.gz -C "${workspace_folder}"
  abort_if_failed 'failed to extract setuptools tarball'

  pushd "${workspace_folder}"/ssdb.py-0.1.8
  "${altenv_bin_folder}"/python setup.py install --prefix="${altenv_folder}"
  abort_if_failed 'failed to install ssdb.py-0.1.8'
  popd
  log_info 'finish setting up ssdb.py-0.1.8'



  yes | cp -f "${basedir}/supervisord.conf" "${altenv_etc_folder}/supervisord.conf"
  abort_if_failed "failed to copy supervisord conf file"
  sed -i "s/<basedir>/${agent_install_folder_escaped}/g" "${altenv_etc_folder}/supervisord.conf"
  abort_if_failed "failed to config supervisord.conf"
  log_info 'finish setting up supervisord and its dependencies'


  log_info 'set up filebeat ...'
  fb_tarball="filebeat-5.4.2-linux-${bitness}.tar.gz"
  if [[ ! -f ${workspace_folder}/${fb_tarball} ]]; then
    log_info "download ${fb_tarball}"
    wget -P ${workspace_folder} https://artifacts.elastic.co/downloads/beats/filebeat/${fb_tarball}
    abort_if_failed "failed to download ${fb_tarball}"
  fi
  filebeat_folder=$(tar tfz ${workspace_folder}/${fb_tarball} | head -1 | sed -e 's/\/.*//')
  tar -xzf ${workspace_folder}/${fb_tarball} -C ${workspace_folder}
  abort_if_failed "failed to extract tar -xzf ${workspace_folder}/${fb_tarball} -C ${workspace_folder}"

  log_info 'set up jolokia'
  if [[ ! -f ${workspace_folder}/jolokia-jvm-1.3.5-agent.jar ]]; then
    log_info "download jolokia-jvm-1.3.5-agent.jar"
    wget -O ${workspace_folder}/jolokia-jvm-1.3.5-agent.jar https://download.cloudwiz.cn/package/jolokia-jvm-1.3.5-agent.jar
  fi

  # snmp
  log_info 'set up snmp'
  if [[ ! -f ${workspace_folder}/net-snmp-5.5-57.el6_8.1.x86_64.rpm ]]; then
    log_info "download net-snmp-5.5-57.el6_8.1.x86_64.rpm"
    wget -O ${workspace_folder}/net-snmp-5.5-57.el6_8.1.x86_64.rpm  https://download.cloudwiz.cn/package/net-snmp-5.5-57.el6_8.1.x86_64.rpm
  fi
  if [[ ! -f ${workspace_folder}/net-snmp-libs-5.5-57.el6_8.1.x86_64.rpm ]]; then
    log_info "download net-snmp-libs-5.5-57.el6_8.1.x86_64.rpm"
    wget -O ${workspace_folder}/net-snmp-libs-5.5-57.el6_8.1.x86_64.rpm https://download.cloudwiz.cn/package/net-snmp-libs-5.5-57.el6_8.1.x86_64.rpm
  fi
  if [[ ! -f ${workspace_folder}/net-snmp-utils-5.5-57.el6_8.1.x86_64.rpm ]]; then
    log_info "download net-snmp-utils-5.5-57.el6_8.1.x86_64.rpm"
    wget -O ${workspace_folder}/net-snmp-utils-5.5-57.el6_8.1.x86_64.rpm https://download.cloudwiz.cn/package/net-snmp-utils-5.5-57.el6_8.1.x86_64.rpm
  fi

  log_info 'set up docker SDK...'
  if [[ ! -f ${workspace_folder}/docker-2.3.0.tar.gz ]]; then
    log_info 'download docker-2.3.0 tarball'
    wget --directory-prefix="${workspace_folder}" https://download.cloudwiz.cn/package/docker-2.3.0.tar.gz
    abort_if_failed 'failed to download docker-2.3.0 tarball'
  fi
  tar -xzf "${workspace_folder}"/docker-2.3.0.tar.gz -C "${workspace_folder}"
  abort_if_failed 'failed to extract docker-2.3.0 tarball'

  pushd "${workspace_folder}"/docker-2.3.0
  "${altenv_bin_folder}"/python setup.py install --prefix="${altenv_folder}"
  abort_if_failed 'failed to install docker-2.3.0'
  popd
  log_info 'finish setting up docker-2.3.0'
fi

log_info "setup agent/runner ${collector_source_path} => ${agent_collector_folder}"
rm -rf ${agent_collector_folder}/*
mkdir -p ${agent_collector_folder}/collectors
cp ${collector_source_path}/runner.py ${agent_collector_folder}/runner.py
abort_if_failed 'failed to copy runner.py'
cp ${collector_source_path}/runner.conf ${agent_collector_folder}/runner.conf
abort_if_failed 'failed to copy runner.conf'
echo -e "version=$(git describe --abbrev=0 --tags)" >> ${agent_collector_folder}/runner.conf
echo -e "commit=$(git log --format="%H" -n 1 | head -c 6)" >> ${agent_collector_folder}/runner.conf

cp ${collector_source_path}/collector_mgr.py ${agent_collector_folder}/collector_mgr.py
abort_if_failed 'failed to copy collector_mgr.py'
cp ${collector_source_path}/common_utils.py ${agent_collector_folder}/common_utils.py
abort_if_failed 'failed to copy common_utils.py'
cp ${collector_source_path}/run ${agent_collector_folder}/run
abort_if_failed 'failed to copy run'
sed -i "s/^\.\/runner/${agent_install_folder_escaped}\/agent\/runner/g" ${agent_collector_folder}/run
sed -i "/^log_folder=/c\log_folder=${agent_install_folder}/altenv/var/log" ${agent_collector_folder}/run
sed -i "/^run_folder=/c\run_folder=${agent_install_folder}/altenv/var/run" ${agent_collector_folder}/run
if [[ "$ssl" = true ]]; then
  log_info "enable collector be true"
  sed -i "/^ssl_enable=/c\ssl_enable=--ssl" ${agent_collector_folder}/run
  log_info "ensure port to 443"
  sed -i "/^ssl_port=/c\ssl_port=443" ${agent_collector_folder}/run
fi
cp ${collector_source_path}/collectors/__init__.py ${agent_collector_folder}/collectors/__init__.py
abort_if_failed 'failed to copy collectors/__init__.py'
cp -ar ${collector_source_path}/collectors/builtin ${agent_collector_folder}/collectors/builtin
abort_if_failed 'failed to copy-archive collectors/builtin'
cp -ar ${collector_source_path}/collectors/conf ${agent_collector_folder}/collectors/conf
abort_if_failed 'failed to copy-archive collectors/conf'
cp -ar ${collector_source_path}/collectors/lib ${agent_collector_folder}/collectors/lib
abort_if_failed 'failed to copy-archive collectors/lib'
log_info 'modify python file scripts path'
fix_python_recursively ${agent_collector_folder}
log_info 'finish setting up agent/tcollector'

log_info "set up uagent"
yes | cp -f -r "${collector_source_path}/uagent" "${agent_install_folder}/"
abort_if_failed "failed to copy ${basedir}/uagent to ${agent_install_folder}/"
#sed -i "/^server_base *= */c\server_base = https://github.com/wangy1931/tcollector/tree/uagent-deploy/deploy/releases" "${agent_install_folder}/uagent/uagent.conf"
sed -i "/^install_root *= */c\install_root = ${agent_install_folder}" "${agent_install_folder}/uagent/uagent.conf"
sed -i "/^platform *= */c\platform = ${os_type}" "${agent_install_folder}/uagent/uagent.conf"
abort_if_failed "failed to config uagent.conf"
sed -i "/^log_folder=/c\log_folder=${agent_install_folder}/altenv/var/log" "${agent_install_folder}/uagent/run-uagent.sh"
sed -i "s/^\.\/daemon/${agent_install_folder_escaped}\/uagent\/daemon/g" "${agent_install_folder}/uagent/run-uagent.sh"
abort_if_failed "failed to config run-uagent.sh"
fix_python_recursively "${agent_install_folder}/uagent"
abort_if_failed "failed to fix python env ${agent_install_folder}/uagent"
cp -f "${collector_source_path}"/version.json "${agent_install_folder}/"
abort_if_failed "failed to copy ${collector_source_path}/version.json ${agent_install_folder}/"
BUILD=$(date -u +%y%m%d%H%M%S)
sed -i "s/%BUILD%/$BUILD/g" "${agent_install_folder}/version.json"
abort_if_failed "failed to update BUILD in version.json"
mkdir -p ${agent_install_folder}/.gnupg
abort_if_failed "failed to create ${agent_install_folder}/.gnupg"
yes | cp -f ${basedir}/gnupg/pubring.gpg ${agent_install_folder}/.gnupg
yes | cp -f ${basedir}/gnupg/trustdb.gpg ${agent_install_folder}/.gnupg
abort_if_failed "failed to copy gpg files"
log_info "finish setting up uagent"

log_info "copy common_utils.py"
yes | cp -f "${collector_source_path}/common_utils.py"  "${agent_install_folder}"
abort_if_failed "failed to cp ${collector_source_path}/common_utils.py ${agent_install_folder}"
log_info "finish copying common_utils.py"

log_info "copy cloudwiz-agent startup scripts ${basedir}/startup_scripts/"
yes | cp -f -r "${basedir}/startup_scripts" "${agent_install_folder}/"
abort_if_failed 'failed to copy startup scripts'

log_info "set up filebeat"
yes | cp -f -r "${workspace_folder}/${filebeat_folder}" "${agent_install_folder}"
yes | cp -f "${basedir}/filebeat.yml" "${agent_install_folder}/${filebeat_folder}"
yes | cp -f "${basedir}/filebeat_template.yml" "${agent_install_folder}/${filebeat_folder}"
yes | cp -f "${basedir}/common.conf" "${agent_install_folder}/${filebeat_folder}"
yes | cp -f "${basedir}/user.conf" "${agent_install_folder}/${filebeat_folder}"
yes | cp -f "${basedir}/filebeat_conf.py" "${agent_install_folder}/${filebeat_folder}"
yes | cp -f "${basedir}/filebeat.startup.sh" "${agent_install_folder}/${filebeat_folder}"
abort_if_failed "failed to copy ${workspace_folder}/${filebeat_folder} to ${agent_install_folder}"
pushd ${agent_install_folder}
ln -s -f -T ${filebeat_folder} filebeat
popd
abort_if_failed "failed to create/update symlink ${agent_install_folder}/filebeat"
#sed -i "s/<basedir>/${agent_install_folder_escaped}/g" "${agent_install_folder}/filebeat/filebeat.yml"
sed -i "s/<basedir>/${agent_install_folder_escaped}/g" "${agent_install_folder}/filebeat/filebeat_template.yml"
abort_if_failed "failed to edit ${agent_install_folder}/filebeat/filebeat_template.yml"
log_info "finish setting up filebeat"

log_info "set up lib folder"
mkdir -p "${lib_folder}"
abort_if_failed "failed to create ${lib_folder}"
log_info "cp -f ${workspace_folder}/jolokia-jvm-1.3.5-agent.jar ${lib_folder}/jolokia-jvm-1.3.5-agent.jar"
yes | cp -f ${workspace_folder}/jolokia-jvm-1.3.5-agent.jar ${lib_folder}/jolokia-jvm-1.3.5-agent.jar
abort_if_failed "failed to copy jolokia agent"

log_info "set up snmp folder"
mkdir -p ${snmp_folder}
abort_if_failed "failed to create ${snmp_folder}"
log_info "cp -f ${workspace_folder}/net-snmp*.rpm ${snmp_folder}"
yes | cp -f ${workspace_folder}/net-snmp*.rpm ${snmp_folder}
abort_if_failed "failed to copy snmp rpms"

log_info "setup local config folder"
mkdir -p "${local_config_folder}"
abort_if_failed "failed to create ${local_config_folder}"
yes | cp -rf "${basedir}/collectors/" "${local_config_folder}"
abort_if_failed "failed to copy local config folder"

tar -zcf ${basedir}/agent.tar.gz "$agent_install_folder"
abort_if_failed 'failed to add agent to tar file'

log_info "publish agent tarball to $publish_location/$os_type"
mkdir -p "$publish_location/$os_type"
scp "${basedir}/agent.tar.gz" "${publish_location}/$os_type/"
mkdir -p /tmp/publish/$os_type
scp "${basedir}/agent.tar.gz" /tmp/publish/$os_type

log_info "publish agent md5 to ${basedir}"
(_md5 "${basedir}/agent.tar.gz")  > ${publish_location}/$os_type//agent.tar.gz.md5
yes | cp -f ${publish_location}/$os_type/agent.tar.gz.md5 /tmp/publish/$os_type

log_info "Done!"