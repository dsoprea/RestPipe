import logging

import web

import rpipe.config
import rpipe.config.client_web

_logger = logging.getLogger(__name__)

web.config.debug = rpipe.config.IS_DEBUG

app = web.application(
            rpipe.config.client_web.URLS, 
            globals(), 
            autoreload=rpipe.config.IS_DEBUG)
