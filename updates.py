import os
import sys
from hashlib import md5
from pathlib import Path
from shutil import unpack_archive

from requests import get as requests_get
from requests import head as requests_head
from requests.exceptions import ConnectionError


class UpdateAppError(Exception):
    pass


class UpdateConfDirsError(Exception):
    pass


class Updates():
    UPD_BASE_URL = 'http://192.168.13.198:8081/cm/'
    APP_NAME = 'cam-manager'
    confDirNotExist = False

    def __init__(self, exec_file, updates_server):
        if updates_server:
            self.UPD_BASE_URL = f"{updates_server.rpartition('/')[0]}/"
            self.APP_NAME = updates_server.rpartition('/')[-1]
        self.exec_file = exec_file

    def md5_checksum(self, file_path):
        url = self.UPD_BASE_URL + self.APP_NAME
        with open(file_path, 'rb') as f:
            local_file = md5(f.read()).hexdigest()
        remote_file = requests_head(url).headers['Content-MD5']
        return local_file == remote_file

    def get_files(self, file_name=None):
        url = self.UPD_BASE_URL + self.APP_NAME
        if file_name:
            url = self.UPD_BASE_URL + file_name
        return requests_get(url, timeout=(3, None))

    def download_and_unpack_dir(self, name):
        zip_name = f'{name}.zip'
        response = self.get_files(zip_name)
        os.makedirs(name, exist_ok=True)
        with open(zip_name, 'wb') as file:
            file.write(response.content)
        unpack_archive(zip_name, name)
        os.remove(zip_name)

    def check_dirs(self, dirs_exist=False):
        conf_dirs = ('configs', 'firmware')
        for dir in conf_dirs:
            if not os.path.exists(dir):
                self.confDirNotExist = True
                self.download_and_unpack_dir(dir)
            if dirs_exist:
                self.download_and_unpack_dir(dir)

    def check(self):
        try:
            self.check_dirs()
            if not self.md5_checksum(self.exec_file):
                response = self.get_files()
                os.remove(self.exec_file)
                with open(self.exec_file, 'wb') as file:
                    file.write(response.content)
                Path(self.exec_file).chmod(0o755)
                if not self.confDirNotExist:
                    print('\033[36mЗагружаем новые '
                          'конфигурационные файлы...\033[0m')
                    self.check_dirs(dirs_exist=True)
                print('\033[36mОбновление установлено \U0001F3C1\n'
                      'Запустите утилиту заново!\033[0m')
                sys.exit()
        except (ConnectionError, KeyError):
            if self.confDirNotExist:
                raise UpdateConfDirsError(
                    '\033[33mНе удалось загрузить конфигурационные файлы '
                    'т.к. сервер обновлений не доступен.\n'
                    'Загрузите вручную и распакуйте zip архивы configs '
                    'и firmware в директорию с утилитой!\033[0m'
                )
            raise UpdateAppError('\033[33mСервер обновлений '
                                 'недоступен!\033[0m')
