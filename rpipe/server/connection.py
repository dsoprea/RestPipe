#!/usr/bin/env python2.7

import os.path
import logging
import time
import socket

import gevent
import gevent.server
import gevent.ssl

import rpipe.config.server
import rpipe.server.exceptions
import rpipe.utility
import rpipe.protocol
import rpipe.connection
import rpipe.request_server
import rpipe.message_loop

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
        event_handler_cls = rpipe.utility.load_cls_from_string(
                                rpipe.config.server.EVENT_HANDLER_FQ_CLASS)

        eh = event_handler_cls(self)
        ctx = rpipe.message_loop.CONNECTION_CONTEXT_T(self.__address)
        cml = rpipe.message_loop.CommonMessageLoop(self.__ws, eh, ctx)

        try:
            cml.handle(exit_on_unknown=True)
        finally:
            self.handle_close()

    @property
    def socket(self):
        return self.__ws

    @property
    def address(self):
        return self.__address

    @property
    def ip(self):
        return self.__address[0]


class Server(rpipe.request_server.RequestServer):
    def __init__(self):
        fq_cls_name = rpipe.config.server.CONNECTION_HANDLER_FQ_CLASS

        self.__connection_handler_cls = rpipe.utility.load_cls_from_string(
                                            fq_cls_name)

        assert issubclass(self.__connection_handler_cls, ServerConnectionHandler)

    def process_requests(self):
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

        # Wait until termination. Generally, we should already be running in 
        # its own gthread. 
        #
        # Since there is no cleanup and everything is based on coroutines, 
        # default CTRL+BREAK and SIGTERM handling should be fine.
        server.serve_forever()

_cc = _ConnectionCatalog()

def get_connection_catalog():
    return _cc