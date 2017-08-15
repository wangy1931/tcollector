import imp
import sys
import os
filebeat_path = "%s/../filebeat"%os.path.split(os.path.realpath(sys.argv[0]))[0]
sys.path.append(filebeat_path)
from filebeat_conf import *
if __name__=='__main__':
    common = get_comman_dict()
    user_conf = get_user_conf()
    set_filebeat_yml(common, user_conf)

