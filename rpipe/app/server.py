import logging

import web

import rpipe.config
import rpipe.config.server_web

_logger = logging.getLogger(__name__)

web.config.debug = rpipe.config.IS_DEBUG

app = web.application(
            rpipe.config.server_web.URLS, 
            globals(), 
            autoreload=rpipe.config.IS_DEBUG)
