

import client
import protocol
import socket
import sys
import os
import select
import logging
from datetime import datetime


log_filename = f"transfer_{datetime.now().strftime('%Y%m%d_%H%M')}.log"
logging.basicConfig(
    filename=log_filename,
    filemode='w',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)



def write_msg(server_socket, fragment_size, fragment_no):
    """ Выводит полученное текстовое сообщение в консоль.

    server_socket: Серверный сокет содержит адрес источника и метод sendto.
    fragment_size: Максимальный размер полученного фрагмента данных. Вводится пользователем.
    fragment_no: Общее количество фрагментов. """

    fragment_count = 0
    while True:
        ready = select.select([server_socket], [], [], 3)
        if ready[0]:
            message, client_address = server_socket.recvfrom(protocol.DEFAULT_BUFF)
            reply_crc = protocol.check_crc(message)
            reply = protocol.add_header(reply_crc, fragment_size, b'')
            server_socket.sendto(reply, client_address)
            if reply_crc.value != protocol.MsgType.ACK.value:                       # ARQ Stop & Wait
                continue
            message = protocol.get_data(message)
            print(message.decode('utf-8'), end='')
            fragment_count += 1
        else:
            break
    print('\nПолученные фрагменты:', fragment_count, ' учтенные фрагменты:', fragment_no, '\n')

def resolve_filename_collision(path):
    """Автоматически добавляет (1), (2), ... если файл с таким именем уже существует."""
    if not os.path.exists(path):
        return path

    base, ext = os.path.splitext(path)
    counter = 1
    new_path = f"{base}({counter}){ext}"
    while os.path.exists(new_path):
        counter += 1
        new_path = f"{base}({counter}){ext}"
    return new_path


def write_file(path, server_socket, fragment_size, fragment_no):
    """ Запись полученного файла в указанную директорию.
    Возвращает количество полученных фрагментов и общее количество фрагментов.

    server_socket: Сокет сервера содержит адрес источника и sendto метод.
    path: Информация, где хранить полученный файл.
    fragment_size: Максимальный размер полученного фрагмента данных. Вводится пользователем.
    fragment_no: Общее количество фрагментов. """

    fragment_count = 0
    with open(path, 'wb+') as file:
        while True:
            ready = select.select([server_socket], [], [], 3)
            if ready[0]:
                data, client_address = server_socket.recvfrom(fragment_size)
                reply_crc = protocol.check_crc(data)
                reply = protocol.add_header(reply_crc, fragment_size, b'')
                server_socket.sendto(reply, client_address)

                if reply_crc.value != protocol.MsgType.ACK.value:
                    continue
                data = protocol.get_data(data)
                fragment_count += 1
                file.write(data)
                logging.info(f"Получен фрагмент {fragment_count}/{fragment_no}")
            else:
                break

    print('\nПолученные фрагменты:', fragment_count, ' учтенные фрагменты:', fragment_no, '\n')


def initialization(server_socket):
    """ Получение инициализационного сообщения. Возвращает полученные данные, адрес клиента, размер фрагмента,
    количество фрагментов и имя файла для приёма передаваемых данных.

    server_socket: Серверный сокет, содержащий адрес источника и метод sendto. """

    while True:
        ready = select.select([server_socket], [], [], 20)
        if ready[0]:
            data, client_address = server_socket.recvfrom(protocol.DEFAULT_BUFF)
        else:
            return None
        reply_crc = protocol.check_crc(data)
        reply = protocol.add_header(reply_crc, 0, b'')
        server_socket.sendto(reply, client_address)
        if reply_crc.value == protocol.MsgType.ACK.value:
            fragment_size = protocol.get_fragment_size(data) + len(data)

            if data.decode('utf-8')[:1] == protocol.MsgType.SET_MSG.value:
                fragment_count = protocol.get_fragment_count(data, protocol.MsgType.SET_MSG.value)
            else:
                fragment_count = protocol.get_fragment_count(data)

            file_name = protocol.get_file_name(data, fragment_count)
            break
    return data, client_address, fragment_size, fragment_count, file_name


def receive(server_socket, dir_path):
    """ Получает данные от клиента и решает, основываясь на заголовке протокола,
      является ли это передача текстовых данных или файловых """

    print('Сервер ожидает!')
    try:
        data, client_address, fragment_size, fragment_count, file_name = initialization(server_socket)
    except TypeError:
        print('Timeout')
        return

    if protocol.get_msg_type(data).decode('utf-8') == protocol.MsgType.SET.value:
        save_path = resolve_filename_collision(dir_path + file_name)
        write_file(save_path, server_socket, fragment_size, fragment_count)
        server_socket.sendto(bytes(protocol.MsgType.ACK.value, 'utf-8'), client_address)
        print('Передача прошла успешно, файл находится', os.path.abspath(save_path), '\n')
        logging.info(f"Файл сохранен как: {os.path.abspath(save_path)}")
        logging.info(f"Получен файл: {file_name}")
        logging.info(f"Сохранено в: {os.path.abspath(dir_path + file_name)}")
        logging.info(f"Ожидаемые фрагменты: {fragment_count}")

    else:
        write_msg(server_socket, fragment_size, fragment_count)


def set_server():
    """ Начальные настройки сервера. Возвращает порт сервера и путь к директории для сохранения полученных файлов.
        И порт сервера, и путь к директории вводятся пользователем. """


    server_port = 0
    dir_path = ''
    while server_port == 0 or dir_path == '':
        try:
            if server_port == 0:
                server_port = int(input('Введите порт сервера для прослушивания: '))

            if server_port < 1024 or server_port > 65535:                   # провека порта сервера
                print('Этот порт зарезервирован. Введите другой.')
                server_port = 0
                continue

            dir_path = input('Введите путь к директории, в которую нужно сохранить файл: ')
            if not os.path.isdir(dir_path):                                 # проверка пути
                print('ERROR 01: Путь', dir_path, 'не существует!')
                dir_path = ''
                continue
            if dir_path[:-1] != '/':                                        # проверка, заканчивается ли имя директории на /
                dir_path += '/'

        except ValueError:                                                  # неверный введенный тип данных
            print('Неверный порт сервера!')
            server_port = 0
            continue

    return server_port, dir_path


def user_interface():
    """ Интерфейс пользователя сервера. """

    print('\n{:^50}'.format('server'))
    server_port, dir_path = set_server()
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind(('', server_port))

    while True:
        print('0 - выход\n'
              '1 - получение\n'
              '9 - переключиться на клиентский интерфейс\n')
        user_input = input('Введите, что вы хотите сделать: ')
        if user_input == '0':
            print('Завершение работы')
            server_socket.close()
            sys.exit(0)
        elif user_input == '1':
            receive(server_socket, dir_path)
        elif user_input == '9':
            client.user_interface()
        else:
            print('\n{:^30}'.format('Некорректный ввод! Введите еще раз.\n'))

            # /home/user/projects/file_transfer/image.jpg
            # /home/user/projects