import logging
import functools

import web

import rpipe.config.web_server
import rpipe.server.exceptions
import rpipe.event
import rpipe.server.connection
import rpipe.utility
import rpipe.server.hostname_resolver

_logger = logging.getLogger(__name__)


class EventServer(object):
    def __init__(self, *args, **kwargs):
        super(EventServer, self).__init__(*args, **kwargs)

        self.__cc = rpipe.server.connection.get_connection_catalog()

        hostname_resolver_cls = rpipe.utility.load_cls_from_string(
                                   rpipe.config.server.\
                                        CLIENT_HOSTNAME_RESOLVER_CLS)

        assert issubclass(
                hostname_resolver_cls, 
                rpipe.server.hostname_resolver.HostnameResolver)

        self.__resolver = hostname_resolver_cls()

    def handle(self, verb, hostname, noun):
        _logger.info("Server received request, to be sent to client [%s]: "
                     "[%s] [%s]", hostname, verb, noun)

        try:
# TODO(dustin): Only do this if the hostname is not already an IP.
            ip = self.__resolver.lookup(hostname)
        except LookupError:
            raise web.HTTPError('404 Hostname not resolvable')
        except:
            _logger.exception("Could not resolve hostname: [%s]", 
                              hostname)
            raise web.HTTPError('500 Hostname resolution error')
        else:
            _logger.debug("Resolved client hostname [%s]: [%s]", hostname, ip)

        try:
            c = self.__cc.wait_for_connection(ip)
        except rpipe.server.exceptions.RpNoConnectionException:
            raise web.HTTPError('503 Client connection unavailable')            

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
