import re

import pexpect

from env import SWI_IP, SWI_LOGIN, SWI_PASSWD


class SwiFail(Exception):
    pass


class Switch():
    prompt = "#"
    _except = [prompt, pexpect.TIMEOUT, pexpect.EOF]
    ports_up = []

    def __init__(self):
        try:
            self.telnet = pexpect.spawn(f"telnet {SWI_IP}", timeout=5,
                                        encoding="utf-8")
            self.telnet.expect("login")
            self.telnet.sendline(SWI_LOGIN)
            self.telnet.expect("[Pp]assword")
            self.telnet.sendline(SWI_PASSWD)
            self.telnet.expect(self.prompt)
            self.telnet.sendline("terminal length 0")
            self.telnet.expect(self.prompt)
        except pexpect.exceptions.EOF:
            return None

    def ethernet_status(self):
        self.telnet.sendline('sh int ethernet status')
        match = self.telnet.expect(self._except)
        if not match:
            output = self.telnet.before.replace("\r\n", ";")
            output = re.sub(r'\s+', '&', output)
            for strg in output.split(';'):
                if 'UP/UP' in strg and '1/0/24' not in strg:
                    self.ports_up.append(strg.split('&')[0].split('/')[-1])
        else:
            return False

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
        self.telnet.sendline('int ethernet 1/0/1-23')
        self.telnet.expect(self.prompt)
        self.telnet.sendline('shutdown')
        self.telnet.expect(self.prompt)
        self.exit_conf_mode()

    def turning_on_ports(self):
        try:
            self.enter_conf_mode()
            self.telnet.sendline('int ethernet 1/0/1-23')
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
