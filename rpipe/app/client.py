import logging

import web
import gevent

import rpipe.config
import rpipe.config.client_web
import rpipe.client.connection

_logger = logging.getLogger(__name__)

web.config.debug = rpipe.config.IS_DEBUG

# Establish a connection to the server.
rpipe.client.connection.get_connection()

# Start the socket-server.
c = rpipe.client.connection.get_connection()
gevent.spawn(c.process_requests)

# Establish the web-server object.
app = web.application(
            rpipe.config.client_web.URLS, 
            globals(), 
            autoreload=rpipe.config.IS_DEBUG)
