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
from utils import (brute_force, find_ip, get_ip, host_ping,
                   input_with_timeout, mac_check,
                   mcast_recv, mcast_send)
from utils import MacAddressBad


def single_setup():
    try:
        ip = find_ip(count=2)
        if ip:
            print(f'Дефолтный ip камеры: {ip}.')
            setup = Camera(host=ip)
            print(setup.setup_camera())
        else:
            print('\n\033[31mКамера с дефолтным ip не найдена.\033[0m\n')
    except ONVIFError as e:
        print(f'\033[31mНе удалось произвести настройку!\nПричина: {e}\033[0m')
    except ModelNotFound as e:
        error_msg = ('\nНе удалось произвести '
                     f'настройку!\nПричина: {e}\n')
        print(f'\033[31m{error_msg}\033[0m')
    finally:
        print('Выход из режима настройки одной камеры...')


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
                ip = find_ip(count=2)
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


def factory_reset():
    mac = None
    timeout = 40
    print(f'Введите mac-адрес камеры (таймаут {timeout} сек.). 0 - отмена')
    while True:
        try:
            mac = mac_check(input_with_timeout(timeout))
            ip = get_ip(mac)
            if ip:
                bf = brute_force()
                while True:
                    try:
                        passwd = next(bf)
                        camera = Camera(host=ip, passwd=passwd)
                        def_ip = camera.SetSystemFactoryDefault()
                        if def_ip:
                            print(camera.get_info_after_setup(ip=def_ip))
                            break
                        else:
                            print('\n\033[33mПосле попытки сброса, '
                                  'камера не вернула дефолтный ip!\n'
                                  'Скорее всего произошел сброс всех '
                                  'параметров, но без настроек сети и '
                                  'пользоваталей.\033[0m\n')
                            break
                    except ONVIFError:
                        pass
                    except ModelNotFound as e:
                        error_msg = ('\nНе удалось произвести '
                                     f'настройку!\nПричина: {e}\n')
                        print(f'\033[31m{error_msg}\033[0m')
                        break
                    except StopIteration:
                        print('\n\033[31mНи один из известных '
                              'паролей не подошёл!\033[0m\n')
                        break
            else:
                print('\n\033[33mКамера не получает ip по DHCP '
                      'от офисного роутера!\033[0m\n')
                break
        except MacAddressBad as e:
            zero = e.args[0]
            if zero.isdigit() and int(zero) == 0:
                break
            print(f'\033[33m{e.args[1]} Попробуйте ещё раз.\033[0m')
        finally:
            if mac:
                print('Выход из режима сброса...')
                break


def setup():
    timeout = 30
    banner = ('\033[36m _ _  _ _    _ _  _  _  _  _  _  _\n'
              '(_(_|| | |  | | |(_|| |(_|(_|(/_| \n'
              '                           _|     \033[0m\n')
    msg = (f'\nВыберите режим настройки (таймаут {timeout} сек.):\n'
           '1 - настройка одной камеры\n'
           '2 - настройка нескольких камер с использованием POE коммутатора\n'
           '3 - сброс камеры к заводским настройкам\n'
           '0 - завершение работы')
    print(banner, msg)
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
                case 3:
                    factory_reset()
                    print(msg)
                case _:
                    print('\033[33mВведите предложенные варианты!\033[0m')
        except ValueError:
            print('\033[33mВведите цифру!\033[0m')


if __name__ == '__main__':
    import multiprocessing

    is_running = mcast_recv()
    if is_running:
        print('\033[33mПроцесс настройки уже выполняется '
              f'одним из пользователей на хосте {is_running}!\033[0m')
    else:
        process = multiprocessing.Process(
            target=mcast_send)
        process.start()
        try:
            setup()
        except SwiFail as e:
            print(f'\033[33m{e}\nНастройка прервана!\033[0m')
        except KeyboardInterrupt:
            process.kill()
            print('\n\033[33mНастройка прервана!\033[0m')
            sys.exit()
        finally:
            process.kill()
