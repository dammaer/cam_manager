import json
import multiprocessing
import os
import time
from datetime import datetime as dt
from glob import glob

import requests
from onvif2 import ONVIFCamera, ONVIFError
from requests.auth import HTTPBasicAuth, HTTPDigestAuth
from tqdm import tqdm
from zeep import helpers

from env import (ADMIN_PASSWD, CONF_DIR, DEF_IP, FW_DIR, NTP_DNS, PRECONFIG_IP,
                 VIEWER_PASSWD)
from utils import find_ip, get_ip, host_ping

# progress bar params
BAR_FMT = '{l_bar}{bar}'
NCOLS = 30
COLOUR = 'CYAN'


class ModelNotFound(Exception):
    pass


class Camera():
    operations = None
    http = None
    session = None
    firmware_new = False
    conf_numbers = None
    selected_conf = {}

    def __init__(self, host, port=80, user='admin',
                 passwd='admin', upgrade=True):
        self.host = host
        self.port = port
        self.user = user
        self.passwd = passwd
        self.upgrade = upgrade
        self.PreConfiguration()
        self.onvif = ONVIFCamera(self.host, port,
                                 user, self.passwd, CONF_DIR + '/wsdl')
        self.devicemgmt = self.onvif.create_devicemgmt_service()
        self.network = self.devicemgmt.GetNetworkInterfaces()[0]
        self.mac = self.network.Info.HwAddress
        deviceinfo = self.devicemgmt.GetDeviceInformation()
        self.model = deviceinfo.Model
        self.firmware = deviceinfo.FirmwareVersion
        self.file = glob(CONF_DIR + f'/**/{self.model}.json',
                         recursive=True)
        self._open_config()
        self.services_versions = self.operations[
            'CamParams']['services_versions']
        self.media = self._get_media_service_version()
        self.profiles = self.media.GetProfiles()
        self.profile_token = self.profiles[0].token
        self.stream_uri = self.GetStreamUri()

    def _open_config(self):
        if self.file:
            self.file = self.file[0]
            with open(self.file, 'r') as f:
                self.operations = json.load(f)
            if self.operations['CamParams'].get('auth'):
                http = f"{self.file.rpartition('/')[0]}/http.json"
                with open(http, 'r') as f:
                    self.http = json.load(f)
            self.GetFirmwareConfig()
        else:
            if not os.path.exists('log'):
                os.makedirs('log')
            with open('log/models_not_found.log', 'a+') as f:
                d_t = dt.now().strftime('%Y-%m-%d_%H:%M')
                f.write(f'{d_t} - {self.model}\n')
            raise ModelNotFound(f'Модель {self.model} не найдена')

    def _get_media_service_version(self):
        match self.services_versions['media']:
            case 1:
                return self.onvif.create_media_service()
            case 2:
                return self.onvif.create_media2_service()

    def _to_dict(self, obj):
        return helpers.serialize_object(obj, dict)

    def _samosbor(self):
        if self.firmware_new:
            config = None
            with open(self.file, 'r') as f:
                config = json.load(f)
            config['Firmware'][self.firmware] = self.selected_conf
            with open(self.file, 'w') as f:
                json.dump(config, f, indent=4, separators=(',', ': '))

    def _selecting_config(func):
        def wrapper(self, *args):
            conf = self.operations[func.__name__]
            if self.conf_numbers:
                num = self.conf_numbers.get(func.__name__)
                conf_num = conf.get(num, conf)
                return func(self, conf_num)
            else:
                if conf.get('1'):
                    for num in conf:
                        result = func(self, conf[num])
                        if result:
                            self.selected_conf[func.__name__] = num
                            return result
                    return False
                return func(self, conf)
        return wrapper

    def _request(self, method, url, data=None,
                 headers=None, files=None, json=None, timeout=None):
        base_url = f"http://{self.host}{url}"

        def http_auth(type):
            match type:
                case 'Basic':
                    return HTTPBasicAuth(self.user, self.passwd)
                case 'Digest':
                    return HTTPDigestAuth(self.user, self.passwd)
                case _:
                    return None

        if self.session is None:
            auth = (self.operations['CamParams'].get('auth')
                    if self.operations else None)
            self.session = requests.Session()
            self.session.auth = http_auth(auth)
        result = self.session.request(method, url=base_url, data=data,
                                      headers=headers, files=files, json=json,
                                      timeout=timeout)
        if result.status_code != 200:
            return False

    def GetFirmwareConfig(self):
        firmware = self.operations['Firmware']
        basic_fw = self.operations['CamParams'].get('basicfirmware')
        self.conf_numbers = firmware.get(self.firmware)
        if self.firmware in firmware:
            print('\n\033[32mВерсия прошивки известна!\033[0m\n')
        elif basic_fw and self.upgrade:
            if self.firmware < basic_fw:
                print('\n\033[33mСтарая версия прошивки!\033[0m\n')
                if not os.path.exists('firmware'):
                    print('\033[31mПапка с прошивками не найдена!\n'
                          'Будет выполнена только конфигурация.\033[0m\n')
                    return
                self.FirmwareUpgrade()
                after_update = self.devicemgmt.GetDeviceInformation()
                if after_update.FirmwareVersion == basic_fw:
                    self.firmware = basic_fw
                else:
                    print('\033[33mОбновление не удалась!\n'
                          'Будет выполнена только конфигурация.\033[0m\n')
        else:
            self.firmware_new = True
            print('\n\033[33mНеизвестная прошивка камеры: '
                  f'{self.firmware}!\033[0m\n')

    def FirmwareUpgrade(self):
        total = 100
        timeout = 40
        num = self.operations['FirmwareUpgradeParams']['http']
        params = self.http['FirmwareUpgradeParams'][num]
        with open(FW_DIR + '/fw.json', 'r') as f:
            file = json.load(f)
        fw_id = file.get(self.model)
        fw_name = file['fw'].get(fw_id)

        def upgrade():
            timeout = 2
            for p in params:
                try:
                    if p.get('files'):
                        p['files'] = {
                            "file": open(FW_DIR + f'/{fw_name}', 'rb')}
                        self._request(**p, timeout=timeout)
                    self._request(**p, timeout=timeout)
                except Exception:
                    pass

        with tqdm(total=total,
                  bar_format=BAR_FMT,
                  ncols=NCOLS, colour=COLOUR,
                  desc='Updating') as pbar:
            process = multiprocessing.Process(
                target=upgrade)
            process.start()
            not_alive = False
            for i in range(timeout):
                ping = host_ping(host=self.host, count=3)
                if not ping.is_alive and not not_alive:
                    not_alive = True
                elif not_alive and ping.is_alive:
                    time.sleep(10)
                    pbar.update(total - (i * (total / timeout)))
                    process.kill()
                    break
                pbar.update(total / timeout)
                time.sleep(1)

    def GetStreamUri(self):
        stream_uri = None
        match self.services_versions['media']:
            case 1:
                stream_uri = self.media.GetStreamUri(
                    {'StreamSetup': {
                        'Stream': 'RTP-Unicast',
                        'Transport': {
                            'Protocol': 'RTSP'}},
                     'ProfileToken': self.profile_token}).Uri
            case 2:
                stream_uri = self.media.GetStreamUri(
                    {'Protocol': 'RtspUnicast',
                     'ProfileToken': self.profile_token})
        return stream_uri.split('554')[-1]

    def TestVideoEncoderConfiguration(self, vec_num, modified_conf):
        resp = self.media.GetVideoEncoderConfigurations()[vec_num]
        params = ('Encoding', 'Resolution', 'RateControl')
        for p in params:
            if resp[p] != modified_conf[p]:
                return False
        return True

    def TestOSDs(self):
        try:
            resp = self.media.GetOSDs()
            if len(resp) == 1 or not resp[0].TextString:
                return True
            return False
        except ONVIFError:
            pass  # в случае если камера не поддерживает запрос OSD

    def TestNTP(self):
        resp = self.devicemgmt.GetNTP()
        params = ('IPv4Address', 'DNSname')
        for p in params:
            ntp_dhcp = self._to_dict(resp['NTPFromDHCP'])
            ntp_manual = self._to_dict(resp['NTPManual'])
            if ntp_dhcp and ntp_dhcp[0][p] == NTP_DNS:
                return True
            elif ntp_manual and ntp_manual[0][p] == NTP_DNS:
                return True
        return False

    def TestSystemDateAndTime(self):
        resp = self.devicemgmt.GetSystemDateAndTime()
        resp_param = resp.TimeZone.TZ
        if 'GMT' in resp_param and '+03' in resp_param:
            return True
        elif '-3' in resp_param or '-03' in resp_param:
            return True
        return False

    def TestUsers(self):
        conf = self.operations['CreateUsers']
        count = 0
        while count < 15:
            resp = self.devicemgmt.GetUsers()
            for user in self._to_dict(resp):
                resp_user = user.get('Username')
                if resp_user == conf['Username']:
                    return True
            else:
                count += 1
                time.sleep(1)
        return False

    def PreConfiguration(self):
        '''
        For Dahua cameras and cameras where you first need
        to set user settings to enable access to the onfiv service
        '''
        if self.host in PRECONFIG_IP:
            file = glob(CONF_DIR + f'/**/{PRECONFIG_IP[self.host]}.json',
                        recursive=True)[0]
            with open(file, 'r') as f:
                params = json.load(f)
            for p in params['PreConfiguration']:
                self._request(**p)
            self.passwd = ADMIN_PASSWD

    @_selecting_config
    def SetVideoEncoderConfiguration0(self, *args):
        '''
        Method of changing the main stream.
        Media service version 2.
        '''
        conf = args[0]
        vec = self.media.GetVideoEncoderConfigurations()[0]
        vec.Encoding = conf['Encoding']
        vec.Resolution.Width = conf['Width']
        vec.Resolution.Height = conf['Height']
        vec.RateControl.BitrateLimit = conf['BitrateLimit']
        if 'http' in conf:
            num = conf['http']
            self._request(**self.http['SetVideoEncoderConfiguration0'][num])
        else:
            match self.services_versions['media']:
                case 1:
                    self.OldSetVideoEncoderConfiguration(0, conf)
                case 2:
                    self.media.SetVideoEncoderConfiguration(vec)
        return self.TestVideoEncoderConfiguration(0, vec)

    @_selecting_config
    def SetVideoEncoderConfiguration1(self, *args):
        '''
        Method of changing the sub stream.
        Media service version 2.
        '''
        conf = args[0]
        vec = self.media.GetVideoEncoderConfigurations()[1]
        vec.Encoding = conf['Encoding']
        vec.Resolution.Width = conf['Width']
        vec.Resolution.Height = conf['Height']
        vec.RateControl.BitrateLimit = conf['BitrateLimit']
        if 'http' in conf:
            num = conf['http']
            self._request(**self.http['SetVideoEncoderConfiguration1'][num])
        else:
            match self.services_versions['media']:
                case 1:
                    self.OldSetVideoEncoderConfiguration(1, conf)
                case 2:
                    self.media.SetVideoEncoderConfiguration(vec)
        return self.TestVideoEncoderConfiguration(1, vec)

    def OldSetVideoEncoderConfiguration(self, vec_num, conf):
        '''
        Method of changing the main/sub stream.
        Media service version 1.
        '''
        token = self.profiles[vec_num].VideoEncoderConfiguration.token
        vec = self.media.GetVideoEncoderConfiguration(token)
        vec.Encoding = conf['Encoding']
        vec.Resolution.Width = conf['Width']
        vec.Resolution.Height = conf['Height']
        vec.RateControl.BitrateLimit = conf['BitrateLimit']
        vec = {'Configuration': vec, 'ForcePersistence': True}
        self.media.SetVideoEncoderConfiguration(vec)

    @_selecting_config
    def DeleteOSD(self, *args):
        conf = args[0]
        if 'http' in conf:
            num = conf['http']
            self._request(**self.http['DeleteOSD'][num])
        elif not self.TestOSDs():
            osd_text_token = [
                text_token.token
                for text_token in self.media.GetOSDs()
                if text_token.TextString
                and text_token.TextString.Type == 'Plain']
            if osd_text_token:
                self.media.DeleteOSD(*osd_text_token)
        return self.TestOSDs()

    def SetAudioEncoderConfiguration(self):
        conf = self.operations['SetAudioEncoderConfiguration']
        if 'http' in conf:
            num = conf['http']
            self._request(**self.http['SetAudioEncoderConfiguration'][num])

    @_selecting_config
    def SetSystemDateAndTime(self, *args):
        conf = args[0]
        if 'http' in conf:
            num = conf['http']
            self._request(**self.http['SetSystemDateAndTime'][num])
        else:
            d_t = self.devicemgmt.create_type('SetSystemDateAndTime')
            d_t.DateTimeType = 'NTP'
            d_t.DaylightSavings = False
            d_t.TimeZone = conf
            self.devicemgmt.SetSystemDateAndTime(d_t)
        return self.TestSystemDateAndTime()

    @_selecting_config
    def SetNTP(self, *args):
        conf = args[0]
        if 'http' in conf:
            num = conf['http']
            self._request(**self.http['SetNTP'][num])
        else:
            ntp = self.devicemgmt.create_type('SetNTP')
            ntp.FromDHCP = False
            ntp.NTPManual = {"Type": "DNS", "DNSname": NTP_DNS}
            self.devicemgmt.SetNTP(ntp)
        return self.TestNTP()

    def CreateUsers(self):
        if not self.TestUsers():
            conf = self.operations['CreateUsers']
            user = self.devicemgmt.create_type('CreateUsers')
            user.User = conf
            user.User['Password'] = VIEWER_PASSWD
            self.devicemgmt.CreateUsers(user)
        return self.TestUsers()

    def SetUser(self):
        conf = self.operations["SetUser"]
        user = self.devicemgmt.create_type('SetUser')
        user.User = conf
        user.User['Password'] = ADMIN_PASSWD
        self.devicemgmt.SetUser(user)

    def SetDNS(self):
        conf = self.operations["SetDNS"]
        if 'http' in conf:
            num = conf['http']
            self._request(**self.http['SetDNS'][num])
        else:
            self.devicemgmt.SetDNS({'FromDHCP': True})

    def SetNetworkInterfaces(self):
        net_token = self.network.token
        net = self.devicemgmt.create_type('SetNetworkInterfaces')
        net.InterfaceToken = net_token
        net.NetworkInterface = {'IPv4': {'Enabled': True, 'DHCP': True}}

        def change():
            try:
                self.devicemgmt.SetNetworkInterfaces(net)
            except ONVIFError:
                ONVIFCamera(
                    self.host,
                    self.port,
                    self.user,
                    ADMIN_PASSWD,
                    'configs/wsdl/').devicemgmt.SetNetworkInterfaces(net)
        process = multiprocessing.Process(
            target=change)
        process.start()
        time.sleep(3)
        process.kill()

    def SetSystemFactoryDefault(self):
        conf = self.operations['FactoryDefault']
        total = 100
        timeout = 10
        def_ip = False
        if 'http' in conf:
            num = conf['http']
            self._request(**self.http['FactoryDefault'][num])
        else:
            self.devicemgmt.SetSystemFactoryDefault('Hard')
        with tqdm(total=total,
                  bar_format=BAR_FMT,
                  ncols=NCOLS, colour=COLOUR,
                  desc='Resetting') as pbar:
            for i in range(timeout):
                ip = find_ip()
                if ip:
                    def_ip = ip
                    pbar.update(total - (i * (total / timeout)))
                    break
                pbar.update(total / timeout)
                time.sleep(1)
        return def_ip

    def SystemReboot(self):
        self.devicemgmt.SystemReboot()

    def get_info_after_setup(self, ip=None):
        ip = ip if ip else get_ip(self.mac)
        info = (f'\nModel: {self.model}\n'
                f'Firmware: {self.firmware}\n'
                f'MAC-address: {self.mac}\n'
                f'RTSP uri: rtsp://admin:admin'
                f"@{ip}:554{self.stream_uri}\n")
        return info

    def setup_camera(self):
        msg = ''
        errors = ''
        for operation in tqdm(
            self.operations,
            bar_format=BAR_FMT,
            ncols=NCOLS,
            colour=COLOUR,
            desc='Configuration'
        ):
            method = getattr(self, operation, None)
            if method is None:
                pass
            elif method() is False:
                errors += f'\nERROR! {operation}\n'
        if not errors:
            self._samosbor()
        ip = self.host if self.host not in DEF_IP else None
        info = self.get_info_after_setup(ip)
        print(f'\033[31m{errors}\033[0m{info}')
        msg += errors
        msg += info
        return msg


if __name__ == '__main__':
    try:
        ip = find_ip()
        if ip:
            setup = Camera(host=ip)
            setup.setup_camera()
        else:
            print('\033[31mКамера с дефолтным ip не найдена.\033[0m')
    except ONVIFError as e:
        print('\033[31mНе удалось произвести настройку!\n'
              f'Причина: {e}\033[0m')
