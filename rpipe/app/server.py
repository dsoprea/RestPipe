import logging

import web

import rpipe.config
import rpipe.config.log
import rpipe.config.server_web
import rpipe.server.connection

_logger = logging.getLogger(__name__)

web.config.debug = rpipe.config.IS_DEBUG

# Start the socket-server.
s = rpipe.server.connection.Server()
s.start()

# TODO(dustin): If we ever want to implement a graceful shutdown process:
#
#s.stop()

# Establish the web-server object.
app = web.application(
            rpipe.config.server_web.URLS, 
            globals(), 
            autoreload=rpipe.config.IS_DEBUG)
