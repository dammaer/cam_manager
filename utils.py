import signal
import socket
import struct
import time

from icmplib import multiping, ping

from env import DEF_IP

HOSTS = DEF_IP

MCAST_GRP = '224.0.0.4'
MCAST_PORT = 4000


class InputTimedOut(Exception):
    pass


def host_ping(host, count=1):
    result = ping(host, count, interval=0.5, timeout=1, privileged=False)
    return result


def check_ip(count=3, interval=0.5):
    result = multiping(HOSTS, count, interval,
                       timeout=1, privileged=False)
    for host in result:
        if host.is_alive:
            return host.address


def inputTimeOutHandler(signum, frame):
    raise InputTimedOut


def input_with_timeout(timeout=0):
    unput = 0
    try:
        signal.signal(signal.SIGALRM, inputTimeOutHandler)
        signal.alarm(timeout)
        unput = input()
        signal.alarm(0)
    except InputTimedOut:
        pass
    return unput


def mcast_send():
    MULTICAST_TTL = 1

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, MULTICAST_TTL)
    try:
        while True:
            sock.sendto(b'RUN', (MCAST_GRP, MCAST_PORT))
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
        if sock.recv(1024):
            return True
    except TimeoutError:
        return False

