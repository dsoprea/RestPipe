#!/usr/bin/env python2.7

import os.path
import contextlib
import logging

import gevent
import gevent.socket
import gevent.ssl

import rpipe.config.client
import rpipe.exceptions

_logger = logging.getLogger(__name__)


class ClientConnection(object):
    def __init__(self):
        self.__ss = None
        self.__connected = False

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

        ss = gevent.ssl.wrap_socket(
                socket,
                keyfile=rpipe.config.client.KEY_FILEPATH,
                certfile=rpipe.config.client.CRT_FILEPATH)
         
        ss.connect(binding)

        self.__ss = ss

        self.__schedule_heartbeat()

    def __schedule_heartbeat(self):
        gevent.spawn_later(
            rpipe.config.client.HEARTBEAT_INTERVAL_S,
            self.__send_heartbeat)

    def close(self):
        _logger.info("Closing connection.")

        if self.__connected is False:
            raise IOError("Client not connected.")

        self.__connected = False
# TODO(dustin): This might have a problem with a broken pipe.
        self.__ss.close()

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def __send_heartbeat(self):
        _logger.debug("Sending heartbeart.")

# TODO(dustin): Finish.
# TODO(dustin): We need to spawn a heartbeat operation on a schedule. Use 
#               Greenlet.start_later. Clear self.__connected if we're 
#               disconnected.
#        raise NotImplementedError()
        self.__schedule_heartbeat()

    def write(self, data):
# TODO(dustin): We need to catch the broken-pipe exception, and translate to 
#               rpipe.exceptions.RpClientReconnectException .
        self.__ss.write(data)

    def read(self, count=rpipe.config.client.DEFAULT_READ_CHUNK_LENGTH):
# TODO(dustin): If the return is empty (''), then we'll need to emit 
#               rpipe.exceptions.RpClientReconnectException .
        return self.__ss.read(count)


def connect_gen():
    """A generator that returns connections. In a perfect world, there will 
    only be one. However, there might be more if reconnections are required.
    """

    attempts = 0
    while 1:
        try:
            with ClientConnection() as c:
                yield c
        except rpipe.exceptions.RpClientReconnectException:
            _logger.warn("We need to reconnect.")

            if rpipe.config.client.MAX_CONNECT_ATTEMPTS > 0 and \
               attempts >= rpipe.config.client.MAX_CONNECT_ATTEMPTS:
                raise IOError("We exceeded our maximum connection attempts "
                              "(%d).", 
                              rpipe.config.client.MAX_CONNECT_ATTEMPTS)

            _logger.info("Waiting (%d) seconds before reconnect (%d).",
                         rpipe.config.client.RECONNECT_DELAY_S,
                         attempts)

            gevent.sleep(rpipe.config.client.RECONNECT_DELAY_S)

            attempts += 1
            continue


class ClientManager(object):
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
            c = _ClientConnection()
            c.open()
            self.__c = c

        return self.__c
