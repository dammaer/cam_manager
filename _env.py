import os
from configparser import ConfigParser


def resolve_path(path):
    resolved_path = os.path.abspath(os.path.join(os.getcwd(), path))
    return resolved_path


CONF_DIR = resolve_path('configs')
FW_DIR = resolve_path('firmware')

config = ConfigParser()
config.read(CONF_DIR + '/settings.ini')

# SNR POE-SWITCH PARAMS:
SWI_IP = config.get('poe_switch', 'SWI_IP')
SWI_LOGIN = config.get('poe_switch', 'SWI_LOGIN')
SWI_PASSWD = config.get('poe_switch', 'SWI_PASSWD')
SWI_UPLINK = config.get('poe_switch', 'SWI_UPLINK')
SWI_MAX_POE_ETH_PORTS = config.get('poe_switch', 'SWI_MAX_POE_ETH_PORTS')

# MIKROTIK PARAMS:
RB_IP = config.get('mikrotik', 'RB_IP')
RB_LOGIN = 'admin'
RB_PASSWD = 'password'
RB_ROS_VERSION = config.get('mikrotik', 'RB_ROS_VERSION')

# CAMERA SETTINGS WHEN SETTING UP:
ADMIN_PASSWD = 'new_password'  # the password of the main user
VIEWER_PASSWD = 'new_password'  # password of the second user
NTP_DNS = config.get('ntp_server', 'NTP_DNS')  # the ntp server that will be specified during configuration
DEF_IP = config.get('default_ip', 'DEF_IP').split()  # default ip

# The default ip address of the camera that needs a pre-configuration
# The value in the dictionary is the name of a pre-configured json file
# For Dahua cameras and cameras where you first need
# to set user settings to enable access to the onfiv service
PRECONFIG_IP = {'192.168.1.108': 'DH_preconfig'}

# CAMERA SETTINGS WHEN RESETTING SETTINGS:
OTHER_LOGINS = ('admin',)  # possible username of cameras
OTHER_PASSWDS = (ADMIN_PASSWD, '1234', 'admin123')  # possible passwords of cameras
