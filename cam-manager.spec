# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='cam-manager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

import shutil

from env import MAIN_DIR
from pathlib import Path

dirs = ('configs', 'firmware')
makeZipDir = MAIN_DIR + '/dist'

for dir in dirs:
    shutil.make_archive(dir, 'zip', MAIN_DIR + f'/{dir}')


for zip_file in Path(MAIN_DIR).glob('*.zip*'):
    zip_in_dir = Path(MAIN_DIR + f"/dist/{zip_file.name.split('/')[-1]}")
    if zip_in_dir.exists():
        os.remove(zip_in_dir)
    shutil.move(zip_file, MAIN_DIR + '/dist')

os.system(f'scp {makeZipDir}/* cam_setup:/var/www/cm/')
os.system('ssh cam_setup "cd /root/configs/ && unzip -u /var/www/cm/configs.zip && cd /root/firmware/ && unzip -u /var/www/cm/firmware.zip && cp /var/www/cm/cam-manager /root/"')
