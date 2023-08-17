from argparse import ArgumentParser

VERSION = '1.6.1'


def Parser():
    parser = ArgumentParser(
        prog='cam-manager',
        description='''Утилита для настройки IP-камер.''',
        epilog='''\033[36m(ノ ˘_˘)ノ\033[0m
                  https://github.com/dammaer/cam_manager'''
        )
    parser.add_argument('-v', '--version',
                        action='version',
                        help='Вывести номер версии',
                        version=VERSION)
    parser.add_argument('-u', '--updates_server',
                        help='Указать url сервера обновлений. '
                             'Пример: http://server:8080/cm/cam-manager',
                        metavar='URL')
    parser.add_argument('-d', '--disable_updates',
                        action='store_true',
                        help='Отключить обновления')
    return parser


if __name__ == '__main__':
    pass
