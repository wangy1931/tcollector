import ConfigParser

import os

runner_config_path = os.path.split(os.path.realpath(__file__))[0]

def load_runner_conf(path):
    runner_config_path = path
    # print runner_config_path
    runner_config = ConfigParser.SafeConfigParser()
    runner_config.read(runner_config_path)
    return runner_config

def get_comman_dict():
    common = load_runner_conf(runner_config_path+'/common.conf')

    return dict(
    input_type="  input_type: %s" % common.get('conf', 'input_type'),
    fileds_orgid = "  fields.orgid: %s" % common.get('conf', 'fields.orgid'),
    fileds_sysid = "  fields.sysid: %s" % common.get('conf', 'fields.sysid'),
    fileds_token = "  fields.token: %s" % common.get('conf', 'fields.token'),
    ields_under_root = "  ields_under_root: %s" % common.get('conf', 'ields_under_root'),
    tail_files = "  tail_files: %s" % common.get('conf', 'tail_files'),
    multiline_negate = "  multiline.negate: %s" % common.get('conf', 'multiline.negate'),
    multiline_match = "  multiline.match: %s" % common.get('conf', 'multiline.match'),
    )
def get_user_conf():
    user =load_runner_conf(runner_config_path+'/user.conf')
    return eval(user.get('conf','logs'))

def set_filebeat_yml(common,user_conf):
    write_date=""
    with open(runner_config_path+'/filebeat_template.yml') as f:
        for line in f.readlines():
             if "##NEXT" in line:
                 write_date += "#" + ("=" * 78) + "\n"
                 for user_info in user_conf:
                     write_date += "-\n"
                     for key in common:
                         write_date += common[key] + "\n"
                     for user_info_key in user_info:
                         if 'path' in user_info_key:
                             write_date += "  paths:\n"
                             for p in user_info[user_info_key]:
                                 write_date +='    - %s\n'%p
                         elif 'document_type' in user_info_key:
                             write_date += "  document_type: %s\n" % user_info[user_info_key]
                         elif 'pattern' in user_info_key:
                             write_date +="  multiline.pattern: \'%s\'\n"%user_info[user_info_key]

                 write_date+="##NEXT\n#"+("="*78)+"\n"

             else:
                 write_date+=line
    with open(runner_config_path+'/filebeat.yml','wr') as f:
        f.writelines(write_date)

if __name__=='__main__':
    common= get_comman_dict()
    user_conf= get_user_conf()
    set_filebeat_yml(common, user_conf)
