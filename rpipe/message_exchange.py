import logging

import gevent
import gevent.queue
import gevent.select
import gevent.event

import rpipe.config.exchange
import rpipe.exceptions
import rpipe.protocol

_logger = logging.getLogger(__name__)


class ResponseTimeoutError(Exception):
    pass


class _MessageExchange(object):
    """This runs for a particular socket in its own gthread."""

    def __init__(self, ws, address):
        self.__ws = ws
        self.__address = address

        self.__incoming = gevent.queue.Queue()
        self.__outgoing = gevent.queue.Queue()

        self.__replied = {}

    def run(self):
        """Read incoming messages and write outgoing messages."""

        _logger.info("Message exchange running for connection: %s", 
                     self.__address)

        while 1:
            is_active = False
            r = gevent.select.select(
                    [self.__ws], [], [], 
                    0)

            if r[0]:
                _logger.debug("Reading message.")

                try:
                    message = rpipe.protocol.read_message_from_file_object(
                                self.__ws)
                except rpipe.exceptions.RpConnectionClosed:
                    break

                (message_info, message_obj) = message
                message_id = rpipe.protocol.get_message_id_from_info(
                                message_info)

                message_id_str = rpipe.protocol.get_string_from_message_id(
                                    message_id)

                try:
                    r = self.__replied[message_id]
                except KeyError:
                    _logger.debug("This message was a general request: %s", 
                                  message_id_str)

                    self.__incoming.put(message)
                else:
                    _logger.debug("This message was a reply: %s", 
                                  message_id_str)

                    r[1] = message
                    r[0].set()

                is_active = True

            if self.__outgoing.empty() is False:
                (message_id, message_obj) = self.__outgoing.get()
                message_id_str = rpipe.protocol.get_string_from_message_id(
                                    message_id)

                _logger.debug("Sending message: %s", message_id_str)

                try:
                    rpipe.protocol.send_message_obj(
                        self.__ws, 
                        message_obj, 
                        message_id=message_id)
                except rpipe.exceptions.RpConnectionClosed:
                    break

                is_active = True

            if is_active is False:
                gevent.sleep(rpipe.config.exchange.IDLE_TIMEOUT_S)

        # The other gthreads can determine that we've existed by checking our 
        # state.

        _logger.warning("Message-exchange terminating for [%s].", 
                        self.__address)

    def send(self, message_obj, reply_to_message_id=None, expect_response=True, **kwargs):
        if reply_to_message_id is None:
            message_id = rpipe.protocol.id_generator()
        else:
            message_id = reply_to_message_id

        self.__outgoing.put((message_id, message_obj))

        if expect_response is True:
            # Add the tracking information to track the future reply.
            self.__replied[message_id] = [gevent.event.Event(), None]

        return message_id

    def read(self, **kwargs):
        return self.__incoming.get(**kwargs)

    def wait_on_reply(self, message_id, timeout_s=None):
        r = self.__replied[message_id]
        if r[0].wait(timeout_s) is True:
            del self.__replied[message_id]
            return r[1]

        raise ResponseTimeoutError()

#    @property
#    def incoming(self):
#        return self.__incoming

#    @property
#    def outgoing(self):
#        return self.__outgoing

_instances = {}

def stop_exchange(address):
    global _instances

    _instances[address][0].kill()
    del _instances[address]

def start_exchange(ws, address):
    global _instances

    assert ws is not None

    me = _MessageExchange(ws, address)
    g = gevent.spawn(me.run)
    _instances[address] = (g, me)

    return me

def is_alive(address):
    return _instances[address][0].ready() is False

def read(address, **kwargs):
    return _instances[address][1].read(**kwargs)

def send(address, message_obj, **kwargs):
    return _instances[address][1].send(message_obj, **kwargs)

def wait_on_reply(address, message_id, **kwargs):
    return _instances[address][1].wait_on_reply(message_id, **kwargs)

def send_and_receive(address, message_obj, timeout_s=None):
    """A convenience function to send a message and wait on a reply."""

    message_id = send(address, message_obj, expect_response=True)

    message = wait_on_reply(address, message_id, timeout_s=timeout_s)
    (message_info, message_obj) = message

    return message_obj
