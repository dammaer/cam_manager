import os
import time
from datetime import datetime as dt
from glob import glob
from json import dump as json_dump
from json import load as json_load
from multiprocessing import Process

from onvif2 import SERVICES, ONVIFCamera, ONVIFError
from requests import Session
from requests import get as requests_get
from requests.auth import HTTPBasicAuth, HTTPDigestAuth
from requests.exceptions import ReadTimeout
from tqdm import tqdm
from zeep import helpers

from env import (ADMIN_PASSWD, CONF_DIR, DEF_IP, FW_DIR, NTP_DNS,
                 VIEWER_PASSWD)
from utils import find_ip, get_ip, host_ping, mac_check, replace_http_params
from hikvision import activate as hw_activate

# progress bar params
BAR_FMT = '{l_bar}{bar}'
NCOLS = 30
COLOUR = 'CYAN'

ACTIONS = ('SetVideoEncoderMainStream', 'SetVideoEncoderSubStream',
           'DeleteOSD', 'SetCameraImage', 'SetEvents',
           'SetAudioEncoderConfiguration',
           'SetSystemDateAndTime', 'SetNTP', 'CreateUsers', 'SetUser',
           'SetDNS', 'SetNetworkInterfaces')


class ModelNotFound(Exception):
    pass


class BadCamera(Exception):
    pass


