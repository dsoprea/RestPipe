#!/usr/bin/env python2.7

import os.path
import logging
import traceback
import time
import socket
import functools

import gevent
import gevent.server
import gevent.ssl

import rpipe.config.server
import rpipe.exceptions
import rpipe.server.exceptions
import rpipe.utility
import rpipe.protocol
#import rpipe.message_catalog
import rpipe.connection

_logger = logging.getLogger(__name__)


class DefaultServerEventHandler(object):
    pass


class _ConnectionCatalog(object):
    """Keep track of connections and their IPs. This is the principle reason 
    that no two clients can connect from the same host.
    """

    def __init__(self):
        self.__connections = {}

    def register(self, c):
        if c in self.__connections:
            raise ValueError("Can not register already-registered connection. "
                             "A previous connection from this client might "
                             "not've been deregistered [properly]: %s" % 
                             (c.ip))

        _logger.debug("Registering client: [%s]", c.ip)

        # These are actually indexed by address (so we can find it either 
        # with a conneciton object -or- an address).
        self.__connections[c] = c

    def deregister(self, c):
        if c not in self.__connections:
            raise ValueError("Can not deregister unregistered connection: %s" %
                             (c.ip))

        _logger.debug("Deregistering client: [%s]", c.ip)
        del self.__connections[c]

    def get_connection_by_ip(self, ip):
        return self.__connections[ip]

    def wait_for_connection(
            self, 
            ip, 
            timeout_s=rpipe.config.server.DEFAULT_CONNECTION_WAIT_TIMEOUT_S):
        """A convenience function to wait for a client to connect (if not 
        immediately available). This is to be used when we might need to wait 
        for a client to reconnect in order to fulfill a request.
        """

        stop_at = time.time() + timeout_s
        while time.time() <= stop_at:
            try:
                return self.__connections[ip]
            except KeyError:
                pass

            gevent.sleep(1)

        raise rpipe.server.exceptions.RpNoConnectionException(ip)


class DefaultServerEventHandler(object):
    def __init__(self, server_connection_handler):
        self.__server_connection_handler = server_connection_handler

    @property
    def sch(self):
        return self.__server_connection_handler


class ServerConnectionHandler(rpipe.connection.Connection):
    def handle(socket, address):
        raise NotImplementedError()


class DefaultServerConnectionHandler(ServerConnectionHandler):
    def __init__(self):
#        mc = rpipe.message_catalog.get_catalog()
#
#        mc.register_type_handler(
#            rpipe.protocols.MT_HEARTBEAT, 
#            self.handle_heartbeat)
#
#        mc.register_type_handler(
#            rpipe.protocols.MT_EVENT, 
#            self.handle_event)
#
#        self.__mc = mc

        event_handler_cls = rpipe.utility.load_cls_from_string(
                                rpipe.config.server.EVENT_HANDLER_FQ_CLASS)

        self.__eh = event_handler_cls(self)

        self.__ws = None
        self.__address = None

    def __hash__(self):
        if self.ip is None:
            raise ValueError("Can not hash an unconnected connection object.")

        return hash(self.ip)

    def __eq__(self, o):
        if o is None:
            return False

        return hash(self) == hash(o)

    def handle_new_connection(self, socket, address):
        """We've received a new connection."""

        self.__ws = rpipe.protocol.SocketWrapper(socket.makefile())
        self.__address = address

        get_connection_catalog().register(self)

        self.handle()

    def handle_close(self):
        _logger.info("Connection from [%s] closed.", self.__address)
        get_connection_catalog().deregister(self)

    def handle(self):
        while 1:
            _logger.debug("Waiting for message from client.")
            
            try:
                message = rpipe.protocol.read_message_from_file_object(self.__ws)
            except EOFError:
                self.handle_close()
                return

            (message_info, message_obj) = message

            message_type = rpipe.protocol.get_message_type_from_info(message_info)
            message_id = rpipe.protocol.get_message_id_from_info(message_info)

            if message_type == rpipe.protocols.MT_HEARTBEAT:
                handler = self.__handle_heartbeat
            elif message_type == rpipe.protocols.MT_EVENT:
                handler = self.__handle_event
            else:
                _logger.warning("Received unhandled message (%d) [%s]. The "
                                "lack of a reply will probably be a big "
                                "problem, so we'll close the connection.", 
                                message_type, message_obj.__class__.__name__)
                return

            gevent.spawn(handler, message_type, message_id, message_obj)
#            self.__mc.hit(message_type, message_id, message_obj)

    def __send_message_primitive(self, message_obj, **kwargs):
        rpipe.protocol.send_message_obj(
            self.__ws,
            message_obj, 
            **kwargs)

# TODO(dustin): We should rename the corresponding methods in the client 
#               respective to whether they'll be waiting on a response or not, 
#               like these.
    def send_response_message(self, message_obj, **kwargs):
        self.__send_message_primitive(message_obj, **kwargs)

    def initiate_message(self, message_obj, **kwargs):
        self.__send_message_primitive(message_obj, **kwargs)
        return self.__read_message()

    def __read_message(self, **kwargs):
# TODO(dustin): We're going to need to not interfere with replies in 
#               unfinished dialogs.
        rpipe.protocol.read_message_from_file_object(
            self.__ws,
            **kwargs)

    def __handle_heartbeat(self, message_type, message_id, message_obj):
        _logger.debug("Responding to heartbeat: %s", self.__address)

        reply_message_obj = rpipe.protocol.get_obj_from_type(
                                rpipe.protocols.MT_HEARTBEAT_R)

        reply_message_obj.version = 1

        self.send_response_message(
            reply_message_obj, 
            message_id=message_id, 
            is_response=True)

    def __handle_event(self, message_type, message_id, message_obj):
        _logger.debug("Responding to event: %s", self.__address)

        _logger.info("Received event [%s] [%s].", 
                     message_obj.verb, message_obj.noun)

        event_handler_name = message_obj.noun.replace('/', '_')

        method = getattr(self.__eh, 'handle_' + event_handler_name)

        handler = functools.partial(
                    method, 
                    message_id, 
                    message_obj.verb, 
                    message_obj.data)

        gevent.spawn(handler,
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

        self.send_response_message(
            reply_message_obj, 
            message_id=message_id, 
            is_response=True)

    @property
    def socket(self):
        return self.__ws

    @property
    def address(self):
        return self.__address

    @property
    def ip(self):
        return self.__address[0]


class Server(object):
    def __init__(self):
        fq_cls_name = rpipe.config.server.CONNECTION_HANDLER_FQ_CLASS

        self.__connection_handler_cls = rpipe.utility.load_cls_from_string(
                                            fq_cls_name)

        assert issubclass(self.__connection_handler_cls, ServerConnectionHandler)

    def run(self):
        binding = (rpipe.config.server.BIND_HOSTNAME, 
                   rpipe.config.server.BIND_PORT)

        _logger.info("Running server: %s", binding)

        handler = self.__connection_handler_cls()

        server = gevent.server.StreamServer(
                    binding, 
                    handler.handle_new_connection, 
                    cert_reqs=gevent.ssl.CERT_REQUIRED,
                    keyfile=rpipe.config.server.KEY_FILEPATH,
                    certfile=rpipe.config.server.CRT_FILEPATH,
                    ca_certs=rpipe.config.server.CA_CRT_FILEPATH)

        # Wait until termination. Since there is no cleanup and everything is 
        # based on coroutines, default CTRL+BREAK and SIGTERM handling should 
        # be fine.
        server.serve_forever()

_cc = _ConnectionCatalog()

def get_connection_catalog():
    return _cc
