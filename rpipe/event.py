import logging

import rpipe.client
import rpipe.protocols
import rpipe.protocol

_logger = logging.getLogger(__name__)

def emit(verb, noun, data):
    _logger.info("Emitting [%s] [%s]: (%d) bytes", verb, noun, len(data))
    print("Emitting [%s] [%s]: (%d) bytes" % (verb, noun, len(data)))

    message_obj = rpipe.protocol.get_obj_from_type(rpipe.protocols.MT_EVENT)
    message_obj.version = 1
    message_obj.verb = verb
    message_obj.noun = noun
    message_obj.data = data

    c = rpipe.client.get_connection()
    r = c.send_message(message_obj)

    return ''
