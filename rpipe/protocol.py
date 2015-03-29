import struct
import random
import logging
import math

import gevent.ssl
import gevent.socket

import rpipe.exceptions
import rpipe.protocols
import rpipe.utility

# Message flags.
MF_IS_REPLY = 0x01

_MESSAGE_ID_MAXIMUM = 2**32
_MESSAGE_ID_MAX_ZEROES = int(math.ceil(math.log(_MESSAGE_ID_MAXIMUM, 10))) - 1
_MESSAGE_ID_MINIMUM = int('1' + '0' * _MESSAGE_ID_MAX_ZEROES)

_logger = logging.getLogger(__name__)


class SocketWrapper(object):
    """A thin wrapper that throws the right exceptions when the pipe is broken.
    """

    def __init__(self, socket, file_):
        assert socket is not None
        assert file_ is not None

        self.__socket = socket
        self.__file = file_

    def __getattr__(self, name):
        return getattr(self.__file, name)

    def read(self, *args, **kwargs):
        try:
            data = self.__file.read(*args, **kwargs)
        except gevent.socket.error as e:
            message = ("There was a socket error (read). Closing stream: %s" % (str(e)))
            _logger.exception(message)
            raise rpipe.exceptions.RpConnectionClosed(message)

        if data == '':
            raise rpipe.exceptions.RpConnectionClosed()

        return data

    def write(self, *args, **kwargs):
        try:
            self.__file.write(*args, **kwargs)
            self.__file.flush()
        except gevent.ssl.SSLError as e:
            message = ("There was an SSL error (read). Closing stream: %s" % (str(e)))
            _logger.exception(message)
            raise rpipe.exceptions.RpConnectionClosed(message)
        except gevent.socket.error as e:
            message = ("There was a socket error (write). Closing stream: %s" % (str(e)))
            _logger.exception(message)
            raise rpipe.exceptions.RpConnectionClosed(message)

    def __str__(self):
        return str(self.__socket.getpeername())

def id_generator():
    """Generate IDs for composed messages. They will all the the same length.
    """

    return random.randrange(_MESSAGE_ID_MINIMUM, _MESSAGE_ID_MAXIMUM)

def get_obj_from_type(message_type):
    fq_module_name = rpipe.protocols.get_fq_module_name_for_type(message_type)
    message_cls = rpipe.utility.load_cls_from_string(fq_module_name)

    return message_cls()

def _serialize(message_obj, message_id=None, is_response=False, flags=0):
    if message_id is None:
        message_id = id_generator()

    if is_response is True:
        flags |= MF_IS_REPLY

    message_type = rpipe.protocols.get_type_from_obj(message_obj)
    serialized = message_obj.SerializeToString()

    header = struct.pack(
                '!BBII', 
                message_type, 
                flags, 
                len(serialized), 
                message_id)

    whole_message = header + serialized
    _logger.debug("Serializing [%s]: (%d) + (%d)", 
                  get_string_from_message_id(message_id), len(header), 
                  len(serialized))

    return (whole_message, message_id)

def get_standard_header_length():
    # (Message_Type + Flags + Data_Length) + Message_ID
    return (1 + 1 + 4 + 4)

def get_message_info_from_header(header):
    parts = struct.unpack('!BBII', header)
    (message_type, flags, data_length, message_id) = parts

    return {
        'type': message_type,
        'length': data_length,
        'message_id': message_id,
        'is_response': bool(flags & MF_IS_REPLY),
    }

def get_message_length_from_info(message_info):
    return message_info['length']

def get_message_id_from_info(message_info):
    return message_info['message_id']

def get_message_type_from_info(message_info):
    return message_info['type']

def _unserialize(message_info, data):
    message_obj = get_obj_from_type(message_info['type'])
    message_obj.ParseFromString(data)

    return message_obj

def get_string_from_message_id(message_id):
    return ('%010d' % (message_id,))

def read_message_from_file_object(file_):
    header_length = get_standard_header_length()

    header = file_.read(header_length)
    _logger.debug("Received header (%d bytes).", header_length)

    message_info = get_message_info_from_header(header)
    _logger.debug("Message info: %s", message_info)

    message_length = get_message_length_from_info(message_info)

    message_type_name = rpipe.protocols.get_fq_cls_name_for_type(
                            message_info['type'])

    message_id_str = get_string_from_message_id(message_info['message_id'])

    _logger.debug("Waiting for (%d) bytes of data: TYPE=[%s] ID=[%s]", 
                  message_length, message_type_name, message_id_str)

    if message_length > 0:
        serialized = file_.read(message_length)
    else:
        serialized = ''

    _logger.debug("Received data.")

    message_obj = _unserialize(message_info, serialized)

    return (message_info, message_obj)

def send_message_obj(ws, message_obj, **kwargs):
    (data, message_id) = _serialize(message_obj, **kwargs)
    _logger.debug("Sending [%s].", get_string_from_message_id(message_id))

    ws.write(data)

    _logger.debug("Message sent.")

    return message_id
