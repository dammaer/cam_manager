import re
import signal
import socket
import struct
import time

from icmplib import multiping, ping

from env import DEF_IP, OTHER_PASSWDS
from ros_old_api import RosOldApi

HOSTS = DEF_IP

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
    result = multiping(HOSTS, count, interval,
                       timeout=1, privileged=False)
    for host in result:
        if host.is_alive:
            return host.address


def get_ip(mac):
    rb = RosOldApi()
    ip = None
    count = 0
    while count < 3:
        lease = rb.get_lease_info(mac)
        if lease:
            ip = lease[0]['address']
            break
        count += 1
        time.sleep(1)
    return ip


def brute_force():
    for passwd in iter(OTHER_PASSWDS):
        yield passwd


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
    MULTICAST_TTL = 1

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, MULTICAST_TTL)
    try:
        while True:
            sock.sendto(get_local_ip().encode(), (MCAST_GRP, MCAST_PORT))
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass


def mcast_recv():
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
