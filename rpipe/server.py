#!/usr/bin/env python2.7

import os.path
import logging
import traceback

import gevent
import gevent.server
import gevent.ssl

import rpipe.config.server
import rpipe.exceptions
import rpipe.utility
import rpipe.protocol
import rpipe.message_catalog

_logger = logging.getLogger(__name__)


class ConnectionHandlerBaseClass(object):
    def handle(socket, address):
        raise NotImplementedError()


class DefaultConnectionHandler(ConnectionHandlerBaseClass):
    def __init__(self):
        mc = rpipe.message_catalog.get_catalog()

        mc.register_type_handler(
            rpipe.protocols.MT_HEARTBEAT, 
            self.handle_heartbeat)

        mc.register_type_handler(
            rpipe.protocols.MT_EVENT, 
            self.handle_event)

        self.__mc = mc

        if rpipe.config.server.EVENT_HANDLER_FQ_CLASS is not None:
            event_handler_cls = rpipe.utility.load_cls_from_string(
                                    rpipe.config.server.\
                                        EVENT_HANDLER_FQ_CLASS)
        
            self.__event_handler = event_handler_cls()
        else:
            self.__event_handler = None

    def new_connection(self, socket, address):
        """We've received a new connection."""

        self.__ws = rpipe.protocol.SocketWrapper(socket.makefile())
        self.__address = address

        self.handle()

    def handle(self):
        while 1:
            _logger.debug("Waiting for message from client.")
            
            try:
                message = rpipe.protocol.read_message_from_file_object(self.__ws)
            except EOFError:
                _logger.info("Connection from [%s] closed.", self.__address)
                return

            (message_info, message_obj) = message

            message_type = rpipe.protocol.get_message_type_from_info(message_info)
            message_id = rpipe.protocol.get_message_id_from_info(message_info)

            self.__mc.hit(message_type, message_id, message_obj)

    def send_message(self, message_obj, **kwargs):
        rpipe.protocol.send_message_obj(
            self.__ws,
            message_obj, 
            **kwargs)

    def handle_heartbeat(self, message_meta, message_obj):
        _logger.debug("Responding to heartbeat: %s", self.__address)

        (message_type, message_id) = message_meta

        reply_message_obj = rpipe.protocol.get_obj_from_type(
                                rpipe.protocols.MT_HEARTBEAT_R)

        reply_message_obj.version = 1

        self.send_message(
            reply_message_obj, 
            message_id=message_id, 
            is_response=True)

    def handle_event(self, message_meta, message_obj):
        _logger.debug("Responding to event: %s", self.__address)

        (message_type, message_id) = message_meta

        _logger.info("Received event [%s] [%s].", 
                     message_obj.verb, message_obj.noun)

        gevent.spawn(self.process_event,
                     message_id,
                     message_obj.verb,
                     message_obj.noun,
                     message_obj.data)

    def process_event(self, message_id, verb, noun, data):
        """Processes event in a new gthread."""

        if self.__event_handler is not None:
            _logger.debug("Forwarding event to event-handler.")

            try:
                result_data = self.__event_handler(verb, noun, data)
            except rpipe.exceptions.RpHandleException as e:
                result_data = traceback.format_exc()
                code = e.code
            else:
                code = 0
        else:
            _logger.warn("No event-handler available. Responding as dumb "
                         "success.")

            result = ''
            code = 0

        reply_message_obj = rpipe.protocol.get_obj_from_type(
                                rpipe.protocols.MT_EVENT_R)

        reply_message_obj.version = 1
        reply_message_obj.code = code
        reply_message_obj.data = result

        self.send_message(
            reply_message_obj, 
            message_id=message_id, 
            is_response=True)

    @property
    def socket(self):
        return self.__ws

    @property
    def address(self):
        return self.__address


class Server(object):
    def __init__(self):
        fq_cls_name = rpipe.config.server.CONNECTION_HANDLER_FQ_CLASS

        self.__connection_handler_cls = rpipe.utility.load_cls_from_string(
                                            fq_cls_name)

    def run(self):
        binding = (rpipe.config.server.BIND_HOSTNAME, 
                   rpipe.config.server.BIND_PORT)

        _logger.info("Running server: %s", binding)

        handler = self.__connection_handler_cls()

        server = gevent.server.StreamServer(
                    binding, 
                    handler.new_connection, 
                    cert_reqs=gevent.ssl.CERT_REQUIRED,
                    keyfile=rpipe.config.server.KEY_FILEPATH,
                    certfile=rpipe.config.server.CRT_FILEPATH,
                    ca_certs=rpipe.config.server.CA_CRT_FILEPATH)

        server.serve_forever()
