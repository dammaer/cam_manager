import time

from routeros_api import RouterOsApiPool
from routeros_api.exceptions import RouterOsApiConnectionError

from env import RB_IP, RB_LOGIN, RB_PASSWD, RB_ROS_VERSION


class RosOldApi:

    def __init__(self):
        self.connection = RouterOsApiPool(
            RB_IP,
            username=RB_LOGIN,
            password=RB_PASSWD,
            plaintext_login=RB_ROS_VERSION >= '6.43')
        self.api = self.connection.get_api()

    def get_lease_info(self, mac_address):
        mac_address = mac_address.upper()
        return self.api.get_resource(
            '/ip/dhcp-server/lease').get(mac_address=mac_address)

    def remove_lease(self, id):
        self.api.get_binary_resource(
            '/ip/dhcp-server/lease').call('remove',
                                          {'numbers': id})

    def __del__(self):
        self.connection.disconnect()


def get_ip_from_rb(mac):
    '''Getting an IP address from the router (mikrotik).'''
    try:
        rb = RosOldApi()
        count = 0
        while count < 3:
            lease = rb.get_lease_info(mac)
            if lease:
                ip = lease[0]['address']
                return ip
            count += 1
            time.sleep(2)
    except RouterOsApiConnectionError:
        pass


if __name__ == '__main__':
    pass
