#!/bin/bash

# ------------ config section ------------ #
admin_user=administrator  # must be a user in "administrators" group 
passwd=Cloud123
org_id=2
sys_id=2
token=9c43fce52bcf44dcc55e8ee6a4288c8ccbf29125
metric=tsdb.cloudwiz.cn
alertd=https://alert.cloudwiz.cn
# ---------------------------------------- #

update=""
if [[ "$#" == 1 && $1 == "-update" ]]; then
   update="update=1"
fi

# create temp 'host' file
echo "[win]" >> hosts.tmp

# copy hosts
cat hosts >> hosts.tmp

# populate windows variables
echo -e "\n[win:vars]\n" >> hosts.tmp
echo -e "ansible_user=${admin_user}\nansible_password=${passwd}\n" >> hosts.tmp
echo -e "ansible_port=5986\nansible_connection=winrm\nansible_winrm_server_cert_validation=ignore\n" >> hosts.tmp

./altenv/bin/ansible-playbook win_agent_setup.yaml -v -i hosts.tmp --extra-vars "org_id=${org_id} sys_id=${sys_id} token=${token} metric=${metric} alertd=${alertd} ${update}"

# delete temp host file
rm -f hosts.tmp
