#!/bin/bash

# ------------ config section ------------ #
remote_user=pezhang  # user for ssh login
become_user=root     # user to run sudo, normally is "root"
org_id=2
sys_id=2
token=9c43fce52bcf44dcc55e8ee6a4288c8ccbf29125
metric=tsdb.cloudwiz.cn
alertd=https://alert.cloudwiz.cn
os=Ubuntu # allowed values: Debian | Ubuntu | Redhat
# ---------------------------------------- #

update=""
if [[ "$#" == 1 && $1 == "-update" ]]; then
   update="update=1"
fi

./altenv/bin/ansible-playbook agent_setup.yaml -v -i hosts --ask-pass --ask-become-pass --user=${remote_user} --become-user=${become_user} --extra-vars "org_id=${org_id} sys_id=${sys_id} token=${token} metric=${metric} alertd=${alertd} os=${os} $update"

