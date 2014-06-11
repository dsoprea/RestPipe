import struct
import random
import time
import hashlib
import logging
import base64
import ssl
import socket

import rpipe.protocols
import rpipe.utility

# Message flags.
MF_IS_REPLY = 0x01

_logger = logging.getLogger(__name__)


class SocketWrapper(object):
    """A thin wrapper that throws the right exceptions when the pipe is broken.
    """

    def __init__(self, s):
        self.__s = s

    def __getattr__(self, name):
        return getattr(self.__s, name)

# TODO(dustin): We need read/write callers to catch EOFError.

    def read(self, *args, **kwargs):
        try:
            data = self.__s.read(*args, **kwargs)
        except socket.error as e:
            message = ("There was a socket error (read). Closing stream: %s" % (str(e)))
            _logger.exception(message)
            raise EOFError(message)

        if data == '':
            raise EOFError()

        return data

    def write(self, *args, **kwargs):
        try:
            self.__s.write(*args, **kwargs)
            self.__s.flush()
        except ssl.SSLError as e:
            message = ("There was an SSL error (read). Closing stream: %s" % (str(e)))
            _logger.exception(message)
            raise EOFError(message)
        except socket.error as e:
            message = ("There was a socket error (write). Closing stream: %s" % (str(e)))
            _logger.exception(message)
            raise EOFError(message)

def id_generator():
    """Generate IDs for composed messages."""

    return random.randrange(1, 2**32)

def get_obj_from_type(message_type):
    fq_module_name = rpipe.protocols.get_fq_module_name_for_type(message_type)
    message_cls = rpipe.utility.load_cls_from_string(fq_module_name)

    return message_cls()

def serialize(message_obj, message_id=None, is_response=False, flags=0):
    if message_id is None:
        message_id = id_generator()

    if is_response is True:
        flags |= MF_IS_REPLY

    message_type = rpipe.protocols.get_type_from_obj(message_obj)
    serialized = message_obj.SerializeToString()

    header = struct.pack('!BBII', message_type, flags, len(serialized), message_id)

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

def unserialize(message_info, data):
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

    message_obj = unserialize(message_info, serialized)

    return (message_info, message_obj)

def send_message_obj(ws, message_obj, **kwargs):
    (data, message_id) = serialize(message_obj, **kwargs)
    _logger.debug("Sending [%s].", get_string_from_message_id(message_id))

    ws.write(data)

    _logger.debug("Message sent.")

    return message_id
