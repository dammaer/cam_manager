import os
import sys

from arg_parser import Parser
from updates import UpdateAppError, UpdateConfDirsError, Updates

try:
    prs = Parser().parse_args(sys.argv[1:])
    exec_file = sys.executable
    if exec_file.split('/')[-1] != 'python' and not prs.disable_updates:
        Updates(exec_file, prs.updates_server).check()
    if not os.path.exists('configs'):  # if prs.disable_updates == True
        print('\033[33mОтсутствуют папки с конфигурационными файлами!\n'
              'Загрузите вручную и распакуйте zip архивы\nconfigs '
              'и firmware в директорию с утилитой!\033[0m')
        sys.exit()
except UpdateConfDirsError as e:
    print(e)
    sys.exit()
except UpdateAppError as e:
    print(e)

import signal
import time
from datetime import datetime as dt

from onvif2 import ONVIFError
from requests.exceptions import ConnectionError
from simple_term_menu import TerminalMenu

from camera import BadCamera, Camera, ModelNotFound
from env import DEF_IP, OTHER_LOGINS, OTHER_PASSWDS, SWI_IP, SWI_UPLINK
from poe_switch import SwiFail, Switch
from utils import (MacAddressBad, brute_force, find_ip, get_ip, host_ping,
                   ip_iface_check, mac_check, mcast_recv, mcast_send, scan_mac,
                   sleep_bar)

ip_iface, iface = ip_iface_check(DEF_IP)
if ip_iface:
    print(('\033[33mДля корректной работы необходимо добавить '
           'ip-интерфейс из сети:\033[0m'))
    for net in ip_iface:
        free_ip = net.rpartition(".")[0] + '.*'
        print((f'\033[33m-> {net}\033[0m\n'
               f'sudo ip address add {free_ip}/24 dev {iface}'))
    sys.exit()

INPUT_TIMEOUT = 120
SUDO = os.getuid() == 0


class InputTimedOut(Exception):
    pass


def inputTimeOutHandler(signum, frame):
    raise InputTimedOut


def menu(menu_items, menu_title=None, clear_screen=True):
    menu_cursor_style = ("fg_cyan", "bold")
    menu = TerminalMenu(
        menu_entries=menu_items,
        title=menu_title,
        menu_cursor="> ",
        menu_cursor_style=menu_cursor_style,
        cycle_cursor=True,
        clear_screen=clear_screen
    )
    return menu


def single_setup():
    try:
        ip = find_ip(DEF_IP, count=2)
        if ip:
            print(f'Дефолтный ip камеры: {ip}.')
            setup = Camera(host=ip)
            setup.setup_camera()
        else:
            print('\033[33mКамера с дефолтным ip не найдена.\033[0m\n')
    except (ONVIFError, ConnectionError):
        print('\033[33mНе удалось подключиться! Повторите попытку.\033[0m\n')
    except (ModelNotFound, BadCamera) as e:
        error_msg = ('\nНе удалось произвести '
                     f'настройку!\nПричина: {e}\n')
        print(f'\033[31m{error_msg}\033[0m')


def multi_setup():
    d_t = dt.now().strftime('%Y-%m-%d_%H:%M')
    switch = Switch()
    switch.turning_on_ports()
    time.sleep(5)
    switch.ethernet_status()
    cam_on_ports = switch.ports_up
    cam_count_msg = f'Камер подключено: {len(cam_on_ports)}.\n'
    if not len(cam_on_ports):
        print('\033[31mНет подключенных камер!\033[0m\n')
        return
    print(cam_count_msg)
    switch.turning_off_ports()
    if not os.path.exists('log'):
        os.makedirs('log')
    with open(f'log/{d_t}.log', 'a+') as f:
        f.write(cam_count_msg)
        for port in cam_on_ports:
            print(f'\033[36mНастраиваем камеру на {port} порту.\033[0m')
            switch.enable_port(port)
            # Ждем 5 сек. после включения порта, чтобы камера
            # гарантированно отвечала на пинг.
            sleep_bar(5, 'Wait')
            ip = find_ip(DEF_IP, count=2)
            result = f'\n-----{port} порт:-----'
            if ip:
                print(f'Дефолтный ip камеры: {ip}.')
                try:
                    msg = Camera(host=ip).setup_camera()
                    result += msg
                    f.write(result)
                    switch.disable_port(port)
                except (ONVIFError, ModelNotFound, BadCamera) as e:
                    error_msg = ('\nНе удалось произвести '
                                 f'настройку!\nПричина: {e}\n')
                    result += error_msg
                    f.write(result)
                    print(f'\033[31m{error_msg}\033[0m')
                    switch.disable_port(port)
            else:
                not_found_msg = ('\nWARNING! Возможно камера уже '
                                 'настроена! Не найдена по '
                                 'дефолтному ip.\n')
                result += not_found_msg
                f.write(result)
                print(f'\033[33m{not_found_msg}\033[0m')
    switch.turning_on_ports()
    print('\033[32mНастройка завершена!\033[0m\n')


