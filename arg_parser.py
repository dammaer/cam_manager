import argparse

VERSION = '1.4.0'


def Parser():
    parser = argparse.ArgumentParser(
        prog='cam-manager',
        description='''Утилита для настройки IP-камер.''',
        epilog='''\033[36m(ノ ˘_˘)ノ\033[0m
                  https://github.com/dammaer/cam_manager'''
        )
    parser.add_argument('-v', '--version',
                        action='version',
                        help = 'Вывести номер версии',
                        version=VERSION)
    parser.add_argument('-u', '--updates_server',
                        help='Указать url сервера обновлений. '
                             'Пример: http://server:8080/cm/cam-manager',
                        metavar='URL')
    return parser


if __name__ == '__main__':
    pass