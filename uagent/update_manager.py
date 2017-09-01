import os
import time
import json
import shutil
import tarfile
import requests
from datetime import datetime, timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
TMP_DIR = os.path.join(BASE_DIR, 'tmp')
NGINX_PATH = "/usr/local/nginx/html/"
FETCH_INTERVAL = 10


def make_targz(output_filename, source_dir):
    tar = tarfile.open(output_filename, "w:gz")
    for root, dir, files in os.walk(source_dir):
        for file in files:
            fullpath = os.path.join(root, file)
            tar.add(fullpath, arcname=file)
    tar.close()


def check_and_clear(dir_path):
    if os.path.isdir(dir_path):
        shutil.rmtree(dir_path)
    os.makedirs(dir_path)


def getUpdatedConfig(token, fromTime):
    getConfig_url = "http://127.0.0.1:5001/cmdb/config/UpdatedConfig?" \
                    + "token=" + str(token) \
                    + "&" \
                    + "fromTime=" + fromTime
    r = requests.get(getConfig_url)
    return r.text


# Core update file managing class
class update_manager:
    def __init__(self, token, uuid):
        self.token = token
        self.uuid = uuid
        self.src_dir = TMP_DIR
        self.des_filename = 'update.tar.gz'
        self.orgId = 0
        self.sysId = 0
        check_and_clear(TMP_DIR)

    # TODO
    def get_current_version(self, orgID, sysID, uuid):
        current_version = 121
        return current_version

    # Packaging updated file for each host
    def packager(self):
        update_files = list(os.listdir(TMP_DIR))
        for directory in update_files:
            abs_path = os.path.join(TMP_DIR, directory)
            path = directory.split('_')
            check_and_clear(os.path.join(NGINX_PATH, path[0], path[1], path[2]))
            des_path = os.path.join(NGINX_PATH, path[0], path[1], path[2], 'update.tar.gz')
            if os.path.isdir(abs_path):
                make_targz(des_path, abs_path)
            shutil.rmtree(abs_path)
            # self.deployer(self.token, directory.split('_')[1], os.path.join(NGINX_PATH, 'update.tar.gz'))

    def fetcher(self):
        check_and_clear(TMP_DIR)
        # Check the host list need update
        # uuid_list = self.get_updated_uuid()

        # Get Modified Configs
        lastHourDateTime = datetime.now() - timedelta(hours=200)
        fromTime = lastHourDateTime.strftime('%Y-%m-%dT%H:%M:%SZ')
        try:
            j = json.loads(getUpdatedConfig(self.token, fromTime))
        except:
            print("Failed to connect to cmsservice or nothing need be updated.")
            return None

        for item in j:
            uuid = "test"
            dir_name = str(item['orgId']) + '_' + str(item['sysId']) + '_' + uuid
            host_dir = os.path.join(TMP_DIR, dir_name)
            if not os.path.exists(host_dir):
                check_and_clear(host_dir)
            txt = open(os.path.join(host_dir, "struct.txt"), "a")
            filename = item['fullPath'].split("/")[-1]
            item_info = filename + ' ' + item['fullPath']
            txt.write(item_info)
            txt.write('\n')
            txt.close()

        for item in j:
            uuid = "test"
            dir_name = str(item['orgId']) + '_' + str(item['sysId']) + '_' + uuid
            host_dir = os.path.join(TMP_DIR, dir_name)
            filename = item['fullPath'].split("/")[-1]

            if (item['configType'] == "host"):
                continue
            content_dic = {}
            for prop in item['props']:
                if content_dic.__contains__(prop['section']):
                    content_dic[prop['section']][prop['name']] = prop['value']
                else:
                    content_dic[prop['section']] = {}
                    content_dic[prop['section']][prop['name']] = prop['value']

            conf = open(os.path.join(host_dir, filename), "w")
            for section in content_dic:
                conf.write('[' + section + ']\n')
                for key in content_dic[section]:
                    conf.write(key + "=" + content_dic[section][key] + "\n")
            conf.close()

        for item in j:
            uuid = "test"
            dir_name = str(item['orgId']) + '_' + str(item['sysId']) + '_' + uuid
            host_dir = os.path.join(TMP_DIR, dir_name)
            filename = item['fullPath'].split("/")[-1]

            if (item['configType'] == "service"):
                continue
            content_dic = {}
            for prop in item['props']:
                if content_dic.__contains__(prop['section']):
                    content_dic[prop['section']][prop['name']] = prop['value']
                else:
                    content_dic[prop['section']] = {}
                    content_dic[prop['section']][prop['name']] = prop['value']

            conf = open(os.path.join(host_dir, filename), "w")
            for section in content_dic:
                conf.write('[' + section + ']\n')
                for key in content_dic[section]:
                    conf.write(key + "=" + content_dic[section][key] + "\n")
            conf.close()

    def deployer(self, token, uuid, src):
        # orgID = str(orgID);sysID = str(sysID);uuid = str(uuid)
        host_path = os.path.join(NGINX_PATH, token, uuid)
        check_and_clear(host_path)
        update_file = src
        shutil.move(update_file, host_path)

    def process(self):
        self.fetcher()
        self.packager()
        #    self.deployer(self.token, self.uuid)


if __name__ == '__main__':
    token = "9c43fce52bcf44dcc55e8ee6a4288c8ccbf29125"
    uuid = "123456"
    u = update_manager(token, uuid)
    u.process()
