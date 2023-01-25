import json
import multiprocessing
import os
import time
from datetime import datetime as dt
from datetime import timedelta as td

import requests
from onvif import ONVIFCamera, ONVIFError
from requests.auth import HTTPBasicAuth, HTTPDigestAuth
from tqdm import tqdm
from zeep import helpers

from env import ADMIN_PASSWD, CONF_DIR, NTP_DNS, VIEWER_PASSWD
from utils import get_ip, find_ip

BAR_FMT = '{l_bar}{bar:50}'


class ModelNotFound(Exception):
    pass


class Camera():
    operations = None
    firmware_new = False
    conf_numbers = None
    selected_conf = {}

    def __init__(self, host, port=80, user='admin', passwd='admin'):
        self.host = host
        self.port = port
        self.user = user
        self.passwd = passwd
        onvif = ONVIFCamera(self.host, port,
                            user, passwd, CONF_DIR + '/wsdl')
        self.media = onvif.create_media_service()
        self.devicemgmt = onvif.create_devicemgmt_service()
        self.media_tokens = self.media.GetProfiles()
        self.profile_token = self.media_tokens[0].token
        self.stream_uri = self.GetStreamUri()
        self.network = self.devicemgmt.GetNetworkInterfaces()[0]
        self.net_token = self.network.token
        self.mac = self.network.Info.HwAddress
        self.deviceinfo = self.devicemgmt.GetDeviceInformation()
        self.model = self.deviceinfo.Model
        self.firmware = self.deviceinfo.FirmwareVersion
        self.file = CONF_DIR + f'/cam/{self.model}.json'
        try:
            with open(self.file, 'r') as f:
                self.operations = json.load(f)
            self.GetFirmwareConfig()
        except FileNotFoundError:
            if not os.path.exists('log'):
                os.makedirs('log')
            with open('log/models_not_found.log', 'a+') as f:
                d_t = dt.now().strftime('%Y-%m-%d_%H:%M')
                f.write(f'{d_t} - {self.model}\n')
            raise ModelNotFound(f'Модель {self.model} не найдена')

    def _request(self, method, url, data=None, headers=None, auth=None):
        base_url = f"http://{self.host}/{url}"

        def http_auth(type):
            match type:
                case 'Basic':
                    return HTTPBasicAuth(self.user, self.passwd)
                case 'Digest':
                    return HTTPDigestAuth(self.user, self.passwd)
                case _:
                    return None
        result = requests.request(method, url=base_url, data=data,
                                  headers=headers, auth=http_auth(auth))
        if result.status_code != 200:
            return False

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

    def GetFirmwareConfig(self):
        firmware = self.operations['Firmware']
        self.conf_numbers = firmware.get(self.firmware)
        if self.firmware in firmware:
            print('\n\033[32mВерсия прошивки известна!\033[0m\n')
        else:
            self.firmware_new = True
            print(f'\n\033[33mНовая прошивка камеры: '
                  f'{self.firmware}!\033[0m\n')

    def GetStreamUri(self):
        stream_uri = self.media.GetStreamUri(
            {'StreamSetup': {
                'Stream': 'RTP-Unicast',
                'Transport': {
                    'Protocol': 'RTSP'}},
             'ProfileToken': self.profile_token}).Uri
        return stream_uri.split('554')[-1]

    def GetVideoEncoderConfiguration(self, conf, token):
        resp = self.media.GetVideoEncoderConfiguration(token)
        params = ('Encoding', 'Resolution', 'Quality', 'H264', 'RateControl')
        for p in params:
            resp_param = self._to_dict(resp[p])
            if not resp_param == conf['Configuration'][p]:
                return False
        return True

    def GetOSDs(self, token):
        try:
            resp = self.media.GetOSDs(token)
            if len(resp) == 1 or not resp[0].TextString:
                return True
            return False
        except ONVIFError:
            pass  # в случае если камера не поддерживает запрос OSD

    def GetNTP(self):
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

    def GetSystemDateAndTime(self):
        resp = self.devicemgmt.GetSystemDateAndTime()
        resp_param = resp.TimeZone.TZ
        if '-3' in resp_param or '-03' in resp_param:
            return True
        return False

    def GetUsers(self):
        conf = self.operations['CreateUsers']['User']
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

    @_selecting_config
    def SetVideoEncoderConfiguration0(self, *args):
        conf = args[0]
        if 'method ' in conf:
            self._request(**conf)
        else:
            vec_token0 = self.media_tokens[0].VideoEncoderConfiguration.token
            conf['Configuration']["token"] = vec_token0
            conf['Configuration']["Name"] = vec_token0
            conf['Configuration']["SessionTimeout"] = td(0)
            self.media.SetVideoEncoderConfiguration(conf)
        test_vec0 = self.GetVideoEncoderConfiguration(conf, vec_token0)
        return test_vec0

    @_selecting_config
    def SetVideoEncoderConfiguration1(self, *args):
        conf = args[0]
        if 'method ' in conf:
            self._request(**conf)
        else:
            vec_token1 = self.media_tokens[1].VideoEncoderConfiguration.token
            conf['Configuration']["token"] = vec_token1
            conf['Configuration']["Name"] = vec_token1
            conf['Configuration']["SessionTimeout"] = td(0)
            self.media.SetVideoEncoderConfiguration(conf)
        test_vec1 = self.GetVideoEncoderConfiguration(conf, vec_token1)
        return test_vec1

    def SetAudioEncoderConfiguration(self):
        aec = self.operations.get('SetAudioEncoderConfiguration')
        self._request(**aec)

    @_selecting_config
    def DeleteOSD(self, *args):
        vsc_token = self.media_tokens[0].VideoSourceConfiguration.token
        conf = args[0]
        if 'method' in conf:
            self._request(**conf)
        else:
            osd_text_token = [
                text_token.token
                for text_token in self.media.GetOSDs(vsc_token)
                if text_token.TextString
                and text_token.TextString.Type == 'Plain']
            if osd_text_token:
                self.media.DeleteOSD(*osd_text_token)
        return self.GetOSDs(vsc_token)

    @_selecting_config
    def SetNTP(self, *args):
        conf = args[0]
        if 'method' in conf:
            self._request(**conf)
        else:
            conf['NTPManual']['DNSname'] = NTP_DNS
            self.devicemgmt.SetNTP(conf)
        return self.GetNTP()

    @_selecting_config
    def SetSystemDateAndTime(self, *args):
        conf = args[0]
        if 'method' in conf:
            self._request(**conf)
        else:
            self.devicemgmt.SetSystemDateAndTime(conf)
        return self.GetSystemDateAndTime()

    def SetDNS(self):
        dns = self.operations.get("SetDNS")
        self._request(**dns)

    def CreateUsers(self):
        user = self.operations["CreateUsers"]
        user['User']['Password'] = VIEWER_PASSWD
        self.devicemgmt.CreateUsers(user)
        return self.GetUsers()

    def SetUser(self):
        user = self.operations["SetUser"]
        user['User']['Password'] = ADMIN_PASSWD
        self.devicemgmt.SetUser(user)

    def SetNetworkInterfaces(self):
        net = self.operations["SetNetworkInterfaces"]
        net["InterfaceToken"] = self.net_token

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
        if 'method' in conf:
            self._request(**conf)
        else:
            self.devicemgmt.SetSystemFactoryDefault('Hard')
        with tqdm(total=total,
                  desc='Идёт сброс к заводским настройкам',
                  bar_format=BAR_FMT) as pbar:
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
        for operation in tqdm(self.operations, bar_format=BAR_FMT):
            method = getattr(self, operation, None)
            if method is None:
                pass
            elif method() is False:
                errors += f'\nERROR! {operation}\n'
        if not errors:
            self._samosbor()
        msg += errors
        msg += self.get_info_after_setup()
        return msg


if __name__ == '__main__':
    try:
        ip = find_ip()
        if ip:
            setup = Camera(host=ip)
            print(setup.setup_camera())
        else:
            print('\033[31mКамера с дефолтным ip не найдена.\033[0m')
    except ONVIFError as e:
        print(f'\033[31mНе удалось произвести настройку!\nПричина: {e}\033[0m')
