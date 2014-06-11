import logging
import functools
import web

import rpipe.event
import rpipe.client.connection

_logger = logging.getLogger(__name__)


class EventClient(object):
    def handle(self, verb, noun):
        _logger.info("Client received request, to be sent to server: [%s] "
                     "[%s]", verb, noun)

        c = rpipe.client.connection.get_connection()
        return rpipe.event.emit(c, verb, noun, web.data())

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
