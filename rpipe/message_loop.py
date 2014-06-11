import logging
import collections
import traceback

import gevent

import rpipe.config.protocol
import rpipe.protocol
import rpipe.protocols
import rpipe.exceptions

_logger = logging.getLogger(__name__)


CONNECTION_CONTEXT_T = collections.namedtuple('ConnectionContext', ['address'])


class CommonMessageLoop(object):
    def __init__(self, wrapped_socket, event_handler, connection_context):
        self.__ws = wrapped_socket
        self.__eh = event_handler
        self.__ctx = connection_context

    def handle(self, exit_on_unknown=False):
        while 1:
            _logger.debug("Waiting for message.")
            
            try:
                message = rpipe.protocol.read_message_from_file_object(self.__ws)
            except EOFError:
                break

            (message_info, message_obj) = message

            message_type = rpipe.protocol.get_message_type_from_info(message_info)
            message_id = rpipe.protocol.get_message_id_from_info(message_info)

            if message_type == rpipe.protocols.MT_HEARTBEAT:
                handler = self.__handle_heartbeat
            elif message_type == rpipe.protocols.MT_EVENT:
                handler = self.__handle_event
            else:
                _logger.warning("Received unhandled message (%d) [%s].", 
                                message_type, message_obj.__class__.__name__)

                if exit_on_unknown is True:
                    # If we're running in a server, the client will probably 
                    # block on a response. So, it's better to just die.

                    _logger.warning("Leaving message-loop. If this is a "
                                    "server, the connection will "
                                    "automatically be reestablished by the "
                                    "client.")
                    return
                else:
                    continue

            gevent.spawn(handler, message_id, message_obj)

    def __send_message_primitive(self, message_obj, **kwargs):
        rpipe.protocol.send_message_obj(
            self.__ws,
            message_obj, 
            **kwargs)

# TODO(dustin): We might isolate the send/receive methods into another class 
#               that can be reused by the CML and the client-only logic (like
#               sending heartbeats).
    def send_response_message(self, message_obj, **kwargs):
        self.__send_message_primitive(message_obj, **kwargs)

    def initiate_message(self, message_obj, **kwargs):
        self.__send_message_primitive(message_obj, **kwargs)
        return self.__read_message()

    def __read_message(self, **kwargs):
# TODO(dustin): We're going to need to not interfere with replies in 
#               unfinished dialogs.
        rpipe.protocol.read_message_from_file_object(self.__ws, **kwargs)

    def __handle_heartbeat(self, message_id, message_obj):
        _logger.debug("Responding to heartbeat: %s", self.__ctx.address)

        reply_message_obj = rpipe.protocol.get_obj_from_type(
                                rpipe.protocols.MT_HEARTBEAT_R)

        reply_message_obj.version = 1

        self.send_response_message(
            reply_message_obj, 
            message_id=message_id, 
            is_response=True)

    def __handle_event(self, message_id, message_obj):
        _logger.info("Received event from [%s]: [%s] [%s]", 
                     self.__ctx.address, message_obj.verb, message_obj.noun)

        event_handler_name = message_obj.noun.replace('/', '_')

        try:
            handler = getattr(self.__eh, 'handle_' + event_handler_name)
        except AttributeError:
            self.__send_response(
                message_id, 
                rpipe.config.protocol.UNHANDLED_EVENT_DEFAULT_RESULT_CODE)
        else:
            gevent.spawn(
                self.__process_event,
                handler,
                message_id,
                message_obj.verb,
                message_obj.noun,
                message_obj.data)

    def __send_response(self, original_message_id, code, data=''):
        reply_message_obj = rpipe.protocol.get_obj_from_type(
                                rpipe.protocols.MT_EVENT_R)

        reply_message_obj.version = 1
        reply_message_obj.code = code
        reply_message_obj.data = data

        self.send_response_message(
            reply_message_obj, 
            message_id=original_message_id, 
            is_response=True)

    def __process_event(self, handler, message_id, verb, noun, data):
        """Processes event in a new gthread."""

        _logger.debug("Forwarding event to event-handler.")

        try:
            result_data = handler(self.__ctx, verb, noun, data)
        except rpipe.exceptions.RpHandleException as e:
            result_data = traceback.format_exc()
            code = e.code
        else:
            code = 0

        self.__send_response(message_id, code, result)
