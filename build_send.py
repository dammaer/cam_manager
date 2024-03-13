import os
import shutil
from pathlib import Path

from env import MAIN_DIR
from utils import sleep_bar

dirs = ('configs', 'firmware')
makeZipDir = MAIN_DIR + '/dist'
container_id = '866c19e6abfe'

print('0 - скомпилировать бинарник и выгрузить конфиги\n1 - только конфиги')
сhoice = int(input('> '))

if not сhoice:
    while os.system(f'docker exec -it {container_id} bash -c "exit"') != 0:
        os.system(f'docker restart {container_id}')
        sleep_bar(3, 'restarting container')

    os.system(f'docker exec -it {container_id} bash -c '
              '"cd /project && source venv_ubuntu16.04/bin/activate '
              '&& pyinstaller --clean cam-manager.spec"')

for dir in dirs:
    shutil.make_archive(dir, 'zip', MAIN_DIR + f'/{dir}')

for zip_file in Path(MAIN_DIR).glob('*.zip*'):
    zip_in_dir = Path(MAIN_DIR + f"/dist/{zip_file.name.split('/')[-1]}")
    if zip_in_dir.exists():
        os.remove(zip_in_dir)
    shutil.move(zip_file, MAIN_DIR + '/dist')

os.system(f'scp {makeZipDir}/* cam_setup:/var/www/cm/')
os.system('ssh cam_setup "cd /root/configs/ && unzip -o '
          '/var/www/cm/configs.zip && cd /root/firmware/ && unzip -o '
          '/var/www/cm/firmware.zip && cp -f /var/www/cm/cam-manager /root/"')