class Camera():
    operations = None
    http = None
    session, session_auth = None, None
    firmware_new = False
    conf_numbers = None
    selected_conf = {}
    services_versions = {}

    def __init__(self, host, port=80, user='admin', passwd='admin',
                 upgrade=True, preconf=True, sudo=False):
        self.host = host
        self.port = port
        self.user = user
        self.passwd = passwd
        self.upgrade = upgrade
        self.preconf = preconf
        self.cam_reboot = False
        self.sudo = sudo
        self.PreConfiguration()
        self.onvif = ONVIFCamera(self.host, port, user, self.passwd,
                                 CONF_DIR + '/wsdl', adjust_time=True)
        self.devicemgmt = self.onvif.create_devicemgmt_service()
        self.network = self.devicemgmt.GetNetworkInterfaces()[0]
        self.mac = mac_check(self.network.Info.HwAddress)
        deviceinfo = self.devicemgmt.GetDeviceInformation()
        self.model = deviceinfo.Model
        self.firmware = deviceinfo.FirmwareVersion
        self.serial_number = deviceinfo.SerialNumber
        self.file = glob(CONF_DIR + f'/**/{self.model}.json',
                         recursive=True)
        self._open_config()
        self.media = self._get_media_service_version()
        self.profiles = self._get_profiles()
        self.profile_token = self.profiles[0].token
        self.stream_uri = self.GetStreamUri()

    def _open_config(self):
        if self.file:
            self.file = self.file[0]
            with open(self.file, 'r') as f:
                self.operations = json_load(f)
            http = f"{self.file.rpartition('/')[0]}/http.json"
            with open(http, 'r') as f:
                self.http = json_load(f)
            self.GetFirmwareConfig()
        else:
            if not os.path.exists('log'):
                os.makedirs('log')
            with open('log/models_not_found.log', 'a+') as f:
                d_t = dt.now().strftime('%Y-%m-%d_%H:%M')
                f.write(f'{d_t} - {self.model}\n')
            raise ModelNotFound(f'Модель {self.model} не найдена!')

    def _get_media_service_version(self):
        if SERVICES['media2']['ns'] in self.onvif.xaddrs:
            media2 = self.onvif.create_media2_service()
            try:
                test_vec = media2.GetVideoEncoderConfigurations()[0]
                media2.SetVideoEncoderConfiguration(test_vec)
                self.services_versions['media'] = 2
                return media2
            except ONVIFError:
                print('\033[33mКамера не поддерживает изменение параметров '
                      'методами onvif media v2.\nНет возможности поменять '
                      'например кодек c H264 на H265.\033[0m\n')
                pass
            except IndexError:
                # If the media2.GetVideoEncoderConfigurations()
                # method returns an empty list
                raise BadCamera('Камера не поддерживает основные '
                                'сервисы onvif!\n'
                                f'SerialNumber: {self.serial_number}')
        self.services_versions['media'] = 1
        return self.onvif.create_media_service()

    def _get_profiles(self):
        media_profiles = self.media.GetProfiles()
        if media_profiles:
            return media_profiles
        else:
            raise BadCamera('Камера не поддерживает основные сервисы onvif!\n'
                            f'SerialNumber: {self.serial_number}')

    def _synchronize_time(self):
        '''
        After changing the time settings on some cameras, synchronization
        is required to perform authorization time
        '''
        self.onvif.update_xaddrs()  # the method performs time synchronization
        # when the adjust_time parameter is True
        # after that, you need to re-create all the services
        self.devicemgmt = self.onvif.create_devicemgmt_service()
        match self.services_versions['media']:
            case 1:
                self.media = self.onvif.create_media_service()
            case 2:
                self.media = self.onvif.create_media2_service()

    def _to_dict(self, obj):
        return helpers.serialize_object(obj, dict)

    def _samosbor(self):
        if self.firmware_new:
            config = None
            with open(self.file, 'r') as f:
                config = json_load(f)
            config['Firmware'][self.firmware] = self.selected_conf
            with open(self.file, 'w') as f:
                json_dump(config, f, indent=4, separators=(',', ': '))

    def _selecting_config(func):
        def wrapper(self, *args):
            conf = self.operations[func.__name__]
            if self.conf_numbers:
                num = self.conf_numbers.get(func.__name__)
                conf_num = conf.get(num, conf)
                return func(self, conf_num)
            else:
                if isinstance(conf.get('1'), dict):
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

        def get_auth():
            resp = dict(requests_get(base_url).headers.lower_items())
            if 'digest' in resp.get('www-authenticate', '').lower():
                return HTTPDigestAuth(self.user, self.passwd)
            return HTTPBasicAuth(self.user, self.passwd)

        if self.session is None:
            self.session = Session()
        self.session.auth = (self.session_auth
                             if self.session_auth else get_auth())
        try:
            s = self.session.request(
                method, url=base_url, data=data,
                headers=headers, files=files,
                json=json, timeout=timeout)
            if s.status_code == 401:
                # If after changing the admin password the new password
                # is not suitable, make a request with the default password
                self.passwd = 'admin'
                self.session.auth = get_auth()
                self.session.request(
                    method, url=base_url, data=data,
                    headers=headers, files=files,
                    json=json, timeout=timeout)
        except ReadTimeout:
            # In the case of an http request after which there is
            # no response from the camera. For example,
            # changing the ip address.
            pass

    def GetFirmwareConfig(self):
        firmware = self.operations['Firmware']
        basic_fw = self.operations['Firmware'].get('basicfirmware')
        self.conf_numbers = firmware.get(self.firmware)
        if basic_fw and self.upgrade:
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
                    print('\033[33mОбновление не удалось!\n'
                          'Будет выполнена только конфигурация.\033[0m\n')
                return
        if self.firmware in firmware:
            print('\n\033[32mВерсия прошивки известна!\033[0m\n')
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
            file = json_load(f)
        fw_id = file.get(self.model)
        fw_name = file['fw'].get(fw_id)

        def upgrade():
            for p in params:
                if p.get('files'):
                    p['files'] = {
                        "file": open(FW_DIR + f'/{fw_name}', 'rb')}
                self._request(**p)

        with tqdm(total=total,
                  bar_format=BAR_FMT,
                  ncols=NCOLS, colour=COLOUR,
                  desc='Updating') as pbar:
            process = Process(target=upgrade)
            process.start()
            not_alive = False
            for i in range(timeout):
                if i == int(timeout * 0.8) and not not_alive:
                    pbar.leave = False
                    process.kill()
                    break
                ping = host_ping(host=self.host, count=3)
                if not ping.is_alive and not not_alive:
                    not_alive = True
                elif not_alive and ping.is_alive:
                    time.sleep(20)  # after camera reboot
                    pbar.update(total - (i * (total / timeout)))
                    process.kill()
                    break
                pbar.update(total / timeout)
                time.sleep(1)

    def GetStreamUri(self):
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
        return stream_uri

    def TestVideoEncoderConfiguration(self, vec_num, modified_conf):
        resp = self.media.GetVideoEncoderConfigurations()[vec_num]
        params = ('Encoding', 'Resolution', 'RateControl')
        for p in params:
            if resp[p] != modified_conf[p]:
                return False
        return True

    def TestOSDs(self, token):
        try:
            resp = self.media.GetOSDs(token)
            if resp:
                if not resp[0].TextString:
                    return True
                elif resp[0].TextString.Type != 'Plain':
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

    def TestNetworkInterfaces(self, cam_reboot=False):
        if cam_reboot:
            ip = False
            while not ip:
                ip = get_ip(self.mac, self.sudo)
                time.sleep(0.5)
            self.host = ip
            return True
        if self.host in DEF_IP:
            ip = get_ip(self.mac, self.sudo)
            if ip:
                self.host = ip
                return True
            return False
        return True

    def PreConfiguration(self):
        '''
        For Dahua cameras and cameras where you first need
        to set user settings to enable access to the onfiv service
        '''
        hikvision_ip = ['192.168.1.64']
        # if self.host in PRECONFIG_IP and self.preconf:
        #     file = glob(CONF_DIR + f'/**/{PRECONFIG_IP[self.host]}.json',
        #                 recursive=True)[0]
        #     with open(file, 'r') as f:
        #         params = json_load(f)
        #     for p in params['PreConfiguration']:
        #         request(**p)
        #     self.passwd = ADMIN_PASSWD
        if self.host in hikvision_ip and self.preconf:
            additional_users = [['viewer', VIEWER_PASSWD, 'v']]
            hw_activate(self.host, ADMIN_PASSWD, additional_users)
            self.passwd = ADMIN_PASSWD
            self.cam_reboot = True

    def SetVideoEncoderConfiguration(self, vec_num, vec_conf, json_conf):
        match self.services_versions['media']:
            case 1:
                enum = ('JPEG', 'MPEG4', 'H264')
                if json_conf['Encoding'] not in enum:
                    json_conf['Encoding'] = 'H264'
                self.OldSetVideoEncoderConfiguration(vec_num, json_conf)
            case 2:
                self.media.SetVideoEncoderConfiguration(vec_conf)

    @_selecting_config
    def SetVideoEncoderMainStream(self, *args):
        '''
        Method of changing the main stream.
        '''
        conf = args[0]
        vec = self.media.GetVideoEncoderConfigurations()[0]
        vec.Encoding = conf['Encoding']
        vec.Resolution.Width = conf['Width']
        vec.Resolution.Height = conf['Height']
        vec.RateControl.BitrateLimit = conf['BitrateLimit']
        if 'http' in conf:
            num = conf['http']
            self._request(**self.http['SetVideoEncoderMainStream'][num])
        else:
            self.SetVideoEncoderConfiguration(0, vec, conf)
        return self.TestVideoEncoderConfiguration(0, vec)

    @_selecting_config
    def SetVideoEncoderSubStream(self, *args):
        '''
        Method of changing the sub stream.
        '''
        conf = args[0]
        vec = self.media.GetVideoEncoderConfigurations()[1]
        vec.Encoding = conf['Encoding']
        vec.Resolution.Width = conf['Width']
        vec.Resolution.Height = conf['Height']
        vec.RateControl.BitrateLimit = conf['BitrateLimit']
        if 'http' in conf:
            num = conf['http']
            self._request(**self.http['SetVideoEncoderSubStream'][num])
        else:
            self.SetVideoEncoderConfiguration(1, vec, conf)
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
        token = None
        if 'http' in conf:
            num = conf['http']
            self._request(**self.http['DeleteOSD'][num])
        else:
            match self.services_versions['media']:
                case 1:
                    token = self.profiles[0].VideoSourceConfiguration.token
            osd_text_token = [
                text_token.token
                for text_token in self.media.GetOSDs(token)
                if text_token.TextString
                and text_token.TextString.Type == 'Plain']
            if osd_text_token:
                self.media.DeleteOSD(*osd_text_token)
        return self.TestOSDs(token)

    def SetCameraImage(self):
        '''Turning on the camera's IR illumination'''
        conf = self.operations['SetCameraImage']
        if 'http' in conf:
            num = conf['http']
            self._request(**self.http['SetCameraImage'][num])

    def SetEvents(self):
        "Turning off motion detection on some camera models"
        conf = self.operations['SetCameraImage']
        if 'http' in conf:
            num = conf['http']
            http_ops = self.http['SetEvents'][num]
            if isinstance(http_ops, list):
                for op in http_ops:
                    self._request(**op)
            else:
                self._request(**http_ops)

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
        self._synchronize_time()
        return self.TestSystemDateAndTime()

    @_selecting_config
    def SetNTP(self, *args):
        conf = args[0]
        if 'http' in conf:
            num = conf['http']
            new_conf = replace_http_params(self.http['SetNTP'][num],
                                           'NTP_SERVER', NTP_DNS)
            self._request(**new_conf)
        else:
            ntp = self.devicemgmt.create_type('SetNTP')
            ntp.FromDHCP = False
            ntp.NTPManual = {"Type": "DNS", "DNSname": NTP_DNS}
            self.devicemgmt.SetNTP(ntp)
        self._synchronize_time()
        return self.TestNTP()

    def CreateUsers(self):
        conf = self.operations['CreateUsers']
        user = self.devicemgmt.create_type('CreateUsers')
        user.User = conf
        user.User['Password'] = VIEWER_PASSWD
        try:
            self.devicemgmt.CreateUsers(user)
            return True
        except ONVIFError:
            return False

    def SetUser(self):
        conf = self.operations["SetUser"]
        user = self.devicemgmt.create_type('SetUser')
        user.User = conf
        user.User['Password'] = ADMIN_PASSWD
        try:
            self.devicemgmt.SetUser(user)
        except ONVIFError:
            user.User['Username'] = conf['Username'].title()
            self.devicemgmt.SetUser(user)
        #  Reset request session
        self.passwd = ADMIN_PASSWD
        self.session, self.session_auth = None, None

    def SetDNS(self):
        conf = self.operations["SetDNS"]
        if 'http' in conf:
            num = conf['http']
            self._request(**self.http['SetDNS'][num], timeout=3)
        else:
            self.devicemgmt.SetDNS({'FromDHCP': True})
        return self.TestNetworkInterfaces()

    @_selecting_config
    def SetNetworkInterfaces(self, *args):
        conf = args[0]
        if 'http' in conf:
            num = conf['http']
            self._request(**self.http['SetNetworkInterfaces'][num])
        else:
            net_token = self.network.token
            net = self.devicemgmt.create_type('SetNetworkInterfaces')
            net.InterfaceToken = net_token
            net.NetworkInterface = {'IPv4': {'Enabled': True, 'DHCP': True}}

            def change():
                try:
                    self.devicemgmt.SetNetworkInterfaces(net)
                    if self.cam_reboot:
                        self.SystemReboot()
                except ONVIFError:
                    ONVIFCamera(
                        self.host,
                        self.port,
                        self.user,
                        self.passwd,
                        'configs/wsdl/',
                        adjust_time=True
                    ).devicemgmt.SetNetworkInterfaces(net)
            process = Process(target=change)
            process.start()
            time.sleep(3)
            process.kill()
        return self.TestNetworkInterfaces(self.cam_reboot)

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
                ip = find_ip(DEF_IP)
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
        ip = ip if ip else self.host
        info = (f'\nModel: {self.model}\n'
                f'Firmware: {self.firmware}\n'
                f'SerialNumber: {self.serial_number}\n'
                f'MAC-address: {self.mac}\n'
                f'IP-address DHCP: {self.host}\n'
                f'RTSP uri: {self.stream_uri}\n')
        return info

    def setup_camera(self):
        msg = ''
        errors = ''
        sorted_operations = {}
        for op in ACTIONS:
            value = self.operations.get(op)
            if value or isinstance(value, dict):
                sorted_operations[op] = value
        for op in tqdm(
            sorted_operations,
            bar_format=BAR_FMT,
            ncols=NCOLS,
            colour=COLOUR,
            desc='Configuration'
        ):
            method = getattr(self, op)
            if method() is False:
                errors += f'\nERROR! {op}\n'
                if op == 'SetNetworkInterfaces' or op == 'SetDNS':
                    raise BadCamera(
                        'Не поменялись настройки сети на DHCP!\n'
                        f'SerialNumber: {self.serial_number}')
        if not errors:
            self._samosbor()
        info = self.get_info_after_setup()
        print(f'\033[31m{errors}\033[0m{info}')
        msg += errors
        msg += info
        return msg


if __name__ == '__main__':
    Camera('192.168.1.64').setup_camera()