def factory_reset():
    mac = None
    ip = None
    while True:
        try:
            signal.alarm(INPUT_TIMEOUT)
            mac = mac_check(input('\033[36m0 - отмена> \033[0m'))
            signal.alarm(0)
            print('\nПолучаем ip...')
            rb_ip = get_ip(mac, sudo=SUDO)
            ip = (rb_ip if rb_ip and host_ping(rb_ip, count=2).is_alive
                  else find_ip(DEF_IP, count=2))
        except MacAddressBad as e:
            zero = e.args[0]
            if zero.isdigit() and int(zero) == 0:
                print('\033[33mОтмена\033[0m\n')
                break
            print(f'\033[33m{e.args[1]} Попробуйте ещё раз.\033[0m')
        if ip:
            print(f'IP камеры: {ip}. Приступаем к сбросу...')
            bf = brute_force(OTHER_LOGINS, OTHER_PASSWDS)
            while True:
                try:
                    login, passwd = next(bf)
                    camera = Camera(host=ip, user=login, passwd=passwd,
                                    upgrade=False, preconf=False)
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
        elif mac and not ip:
            print('\n\033[33mКамера не получает ip по DHCP '
                  'от офисного роутера и не найдена ни по одному из '
                  'дефолтных ip!\033[0m\n')
        if mac:
            break


def without_additional_devices():
    d_t = dt.now().strftime('%Y-%m-%d_%H:%M')
    if not os.path.exists('log'):
        os.makedirs('log')
    with open(f'log/sudo_mode_{d_t}.log', 'a+') as f:
        done = []
        f.write('-----sudo mode:-----')
        while True:
            def_ip = find_ip(DEF_IP, count=2)
            if def_ip:
                mac_addr = scan_mac(def_ip)
                if mac_addr not in done:
                    try:
                        print(f'Дефолтный ip камеры: {def_ip}. '
                              f'MAC: {mac_addr}.')
                        os.system(f'arp -s {def_ip} {mac_addr}')
                        msg = Camera(host=def_ip, sudo=SUDO).setup_camera()
                        f.write(msg)
                        done.append(mac_addr)
                    except (ONVIFError, ModelNotFound, BadCamera) as e:
                        error_msg = ('\nНе удалось произвести '
                                     'настройку камеры!\n'
                                     f'Причина: {e}\n')
                        f.write(error_msg)
                        print(f'\033[31m{error_msg}\033[0m\n'
                              '\033[33mДля продолжения настройки отключите '
                              'проблемную камеру и нажмите Enter.\033[0m')
                        while input() != '':
                            time.sleep(1)
                    os.system(f'arp -d {def_ip}')
            else:
                not_found_msg = ('\nКамер с дефолтным ip '
                                 'не найдено!\n')
                if not done:
                    f.write(not_found_msg)
                    print(f'\033[33m{not_found_msg}\033[0m')
                else:
                    print(f'\033[32mКамер настроено: {len(done)}\033[0m')
                print('\033[32mНастройка завершена!\033[0m\n')
                break


