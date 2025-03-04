import re

import pexpect

from env import (SWI_IP, SWI_LOGIN, SWI_MAX_POE_ETH_PORTS, SWI_PASSWD,
                 SWI_UPLINK)


class SwiFail(Exception):
    pass


class Switch():
    prompt = "#"
    _except = [prompt, pexpect.TIMEOUT, pexpect.EOF]
    ports_up = []

    def __init__(self):
        if self.check_telnet_connect():
            self.telnet = pexpect.spawn(f"telnet {SWI_IP}", timeout=30,
                                        encoding="utf-8")
            self.telnet.expect("login")
            self.telnet.sendline(SWI_LOGIN)
            self.telnet.expect("[Pp]assword")
            self.telnet.sendline(SWI_PASSWD)
            self.telnet.expect(self.prompt)
            self.telnet.sendline("terminal length 0")
            self.telnet.expect(self.prompt)
        else:
            raise SwiFail('Не удается подключиться к коммутатору! '
                          'Возможно указан\nне тот IP адрес, '
                          'либо нет доступа по telnet.')

    def check_telnet_connect(self):
        '''
        We make a trial connection to the switch, with the
        specified ip, login and password in settings.ini
        '''
        try:
            telnet = pexpect.spawn(f"telnet {SWI_IP}", timeout=3,
                                   encoding="utf-8")
            telnet.expect("login")
            telnet.sendline(SWI_LOGIN)
            telnet.expect("[Pp]assword")
            telnet.sendline(SWI_PASSWD)
            telnet.expect(self.prompt)
            telnet.close()
            return True
        except (pexpect.exceptions.TIMEOUT, pexpect.exceptions.EOF):
            return False

    def ethernet_status(self):
        self.telnet.sendline('sh int ethernet status')
        match = self.telnet.expect(self._except)
        if not match:  # Checking when to parse the output
            output = self.telnet.before.replace("\r\n", ";")
            output = re.sub(r'\s+', '&', output)
            for strg in output.split(';'):
                port_num = strg.split('&')[0].split('/')[-1]
                if ('UP/UP' in strg and int(port_num)
                   <= int(SWI_MAX_POE_ETH_PORTS)):
                    if port_num != SWI_UPLINK:
                        self.ports_up.append(port_num)

    def ports_range(self):
        try:
            command = 'int ethernet 1/0/'
            uplink = int(SWI_UPLINK)
            max_ports = int(SWI_MAX_POE_ETH_PORTS)
            if uplink in range(1, max_ports+1):
                if uplink == 1:
                    command += f'2-{max_ports}'
                elif uplink == max_ports:
                    command += f'1-{max_ports-1}'
                else:
                    command += f'1-{uplink-1};{uplink+1}-{max_ports}'
            else:
                command += f'1-{max_ports}'
            return command
        except ValueError:
            raise SwiFail('В settings.ini указаны неправильные '
                          'значения портов POE коммутатора!')

    def enter_conf_mode(self):
        self.telnet.sendline('conf t')
        self.telnet.expect(self.prompt)

    def exit_conf_mode(self):
        self.telnet.sendline('exit')
        self.telnet.expect(self.prompt)
        self.telnet.sendline('exit')
        self.telnet.expect(self.prompt)

    def turning_off_ports(self):
        self.enter_conf_mode()
        self.telnet.sendline(self.ports_range())
        self.telnet.expect(self.prompt)
        self.telnet.sendline('shutdown')
        self.telnet.expect(self.prompt)
        self.exit_conf_mode()

    def turning_on_ports(self):
        try:
            self.enter_conf_mode()
            self.telnet.sendline(self.ports_range())
            self.telnet.expect(self.prompt)
            self.telnet.sendline('no shutdown')
            self.telnet.expect(self.prompt)
            self.exit_conf_mode()
        except pexpect.exceptions.EOF:
            raise SwiFail('Режим конфигурации коммутатора используется '
                          'другим пользователем!')

    def enable_port(self, port):
        self.enter_conf_mode()
        self.telnet.sendline(f'int ethernet 1/0/{port}')
        self.telnet.expect(self.prompt)
        self.telnet.sendline('no shutdown')
        self.telnet.expect(self.prompt)
        self.exit_conf_mode()

    def disable_port(self, port):
        self.enter_conf_mode()
        self.telnet.sendline(f'int ethernet 1/0/{port}')
        self.telnet.expect(self.prompt)
        self.telnet.sendline('shutdown')
        self.telnet.expect(self.prompt)
        self.exit_conf_mode()


if __name__ == '__main__':
    pass
