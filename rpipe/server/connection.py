#!/usr/bin/env python2.7

import logging
import os.path
import time
import socket
import datetime

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


class ServerEventHandler(object):
    def start_hook(self):
        """Called after a connection has been established and before we start 
        the CML.
        """

        pass

    def stop_hook(self):
        """Called after a connection has been closed and the CML has been 
        stopped."""

        pass


class TestServerEventHandler(ServerEventHandler):
    """Example server event-handler."""

    def get_time(self, ctx, post_data):
        _logger.info("TEST: get_time()")
        return { 'time_from_server': time.time() }

    def get_cat(self, ctx, post_data, x, y):
        _logger.info("TEST: get_cat()")
        return { 'result_from_server': str(x) + str(y) }


class _ConnectionCatalog(object):
    """Keep track of connections and their IPs. This is the principle reason 
    that no two clients can connect from the same host.
    """

    def __init__(self):
        self.__connections = {}

        event_class_name = rpipe.config.server.\
                                CONNECTION_STATE_CHANGE_EVENT_CLASS

        _logger.debug("Server event handler: [%s]", event_class_name)

        cls = rpipe.utility.load_cls_from_string(event_class_name)

        self.__server_events = cls()

        self.__monitor_running = False
        self.__monitor_g = None

        self.__start_monitor()

    def __start_monitor(self):
        assert self.__monitor_running is False, \
               "The monitor is already running."

        _logger.info("Starting idleness monitor.")

        self.__monitor_running = True

        self.__monitor_g = gevent.spawn(self.__idleness_monitor)

    def __stop_monitor(self):
        if self.__monitor_running is False:
            return

        _logger.info("Stopping idleness monitor.")

        self.__monitor_running = False

        self.__monitor_g.kill()
        self.__monitor_g.join()

    def __idleness_monitor(self):
        """This runs while we're not hosting any connections."""

        waiting_since_dt = datetime.datetime.now()

        while 1:
            duration_s = (datetime.datetime.now() - 
                          waiting_since_dt).total_seconds()

            self.__server_events.idle(waiting_since_dt, duration_s)

            gevent.sleep(60)

    def register(self, c):
        # A client might've disconnected and reconnected, and we'll very likely 
        # not notice the broken connection before receiving the new one. 
        # However, since our catalog is keyed by the IP of the client, we could 
        # replace the old connection with the new one but shoot ourselves in 
        # the foot by then removing the new connection when we *do* try to 
        # cleanup the old connection. So, we'll just have to throw an exception 
        # on the new exception (and, theoretically, all repeated, future 
        # attempts) until the old connection gets cleaned-up.
        #
        # Note that this only works if the client system correctly fails the 
        # heartbeats, terminates the connection, and tries again (which it 
        # does).

        if c in self.__connections:
            _logger.error("The incoming connection is redundant and will be "
                          "closed: [%s]", c)

            try:
                c.close()
            except:
                _logger.exception("We tried to close the redundant connection, "
                                  "but there was a problem: [%s]", c)

            raise ValueError("Can not register already-registered connection. "
                             "A previous connection from this client might "
                             "not've been deregistered [properly]: %s" % 
                             (c.ip))

        _logger.debug("Registering client: [%s]", c.ip)

        # These are actually indexed by address (so we can find it either 
        # with a conneciton object -or- an address).
        self.__connections[c] = c

        self.__stop_monitor()

        self.__server_events.connection_added(c.ip, len(self.__connections))

    def deregister(self, c):
        if c not in self.__connections:
            raise ValueError("Can not deregister unregistered connection: %s" %
                             (c.ip))

        _logger.debug("Deregistering client: [%s]", c.ip)
        del self.__connections[c]

        self.__server_events.connection_removed(c.ip, len(self.__connections))

        if not self.__connections:
            self.__start_monitor()

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
# TODO(dustin): This works great, but we need the same thing on the client side 
#               (requests on the client need to block until reconnected).
        stop_at = time.time() + timeout_s
        while time.time() <= stop_at:
            try:
                return self.__connections[ip]
            except KeyError:
                pass

            gevent.sleep(1)

        raise rpipe.server.exceptions.RpNoConnectionException(ip)


class _ServerConnectionHandler(rpipe.connection.Connection):
    """Represents a single client connection."""

    def __init__(self, *args, **kwargs):
        super(_ServerConnectionHandler, self).__init__(*args, **kwargs)

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

    def close(self):
        self.__ws.close()

    def handle_new_connection(self, socket, address):
        """We've received a new connection."""

        self.__ws = rpipe.protocol.SocketWrapper(socket, socket.makefile())
        self.__address = address
        self.__ctx = rpipe.message_loop.CONNECTION_CONTEXT_T(self.__address)

        get_connection_catalog().register(self)

        event_handler_cls = rpipe.utility.load_cls_from_string(
                                rpipe.config.server.EVENT_HANDLER_FQ_CLASS)

        assert issubclass(event_handler_cls, ServerEventHandler) is True

        eh = event_handler_cls()

        _logger.debug("Calling start-hook: [%s]", self.__address)
        eh.start_hook()
        self.handle(eh)

        _logger.debug("Calling stop-hook: [%s]", self.__address)
        eh.stop_hook()

    def handle_close(self):
        _logger.info("Connection from [%s] closed.", self.__address)
        get_connection_catalog().deregister(self)

    def handle(self, event_handler):
        cml = rpipe.message_loop.CommonMessageLoop(
                self.__ws, 
                event_handler, 
                self.__ctx, 
                watch_heartbeats=True)

        _logger.debug("Common message-loop running.")

        try:
            cml.handle(exit_on_unknown=True)
        finally:
            self.handle_close()

            _logger.warning("Common message-loop ended.")

    def initiate_message(self, message_obj, **kwargs):
        # This only works because the CommonMessageLoop has already registered 
        # the other participant with the MessageExchange.
        return rpipe.message_exchange.send_and_receive(self.__address, message_obj)

    @property
    def socket(self):
        return self.__ws

    @property
    def address(self):
        return self.__address

    @property
    def ip(self):
        return self.__address[0]

_cc = _ConnectionCatalog()

def get_connection_catalog():
    return _cc


class Server(rpipe.request_server.RequestServer):
    """Wait for incoming client-connections. This is forked at the top of the 
    application.
    """

    def __init__(self):
        self.__g = None

    def start(self):
        self.__g = gevent.spawn(self.process_requests)

    def stop(self):
        self.__g.kill()
        self.__g.join()

    def process_requests(self):
        binding = (rpipe.config.server.BIND_IP, 
                   rpipe.config.server.BIND_PORT)

        _logger.info("Running server: %s", binding)

        handler = _ServerConnectionHandler()

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
