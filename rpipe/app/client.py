import sys
import logging
import time
import json

import web
import gevent

import rpipe.config
import rpipe.config.client_web
import rpipe.config.statsd
import rpipe.stats
import rpipe.exceptions
import rpipe.client.connection
import rpipe.utility

_logger = logging.getLogger(__name__)

web.config.debug = rpipe.config.IS_DEBUG

def connection_cycle():
    state_change_event_cls = rpipe.utility.load_cls_from_string(
                                rpipe.config.client.\
                                    CONNECTION_STATE_CHANGE_EVENT_CLASS)

    sce = state_change_event_cls()

    while 1:
        rpipe.stats.post_to_counter(
            rpipe.config.statsd.EVENT_CONNECTION_CLIENT_NEW_TICK)

        # If we get disconnected, we'll continually reconnect.
        try:
            _logger.info("Reattempting connection to server.")

            # Establish a connection to the server.
            with rpipe.stats.time_and_post(
                    rpipe.config.statsd.\
                        EVENT_CONNECTION_CLIENT_HEARTBEAT_TIMING,
                    success_event=\
                        rpipe.config.statsd.\
                            EVENT_CONNECTION_CLIENT_HEARTBEAT_SUCCESS_TICK,
                    fail_event=\
                        rpipe.config.statsd.\
                            EVENT_CONNECTION_CLIENT_HEARTBEAT_FAIL_TICK):
                last_attempt = time.time()
                c = rpipe.client.connection.get_connection()

            rpipe.stats.post_to_counter(
                rpipe.config.statsd.EVENT_CONNECTION_CLIENT_CONNECTED_TICK)

            sce.connect_success()

            # Start the local socket-server.
            c.process_requests()
        except rpipe.exceptions.RpConnectionRetry:
            _logger.exception("Connection has broken and will be "
                              "reattempted.")

            sce.connect_fail()

            rpipe.stats.post_to_counter(
                rpipe.config.statsd.EVENT_CONNECTION_CLIENT_BROKEN_TICK)

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
