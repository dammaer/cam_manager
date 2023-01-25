from onvif import ONVIFError
from zeep import helpers

from camera import Camera
from env import ADMIN_PASSWD, NTP_DNS

OK = '\033[32mOK\033[0m'
ERROR = '\033[93mERROR'
FAIL = '\033[31mFAIL'
ENDC = '\033[0m'


class TestingOnvif(Camera):

    def __init__(self, host, port=80, user='admin',
                 passwd='admin', check=False, debug=False):
        self.check = check
        super().__init__(host, port, user, passwd, debug)

    def to_dict(self, obj):
        return helpers.serialize_object(obj, dict)

    def GetInfo(self):
        info = (f'Model: {self.model}\n'
                f'Firmware: {self.firmware}\n'
                f'MAC-address: {self.mac}\n'
                f'RTSP uri: {self.GetStreamUri()}\n'
                )
        return info

    def GetStreamUri(self):
        stream_uri = self.media.GetStreamUri(
            {'StreamSetup': {
                'Stream': 'RTP-Unicast',
                'Transport': {
                    'Protocol': 'RTSP'}},
             'ProfileToken': self.profile_token}).Uri
        return stream_uri

    def GetVideoEncoderConfiguration(self, vec=0):
        vec_token = self.media_tokens[vec].VideoEncoderConfiguration.token
        resp = self.media.GetVideoEncoderConfiguration(vec_token)
        if self.check:
            params = ('Encoding', 'Resolution', 'Quality',
                      'H264', 'RateControl')
            conf = self.operations[
                f'SetVideoEncoderConfiguration{vec}']['Configuration']
            test = ''
            for p in params:
                resp_param = self.to_dict(resp[p])
                if resp_param == conf[p]:
                    test += f'Video profile-{vec}: {p} - {OK}\n'
                else:
                    test += (f'Video profile-{vec}: {p} - '
                             f'{ERROR} ({resp_param}){ENDC}\n')
            return test[:-1]
        return resp

    def GetOSDs(self):
        vsc_token = self.media_tokens[0].VideoSourceConfiguration.token
        try:
            resp = self.media.GetOSDs(vsc_token)
            if self.check:
                test = None
                if len(resp) == 1 or not resp[0].TextString:
                    test = f'OSD - {OK}'
                else:
                    test = (f'OSD - {ERROR} (не убрана лишняя '
                            f'информация на видео){ENDC}')
                return test
            return resp
        except ONVIFError:
            return f'OSD - {FAIL} (не поддерживается){ENDC}'

    def GetNTP(self):
        resp = self.devicemgmt.GetNTP()
        if self.check:
            params = ('IPv4Address', 'DNSname')
            test = f'NTP - {ERROR} (адрес не совпадает){ENDC}'
            for p in params:
                ntp_dhcp = self.to_dict(resp['NTPFromDHCP'])
                ntp_manual = self.to_dict(resp['NTPManual'])
                if ntp_dhcp and ntp_dhcp[0][p] == NTP_DNS:
                    return f'NTP - {OK}'
                elif ntp_manual and ntp_manual[0][p] == NTP_DNS:
                    return f'NTP - {OK}'
            return test
        return resp

    def GetSystemDateAndTime(self):
        resp = self.devicemgmt.GetSystemDateAndTime()
        if self.check:
            test = None
            resp_param = resp.TimeZone.TZ
            if '-3' in resp_param or '-03' in resp_param:
                test = f'TimeZone - {OK}'
            else:
                test = f'TimeZone - {ERROR} ({resp_param}){ENDC}'
            return test
        return resp

    def GetUsers(self):
        resp = self.devicemgmt.GetUsers()
        if self.check:
            try:
                conf = self.operations['CreateUsers']['User']
                resp_param = self.to_dict(resp[1]['Username'])
                if resp_param == conf['Username']:
                    return f'User viewer: {OK}\n'
            except IndexError:
                return (f'User viewer - {FAIL} '
                        f'(пользователь viewer не создан){ENDC}\n')
        return resp

    def GetDNS(self):
        return self.devicemgmt.GetDNS()


if __name__ == '__main__':
    """
    debug:
        True - отключаем загрузку json конфига камеры
    check:
        True - проверка конкретных параметров после настройки камеры
                (debug=False)
        False - полный вывод всех параметров
                (debug=True)
    """
    test = TestingOnvif(host='192.168.13.234',
                        passwd=ADMIN_PASSWD,
                        check=True,
                        debug=False)
    print(test.GetInfo())
    try:
        print(test.GetVideoEncoderConfiguration())
        print(test.GetVideoEncoderConfiguration(vec=1))
        print(test.GetOSDs())
        print(test.GetNTP())
        print(test.GetSystemDateAndTime())
        print(test.GetUsers())
    except TypeError:
        pass
