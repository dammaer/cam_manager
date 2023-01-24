import os
import sys

if not os.path.exists('configs'):
    print('\n\033[33mДля запуска утилиты необходима '
          'директория configs c конфигурационными файлами!\n\033[0m')
    sys.exit()

import time
from datetime import datetime as dt

from onvif import ONVIFError

from camera import Camera, ModelNotFound
from env import SWI_IP
from poe_switch import SwiFail, Switch
from utils import (check_ip, host_ping, input_with_timeout,
                   mcast_recv, mcast_send)


def single_setup():
    try:
        ip = check_ip(count=2)
        if ip:
            print(f'Дефолтный ip камеры: {ip}.\n')
            setup = Camera(host=ip)
            print(setup.setup_camera())
        else:
            print('\033[31mКамера с дефолтным ip не найдена.\033[0m')
    except ONVIFError as e:
        print(f'\033[31mНе удалось произвести настройку!\nПричина: {e}\033[0m')


def multi_setup():
    timeout = 20
    run = False
    while True:
        if host_ping(SWI_IP, count=2).is_alive:
            print('\033[32mPOE коммутатор работает.\033[0m\n'
                  '\033[35mЕсли камеры подключены и линки '
                  'на свиче загорелись,\nто введите любую цифру кроме 0'
                  f' (0 - отмена). Таймаут {timeout} сек..\033[0m')
        else:
            print('\033[31mВключите POE коммутатор SNR-S2982G-24T-POE-E!\n'
                  'Убедитесь, что 24 порт - uplink.\033[0m')
            break
        try:
            cam_connected = int(input_with_timeout(timeout))
            if cam_connected:
                print('Отлично! Начинаем настройку!\n')
                run = True
                break
            else:
                break
        except ValueError:
            print('\033[33mВведите цифру!\033[0m')

    if run:
        d_t = dt.now().strftime('%Y-%m-%d_%H:%M')
        switch = Switch()
        switch.turning_on_ports()
        switch.ethernet_status()
        cam_on_ports = switch.ports_up
        cam_count_msg = f'Камер подключено: {len(cam_on_ports)}.\n'
        if not len(cam_on_ports):
            print('\033[31mНет подключенных камер!\033[0m')
            return
        print(cam_count_msg)
        switch.turning_off_ports()
        if not os.path.exists('log'):
            os.makedirs('log')
        with open(f'log/{d_t}.log', 'a+') as f:
            f.write(cam_count_msg)
            for port in cam_on_ports:
                print(f'\033[35mНастраиваем камеру на {port} порту.\033[0m')
                t = 3 if cam_on_ports.index(port) != 0 else 0
                # Ждём 3 сек. так как предыдущая настроенная камера
                # может все еще пинговаться по дефолтному ip.
                time.sleep(t)
                switch.enable_port(port)
                # Ждем 2 сек. после включения порта, чтобы камера
                # гарантированно отвечала на пинг.
                time.sleep(2)
                ip = check_ip(count=2)
                result = f'\n-----{port} порт:-----'
                if ip:
                    print(f'Дефолтный ip камеры: {ip}.')
                    try:
                        ok_msg = Camera(host=ip).setup_camera()
                        result += ok_msg
                        print(ok_msg)
                    except ONVIFError as e:
                        error_msg = ('\nНе удалось произвести '
                                     f'настройку!\nПричина: {e}\n')
                        result += error_msg
                        print(f'\033[31m{error_msg}\033[0m')
                        switch.disable_port(port)
                    except ModelNotFound as e:
                        error_msg = ('\nНе удалось произвести '
                                     f'настройку!\nПричина: {e}\n')
                        result += error_msg
                        print(f'\033[31m{error_msg}\033[0m')
                        switch.disable_port(port)
                else:
                    not_found_msg = ('\nWARNING! Возможно камера уже '
                                     'настроена! Не найдена по '
                                     'дефолтному ip.\n')
                    result += not_found_msg
                    print(f'\033[33m{not_found_msg}\033[0m')
                f.write(result)
        switch.turning_on_ports()
        print('\033[32mНастройка завершена!\033[0m')


def setup():
    timeout = 30
    msg = (f'\nВыберите режим настройки (таймаут {timeout} сек.):\n'
           '1 - настройка одной камеры\n'
           '2 - настройка нескольких камер с использованием POE коммутатора\n'
           '0 - завершение работы')
    print(msg)
    while True:
        try:
            mode = int(input_with_timeout(timeout))
            match mode:
                case 0:
                    break
                case 1:
                    single_setup()
                    print(msg)
                case 2:
                    multi_setup()
                    print(msg)
                case _:
                    print('\033[33mВведите предложенные варианты!\033[0m')
        except ValueError:
            print('\033[33mВведите цифру!\033[0m')


if __name__ == '__main__':
    import multiprocessing

    if mcast_recv():
        print('\033[33mПроцесс настройки уже выполняется '
              'одним из пользователей!\033[0m')
    else:
        try:
            process = multiprocessing.Process(
                target=mcast_send)
            process.start()
            setup()
            process.kill()
        except SwiFail as e:
            print(f'\033[33m{e}\nНастройка прервана!\033[0m')
        except KeyboardInterrupt:
            print('\n\033[33mНастройка прервана!\033[0m')
            try:
                sys.exit(1)
            except SystemExit:
                os._exit(1)
