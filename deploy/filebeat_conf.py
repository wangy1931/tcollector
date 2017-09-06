import ConfigParser

import os

runner_config_path = os.path.split(os.path.realpath(__file__))[0]

template = """
- input_type: <input_type>

  # Paths that should be crawled and fetched. Glob based paths.
  paths:
    #- <path>

  document_type: <document_type>
  fields.orgid: <orgid>
  fields.sysid: <sysid>
  fields.token: <token>
  fields_under_root: true
  close_inactive: 2h
  tail_files: true
  multiline.pattern: '<pattern>'
  multiline.negate: true
  multiline.match: after
  encoding: <encoding>
  
"""


def load_runner_conf(path):
    runner_config_path = path
    # print runner_config_path
    runner_config = ConfigParser.SafeConfigParser()
    runner_config.read(runner_config_path)
    return runner_config


def get_comman_dict():
    common = load_runner_conf(runner_config_path + '/common.conf')

    return {
        "<input_type>": common.get('conf', 'input_type'),
        "<orgid>": common.get('conf', 'fields.orgid'),
        "<sysid>": common.get('conf', 'fields.sysid'),
        "<token>": common.get('conf', 'fields.token')
    }


def get_all_dict(common, user):
    temp = common.copy()
    for key in user:
        temp["<%s>" % key] = user[key]
    return temp


def set_filebeat_yml(common, user_conf):
    write_date = ""
    with open(runner_config_path + '/filebeat_template.yml') as f:
        for line in f.readlines():
            if "##NEXT" in line:
                write_date += "#" + ("=" * 78) + "\n"
                for user_info in user_conf:
                    temp = get_all_dict(common, user_info)
                    temp_str = template
                    for key in temp:
                        if '<path>' == key:
                            for path in temp[key]:
                                temp_str = temp_str.replace("#- <path>", "- %s\n    #- <path>" % path)
                        else:
                            temp_str = temp_str.replace(key, temp[key])

                    write_date += temp_str
                write_date += "##NEXT\n#" + ("=" * 78) + "\n"

            else:
                write_date += line
    with open(runner_config_path + '/filebeat.yml', 'wr') as f:
        f.writelines(write_date)


def get_user_conf_dict(config, config_name):
    return {
        "document_type": config.get(config_name, "document_type"),
        "path": config.get(config_name, "path").split(","),
        "pattern": config.get(config_name, "pattern") if (config.has_option(config_name, "pattern")) else '',
        "encoding": config.get(config_name, "encoding") if (config.has_option(config_name, "encoding")) else 'plain'
    }


def get_user_conf():
    user = load_runner_conf(runner_config_path + '/user.conf')
    conf_list = user.sections()
    conf_dict_list = []
    if "conf" in conf_list:
        old_list = eval(user.get('conf', 'logs'))
        conf_dict_list = conf_dict_list + old_list
        conf_list.remove("conf")
    for conf_name in conf_list:
        conf_dict_list.append(get_user_conf_dict(user, conf_name))
    return conf_dict_list


if __name__ == '__main__':
    common = get_comman_dict()
    user_conf = get_user_conf()
    set_filebeat_yml(common, user_conf)
