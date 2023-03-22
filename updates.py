import os
import shutil
import sys
from hashlib import md5
from pathlib import Path

import requests

from utils import sleep_bar


class UpdateAppError(Exception):
    pass


class UpdateConfDirsError(Exception):
    pass


class Updates():
    UPD_BASE_URL = 'http://192.168.13.198:8081/cm/'
    APP_NAME = 'cam-manager'

    def __init__(self, exec_file, updates_server):
        if updates_server:
            self.UPD_BASE_URL = f"{updates_server.rpartition('/')[0]}/"
            self.APP_NAME = updates_server.rpartition('/')[-1]
        self.exec_file = exec_file

    def md5_checksum(self, file_path):
        url = self.UPD_BASE_URL + self.APP_NAME
        with open(file_path, 'rb') as f:
            local_file = md5(f.read()).hexdigest()
        remote_file = requests.head(url).headers['Content-MD5']
        return local_file == remote_file

    def get_files(self, file_name=None):
        url = self.UPD_BASE_URL + self.APP_NAME
        if file_name:
            url = self.UPD_BASE_URL + file_name
        return requests.get(url, timeout=(3, None))

    def check(self):
        conf_dirs = ('configs', 'firmware')
        confDirNotExist = False
        try:
            for dir in conf_dirs:
                if not os.path.exists(dir):
                    confDirNotExist = True
                    zip_name = f'{dir}.zip'
                    response = self.get_files(zip_name)
                    os.makedirs(dir)
                    with open(zip_name, 'wb') as file:
                        file.write(response.content)
                    shutil.unpack_archive(zip_name, dir)
                    os.remove(zip_name)

            if not self.md5_checksum(self.exec_file):
                response = self.get_files()
                os.popen(f'rm -f {self.exec_file}')
                sleep_bar(5, 'Updating')
                with open(self.exec_file, 'wb') as file:
                    file.write(response.content)
                Path(self.exec_file).chmod(0o755)
                print('\033[36mОбновление установлено \U0001F3C1\n'
                      'Запустите утилиту заново!\033[0m')
                sys.exit()
        except (requests.exceptions.ConnectionError, KeyError):
            if confDirNotExist:
                raise UpdateConfDirsError(
                    '\033[33mНе удалось загрузить конфигурационные файлы '
                    'т.к. сервер обновлений не доступен.\n'
                    'Загрузите вручную и распакуйте zip архивы configs '
                    'и firmware в директорию с утилитой!\033[0m'
                )
            raise UpdateAppError('\033[33mСервер обновлений '
                                 'недоступен!\033[0m')
