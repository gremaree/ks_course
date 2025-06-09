
import enum
import re

HEADER_SIZE = 6
DEFAULT_BUFF = 4096
DEFAULT_FRAGMENT_LEN = 4
FRAGMENT_MAX = 1466         # max_fragment = данные(1500) - UDP заголовок(8) - IP заголовок(20) - новый заголовок(6) = 1466
FRAGMENT_MIN = 1            # min_fragment = данные(46) - UDP заголовок(8) - IP заголовок(20) - новый заголовок(6) = 12
CRC_KEY = '1001'            # x^3 + 1


class MsgType(enum.Enum):
    """ Enum with constant as signal msg in protocol. """

    SET = '0'       # константа для заголовка при инициализации передачи файла
    PSH = '1'       # константа для заголовка при отправке данных файла
    ACK = '2'       # константа для заголовка при положительном ответе
    RST = '3'       # константа для заголовка при отрицательном ответе

    SET_MSG = '8'   # константа для заголовка при инициализации передачи сообщения


class MsgReply(enum.Enum):
    """ Перечисление констант  для взаимодействия клиент-сервер """

    SET = 'Успешная инициализация передачи'  
    ACK = 'Сообщение получено!'       
    RST = 'Сообщение повреждено'           
    KAP = 'Подключено'                   


def zero_fill(data):
    """ Заполнение фрагмента нулями, если он меньше длины по умолчанию(4).

     data: Данные, которые нужно заполнить нулями. """

    if DEFAULT_FRAGMENT_LEN == len(data):
        return data
    count = DEFAULT_FRAGMENT_LEN - len(data) - 1
    new_data = b'0'
    while count > 0:
        new_data += b'0'
        count -= 1
    new_data += data
    return new_data


def xor(a, b):
    """ Логический метод XOR для CRC. Возвращает строку битов.
    a XOR b

    a: Номер бита для XOR.
    b: Номер бита для XOR. """

    result = []                                            # список результатов
    for i in range(1, len(b)):                             # проходим по всем битам
        if a[i] == b[i]:                                   # если одинаковые - XOR 0
            result.append('0')
            continue
        result.append('1')                                 # если разные - XOR 1
    return ''.join(result)


def sum_checksum(checksum):
    """ Подсчитывает биты заданной контрольной суммы. Возвращает строку.

    checksum: Вычисляется контрольная сумма для суммирования всех битов. """

    sum_digit = 0
    for char in checksum:
        if char.isdigit():
            sum_digit += int(char)
    return str(sum_digit)


def set_crc(data):
    """ Получает контрольную сумму на основе CRC. Возвращает сводку всех битов контрольной суммы в виде строки.

     data: Данные для CRC. """

    crc_key_len = len(CRC_KEY)
    bin_data = (''.join(format(ord(char), 'b') for char in str(data))) + ('0' * (crc_key_len - 1))
    checksum = bin_data[:crc_key_len]
    while crc_key_len < len(bin_data):
        if checksum[0] == '1':
            checksum = xor(CRC_KEY, checksum) + bin_data[crc_key_len]
        else:
            checksum = xor('0' * crc_key_len, checksum) + bin_data[crc_key_len]
        crc_key_len += 1
    if checksum[0] == '1':
        checksum = xor(CRC_KEY, checksum)
    else:
        checksum = xor('0' * crc_key_len, checksum)
    return sum_checksum(checksum)


def check_crc(data):
    """ Проверяет, была ли передана полученная информация корректно. Возвращает положительное подтверждение, если полученные данные
    корректны, в противном случае возвращает отрицательное подтверждение.

    data: Данные содержат заголовок протокола с информацией о первоначально вычисленной контрольной сумме. Вычисляется контрольная сумма для
    полученных данных и сравнивается с оригинальной контрольной суммой. """

    if data[5:6].decode('utf-8') != set_crc(data[6:]):
        return MsgType.RST
    return MsgType.ACK


def get_fragment_size(data):
    """ Получение размера фрагмента из заголовка протокола. Возвращает размер фрагмента в виде int.

    data: содержит заголовок протокола с информацией о размере фрагмента, введенном пользователем. """
    return int(data[1:5].decode('utf-8'))


def get_file_name(data, fragment_count):
    """ Получение имени файла из заголовка протокола. Возвращает имя файла в виде строки.

    data: содержит данные из инициализации передачи с информацией о имени файла, введенном пользователем. """
    return data[6:-len(fragment_count)].decode('utf-8')


def get_data(data):
    """ Получение данных без заголовка протокола. Возвращает полученные данные в виде байтов.
 """
    return data[6:]


def get_fragment_count(data, msg_type=None):
    """ Получение количества фрагментов из данных. Возвращает количество фрагментов в виде строки.
    Для текстовой передачи сообщения просто возвращает данные с индекса 7(6-битный заголовок + 1-битные данные).
    Для передачи файлов возвращает последнее число из данных, потому что данные также содержат имя файла, возможно, данные могут быть
    name1.pdf720, где последнее число 720 - это количество фрагментов.

    data:  полученные данные с заголовком протокола. """

    if msg_type == MsgType.SET_MSG.value:
        return data.decode('utf-8')[7:]
    return re.compile(r'\d+').findall(data.decode('utf-8'))[-1:][0]     # получение последнего числа из имени файла


def get_msg_type(data):
    """ Получение типа сигнального сообщения.

    data:  полученные данные с заголовком протокола. """
    return data[:1]


def add_header(msg_type, fragment_size, data):
    """ Добавление заголовка протокола к данным. Возвращает новые данные с заголовком протокола в виде байтов.

    msg_type: Тип сообщения в виде MsgType.
    fragment_size:  размер фрагмента данных. Введен пользователем.
    data:  полученные данные без заголовка протокола. """

    fragment_size_bytes = zero_fill(bytes(str(fragment_size), 'utf-8'))
    new_data = bytes(msg_type.value, 'utf-8') + fragment_size_bytes
    checksum = set_crc(data)
    new_data += bytes(checksum, 'utf-8') + data
    return new_data


def msg_initialization(fragment_size, data):
    """ Добавлеяет заголовок протокола к данным для инициализации.

    fragment_size: размер фрагмента данных. Введен пользователем.
    data: полученные данные без заголовка протокола. """

    new_data = bytes(MsgType.SET.value, 'utf-8') if data[:1] != bytes(MsgType.SET_MSG.value, 'utf-8') else \
        bytes(MsgType.SET_MSG.value, 'utf-8')                               # тип сообщения
    fragment_size_bytes = zero_fill(bytes(str(fragment_size), 'utf-8'))     # заполнение нулями до 4 байт
    checksum = set_crc(data)                                                # получение контрольной суммы
    new_data += fragment_size_bytes + bytes(checksum, 'utf-8')              # добавление размера фрагмента и контрольной суммы
    new_data += data                                                        # добавление данных
    return new_data                                                         # возвращение заголовка + данных как новых данных