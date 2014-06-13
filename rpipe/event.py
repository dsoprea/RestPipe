import logging

import rpipe.protocols
import rpipe.protocol
import rpipe.connection

_logger = logging.getLogger(__name__)

def emit(c, verb, noun, data, mimetype=None):
    assert issubclass(c.__class__, rpipe.connection.Connection)

    if mimetype is None:
        mimetype = ''

    mimetype = mimetype.split(';')[0]

    _logger.info("Emitting [%s] [%s]: (%d) bytes", verb, noun, len(data))

    message_obj = rpipe.protocol.get_obj_from_type(rpipe.protocols.MT_EVENT)
    message_obj.version = 1
    message_obj.verb = verb
    message_obj.noun = noun
    message_obj.mimetype = mimetype
    message_obj.data = data

    r = c.initiate_message(message_obj)

    return (r.code, r.mimetype, r.data)
