#!/usr/bin/env python2.7

import os.path
import contextlib
import logging

import gevent
import gevent.socket
import gevent.ssl

import rpipe.config.client
import rpipe.exceptions
import rpipe.protocol
import rpipe.protocols
import rpipe.connection
import rpipe.request_server
import rpipe.message_loop
import rpipe.message_exchange

_logger = logging.getLogger(__name__)


class DefaultClientEventHandler(object):
    def __init__(self, client_connection_handler):
        self.__client_connection_handler = client_connection_handler

    @property
    def cch(self):
        return self.__client_connection_handler


class _ClientConnectionHandler(
        rpipe.connection.Connection, 
        rpipe.request_server.RequestServer):
    def __init__(self):
        self.__ws = None
        self.__connected = False

        self.__heartbeat_msg = rpipe.protocol.get_obj_from_type(
                                rpipe.protocols.MT_HEARTBEAT)

        self.__heartbeat_msg.version = 1

        self.__ctx = rpipe.message_loop.CONNECTION_CONTEXT_T(None)

    def __del__(self):
        if self.__connected is True:
            _logger.debug("Closing connection (__del__).")
            self.close()

    def open(self):
        binding = (rpipe.config.client.TARGET_HOSTNAME, 
                   rpipe.config.client.TARGET_PORT)

        _logger.info("Connecting to: %s", binding)

        if self.__connected is True:
            raise IOError("Client already connected.")

        socket = gevent.socket.socket(
                    gevent.socket.AF_INET, 
                    gevent.socket.SOCK_STREAM)

#        print("Socket:\n%s" % (dir(socket)))

        ss = gevent.ssl.wrap_socket(
                socket,
                keyfile=rpipe.config.client.KEY_FILEPATH,
                certfile=rpipe.config.client.CRT_FILEPATH)

#        print("SSL:\n%s" % (dir(ss)))

        try:
            ss.connect(binding)
        except gevent.socket.error:
            raise rpipe.exceptions.RpConnectionFail(str(gevent.socket.error))

        self.__ws = rpipe.protocol.SocketWrapper(ss.makefile())
        self.__connected = True

# We can't read or write on the socket simultaneously. This will require some 
# thought, and a heartbeat is redundant and unnecessary (except saving a second 
# when we occasionally have to reconnect a broken pipe).
#        _logger.debug("Scheduling heartbeat.")
#        self.__schedule_heartbeat()

    def close(self):
        _logger.info("Closing connection.")

        if self.__connected is False:
            raise IOError("Client not connected.")

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

#    def __schedule_heartbeat(self):
#        _logger.debug("Scheduling heartbeat: (%d) seconds", 
#                      rpipe.config.client.HEARTBEAT_INTERVAL_S)
#
#        g = gevent.spawn_later(
#                rpipe.config.client.HEARTBEAT_INTERVAL_S,
#                self.__send_heartbeat)
#
#        def heartbeat_die_cb(hb_g):
#            _logger.error("The heartbeat gthread exceptioned-out. Killing "
#                          "connection-handler gthread.")
#
#            self.close()
#            gevent.kill(gevent.getcurrent())
#
#        g.link_exception(heartbeat_die_cb)
#
#    def __send_heartbeat(self):
#        _logger.debug("Sending heartbeart.")
#
#        try:
#            self.initiate_message(self.__heartbeat_msg)
#        except EOFError:
#            raise
#        except:
## TODO(dustin): We might have some tolerance. Though it's an AssertionError,
##               it might allow a momentary wait. We might not have to do 
##               anything
## TODO(dustin): We prefer this rather than a lock that might silently lock 
##               everything up. However, we can avoid this problem by creating 
##               an outbound queue, and a "send" gthread.
#            _logger.exception("Could not send heartbeat. The socket might be "
#                              "blocked by another gthread. Since this wasn't "
#                              "an EOFError (broken pipe), we'll just skip "
#                              "this heartbeat.")
#        else:
#            _logger.debug("Heartbeat response received.")
#
#        self.__schedule_heartbeat()

    def initiate_message(self, message_obj, **kwargs):
        message_id = rpipe.message_exchange.send(
                        self.__ctx.client_address, 
                        message_obj, 
                        expect_response=True)

        message = rpipe.message_exchange.wait_on_reply(
                    self.__ctx.client_address, 
                    message_id)

        (message_info, message_obj) = message

        return message_obj

    def process_requests(self):
        try:
            event_handler_cls = rpipe.utility.load_cls_from_string(
                                    rpipe.config.client.EVENT_HANDLER_FQ_CLASS)

            eh = event_handler_cls(self)
            cml = rpipe.message_loop.CommonMessageLoop(self.__ws, eh, self.__ctx)

            cml.handle()
        finally:
            # The message-loop has terminated (either purposely or via 
            # exception). Make sure we close the connection (thereby 
            # disqualifying it for reuse).
            self.close()

    @property
    def connected(self):
        return self.__connected

#def connect_gen():
#    """A generator that returns connections. In a perfect world, there will 
#    only be one. However, there might be more if reconnections are required.
#    """
#
#    attempts = 0
#    while 1:
#        try:
#            with _ClientConnectionHandler() as c:
#                yield c
#        except rpipe.exceptions.RpClientReconnectException:
#            _logger.warn("We need to reconnect.")
#
#            if rpipe.config.client.MAX_CONNECT_ATTEMPTS > 0 and \
#               attempts >= rpipe.config.client.MAX_CONNECT_ATTEMPTS:
#                raise IOError("We exceeded our maximum connection attempts "
#                              "(%d).", 
#                              rpipe.config.client.MAX_CONNECT_ATTEMPTS)
#
#            _logger.info("Waiting (%d) seconds before reconnect (%d).",
#                         rpipe.config.client.RECONNECT_DELAY_S,
#                         attempts)
#
#            gevent.sleep(rpipe.config.client.RECONNECT_DELAY_S)
#
#            attempts += 1
#            continue


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
# TODO(dustin): As long as we can keep the EOFError's from interrupting the 
#               process, this should keep us connected. We might have to wrap
#               the read/write method in SocketWrapper to automatically connect 
#               and retry if we get EOF.
        if self.__c is None or self.__c.connected is False:
            _logger.debug("Establishing connection.")
            c = _ClientConnectionHandler()
            c.open()
            self.__c = c
        else:
            _logger.debug("Reusing connection.")

        return self.__c

_cm = _ClientManager()

def get_connection():
    return _cm.connection
