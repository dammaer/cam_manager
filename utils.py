import re
import signal
import socket
import struct
import time
from itertools import product

from icmplib import multiping, ping
from tqdm import trange

from env import DEF_IP, OTHER_LOGINS, OTHER_PASSWDS
from ros_old_api import RosOldApi

MCAST_GRP = '224.0.0.4'
MCAST_PORT = 4000


class InputTimedOut(Exception):
    pass


class MacAddressBad(Exception):
    pass


def host_ping(host, count=1):
    result = ping(host, count, interval=0.5, timeout=1, privileged=False)
    return result


def find_ip(count=3, interval=0.5):
    '''
    Send ICMP Echo Request packets to default ip.
    '''
    result = multiping(DEF_IP, count, interval,
                       timeout=1, privileged=False)
    for host in result:
        if host.is_alive:
            return host.address


def get_ip(mac):
    '''
    Getting an IP address from a router (mikrotik).
    '''
    rb = RosOldApi()
    ip = None
    count = 0
    while count < 3:
        lease = rb.get_lease_info(mac)
        if lease:
            ip = lease[0]['address']
            break
        count += 1
        time.sleep(2)
    return ip


def brute_force():
    '''
    Brute force of usernames and passwords. Used when resetting the camera.
    '''
    for login, passwd in product(OTHER_LOGINS, OTHER_PASSWDS):
        yield login, passwd

def replace_http_params(structure, old_value, new_value):
    '''
    Replaces the parameters in /configs/cam/name/http.json to the required values.
    For example NTP_SERVER on ntp.example.com
    '''
    new_structure = {}
    for key, value in structure.items():
        if isinstance(value, dict):
            new_structure[key] = replace_http_params(value, old_value, new_value)
        else:
            new_structure[key] = value.replace(old_value, new_value) if old_value in value else value
    return new_structure

def sleep_bar(sec):
    t = trange(sec, leave=False,
               bar_format='{postfix[0]} {postfix[1][value]} {postfix[2]}',
               postfix=["Wait", dict(value=sec), 'sec.'])
    for _ in t:
        time.sleep(1)
        t.postfix[1]["value"] -= 1
        t.update()


def inputTimeOutHandler(signum, frame):
    raise InputTimedOut


def input_with_timeout(timeout=0):
    unput = 0
    try:
        signal.signal(signal.SIGALRM, inputTimeOutHandler)
        signal.alarm(timeout)
        unput = input('\033[32m> \033[0m')
        signal.alarm(0)
    except InputTimedOut:
        pass
    return unput


def mac_check(mac):
    mac = mac.strip()
    mac_pattern = '([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})'
    if bool(re.match(mac_pattern, mac)):
        return mac
    else:
        raise MacAddressBad(mac, 'Некорректно введён mac-адрес!')


def get_local_ip():
    '''
    Returns the primary ip address specified to the host.
    '''
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        # doesn't even have to be reachable
        s.connect(('1.1.1.1', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


def mcast_send():
    '''
    Used to send multicast the ip address of the host
    on which the utility is running.
    '''
    MULTICAST_TTL = 1

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, MULTICAST_TTL)
    while True:
        sock.sendto(get_local_ip().encode(), (MCAST_GRP, MCAST_PORT))
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
