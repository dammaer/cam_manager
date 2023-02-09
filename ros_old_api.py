import routeros_api

from env import RB_IP, RB_LOGIN, RB_PASSWD, RB_ROS_VERSION


class RosOldApi:
    def __init__(self):
        self.connection = routeros_api.RouterOsApiPool(
            RB_IP,
            username=RB_LOGIN,
            password=RB_PASSWD,
            plaintext_login=RB_ROS_VERSION >= '6.43')
        self.api = self.connection.get_api()

    def get_lease_info(self, mac_address):
        mac_address = mac_address.replace('-', ':').upper()
        return self.api.get_resource(
            '/ip/dhcp-server/lease').get(mac_address=mac_address)

    def remove_lease(self, id):
        self.api.get_binary_resource(
            '/ip/dhcp-server/lease').call('remove',
                                          {'numbers': id})

    def __del__(self):
        self.connection.disconnect()


if __name__ == '__main__':
    pass