def setup():
    banner = ('\033[?25l\033[36m _ _  _ _    _ _  _  _  _  _  _  _\n'
              '(_(_|| | |  | | |(_|| |(_|(_|(/_| \n'
              '                           _|     \n'
              '   > https://github.com/dammaer\033[0m')
    banner_shown = False
    title = 'ДЛЯ НАСТРОЙКИ КАМЕР HiWatch ПОПОЛНИТЕ МОЮ КАРТУ 2202203210783777 НА 100 р.!!!\nВыберите режим настройки:\n'
    options = ["Настройка одной камеры",
               "Настройка нескольких камер с использованием POE коммутатора",
               "Сброс камеры к заводским настройкам",
               "Завершение работы (Q или Esc)"]
    options_with_sudo = ["Настройка одной или нескольких камер",
                         "Сброс камеры к заводским настройкам",
                         "Завершение работы (Q или Esc)"]
    main_menu_exit = False
    single_setup_menu_back = False
    multi_setup_menu_back = False
    factory_reset_menu_back = False
    wad_menu_back = False

    factory_title = ('Введите mac-адрес камеры:\n')
    factory_reset_select = menu(['Ввести mac-адрес',
                                 'Назад'],
                                factory_title,
                                clear_screen=False)
    signal.signal(signal.SIGALRM, inputTimeOutHandler)

    while not main_menu_exit:
        signal.alarm(INPUT_TIMEOUT)
        if not banner_shown:
            os.system('cls' if os.name == 'nt' else 'clear')
            print(banner)
            banner_shown = True
            time.sleep(1.2)
        if not SUDO:
            main_select = menu(options, title).show()
            match main_select:
                case 0:
                    while not single_setup_menu_back:
                        signal.alarm(INPUT_TIMEOUT)
                        single_title = ('Если камера подключена и линк\n'
                                        'загорелcя, то выберите кнопку '
                                        '"Запуск"\n')
                        single_setup_select = menu(['Запуск', 'Назад'],
                                                   single_title,
                                                   clear_screen=False).show()
                        match single_setup_select:
                            case 0:
                                signal.alarm(0)
                                single_setup()
                            case 1 | None:
                                single_setup_menu_back = True
                    single_setup_menu_back = False
                case 1:
                    while not multi_setup_menu_back:
                        signal.alarm(INPUT_TIMEOUT)
                        if host_ping(SWI_IP, count=2).is_alive:
                            multi_title = ('POE коммутатор работает!\n'
                                           'Если камеры подключены и '
                                           'все линки\nзагорелись, то '
                                           'выберите "Запуск"\n'
                                           )
                            multi_setup_select = menu(
                                ['Запуск', 'Назад'],
                                multi_title,
                                clear_screen=False).show()
                            match multi_setup_select:
                                case 0:
                                    signal.alarm(0)
                                    multi_setup()
                                case 1 | None:
                                    multi_setup_menu_back = True
                        else:
                            multi_title = ('Включите POE коммутатор!\n'
                                           f'Убедитесь, что {SWI_UPLINK} '
                                           'порт - uplink.\n')
                            multi_setup_select = menu(['Назад'],
                                                      multi_title).show()
                            match multi_setup_select:
                                case 0 | None:
                                    multi_setup_menu_back = True
                    multi_setup_menu_back = False
                case 2:
                    while not factory_reset_menu_back:
                        signal.alarm(INPUT_TIMEOUT)
                        match factory_reset_select.show():
                            case 0:
                                factory_reset()
                            case 1 | None:
                                factory_reset_menu_back = True
                    factory_reset_menu_back = False
                case 3 | None:
                    main_menu_exit = True
        else:
            main_select_with_sudo = menu(options_with_sudo, title).show()
            match main_select_with_sudo:
                case 0:
                    while not wad_menu_back:
                        signal.alarm(INPUT_TIMEOUT)
                        wad_title = ('Если камеры подключены и линк\n'
                                     'загорелcя, то выберите кнопку '
                                     '"Запуск"\n')
                        wad_setup_select = menu(['Запуск', 'Назад'],
                                                wad_title,
                                                clear_screen=False).show()
                        match wad_setup_select:
                            case 0:
                                signal.alarm(0)
                                without_additional_devices()
                            case 1 | None:
                                wad_menu_back = True
                    wad_menu_back = False
                case 1:
                    while not factory_reset_menu_back:
                        signal.alarm(INPUT_TIMEOUT)
                        match factory_reset_select.show():
                            case 0:
                                factory_reset()
                            case 1 | None:
                                factory_reset_menu_back = True
                    factory_reset_menu_back = False
                case 2 | None:
                    main_menu_exit = True


if __name__ == '__main__':
    from multiprocessing import Process

    is_running = mcast_recv()

    if is_running:
        print('\033[33mПроцесс настройки уже выполняется '
              f'одним из пользователей на хосте {is_running}!\033[0m')
    else:
        process = Process(
            target=mcast_send)
        process.start()
        try:
            setup()
        except SwiFail as e:
            print(f'\033[33m{e}\nНастройка прервана!\033[0m')
        except InputTimedOut:
            print(f'\033[33mПрервано по таймауту {INPUT_TIMEOUT} c.\033[0m')
        except KeyboardInterrupt:
            process.kill()
            print('\n\033[33mНастройка прервана!\033[0m')
            sys.exit()
        finally:
            process.kill()
