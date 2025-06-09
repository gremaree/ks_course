

import server
import protocol
import select
import socket
import sys
import os
import ntpath
import math
import time
import logging
from datetime import datetime
import matplotlib.pyplot as plt


# Настройка логгирования 
log_filename = f"transfer_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    filename=log_filename,
    filemode='w',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger()

def get_file_name(file_path):
    """ Получает имя файла из пути к файлу. Возвращает имя файла.

     file_path: Заданный пользователем путь к передаваемому файлу. """
    return ntpath.split(file_path.decode('utf-8'))[1]


def initialization(client_socket, server_ip, server_port, fragment_size, data):
    """ Инициализация передачи текста или файла.

        client_socket: Клиентский сокет содержит адрес источника и метод sendto.
        server_ip: Одна часть целевого адреса в сокете
        server_port: Вторая часть целевого адреса в сокете
        fragment_size: Максимальный размер одного фрагмента, заданный пользователем
        data: данные для передачи текста содержат один байт, указывающий протоколу
              на добавление типа msg в качестве текстовой передачи.
              Данные для передачи файла содержат имя файла, который будет создан на сервере.
              Остальное - количество фрагментов как для передачи текста, так и для передачи файла.  """
    try:
        while True:
            client_socket.sendto(  # инициализация передачи данных
                protocol.msg_initialization(fragment_size, data),  # инициализационный msg
                (server_ip, server_port))  # адрес сервера
            ready = select.select([client_socket], [], [], 5)
            if ready[0]:
                new_data, server_address = client_socket.recvfrom(fragment_size)
            else:
                print('Соединение не установлено')
                return 0

            if new_data[:1].decode('utf-8') == protocol.MsgType.ACK.value:
                break
        print(protocol.MsgReply.SET.value)

    except ConnectionResetError:
        print('Соединение потеряно. Включите сервер.')
    return 1


def send_file(server_ip, client_socket, server_port, fragment_size, file_path):
    """ Передача файла с логированием. """
    # используем глобальную переменную, которую задаёт GUI
    user_input_mistake = globals().get("user_input_mistake", "n")
    # user_input_mistake = input('Добавить ошибку в передачу данных? д/н ')

    if user_input_mistake.lower() not in ['д', 'н']:
        print('Неверный ввод!')
        return

    file_name = bytes(get_file_name(file_path), 'utf-8')
    file_size = os.path.getsize(file_path)
    num_of_fragment = math.ceil(file_size / (fragment_size - protocol.HEADER_SIZE))

    nack_fragment, all_fragment = 0, 0
    status_log = []

    try:
        if initialization(client_socket, server_ip, server_port, fragment_size,
                          file_name + bytes(str(num_of_fragment), 'utf-8')) == 0:
            return

        start_time = time.time()
        with open(file_path, 'rb') as file:
            data = file.read(fragment_size - protocol.HEADER_SIZE)
            fragment_count = 0

            while data:
                new_data = protocol.add_header(protocol.MsgType.PSH, fragment_size, data)
                if user_input_mistake == 'д':
                    header = new_data[:6]
                    new_data = header + new_data[20:]
                    user_input_mistake = 'н'

                if client_socket.sendto(new_data, (server_ip, server_port)):
                    reply, _ = client_socket.recvfrom(fragment_size)

                    if reply[:1].decode('utf-8') != protocol.MsgType.ACK.value:
                        print('negative acknowledgment msg. Ошибка обработки сообщения')
                        nack_fragment += 1
                        all_fragment += 1
                        status_log.append(0)  # Повторная передача
                    else:
                        data = file.read(fragment_size - protocol.HEADER_SIZE)
                        fragment_count += 1
                        all_fragment += 1
                        status_log.append(1)  # Успешная передача

        ready = select.select([client_socket], [], [], 5)
        if ready[0]:
            _ = client_socket.recvfrom(fragment_size)
            end_time = time.time()
            print(protocol.MsgReply.ACK.value)
            print('Время:', end_time - start_time)
            print('Сохранено в', os.path.abspath(file_path.decode('utf-8')))
            print('Отправлено фрагментов:', fragment_count, ' всего фрагментов:', num_of_fragment)
            print('Отправлено фрагментов:', all_fragment, ' NACK фрагментов:', nack_fragment)

            # Логгирование
            logger.info(f"Отправленный файл: {file_path.decode('utf-8')}")
            logger.info(f"Всего фрагментов: {all_fragment}, Повторные передачи (NACK): {nack_fragment}")
            logger.info(f"Время передачи: {end_time - start_time:.2f} секунд")
            logger.info(f"Сохранено как: {os.path.abspath(file_path.decode('utf-8'))}")

        else:
            print('Соединение не установлено')

    except ConnectionResetError:
        print('Соединение потеряно. Включите сервер.')


