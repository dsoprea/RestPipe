import gevent
import time
import Queue
import logging

import rpipe.config.protocol

_logger = logging.getLogger(__name__)


class _MessageWatch(object):
    """A convenience object to wait it easy to wait for messages."""

    def __init__(self, wait_function):
        self.__wait_function = wait_function

    @property
    def wait(self):
        return self.__wait_function


class MessageCatalog(object):
    """A class that can route incoming messages based on either expected 
    message-ID (responses have the same ID as the original message) or message-
    type.
    """

# TODO(dustin): All of these methods need to be threadsafe.
    def __init__(self):
        self.__response_handlers = {}
        self.__response_watches = set()
        self.__response_watches_received = {}

        self.__type_handlers = {}
        self.__type_watches_received = {}

    def register_response_handler(self, message_id, cb):
        """Register a callback to be asynchronously invoked when a particular 
        message is received. These will be removed immediately upon receipt, 
        just before the CB is called.
        """

        if message_id not in self.__response_handlers:
            self.__response_handlers[message_id] = [cb]
        else:
            self.__response_handlers[message_id].append(cb)

    def register_response_watch(self, message_id):
        """Indicate that the given message will be received but not removed 
        when received until picked-up by a watch loop.
        """

        self.__response_watches.add(message_id)

        wait_function = functools.partial(wait_on_response_watch, message_id)
        return _MessageWatch(wait_function)

    def register_type_handler(self, message_type, cb):
        """Register a callback to be asynchronously invoked when a message of
        a particular message-type is received. Messages will only be 
        encountered here if not already matched as a response.
        """

        if message_type not in self.__response_handlers:
            self.__type_handlers[message_type] = [cb]
        else:
            self.__type_handlers[message_type].append(cb)

    def register_type_watch(self, message_type):
        """Indicate that the given message will be received but not removed 
        when received until picked-up by a watch loop.
        """

        if message_type not in self.__type_watches_received:
            self.__type_watches_received[message_type] = Queue.Queue()

        wait_function = functools.partial(wait_on_type_watch, message_type)
        return _MessageWatch(wait_function)

    def wait_on_response_watch(
            self, 
            message_id, 
            timeout_s=rpipe.config.protocol.DEFAULT_WATCH_WAIT_TIMEOUT_S):
        start_at = time.time()
        while timeout_s is None or (time.time() - start_at) < timeout_s:
            if message_id in self.__response_watches_received:
                message_obj = self.__response_watches_received[message_id]
                del self.__response_watches_received[message_id]
                return message_obj

            gevent.sleep(rpipe.config.protocol.WATCH_LOOP_INTERVAL_S)

        # We'll explicitly say it.
        return None

    def wait_on_type_watch(
            self, 
            message_type, 
            timeout_s=rpipe.config.protocol.DEFAULT_WATCH_WAIT_TIMEOUT_S):
        start_at = time.time()
        while timeout_s is None or (time.time() - start_at) < timeout_s:
            if not self.__type_watches_received[message_type].empty():
                return self.__type_watches_received[message_type].get()

            gevent.sleep(rpipe.config.protocol.WATCH_LOOP_INTERVAL_S)

        # We'll explicitly say it.
        return None

    def __hit(self, message_type, message_id, message_obj):
        """Store a received message (in another gthread)."""

        message_meta = (message_type, message_id)

        handled = False

        # Match as message-type.

        try:
            cb_list = self.__type_handlers[message_type]
        except KeyError:
            pass
        else:
            map(lambda cb: cb(message_meta, message_obj), cb_list)
            handled = True

        if message_type in self.__type_watches_received:
            self.__type_watches_received[message_type].put(message_obj)
            handled = True

        # Match as response.

        try:
            cb = self.__response_handlers[message_id]
        except KeyError:
            pass
        else:
            del self.__response_handlers[message_id]
            cb(message_meta, message_obj)
            handled = True

        if message_id in self.__response_watches:
            self.__response_watches.remove(message_id)
            self.__response_watches_received[message_id] = message_obj
            handled = True

        if handled is True:
            _logger.debug("Message handled.")
        else:
            _logger.warning("Message was not handled.")

    def hit(self, message_type, message_id, message_obj):
        """Process a received message in another gthread."""

        _logger.debug("Spawning handler for received message.")

# TODO(dustin): We don't have to clean this up, right?
        gevent.spawn(self.__hit, message_type, message_id, message_obj)

_mc = MessageCatalog()

def get_catalog():
    return _mc
