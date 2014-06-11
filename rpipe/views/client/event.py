import logging
import functools
import web

import rpipe.event

_logger = logging.getLogger(__name__)


class EventClient(object):
    def handle(self, verb, noun):
        _logger.info("Received [%s] request: %s", verb, noun)
        return rpipe.event.emit(verb, noun, web.data())

    def GET(self, path):
        return self.handle('get', path)

    def POST(self, path):
        return self.handle('post', path)

    def PUT(self, path):
        return self.handle('put', path)

    def DELETE(self, path):
        return self.handle('delete', path)

    def PATCH(self, path):
        return self.handle('patch', path)
