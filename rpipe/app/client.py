import sys
import logging
import time
import json

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

            # Start the local socket-server.
            c.process_requests()
        except rpipe.exceptions.RpConnectionRetry:
            _logger.exception("Connection has broken and will be "
                              "reattempted.")

            time_since_attempt_s = (time.time() - last_attempt)
            wait_time_s = \
                rpipe.config.client.\
                    MINIMAL_CONNECTION_FAIL_REATTEMPT_WAIT_TIME_S - \
                time_since_attempt_s

            if wait_time_s > 0:
                _logger.info("Waiting for (%d) seconds before reconnect.", 
                             wait_time_s)

                gevent.sleep(wait_time_s)

def client_socket_server_killed_cb(g):
# TODO(dustin): We need to signal the web-server to die, here.
#    gevent.kill(main)
    pass

g = gevent.spawn(connection_cycle)
g.link(client_socket_server_killed_cb)

# Establish the web-server object.
app = web.application(
            rpipe.config.client_web.URLS, 
            globals(), 
            autoreload=rpipe.config.IS_DEBUG)

#def handle_wrap(handler):
#    if web.ctx.env.get('CONTENT_TYPE') == 'application/json':
#        web.ctx.json = json.loads(web.data())
#
#    try:
#        result = handler()
#    except Exception as e:
#        raise
#
#    if issubclass(result.__class__, (basestring, types.GeneratorType)) is True:
#        return result
#    else:
#        web.header('Content-type', 'application/json')
#        return json.dumps(result)
#
#app.add_processor(handle_wrap)