def send_message(server_ip, client_socket, server_port, fragment_size, message):
    """ Передача текстовых сообщений.

     client_socket: Клиентский сокет содержит адрес источника и метод sendto.
     server_ip: Одна часть целевого адреса в сокете
     server_port: Вторая часть целевого адреса в сокете
     fragment_size: Максимальный размер одного фрагмента, заданный пользователем
     Message: Данные, которые необходимо передать. """

    fragment_count = 0
    num_of_fragment = math.ceil(len(message.decode('utf-8')) / fragment_size)

    nack_fragment, all_fragment = 0, 0
    try:
        if initialization(client_socket, server_ip, server_port, fragment_size + protocol.HEADER_SIZE,
                          bytes(protocol.MsgType.SET_MSG.value, 'utf-8') + bytes(str(num_of_fragment), 'utf-8')) == 0:
            return
        lenght = math.ceil(len(message) / fragment_size)
        index1, index2 = 0, fragment_size

        while lenght > 0:
            data = protocol.add_header(protocol.MsgType.PSH, fragment_size, message[index1:index2])
            client_socket.sendto(data, (server_ip, server_port))
            ready = select.select([client_socket], [], [], 5)
            if ready[0]:
                reply, server_address = client_socket.recvfrom(fragment_size + protocol.HEADER_SIZE)
                if reply[:1].decode('utf-8') != protocol.MsgType.ACK.value: # проверка на ACK
                    print('negative acknowledgment msg. Ошибка обработки сообщения')
                    nack_fragment += 1
                    all_fragment += 1
                else:
                    index1 += fragment_size
                    index2 += fragment_size
                    lenght -= 1
                    fragment_count += 1
                    all_fragment += 1
            else:
                print('Соединение не установлено')
                return
        logger.info(f"Отправлено текстовое сообщение: {message.decode('utf-8')}")
        logger.info(f"Всего фрагментов: {all_fragment}, Повторные передачи (NACK): {nack_fragment}")

    except ConnectionResetError:
        print('Соединение потеряно. Включите сервер.')
    print('Отправлено фрагментов:', fragment_count, ' всего фрагментов:', num_of_fragment, '\n')


def set_client():
    """ Инициализация настроек клиента. Возвращает server_ip,
      client_port, server_port, fragmentation, введенные пользователем. """

    server_ip, client_port, server_port, fragmentation = '', '', '', ''
    while server_ip == '' or server_port == '' or fragmentation == '':  # считывание значений для установки клиентом
        try:
            if server_ip == '':
                server_ip = input('Введите IP-адрес сервера: ')
                socket.inet_aton(server_ip)  

            if client_port == '':
                client_port = int(input('Введите порт клиента/источника: '))

            if client_port < 1024 or client_port > 65535:  #
                print('Этот порт зарезервирован. Введите другой.')
                client_port = ''
                continue

            if server_port == '':
                server_port = int(input('Введите порт сервера: '))

            if server_port < 1024 or server_port > 65535:  #
                print('Этот порт зарезервирован. Введите другой.')
                server_port = ''
                continue

            fragmentation = int(input('Введите максимальный размер фрагмента: '))

            if fragmentation < protocol.FRAGMENT_MIN:  # проверка заданного значения фрагмента
                fragmentation = protocol.FRAGMENT_MIN

            if fragmentation > protocol.FRAGMENT_MAX:  # проверка максимального значения фрагмента
                fragmentation = protocol.FRAGMENT_MAX

        except ValueError:  # введен неправильный тип данных
            print('Неверный ввод! Попробуйте снова')
            server_ip, server_port, fragmentation = '', '', ''
            continue

        except OSError:  # введен неправильный IP-адрес
            print('Неверный IP-адрес! Попробуйте снова')
            server_ip = ''
            continue

    return server_ip, client_port, server_port, fragmentation


def user_interface():
    """ Интерфейс пользователя клиента. """

    print('\n{:^50}'.format('client'))
    server_ip, client_port, server_port, fragmentation = set_client()
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # установить сокет с IPv4 и UDP
    client_socket.bind(('', client_port))  # установить порт источника

    while True:
        print('0 - выход\n'
              '1 - отправить текстовое сообщение\n'
              '2 - отправить файл\n'
              '9 - переключиться на сервер')
        user_input = input('Введите, что вы хотите сделать: ')

        if user_input == '0':
            print('Выход')
            client_socket.close()
            sys.exit(0)

        if user_input == '1':
            message = bytes(input('Введите сообщение: '), 'utf-8')
            send_message(server_ip, client_socket, server_port, fragmentation, message)

        elif user_input == '2':
            file = bytes(input('Введите путь к файлу: '), 'utf-8')
            if not os.path.isfile(file):  # check if given path is valid
                print('ERROR 01: Путь', file.decode('utf-8'), 'не существует!')
                continue
            send_file(server_ip, client_socket, server_port, fragmentation + protocol.HEADER_SIZE, file)

        elif user_input == '9':
            client_socket.close()
            server.user_interface()

        else:
            print('\n{:^30}'.format('Неверный ввод! Попробуйте снова.\n'))
