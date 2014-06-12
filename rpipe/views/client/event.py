import logging
import json
import web

import rpipe.config.web_server
import rpipe.event
import rpipe.client.connection

_logger = logging.getLogger(__name__)


class EventClient(object):
    def handle(self, verb, noun):
        _logger.info("Client received request, to be sent to server: [%s] "
                     "[%s]", verb, noun)

        c = rpipe.client.connection.get_connection()
        (code, mimetype, data) = rpipe.event.emit(c, verb, noun, web.data())

        web.header(rpipe.config.web_server.HEADER_EVENT_RETURN_CODE, code)

        if mimetype is not None:
            web.header('Content-Type', mimetype)

        return data

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
