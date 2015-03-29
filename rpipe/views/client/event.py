import logging
import json
import web

import rpipe.config.web_server
import rpipe.event
import rpipe.client_connection

_logger = logging.getLogger(__name__)

_CT_JSON = 'application/json'


class EventClient(object):
    def handle(self, verb, noun):
        _logger.info("Client received request, to be sent to server: [%s] "
                     "[%s]", verb, noun)

        c = rpipe.client_connection.get_connection()
        mimetype = web.ctx.env.get('CONTENT_TYPE')

        r = rpipe.event.emit(c, verb, noun, web.data(), mimetype)
        (code, mimetype, data) = r

        web.header(rpipe.config.web_server.HEADER_EVENT_RETURN_CODE, code)

        if mimetype is not None:
            web.header('Content-Type', mimetype)

        return data

    def GET(self, *args):
        return self.handle('get', *args)

    def POST(self, *args):
        return self.handle('post', *args)

    def PUT(self, *args):
        return self.handle('put', *args)

    def DELETE(self, *args):
        return self.handle('delete', *args)

    def PATCH(self, *args):
        return self.handle('patch', *args)
