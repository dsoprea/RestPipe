import sys
import logging
import time

import web
import gevent

import rpipe.config
import rpipe.config.client_web
import rpipe.exceptions
import rpipe.client.connection

_logger = logging.getLogger(__name__)

web.config.debug = rpipe.config.IS_DEBUG

def connection_cycle():
    while 1:
        # If we get disconnected, we'll continually reconnect.
        try:
            _logger.info("Reattempting connection to server.")

            # Establish a connection to the server.
            last_attempt = time.time()
            c = rpipe.client.connection.get_connection()

# TODO(dustin): Make sure that we can tolerate non-connectivity from the very 
#               beginning (and just reconnect when we can).
            # Start the local socket-server.
            c.process_requests()
        except rpipe.exceptions.RpConnectionRetry:
            _logger.exception("Connection has broken and will be "
                              "reattempted.")

            time_since_attempt_s = (time.time() - last_attempt)
            wait_time_s = \
                rpipe.config.client_web.\
                    MINIMAL_CONNECTION_FAIL_REATTEMPT_WAIT_TIME_S - \
                time_since_attempt_s

            if wait_time_s > 0:
                _logger.info("Waiting for (%d) seconds before reconnect.", 
                             wait_time_s)

                gevent.sleep(wait_time_s)

def client_socket_server_killed_cb(g):
    _logger.error("The client socket-server is terminated. Stopping app.")
# TODO(dustin): We need to signal the web-server to die, here.
#    gevent.kill(main)

g = gevent.spawn(connection_cycle)
g.link(client_socket_server_killed_cb)

# Establish the web-server object.
app = web.application(
            rpipe.config.client_web.URLS, 
            globals(), 
            autoreload=rpipe.config.IS_DEBUG)
