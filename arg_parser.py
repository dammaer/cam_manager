import argparse


def Parser():
    parser = argparse.ArgumentParser(
        prog='cam-manager',
        description='''Утилита для настройки IP-камер.''',
        epilog='''(ノ ˘_˘)ノ
                  https://github.com/dammaer/cam_manager'''
        )
    parser.add_argument('-u', '--updates_server',
                        help='Указать url сервера обновлений. '
                             'Пример: http://server:8080/cm/cam-manager',
                        metavar='URL')
    return parser


if __name__ == '__main__':
    pass
