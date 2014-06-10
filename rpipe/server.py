#!/usr/bin/env python2.7

import os.path
import logging

import gevent
import gevent.server
import gevent.ssl

import rpipe.config.server
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
            self.heartbeat)

        self.__mc = mc

    def new_connection(self, socket, address):
        """We've received a new connection."""

        self.__ws = rpipe.protocol.SocketWrapper(socket.makefile())
        self.__address = address

        self.handle()

    def handle(self):
        while 1:
            _logger.debug("Waiting for message from client.")
            message = rpipe.protocol.read_message_from_file_object(self.__ws)

            (message_info, message_obj) = message

            message_type = rpipe.protocol.get_message_type_from_info(message_info)
            message_id = rpipe.protocol.get_message_id_from_info(message_info)

            self.__mc.hit(message_type, message_id, message_obj)

    def send_message(self, message_obj, **kwargs):
        rpipe.protocol.send_message_obj(
            self.__ws,
            message_obj, 
            **kwargs)

    def heartbeat(self, message_meta, message_obj):
        _logger.debug("Responding to heartbeat: %s", self.__address)

        (message_type, message_id) = message_meta

        reply_message_obj = rpipe.protocol.get_obj_from_type(
                                rpipe.protocols.MT_HEARTBEAT_R)

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
        fq_cls_name = rpipe.config.server.CONNECTION_HANDLER_CLASS

        cls_connection_handler = rpipe.utility.load_cls_from_string(
                                    fq_cls_name)

        self.__handler = cls_connection_handler()

    def run(self):
        binding = (rpipe.config.server.BIND_HOSTNAME, 
                   rpipe.config.server.BIND_PORT)

        _logger.info("Running server: %s", binding)

        server = gevent.server.StreamServer(
                    binding, 
                    self.__handler.new_connection, 
                    cert_reqs=gevent.ssl.CERT_REQUIRED,
                    keyfile=rpipe.config.server.KEY_FILEPATH,
                    certfile=rpipe.config.server.CRT_FILEPATH,
                    ca_certs=rpipe.config.server.CA_CRT_FILEPATH)

        server.serve_forever()
