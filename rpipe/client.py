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

_logger = logging.getLogger(__name__)


class _ClientConnection(object):
    def __init__(self):
        self.__ws = None
        self.__connected = False

        self.__heartbeat_msg = rpipe.protocol.get_obj_from_type(
                                rpipe.protocols.MT_HEARTBEAT)

        self.__heartbeat_msg.version = 1

    def __del__(self):
        if self.__connected is True:
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
         
        ss.connect(binding)

        self.__ws = rpipe.protocol.SocketWrapper(ss.makefile())

        _logger.debug("Scheduling heartbeat.")
        self.__schedule_heartbeat()

    def close(self):
        _logger.info("Closing connection.")

        if self.__connected is False:
            raise IOError("Client not connected.")

        self.__connected = False
# TODO(dustin): This might have a problem with a broken pipe.
        self.__ws.close()

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def __schedule_heartbeat(self):
        _logger.debug("Scheduling heartbeat: (%d) seconds", 
                      rpipe.config.client.HEARTBEAT_INTERVAL_S)

        gevent.spawn_later(
            rpipe.config.client.HEARTBEAT_INTERVAL_S,
            self.__send_heartbeat)

    def __send_heartbeat(self):
        _logger.debug("Sending heartbeart.")

        try:
            self.send_message(self.__heartbeat_msg)
        except EOFError:
            raise
        except:
# TODO(dustin): We might have some tolerance. Though it's an AssertionError,
#               it might allow a momentary wait. We might not have to do 
#               anything
# TODO(dustin): We prefer this rather than a lock that might silently lock 
#               everything up. However, we can avoid this problem by creating 
#               an outbound queue, and a "send" gthread.
            _logger.exception("Could not send heartbeat. The socket might be "
                              "blocked by another gthread. Since this wasn't "
                              "an EOFError (broken pipe), we'll just skip "
                              "this heartbeat.")
        else:
            _logger.debug("Heart response received.")

        self.__schedule_heartbeat()

    def send_message(self, message_obj):
        message_id = rpipe.protocol.send_message_obj(self.__ws, message_obj)

# TODO(dustin): We need to make sure that we wait on just the heartbeat response.
        message = rpipe.protocol.read_message_from_file_object(self.__ws)
        (message_info, message_obj) = message

        return message_obj

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
#            with _ClientConnection() as c:
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
            c = _ClientConnection()
            c.open()
            self.__c = c
        else:
            _logger.debug("Reusing connection.")

        return self.__c

_cm = _ClientManager()

def get_connection():
    return _cm.connection
