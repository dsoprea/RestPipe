import logging
import collections
import traceback
import json
import types

import gevent

import rpipe.config.protocol
import rpipe.protocol
import rpipe.protocols
import rpipe.exceptions
import rpipe.message_exchange

_logger = logging.getLogger(__name__)


CONNECTION_CONTEXT_T = collections.namedtuple(
                        'ConnectionContext', 
                        ['participant_address'])

_CT_JSON = 'application/json'


class CommonMessageLoop(object):
    def __init__(self, wrapped_socket, event_handler, connection_context):
        assert wrapped_socket is not None

        self.__ws = wrapped_socket
        self.__eh = event_handler
        self.__ctx = connection_context
        
        heartbeat_reply_message_obj = \
            rpipe.protocol.get_obj_from_type(
                rpipe.protocols.MT_HEARTBEAT_R)#

        heartbeat_reply_message_obj.version = 1

        self.__heartbeat_reply_message_obj = heartbeat_reply_message_obj

    def handle(self, exit_on_unknown=False):
        rpipe.message_exchange.start_exchange(
            self.__ws, 
            self.__ctx.participant_address)

        _logger.debug("Starting loop for messages from participant: %s", 
                      self.__ctx.participant_address)
            
        while 1:
            if rpipe.message_exchange.is_alive(self.__ctx.participant_address) is False:
                _logger.warning("Message exchange has ended. Terminating "
                                "message-loop.")
                break

            try:
                message = rpipe.message_exchange.read(
                            self.__ctx.participant_address, 
                            timeout=rpipe.config.protocol.\
                                        MESSAGE_LOOP_READ_TIMEOUT_S)
            except gevent.queue.Empty:
                continue
            except rpipe.exceptions.RpConnectionClosed:
                break

            (message_info, message_obj) = message

            message_type = rpipe.protocol.get_message_type_from_info(
                            message_info)
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
                    # block for a response. So, it's better to just close and 
                    # get the client to reestablish the connection.

                    _logger.warning("Leaving message-loop. If this is a "
                                    "server, the connection will "
                                    "automatically be reestablished by the "
                                    "client.")
                    return
                else:
                    continue

            gevent.spawn(handler, message_id, message_obj)

        rpipe.message_exchange.stop_exchange(self.__ctx.participant_address)

    def __handle_heartbeat(self, message_id, message_obj):
        _logger.debug("Responding to heartbeat: %s", 
                      self.__ctx.participant_address)

        rpipe.message_exchange.send(
            self.__ctx.participant_address, 
            self.__heartbeat_reply_message_obj,
            reply_to_message_id=message_id,
            expect_response=False)

    def __handle_event(self, message_id, message_obj):
        _logger.info("Received event from [%s]: [%s] [%s]", 
                     self.__ctx.participant_address, message_obj.verb, 
                     message_obj.noun)

        event_handler_name = message_obj.noun.replace('/', '_')

        try:
            handler = getattr(self.__eh, 'handle_' + event_handler_name)
        except AttributeError:
            _logger.warning("Event is not handled: [%s]", event_handler_name)

            self.__send_event_response(
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

    def __process_event(self, handler, message_id, verb, noun, data):
        """Processes event in a new gthread."""

        _logger.debug("Forwarding event to event-handler.")

        try:
            result = handler(self.__ctx, verb, noun, data)
        except rpipe.exceptions.RpHandleException as e:
            result = traceback.format_exc()
            code = e.code
        else:
            code = 0

        if issubclass(result.__class__, tuple) is True:
            (mimetype, code, result_data) = result
        else:
            mimetype = None
            result_data = result

        if mimetype is None:
            mimetype = _CT_JSON

        _logger.debug("Event result for verb [%s] and noun [%s]: [%s] [%s] "
                      "(%s)", verb, noun, mimetype, 
                      result_data.__class__.__name__, code)

        if result_data is None:
            _logger.debug("Result data was None. Coalescing to empty.")
            result_data = ''

        if issubclass(result_data.__class__, 
                      (basestring, types.GeneratorType)) is False:
            if mimetype == _CT_JSON:
                result_data = json.dumps(result_data)
            else:
                raise ValueError("Response to noun [%s] was invalid type and "
                                 "we're not allowed to encode it to JSON: "
                                 "[%s]" %
                                 (noun, result_data.__class__.__name__))

        self.__send_event_response(message_id, code, mimetype, result_data)

    def __send_event_response(self, reply_to_message_id, code, mimetype, data):
        reply_to_message_id_str = rpipe.protocol.get_string_from_message_id(
                                    reply_to_message_id)

        _logger.debug("Responding to message [%s] with code [%s] (with data? "
                      "[%s])", 
                      reply_to_message_id_str, code, bool(data))

        reply_message_obj = rpipe.protocol.get_obj_from_type(
                                rpipe.protocols.MT_EVENT_R)

        reply_message_obj.version = 1
        reply_message_obj.mimetype = mimetype
        reply_message_obj.code = code
        reply_message_obj.data = data

        rpipe.message_exchange.send(
            self.__ctx.participant_address, 
            reply_message_obj,
            reply_to_message_id=reply_to_message_id,
            expect_response=False)
