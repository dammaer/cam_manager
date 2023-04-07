import fcntl
import re
import signal
import socket
import struct
import time
from scapy.all import conf, get_if_addr, srp
from scapy.layers.l2 import ARP, Ether
from ipaddress import IPv4Network
from itertools import product
from icmplib import multiping, ping
from tqdm import trange

from ros_old_api import get_ip_from_rb

MCAST_GRP = '224.0.0.4'
MCAST_PORT = 4000


class InputTimedOut(Exception):
    pass


class MacAddressBad(Exception):
    pass


def host_ping(host, count=1):
    result = ping(host, count, interval=0.5, timeout=1, privileged=False)
    return result


def find_ip(def_ip, count=3, interval=0.5):
    '''
    Send ICMP Echo Request packets to default ip.
    '''
    result = multiping(def_ip, count, interval,
                       timeout=1, privileged=False)
    for host in result:
        if host.is_alive:
            return host.address


def get_local_net_and_mask():
    iface = str(conf.iface)
    local_ip = get_if_addr(iface)
    local_mask = socket.inet_ntoa(
        fcntl.ioctl(
            socket.socket(socket.AF_INET, socket.SOCK_DGRAM),
            35099,
            struct.pack('256s', iface.encode('utf-8')))[20:24])
    address = IPv4Network(
        f'{local_ip}/{local_mask}',
        strict=False)
    return f'{address.network_address}/{address.prefixlen}'


def scan_ip_by_mac(mac, def_net=None):
    net = get_local_net_and_mask() if def_net is None else def_net
    count = 0
    while count < 5:
        ans, _ = srp(Ether(dst=mac)/ARP(
            pdst=net), verbose=0, timeout=3)
        for i in ans:
            if i[1].getlayer(Ether).src == mac:
                return (i[1].getlayer(ARP).psrc)
        count += 1
        time.sleep(1)


def scan_mac(ip):
    """
    Returns MAC address of any device connected to the network
    If ip is down, returns None instead
    """
    ans, _ = srp(
        Ether(dst='ff:ff:ff:ff:ff:ff')/ARP(pdst=ip), timeout=3, verbose=0)
    if ans:
        return ans[0][1].src


def get_ip(mac, sudo=False):
    return get_ip_from_rb(mac) if not sudo else scan_ip_by_mac(mac)


def brute_force(other_logins, other_passwds):
    '''
    Brute force of usernames and passwords. Used when resetting the camera.
    '''
    for login, passwd in product(other_logins, other_passwds):
        yield login, passwd


def replace_http_params(structure, old_value, new_value):
    '''
    Replaces the parameters in /configs/cam/name/http.json
    to the required values.
    For example NTP_SERVER on ntp.example.com
    '''
    new_structure = {}
    for key, value in structure.items():
        if isinstance(value, dict):
            new_structure[key] = replace_http_params(
                value, old_value, new_value)
        else:
            new_structure[key] = value.replace(
                old_value, new_value) if old_value in value else value
    return new_structure


def sleep_bar(sec, msg):
    t = trange(sec, leave=False,
               bar_format='{postfix[0]} {postfix[1][value]} {postfix[2]}',
               postfix=[msg, dict(value=sec), 'sec.'])
    for _ in t:
        time.sleep(1)
        t.postfix[1]["value"] -= 1
        t.update()


def inputTimeOutHandler(signum, frame):
    raise InputTimedOut


def input_with_timeout(timeout=0, msg='>'):
    signal.signal(signal.SIGALRM, inputTimeOutHandler)
    signal.alarm(timeout)
    unput = input(f'\033[36m{msg} \033[0m')
    signal.alarm(0)
    return unput


def mac_check(mac):
    mac = mac.strip()
    mac_pattern = '([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})'
    if bool(re.match(mac_pattern, mac)):
        return mac
    else:
        raise MacAddressBad(mac, 'Некорректно введён mac-адрес!')


# def get_local_ip():
#     '''
#     Returns the primary ip address specified to the host.
#     '''
#     s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#     s.settimeout(0)
#     try:
#         # doesn't even have to be reachable
#         s.connect(('1.1.1.1', 1))
#         ip = s.getsockname()[0]
#     except Exception:
#         ip = '127.0.0.1'
#     finally:
#         s.close()
#     return ip


def mcast_send():
    '''
    Used to send multicast the ip address of the host
    on which the utility is running.
    '''
    MULTICAST_TTL = 1

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, MULTICAST_TTL)
    while True:
        sock.sendto(get_if_addr(conf.iface).encode(), (MCAST_GRP, MCAST_PORT))
        time.sleep(0.5)


def mcast_recv():
    '''
    Subscribes to a multicast group in which the ip address of the host
    is broadcast if the utility is already running.
    '''
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.settimeout(0.5)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((MCAST_GRP, MCAST_PORT))
    mreq = struct.pack("4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)

    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    try:
        return sock.recv(1024).decode()
    except TimeoutError:
        return False
