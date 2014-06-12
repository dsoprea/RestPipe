import logging
import collections
import traceback
import json

import gevent

import rpipe.config.protocol
import rpipe.protocol
import rpipe.protocols
import rpipe.exceptions
import rpipe.message_exchange

_logger = logging.getLogger(__name__)


CONNECTION_CONTEXT_T = collections.namedtuple(
                        'ConnectionContext', 
                        ['client_address'])


class CommonMessageLoop(object):
    def __init__(self, wrapped_socket, event_handler, connection_context):
        self.__ws = wrapped_socket
        self.__eh = event_handler
        self.__ctx = connection_context

    def handle(self, exit_on_unknown=False):
        rpipe.message_exchange.start_exchange(
            self.__ws, 
            self.__ctx.client_address)

        if self.__ctx.client_address is None:
            _logger.debug("Starting loop for messages from server.")
        else:
            _logger.debug("Starting loop for messages from client: %s", 
                          self.__ctx.client_address)
            
        while 1:
            if rpipe.message_exchange.is_alive(self.__ctx.client_address) is False:
                _logger.warning("Message exchange has ended. Terminating "
                                "message-loop.")
                break

            try:
                message = rpipe.message_exchange.read(
                            self.__ctx.client_address, 
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

        rpipe.message_exchange.stop_exchange(self.__ctx.client_address)

# TODO(dustin): We might isolate the send/receive methods into another class 
#               that can be reused by the CML and the client-only logic (like
#               sending heartbeats).
    def send_response_message(self, message_obj, reply_to_message_id, **kwargs):
        rpipe.message_exchange.send(
            self.__ctx.client_address, 
            message_obj,
            reply_to_message_id=reply_to_message_id,
            expect_response=False)

    def initiate_message(self, message_obj, **kwargs):
        message_id = rpipe.message_exchange.send(
                        self.__ctx.client_address, 
                        message_obj)

        return rpipe.message_exchange.wait_on_reply(
                    self.__ctx.client_address, 
                    message_id)

#    def __handle_heartbeat(self, message_id, message_obj):
#        _logger.debug("Responding to heartbeat: %s", self.__ctx.client_address)
#
#        reply_message_obj = rpipe.protocol.get_obj_from_type(
#                                rpipe.protocols.MT_HEARTBEAT_R)#
#
#        reply_message_obj.version = 1
#
#        self.send_response_message(
#            reply_message_obj, 
#            message_id=message_id, 
#            is_response=True)

    def __handle_event(self, message_id, message_obj):
        _logger.info("Received event from [%s]: [%s] [%s]", 
                     self.__ctx.client_address, message_obj.verb, 
                     message_obj.noun)

        event_handler_name = message_obj.noun.replace('/', '_')

        try:
            handler = getattr(self.__eh, 'handle_' + event_handler_name)
        except AttributeError:
            _logger.warning("Event is not handled: [%s]", event_handler_name)

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

    def __send_response(self, reply_to_message_id, code, 
                        mimetype='application/json', data={}):
        reply_message_obj = rpipe.protocol.get_obj_from_type(
                                rpipe.protocols.MT_EVENT_R)

        reply_message_obj.version = 1
        reply_message_obj.mimetype = mimetype
        reply_message_obj.code = code

        if mimetype == 'application/json':
            reply_message_obj.data = json.dumps(data)
        else:
            reply_message_obj.data = data

        self.send_response_message(
            reply_message_obj, 
            reply_to_message_id=reply_to_message_id)

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
