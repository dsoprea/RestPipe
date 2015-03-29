#!/usr/bin/env python2.7

import logging
import os.path
import time

import gevent
import gevent.socket
import gevent.ssl

import rpipe.config.client
import rpipe.config.statsd
import rpipe.config.heartbeat

import rpipe.exceptions
import rpipe.protocol
import rpipe.protocols
import rpipe.connection
import rpipe.request_server
import rpipe.message_loop
import rpipe.message_exchange
import rpipe.stats

_logger = logging.getLogger(__name__)


class ClientEventHandler(object):
    pass


class HeartbeatTimeoutError(Exception):
    pass


class TestClientEventHandler(ClientEventHandler):
    def get_time(self, ctx, post_data):
        _logger.info("TEST: get_time()")
        return { 'time_from_client': time.time() }

    def get_cat(self, ctx, post_data, x, y):
        _logger.info("TEST: get_cat()")
        return { 'result_from_client': str(x) + str(y) }


class _ClientConnectionHandler(
        rpipe.connection.Connection, 
        rpipe.request_server.RequestServer):
    def __init__(self):
        self.__ws = None
        self.__connected = False

        self.__heartbeat_msg = rpipe.protocol.get_obj_from_type(
                                rpipe.protocols.MT_HEARTBEAT)

        self.__heartbeat_msg.version = 1

        self.__binding = (rpipe.config.client.TARGET_HOSTNAME, 
                          rpipe.config.client.TARGET_PORT)

    def __del__(self):
        if self.__connected is True:
            _logger.debug("Closing connection (__del__).")
            self.close()

    def open(self):
        _logger.info("Connecting to: %s", self.__binding)

        if self.__connected is True:
            raise IOError("Client already connected.")

        socket = gevent.socket.socket(
                    gevent.socket.AF_INET, 
                    gevent.socket.SOCK_STREAM)

        ss = gevent.ssl.wrap_socket(
                socket,
                keyfile=rpipe.config.client.KEY_FILEPATH,
                certfile=rpipe.config.client.CRT_FILEPATH)

        try:
            ss.connect(self.__binding)
        except gevent.socket.error:
            raise rpipe.exceptions.RpConnectionFail(str(gevent.socket.error))

        ss.settimeout(rpipe.config.protocol.WRITE_TIMEOUT_S)

        self.__ws = rpipe.protocol.SocketWrapper(ss, ss.makefile())
        self.__connected = True

        _logger.debug("Scheduling heartbeat.")
        self.__schedule_heartbeat()

    def close(self):
        _logger.info("Closing connection.")

        if self.__connected is False:
            raise rpipe.exceptions.RpConnectionClosed("Client no longer connected.")

        self.__connected = False

        try:
            self.__ws.close()
        except:
            _logger.exception("Error while closing socket. Ignoring.")

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, type, value, traceback):
        _logger.debug("Closing connection (__exit__).")
        self.close()

    def __schedule_heartbeat(self):
        _logger.debug("Scheduling heartbeat: (%d) seconds", 
                      rpipe.config.heartbeat.HEARTBEAT_INTERVAL_S)

        g = gevent.spawn_later(
                rpipe.config.heartbeat.HEARTBEAT_INTERVAL_S,
                self.__send_heartbeat)

        def heartbeat_die_cb(hb_g):
            _logger.error("The heartbeat gthread exceptioned-out. Killing "
                          "connection-handler gthread.")

            self.close()

        g.link_exception(heartbeat_die_cb)

    def __send_heartbeat(self):
        _logger.debug("Sending heartbeart.")

        with rpipe.stats.time_and_post(
                rpipe.config.statsd.EVENT_CONNECTION_CLIENT_HEARTBEAT_TIMING):
            try:
                self.initiate_message(
                    self.__heartbeat_msg,
                    rpipe.config.heartbeat.HEARTBEAT_TIMEOUT_S)
            except rpipe.message_exchange.ResponseTimeoutError:
                raise HeartbeatTimeoutError()

        _logger.debug("Heartbeat response received.")

        self.__schedule_heartbeat()

    def initiate_message(self, message_obj, timeout_s=None):
        # This only works because the CommonMessageLoop has already been 
        # started and has registered the other participant with the 
        # MessageExchange.

        rpipe.stats.post_to_counter(
            rpipe.config.statsd.EVENT_CONNECTION_SEND_TICK)

        with rpipe.stats.time_and_post(
                rpipe.config.statsd.EVENT_CONNECTION_SEND_TIMING):
            return rpipe.message_exchange.send_and_receive(
                    self.__binding, 
                    message_obj,
                    timeout_s=timeout_s)

    def process_requests(self):
        assert self.__ws is not None
        assert self.__connected is True

        try:
            event_handler_cls = rpipe.utility.load_cls_from_string(
                                    rpipe.config.client.EVENT_HANDLER_FQ_CLASS)

            assert issubclass(event_handler_cls, ClientEventHandler) is True

            eh = event_handler_cls()
            ctx = rpipe.message_loop.CONNECTION_CONTEXT_T(self.__binding)
            cml = rpipe.message_loop.CommonMessageLoop(self.__ws, eh, ctx)

            cml.handle()
        finally:
            # The message-loop has terminated (either purposely or via 
            # exception). Make sure we close the connection (thereby 
            # disqualifying it for reuse).
            self.close()

    @property
    def connected(self):
        return self.__connected


class _ClientManager(object):
    """Establish a connection, and recall it from one invocation to the next. 
    It will be reconnected as needed.
    """

    def __init__(self):
        self.__c = None

    def __del__(self):
        if self.__c is not None:
            del self.__c

    @property
    def connection(self):
        if self.__c is None or self.__c.connected is False:
            _logger.info("Establishing new connection.")
            c = _ClientConnectionHandler()
            c.open()
            self.__c = c
        else:
            _logger.debug("Reusing connection.")

        return self.__c

_cm = _ClientManager()

def get_connection():
    return _cm.connection
